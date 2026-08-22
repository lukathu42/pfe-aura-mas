"""AURA-MAS core message bus abstraction.

Two transports:
- MQTT (paho-mqtt) for high-frequency edge events (detections, tracks, zone/audio events).
- Redis Streams for durable, replayable alert logging with consumer groups.

If neither broker is available (e.g., quick local test), an in-process
fallback bus (`LocalBus`) lets the whole pipeline run in a single process.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import traceback
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("aura.bus")

# ---------------------------------------------------------------------------
# Message schemas (kept as plain dataclasses -> JSON for transparency)
# ---------------------------------------------------------------------------


def now_ts() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Detection:
    """Single-frame object detection from a CameraAgent."""
    sensor_id: str
    frame_id: int
    timestamp: float
    objects: List[Dict[str, Any]]  # {class, confidence, bbox[x1,y1,x2,y2], track_id}

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class Event:
    """Semantic event emitted by an edge agent (zone rule, anomaly, audio)."""
    event_id: str
    sensor_id: str
    timestamp: float
    event_type: str          # intrusion | loitering | abandoned_object | anomaly | audio_scream | ...
    confidence: float
    modality: str            # video | audio
    zone: Optional[str] = None
    track_id: Optional[int] = None
    evidence_path: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "Event":
        return Event(**json.loads(s))


@dataclass
class Alert:
    """Final alert produced by the PolicyAgent, durable in Redis Streams."""
    alert_id: str
    timestamp: float
    severity: str            # INFO | WARNING | CRITICAL
    event_type: str
    confidence: float
    zone: Optional[str]
    sensors: List[str]
    evidence: List[str]
    fused_events: List[str]
    explanation: Optional[str] = None
    status: str = "OPEN"     # OPEN | ACKNOWLEDGED | DISMISSED

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "Alert":
        return Alert(**json.loads(s))


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

TOPIC_DETECTIONS = "site/{sensor_id}/detections"   # QoS 0, high frequency
TOPIC_EVENTS = "site/events"                       # QoS 1, semantic events
TOPIC_TASKS = "site/coordination/tasks"            # auction announcements
TOPIC_BIDS = "site/coordination/bids"              # agent bids
TOPIC_AWARDS = "site/coordination/awards"          # auction results
TOPIC_VERIFICATIONS = "site/coordination/verifications"
ALERT_STREAM = "aura:alerts"                       # Redis stream key
AUDIT_STREAM = "aura:audit"


# ---------------------------------------------------------------------------
# Bus implementations
# ---------------------------------------------------------------------------

class BaseBus:
    """Interface each transport implements.

    A subscriber raising must not stop delivery to the other subscribers, so
    the transports catch and log per-callback errors -- but they also record
    them in `subscriber_errors` so a run that dropped events (malformed
    payload, buggy handler) is distinguishable from a quiet one instead of
    only existing in a log nobody reads.
    """

    def __init__(self) -> None:
        self.subscriber_errors: List[str] = []

    def _dispatch(self, cb: Callable[[str, str], None], topic: str,
                  payload: str) -> None:
        try:
            cb(topic, payload)
        except Exception:  # noqa: BLE001
            log.exception("subscriber error on %s", topic)
            self.subscriber_errors.append(f"{topic}: {traceback.format_exc()}")

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        raise NotImplementedError

    def subscribe(self, topic: str, callback: Callable[[str, str], None]) -> None:
        raise NotImplementedError

    def start(self) -> None:  # pragma: no cover
        pass

    def stop(self) -> None:  # pragma: no cover
        pass


class LocalBus(BaseBus):
    """In-process pub/sub used for tests and single-machine demos without brokers."""

    def __init__(self) -> None:
        super().__init__()
        self._subs: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    @staticmethod
    def _match(pattern: str, topic: str) -> bool:
        # MQTT-style wildcard matching: '+' one level, '#' multi-level
        p, t = pattern.split("/"), topic.split("/")
        for i, seg in enumerate(p):
            if seg == "#":
                return True
            if i >= len(t):
                return False
            if seg != "+" and seg != t[i]:
                return False
        return len(p) == len(t)

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        with self._lock:
            targets = [(pat, cbs[:]) for pat, cbs in self._subs.items()
                       if self._match(pat, topic)]
        for _, cbs in targets:
            for cb in cbs:
                self._dispatch(cb, topic, payload)

    def subscribe(self, topic: str, callback: Callable[[str, str], None]) -> None:
        with self._lock:
            self._subs[topic].append(callback)


class MqttBus(BaseBus):
    """MQTT transport (Mosquitto broker)."""

    def __init__(self, host: str = "localhost", port: int = 1883,
                 client_id: Optional[str] = None) -> None:
        super().__init__()
        import paho.mqtt.client as mqtt  # lazy import
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id or new_id("aura"))
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._client.on_message = self._on_message
        self._client.connect(host, port, keepalive=30)

    def _on_message(self, client, userdata, msg) -> None:  # noqa: ANN001
        payload = msg.payload.decode("utf-8", errors="replace")
        for pattern, cbs in self._callbacks.items():
            if LocalBus._match(pattern, msg.topic):
                for cb in cbs:
                    self._dispatch(cb, msg.topic, payload)

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        self._client.publish(topic, payload, qos=qos)

    def subscribe(self, topic: str, callback: Callable[[str, str], None]) -> None:
        self._callbacks[topic].append(callback)
        self._client.subscribe(topic, qos=1)

    def start(self) -> None:
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()


class AlertStore:
    """Durable alert log. Redis Streams if available, else JSONL file.

    `append` is reached from a bus callback, so a broker dying mid-run would
    surface only as a generic tick error while the alert itself was lost --
    an artifact showing a missed detection the pipeline actually produced.
    A Redis write failure therefore demotes the store to its JSONL path for
    the rest of the run and is recorded in `write_errors`.
    """

    def __init__(self, redis_url: Optional[str] = "redis://localhost:6379",
                 jsonl_path: str = "data/alerts.jsonl") -> None:
        self._redis = None
        self._jsonl_path = jsonl_path
        self.write_errors: List[str] = []
        self.read_skipped = 0
        if redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
                self._redis.ping()
                log.info("AlertStore using Redis Streams at %s", redis_url)
            except Exception:  # noqa: BLE001
                self._redis = None
                log.warning("Redis unavailable; falling back to JSONL %s",
                            jsonl_path, exc_info=True)

    def _append_jsonl(self, path: str, line: str) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _write(self, stream: str, path: str, payload: str) -> None:
        if self._redis is not None:
            try:
                self._redis.xadd(stream, {"json": payload})
                return
            except Exception:  # noqa: BLE001
                log.exception("Redis write to %s failed; demoting store to "
                              "JSONL %s for the rest of this run", stream, path)
                self.write_errors.append(traceback.format_exc())
                self._redis = None
        self._append_jsonl(path, payload)

    def append(self, alert: Alert) -> None:
        self._write(ALERT_STREAM, self._jsonl_path, alert.to_json())

    def audit(self, entry: Dict[str, Any]) -> None:
        entry = {"timestamp": now_ts(), **entry}
        self._write(AUDIT_STREAM, self._jsonl_path.replace("alerts", "audit"),
                    json.dumps(entry))

    def read_alerts(self, count: int = 100) -> List[Alert]:
        """Best-effort read; `read_skipped` counts records that could not be
        decoded, so a caller can tell an empty feed from a corrupt one."""
        self.read_skipped = 0
        if self._redis is not None:
            rows = self._redis.xrevrange(ALERT_STREAM, count=count)
            return self._decode([v[b"json"].decode() for _, v in rows],
                                ALERT_STREAM)
        try:
            with open(self._jsonl_path, encoding="utf-8") as f:
                lines = f.readlines()[-count:]
        except FileNotFoundError:
            return []
        return self._decode(list(reversed(lines)), self._jsonl_path)

    def _decode(self, records: List[str], source: str) -> List[Alert]:
        alerts = []
        for record in records:
            if not record.strip():
                continue
            try:
                alerts.append(Alert.from_json(record))
            except Exception:  # noqa: BLE001
                self.read_skipped += 1
                log.exception("skipping unreadable alert record in %s", source)
        if self.read_skipped:
            log.error("%d unreadable alert record(s) skipped in %s",
                      self.read_skipped, source)
        return alerts


def make_bus(kind: str = "auto", **kwargs) -> BaseBus:
    """Factory: 'mqtt', 'local', or 'auto' (try MQTT then fall back)."""
    if kind in ("mqtt", "auto"):
        try:
            bus = MqttBus(**kwargs)
            bus.start()
            log.info("Using MQTT bus")
            return bus
        except Exception as e:  # noqa: BLE001
            if kind == "mqtt":
                raise
            log.warning("MQTT unavailable (%s); using LocalBus", e)
    return LocalBus()
