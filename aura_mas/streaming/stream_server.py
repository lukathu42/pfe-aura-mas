"""Lightweight HTTP MJPEG stream server for live surveillance video.

Allows the Next.js CameraWall (or any standard browser/web client) to stream
live camera feeds with zero client-side dependencies via:
    GET /stream/{camera_id}
"""
from __future__ import annotations

import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, Optional

log = logging.getLogger("aura.streaming")


class StreamRegistry:
    """Thread-safe registry mapping camera_id to frame-getter functions."""
    _instance: Optional[StreamRegistry] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._sources: Dict[str, Callable[[], Optional[bytes]]] = {}

    @classmethod
    def get_instance(cls) -> StreamRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = StreamRegistry()
            return cls._instance

    def register(self, camera_id: str, get_frame_fn: Callable[[], Optional[bytes]]) -> None:
        self._sources[camera_id] = get_frame_fn
        log.info("Registered stream source for %s", camera_id)

    def unregister(self, camera_id: str) -> None:
        self._sources.pop(camera_id, None)

    def get_frame(self, camera_id: str) -> Optional[bytes]:
        fn = self._sources.get(camera_id)
        return fn() if fn else None

    def list_cameras(self) -> list[str]:
        return list(self._sources.keys())


class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        if self.path.startswith("/stream/"):
            cam_id = self.path.replace("/stream/", "").split("?")[0]
            registry = StreamRegistry.get_instance()

            # Send multipart MJPEG stream header
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=--frame")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            try:
                while True:
                    frame = registry.get_frame(cam_id)
                    if frame is not None:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.066)  # ~15 FPS target
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # suppress per-frame request logging


class LiveStreamServer:
    """Async background HTTP server providing MJPEG camera streams."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self.server = ThreadingHTTPServer((self.host, self.port), MJPEGHandler)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        log.info("LiveStreamServer running at http://%s:%d/stream/<cam_id>", self.host, self.port)

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            log.info("LiveStreamServer stopped")
