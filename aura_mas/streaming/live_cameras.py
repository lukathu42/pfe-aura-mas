"""Configuration-driven live cameras with credential-safe health reporting."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

import cv2

from aura_mas.streaming.stream_server import LiveStreamServer, StreamRegistry

log = logging.getLogger("aura.live")
ALLOWED_SCHEMES = {"rtsp", "rtsps", "http", "https"}
CAMERA_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def redact_url(value: str) -> str:
    """Remove URL user-info and query values before logging an arbitrary value."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            return "[redacted-source]"
        host = parsed.hostname or ""
        if parsed.port:
            host += f":{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    except (ValueError, TypeError):
        return "[redacted-source]"


def load_camera_config(path: Path, environ: Optional[Dict[str, str]] = None) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text())
    if raw.get("schema_version") != 1 or not isinstance(raw.get("cameras"), list):
        raise ValueError("live camera config must use schema_version 1 and contain cameras")
    env = os.environ if environ is None else environ
    cameras = []
    seen = set()
    for item in raw["cameras"]:
        camera_id, source_env = item.get("id"), item.get("source_env")
        if not isinstance(camera_id, str) or not CAMERA_ID_RE.fullmatch(camera_id):
            raise ValueError("camera id must contain only letters, numbers, '_' or '-'")
        if camera_id in seen:
            raise ValueError(f"duplicate camera id: {camera_id}")
        if not isinstance(source_env, str) or source_env not in env:
            raise ValueError(f"source environment variable is not set for {camera_id}")
        source = env[source_env]
        if urlsplit(source).scheme.lower() not in ALLOWED_SCHEMES:
            raise ValueError(f"unsupported source scheme for {camera_id}")
        seen.add(camera_id)
        cameras.append({
            "id": camera_id,
            "label": str(item.get("label") or camera_id),
            "source": source,
            "physical_zone_id": item.get("physical_zone_id"),
            "stale_after_seconds": max(0.5, float(item.get("stale_after_seconds", 5))),
            "initial_backoff_seconds": max(0.05, float(item.get("initial_backoff_seconds", 0.5))),
            "max_backoff_seconds": max(0.1, float(item.get("max_backoff_seconds", 30))),
        })
    return cameras


@dataclass
class CameraHealth:
    id: str
    label: str
    state: str = "CONNECTING"
    last_frame_at: Optional[float] = None
    last_error: Optional[str] = None
    reconnect_attempts: int = 0


@dataclass(frozen=True)
class BufferedFrame:
    sequence: int
    captured_at: float
    jpeg: bytes


class FrameRingBuffer:
    """Thirty seconds bounds private non-event footage retained in memory."""

    def __init__(self, retention_seconds: float = 30, max_frames: int = 450) -> None:
        if retention_seconds <= 0 or max_frames <= 0:
            raise ValueError("ring buffer bounds must be positive")
        self.retention_seconds = retention_seconds
        self._frames: deque[BufferedFrame] = deque(maxlen=max_frames)
        self._lock = threading.Lock()

    def append(self, sequence: int, captured_at: float, jpeg: bytes) -> None:
        with self._lock:
            self._frames.append(BufferedFrame(sequence, captured_at, jpeg))
            cutoff = captured_at - self.retention_seconds
            while self._frames and self._frames[0].captured_at < cutoff:
                self._frames.popleft()

    def snapshot(self) -> list[BufferedFrame]:
        with self._lock:
            return list(self._frames)

    def incident_clip(
        self, first_event_at: float, last_event_at: float,
        pre_event_seconds: float = 15, post_event_seconds: float = 15,
    ) -> list[BufferedFrame]:
        start = first_event_at - pre_event_seconds
        end = last_event_at + post_event_seconds
        with self._lock:
            return [frame for frame in self._frames if start <= frame.captured_at <= end]


