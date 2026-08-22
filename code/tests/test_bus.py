"""Bus, message-schema and AlertStore tests (no broker required).

Covers wildcard matching, subscriber fault isolation, dataclass JSON
round-trips (schemas that `results/run_*.json` consumers depend on), the
JSONL fallback of AlertStore, and the make_bus fallback policy.
"""
from __future__ import annotations

import json
import sys
import types

import pytest

from aura_mas.core import bus as bus_mod
from aura_mas.core.bus import (ALERT_STREAM, Alert, AlertStore, BaseBus,
                               Detection, Event, LocalBus, make_bus, new_id,
                               now_ts)


@pytest.mark.parametrize("pattern,topic,expected", [
    ("site/events", "site/events", True),
    ("site/events", "site/other", False),
    ("site/+/detections", "site/cam_01/detections", True),
    ("site/+/detections", "site/cam_01/tracks", False),
    ("site/+/detections", "site/detections", False),
    ("site/#", "site/coordination/bids", True),
    ("#", "anything/at/all", True),
    ("site/cam_01", "site/cam_01/detections", False),
])
def test_local_bus_match(pattern, topic, expected):
    assert LocalBus._match(pattern, topic) is expected


def test_local_bus_fans_out_to_every_subscriber():
    bus = LocalBus()
    seen = []
    bus.subscribe("site/events", lambda t, p: seen.append(("a", p)))
    bus.subscribe("site/#", lambda t, p: seen.append(("b", p)))
    bus.publish("site/events", "payload")
    assert sorted(seen) == [("a", "payload"), ("b", "payload")]


def test_local_bus_isolates_failing_subscriber():
    bus = LocalBus()
    delivered = []

    def boom(topic, payload):
        raise RuntimeError("subscriber bug")

    bus.subscribe("site/events", boom)
    bus.subscribe("site/events", lambda t, p: delivered.append(p))
    bus.publish("site/events", "still-delivered")
    assert delivered == ["still-delivered"]


def test_base_bus_is_abstract():
    base = BaseBus()
    with pytest.raises(NotImplementedError):
        base.publish("t", "p")
    with pytest.raises(NotImplementedError):
        base.subscribe("t", lambda t, p: None)
    assert base.start() is None and base.stop() is None


def test_new_id_and_now_ts():
    assert new_id("ev").startswith("ev_")
    assert new_id("ev") != new_id("ev")
    assert now_ts() > 0


def test_detection_to_json():
    det = Detection(sensor_id="cam_01", frame_id=7, timestamp=1.5,
                    objects=[{"class": "person", "confidence": 0.9,
                              "bbox": [0, 0, 1, 1], "track_id": 3}])
    payload = json.loads(det.to_json())
    assert payload["sensor_id"] == "cam_01" and payload["frame_id"] == 7
    assert payload["objects"][0]["track_id"] == 3


def test_event_json_roundtrip_preserves_optional_fields():
    ev = Event(event_id="ev_1", sensor_id="mic_01", timestamp=2.0,
               event_type="audio_glass_break", confidence=0.42,
               modality="audio", zone="zone_A", track_id=None,
               evidence_path=None, extra={"method": "dsp_zscore"})
    assert Event.from_json(ev.to_json()) == ev


def test_alert_json_roundtrip_preserves_defaults():
    alert = Alert(alert_id="alt_1", timestamp=3.0, severity="CRITICAL",
                  event_type="intrusion", confidence=0.9, zone="zone_A",
                  sensors=["cam_01"], evidence=[], fused_events=["ev_1"])
    restored = Alert.from_json(alert.to_json())
    assert restored == alert
    assert restored.status == "OPEN" and restored.explanation is None


def make_alert(alert_id: str, ts: float = 0.0) -> Alert:
    return Alert(alert_id=alert_id, timestamp=ts, severity="WARNING",
                 event_type="anomaly", confidence=0.6, zone=None,
                 sensors=["cam_01"], evidence=[], fused_events=[])


def test_alert_store_jsonl_append_and_read_newest_first(tmp_path):
    store = AlertStore(redis_url=None, jsonl_path=str(tmp_path / "alerts.jsonl"))
    for i in range(3):
        store.append(make_alert(f"alt_{i}", ts=float(i)))
    assert [a.alert_id for a in store.read_alerts()] == ["alt_2", "alt_1", "alt_0"]
    assert [a.alert_id for a in store.read_alerts(count=2)] == ["alt_2", "alt_1"]


def test_alert_store_read_alerts_missing_file(tmp_path):
    store = AlertStore(redis_url=None, jsonl_path=str(tmp_path / "none.jsonl"))
    assert store.read_alerts() == []


def test_alert_store_audit_writes_sibling_file(tmp_path):
    store = AlertStore(redis_url=None, jsonl_path=str(tmp_path / "alerts.jsonl"))
    store.audit({"actor": "policy", "action": "decision"})
    entry = json.loads((tmp_path / "audit.jsonl").read_text().strip())
    assert entry["actor"] == "policy" and entry["timestamp"] > 0


def test_alert_store_falls_back_to_jsonl_when_redis_unreachable(tmp_path, monkeypatch):
    class FakeRedisModule:
        class Redis:
            @staticmethod
            def from_url(url, socket_connect_timeout=None):
                raise OSError("connection refused")

    monkeypatch.setitem(sys.modules, "redis", FakeRedisModule)
    store = AlertStore(redis_url="redis://localhost:6379",
                       jsonl_path=str(tmp_path / "alerts.jsonl"))
    store.append(make_alert("alt_fallback"))
    assert [a.alert_id for a in store.read_alerts()] == ["alt_fallback"]


