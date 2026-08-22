"""Offline tests for failure visibility: every path here used to fail silently.

Same constraints as test_pipeline.py -- no video, no ML models, <1 s.
"""
from __future__ import annotations

import json

import pytest

from aura_mas.core.bus import (Alert, AlertStore, LocalBus, TOPIC_AWARDS,
                               TOPIC_BIDS, TOPIC_EVENTS, TOPIC_TASKS,
                               TOPIC_VERIFICATIONS, now_ts)
from aura_mas.agents.coordinator_agent import CoordinatorAgent
from aura_mas.agents.fusion_agent import FusionAgent

from aura_mas.tests.test_pipeline import make_event


class _Hyp:
    hypothesis_id = "hyp_test"
    zone = "zone_A"
    sensors = {"cam_01"}
    confidence = 0.5

    def dominant_type(self) -> str:
        return "intrusion"


def test_failing_subscriber_is_recorded_and_others_still_run():
    bus = LocalBus()
    got = []
    bus.subscribe(TOPIC_EVENTS, lambda t, p: (_ for _ in ()).throw(
        RuntimeError("boom")))
    bus.subscribe(TOPIC_EVENTS, lambda t, p: got.append(p))
    bus.publish(TOPIC_EVENTS, "{}")
    assert got == ["{}"]
    assert len(bus.subscriber_errors) == 1
    assert "boom" in bus.subscriber_errors[0]


def test_fusion_records_malformed_event_instead_of_dropping_it_silently():
    bus = LocalBus()
    fusion = FusionAgent("fusion", bus, window_seconds=5.0)
    fusion.setup()
    bus.publish(TOPIC_EVENTS, "not json")
    bus.publish(TOPIC_EVENTS, make_event().to_json())
    assert fusion.metrics["malformed_events"] == 1
    assert fusion.metrics["events_in"] == 1
    assert fusion.tick_errors


def test_fusion_downstream_failure_does_not_swallow_other_hypotheses():
    bus = LocalBus()
    seen = []

    def handler(hyp):
        seen.append(hyp)
        raise RuntimeError("policy exploded")

    fusion = FusionAgent("fusion", bus, window_seconds=5.0,
                         on_hypothesis=handler)
    fusion.setup()
    bus.publish(TOPIC_EVENTS, make_event(zone="zone_A").to_json())
    bus.publish(TOPIC_EVENTS, make_event(zone="zone_B").to_json())
    fusion.flush_all()
    assert len(seen) == 2
    assert fusion.metrics["downstream_errors"] == 2
    assert len(fusion.tick_errors) == 2


def test_alert_store_falls_back_to_jsonl_when_redis_write_fails(tmp_path):
    class BrokenRedis:
        def xadd(self, *a, **kw):
            raise ConnectionError("redis gone")

    path = tmp_path / "alerts.jsonl"
    store = AlertStore(redis_url=None, jsonl_path=str(path))
    store._redis = BrokenRedis()
    alert = Alert(alert_id="alt_1", timestamp=now_ts(), severity="WARNING",
                  event_type="intrusion", confidence=0.8, zone="zone_A",
                  sensors=["cam_01"], evidence=[], fused_events=[])
    store.append(alert)

    assert store.write_errors, "a lost Redis write must be recorded"
    assert [a.alert_id for a in store.read_alerts()] == ["alt_1"]
    store.append(alert)                       # demoted for the rest of the run
    assert len(store.write_errors) == 1


def test_alert_store_read_skips_and_counts_unreadable_records(tmp_path):
    path = tmp_path / "alerts.jsonl"
    good = Alert(alert_id="alt_ok", timestamp=now_ts(), severity="INFO",
                 event_type="intrusion", confidence=0.5, zone="zone_A",
                 sensors=["cam_01"], evidence=[], fused_events=[])
    path.write_text("{ truncated\n" + good.to_json() + "\n")
    store = AlertStore(redis_url=None, jsonl_path=str(path))
    assert [a.alert_id for a in store.read_alerts()] == ["alt_ok"]
    assert store.read_skipped == 1


def test_evidence_write_failure_propagates(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    cv2 = pytest.importorskip("cv2")
    from aura_mas.core import privacy

    monkeypatch.setattr(cv2, "imwrite", lambda *a, **kw: False)
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    with pytest.raises(OSError):
        privacy.anonymize_and_save(frame, str(tmp_path), prefix="ev")


def test_verification_error_is_scored_as_an_error_not_a_timeout():
    bus = LocalBus()
    coord = CoordinatorAgent("coord", bus, mode="auction",
                             camera_ids=["cam_01"], bid_window=0.05)
    coord.setup()

    def bidder(topic, payload):
        task = json.loads(payload)
        bus.publish(TOPIC_BIDS, json.dumps(
            {"task_id": task["task_id"], "agent_id": "cam_01", "bid": 0.9,
             "timestamp": now_ts()}))
    bus.subscribe(TOPIC_TASKS, bidder)

    def failing_verifier(topic, payload):
        award = json.loads(payload)
        bus.publish(TOPIC_VERIFICATIONS, json.dumps(
            {"task_id": award["task_id"], "agent_id": "cam_01",
             "error": "RuntimeError: camera died", "timestamp": now_ts()}))
    bus.subscribe(TOPIC_AWARDS, failing_verifier)

    assert coord.request_verification(_Hyp()) is None
    assert coord.metrics["verification_errors"] == 1
    assert coord.metrics["verifications"] == 0
    assert coord.metrics["verification_timeouts"] == 0


def test_unanswered_verification_is_counted_as_a_timeout():
    bus = LocalBus()
    coord = CoordinatorAgent("coord", bus, mode="roundrobin",
                             camera_ids=["cam_01"], verification_timeout=0.1)
    coord.setup()
    assert coord.request_verification(_Hyp()) is None
    assert coord.metrics["verification_timeouts"] == 1


def test_replay_refuses_to_write_an_artifact_for_a_degraded_run():
    from aura_mas.scenarios import replay

    bus = LocalBus()
    bus.subscriber_errors.append("cam_01: Traceback ...")
    with pytest.raises(replay.ScenarioRunError):
        replay._abort_on_failure("demo", "mas-auction", [], [], [], bus,
                                 AlertStore(redis_url=None))


def test_replay_thread_guard_captures_tracebacks():
    from aura_mas.scenarios import replay

    errors = []
    replay._guarded(lambda: 1 / 0, "cam_01", errors)()
    assert errors and errors[0].startswith("cam_01: ")
    assert "ZeroDivisionError" in errors[0]