class LiveCameraWorker:
    """Read one OpenCV source, reconnecting with bounded exponential backoff."""

    def __init__(self, spec: dict[str, Any], capture_factory: Callable[[str], Any] = cv2.VideoCapture,
                 clock: Callable[[], float] = time.time,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.spec, self.capture_factory = spec, capture_factory
        self.clock, self.sleeper = clock, sleeper
        self.health = CameraHealth(spec["id"], spec["label"])
        self.frames = FrameRingBuffer()
        self._jpeg: Optional[bytes] = None
        self._sequence = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def get_frame(self) -> Optional[bytes]:
        with self._lock:
            if (self.health.last_frame_at is not None
                    and self.clock() - self.health.last_frame_at > self.spec["stale_after_seconds"]):
                self.health.state = "DEGRADED"
            return self._jpeg

    def public_health(self, stream_path: str) -> dict[str, Any]:
        with self._lock:
            value = asdict(self.health)
        value["stream"] = stream_path
        return value

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        backoff = self.spec["initial_backoff_seconds"]
        while not self._stop.is_set():
            self.health.state = "CONNECTING"
            capture = self.capture_factory(self.spec["source"])
            if not capture.isOpened():
                self._failure("connection failed")
                self.sleeper(backoff)
                backoff = min(self.spec["max_backoff_seconds"], backoff * 2)
                continue
            backoff = self.spec["initial_backoff_seconds"]
            try:
                while not self._stop.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        self._failure("frame read failed")
                        break
                    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if not ok:
                        self._failure("frame encoding failed")
                        break
                    captured_at = self.clock()
                    jpeg = encoded.tobytes()
                    with self._lock:
                        self._jpeg = jpeg
                        self.health.last_frame_at = captured_at
                        self.health.last_error = None
                        self.health.state = "ONLINE"
                        self._sequence += 1
                        sequence = self._sequence
                    self.frames.append(sequence, captured_at, jpeg)
            finally:
                capture.release()
            if not self._stop.is_set():
                self.sleeper(backoff)
                backoff = min(self.spec["max_backoff_seconds"], backoff * 2)
        self.health.state = "OFFLINE"

    def _failure(self, message: str) -> None:
        self.health.reconnect_attempts += 1
        self.health.last_error = message
        self.health.state = "DEGRADED" if self.health.last_frame_at else "OFFLINE"
        log.warning("camera %s: %s (%s)", self.spec["id"], message,
                    redact_url(self.spec["source"]))


def write_health(path: Path, workers: Iterable[LiveCameraWorker], stream_port: int) -> None:
    payload = {
        "schema_version": 1,
        "generated_at": time.time(),
        "cameras": [worker.public_health(f"/api/cameras/{worker.spec['id']}/stream")
                    for worker in workers],
        "mjpeg_port": stream_port,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def publish_health(operations_url: str, session_id: str, worker: LiveCameraWorker) -> None:
    health = worker.public_health("")
    payload = json.dumps({
        "session_id": session_id,
        "camera_id": worker.spec["id"],
        "physical_zone_id": worker.spec.get("physical_zone_id"),
        "state": health["state"],
        "reason": health["last_error"],
        "recorded_at": time.time(),
    }).encode()
    request = Request(
        f"{operations_url.rstrip('/')}/v1/camera-health", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=1):  # noqa: S310 - URL is an operator CLI setting
            pass
    except OSError as error:
        log.warning("operational health publish failed for %s: %s", worker.spec["id"], error)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run configured RTSP/MJPEG cameras")
    parser.add_argument("--config", default="config/live_cameras.json")
    parser.add_argument("--health", default="results/live_camera_health.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--session-id", help="active Monitoring Session receiving health records")
    parser.add_argument("--operations-url", default="http://127.0.0.1:8090")
    args = parser.parse_args()
    workers = [LiveCameraWorker(spec) for spec in load_camera_config(Path(args.config))]
    registry = StreamRegistry.get_instance()
    server = LiveStreamServer(args.host, args.port)
    threads = []
    try:
        server.start()
        for worker in workers:
            registry.register(worker.spec["id"], worker.get_frame)
            thread = threading.Thread(target=worker.run, daemon=True)
            thread.start()
            threads.append(thread)
        while True:
            write_health(Path(args.health), workers, args.port)
            if args.session_id:
                for worker in workers:
                    publish_health(args.operations_url, args.session_id, worker)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for worker in workers:
            worker.stop()
            registry.unregister(worker.spec["id"])
        for thread in threads:
            thread.join(timeout=2)
        server.stop()
        write_health(Path(args.health), workers, args.port)


if __name__ == "__main__":
    main()