def test_alert_store_uses_redis_streams_when_available(tmp_path, monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.streams = {}

        def ping(self):
            return True

        def xadd(self, stream, fields):
            self.streams.setdefault(stream, []).append(fields)

        def xrevrange(self, stream, count=None):
            rows = list(reversed(self.streams.get(stream, [])))[:count]
            return [(b"1-1", {b"json": r["json"].encode()}) for r in rows]

    fake = FakeRedis()

    class FakeRedisModule:
        class Redis:
            @staticmethod
            def from_url(url, socket_connect_timeout=None):
                return fake

    monkeypatch.setitem(sys.modules, "redis", FakeRedisModule)
    store = AlertStore(redis_url="redis://x", jsonl_path=str(tmp_path / "a.jsonl"))
    store.append(make_alert("alt_redis"))
    store.audit({"actor": "operator", "action": "acknowledge"})
    assert [a.alert_id for a in store.read_alerts()] == ["alt_redis"]
    assert len(fake.streams[ALERT_STREAM]) == 1
    assert not (tmp_path / "a.jsonl").exists()


class FakeMqttClient:
    def __init__(self, api_version, client_id=None):
        self.api_version = api_version
        self.client_id = client_id
        self.published = []
        self.subscribed = []
        self.connected = None
        self.loop = None
        self.on_message = None

    def connect(self, host, port, keepalive=None):
        self.connected = (host, port, keepalive)

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, payload, qos))

    def subscribe(self, topic, qos=0):
        self.subscribed.append((topic, qos))

    def loop_start(self):
        self.loop = "started"

    def loop_stop(self):
        self.loop = "stopped"

    def disconnect(self):
        self.connected = None


@pytest.fixture
def mqtt_bus(monkeypatch):
    class CallbackAPIVersion:
        VERSION2 = "v2"

    client_mod = types.ModuleType("paho.mqtt.client")
    client_mod.Client = FakeMqttClient
    client_mod.CallbackAPIVersion = CallbackAPIVersion
    mqtt_mod = types.ModuleType("paho.mqtt")
    mqtt_mod.client = client_mod
    paho_mod = types.ModuleType("paho")
    paho_mod.mqtt = mqtt_mod
    for name, mod in (("paho", paho_mod), ("paho.mqtt", mqtt_mod),
                      ("paho.mqtt.client", client_mod)):
        monkeypatch.setitem(sys.modules, name, mod)
    return bus_mod.MqttBus(host="broker", port=1884, client_id="cam_01")


def test_mqtt_bus_connects_publishes_and_subscribes(mqtt_bus):
    client = mqtt_bus._client
    assert client.connected == ("broker", 1884, 30)
    assert client.client_id == "cam_01"

    mqtt_bus.publish("site/events", "payload", qos=1)
    assert client.published == [("site/events", "payload", 1)]

    mqtt_bus.subscribe("site/+/detections", lambda t, p: None)
    assert client.subscribed == [("site/+/detections", 1)]

    mqtt_bus.start()
    assert client.loop == "started"
    mqtt_bus.stop()
    assert client.loop == "stopped" and client.connected is None


def test_mqtt_bus_on_message_dispatches_matching_wildcards(mqtt_bus):
    seen, failed = [], []
    mqtt_bus.subscribe("site/+/detections", lambda t, p: seen.append((t, p)))
    mqtt_bus.subscribe("site/events", lambda t, p: failed.append(t))

    class Msg:
        topic = "site/cam_01/detections"
        payload = b"{}"

    mqtt_bus._client.on_message(None, None, Msg())
    assert seen == [("site/cam_01/detections", "{}")] and failed == []


def test_mqtt_bus_on_message_survives_subscriber_error(mqtt_bus):
    delivered = []
    mqtt_bus.subscribe("site/events", lambda t, p: (_ for _ in ()).throw(
        RuntimeError("boom")))
    mqtt_bus.subscribe("site/events", lambda t, p: delivered.append(p))

    class Msg:
        topic = "site/events"
        payload = b"\xff invalid utf8"

    mqtt_bus._client.on_message(None, None, Msg())
    assert delivered and "invalid utf8" in delivered[0]


def test_make_bus_local_never_touches_mqtt(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("MqttBus must not be constructed for kind='local'")

    monkeypatch.setattr(bus_mod, "MqttBus", fail)
    assert isinstance(make_bus("local"), LocalBus)


def test_make_bus_auto_falls_back_to_local(monkeypatch):
    class DeadMqtt:
        def __init__(self, **kwargs):
            raise OSError("no broker")

    monkeypatch.setattr(bus_mod, "MqttBus", DeadMqtt)
    assert isinstance(make_bus("auto"), LocalBus)


def test_make_bus_mqtt_raises_instead_of_degrading(monkeypatch):
    class DeadMqtt:
        def __init__(self, **kwargs):
            raise OSError("no broker")

    monkeypatch.setattr(bus_mod, "MqttBus", DeadMqtt)
    with pytest.raises(OSError):
        make_bus("mqtt")


def test_make_bus_returns_started_mqtt_bus(monkeypatch):
    started = []

    class FakeMqtt:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def start(self):
            started.append(True)

    monkeypatch.setattr(bus_mod, "MqttBus", FakeMqtt)
    bus = make_bus("mqtt", host="broker", port=1884)
    assert isinstance(bus, FakeMqtt) and started == [True]
    assert bus.kwargs == {"host": "broker", "port": 1884}
