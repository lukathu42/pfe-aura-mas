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
import threading
import time
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
    scene_time_seconds: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "Event":
        return Event(**json.loads(s))


@dataclass
class Alert:
    """Final alert produced by the PolicyAgent, durable in Redis Streams and SQLite."""
    alert_id: str
    timestamp: float
    severity: str            # INFO | WARNING | CRITICAL
    event_type: str
    confidence: float
    zone: Optional[str]
    sensors: List[str]
    evidence: List[str]
    fused_events: List[str]
    scene_time_seconds: Optional[float] = None
    explanation: Optional[str] = None
    status: str = "OPEN"     # OPEN | ACKNOWLEDGED | DISMISSED
    contributing_types: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.contributing_types:
            self.contributing_types = [self.event_type]

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "Alert":
        data = json.loads(s)
        if "contributing_types" not in data:
            data["contributing_types"] = [data.get("event_type", "unknown")]
        return Alert(**data)


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
    """Interface each transport implements."""

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
                try:
                    cb(topic, payload)
                except Exception:  # noqa: BLE001
                    log.exception("subscriber error on %s", topic)

    def subscribe(self, topic: str, callback: Callable[[str, str], None]) -> None:
        with self._lock:
            self._subs[topic].append(callback)


class MqttBus(BaseBus):
    """MQTT transport (Mosquitto broker)."""

    def __init__(self, host: str = "localhost", port: int = 1883,
                 client_id: Optional[str] = None) -> None:
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
                    try:
                        cb(msg.topic, payload)
                    except Exception:  # noqa: BLE001
                        log.exception("subscriber error on %s", msg.topic)

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
    """Durable alert log. Redis Streams + SQLite database + JSONL file."""

    def __init__(self, redis_url: Optional[str] = "redis://localhost:6379",
                 jsonl_path: str = "data/alerts.jsonl",
                 db_path: Optional[str] = "data/aura_surveillance.db") -> None:
        self._redis = None
        self._jsonl_path = jsonl_path
        self._db = None
        if db_path:
            try:
                from .db import AuraDatabase
                self._db = AuraDatabase(db_path)
            except Exception:  # noqa: BLE001
                log.warning("SQLite DB unavailable; continuing without relational store")
        if redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
                self._redis.ping()
                log.info("AlertStore using Redis Streams at %s", redis_url)
            except Exception:  # noqa: BLE001
                self._redis = None
                log.warning("Redis unavailable; falling back to JSONL %s", jsonl_path)

    def append(self, alert: Alert) -> None:
        if self._db is not None:
            try:
                self._db.save_alert(json.loads(alert.to_json()))
            except Exception:  # noqa: BLE001
                log.exception("Failed writing alert to SQLite DB")
        if self._redis is not None:
            self._redis.xadd(ALERT_STREAM, {"json": alert.to_json()})
        else:
            with open(self._jsonl_path, "a", encoding="utf-8") as f:
                f.write(alert.to_json() + "\n")

    def audit(self, entry: Dict[str, Any]) -> None:
        entry = {"timestamp": now_ts(), **entry}
        if self._db is not None:
            try:
                self._db.log_audit(
                    actor=entry.get("actor", "system"),
                    action=entry.get("action", "unknown"),
                    alert_id=entry.get("alert_id"),
                    hypothesis_id=entry.get("hypothesis_id"),
                    details=entry
                )
            except Exception:  # noqa: BLE001
                pass
        if self._redis is not None:
            self._redis.xadd(AUDIT_STREAM, {"json": json.dumps(entry)})
        else:
            with open(self._jsonl_path.replace("alerts", "audit"), "a",
                      encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

    def read_alerts(self, count: int = 100) -> List[Alert]:
        if self._db is not None:
            try:
                rows = self._db.query_alerts(limit=count)
                if rows:
                    return [Alert(**r) for r in rows]
            except Exception:  # noqa: BLE001
                pass
        if self._redis is not None:
            rows = self._redis.xrevrange(ALERT_STREAM, count=count)
            return [Alert.from_json(v[b"json"].decode()) for _, v in rows]
        try:
            with open(self._jsonl_path, encoding="utf-8") as f:
                lines = f.readlines()[-count:]
            return [Alert.from_json(l) for l in reversed(lines)]
        except FileNotFoundError:
            return []


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
