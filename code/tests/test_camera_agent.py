"""CameraAgent tests: zone rules, bidding and verification.

YOLO is never loaded — detections are injected as plain dicts (the shape
`_process_frame` builds from ultralytics boxes), so the zone-rule state
machine and the auction callbacks are covered without `ultralytics`/models.
"""
from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pytest

from aura_mas.agents.camera_agent import (CameraAgent, ZoneRuleEngine, _iou,
                                          point_in_polygon)
from aura_mas.core.bus import (Event, LocalBus, TOPIC_AWARDS, TOPIC_BIDS,
                               TOPIC_EVENTS, TOPIC_TASKS,
                               TOPIC_VERIFICATIONS)

ZONE_A = {"name": "zone_A", "type": "restricted",
          "polygon": [(0, 0), (100, 0), (100, 100), (0, 100)]}
ENTRY_ZONE = {"name": "entry", "type": "entry",
              "polygon": [(0, 0), (100, 0), (100, 100), (0, 100)]}


def track(track_id=1, cls="person", bbox=(10, 10, 30, 50), conf=0.8) -> dict:
    return {"class": cls, "confidence": conf, "bbox": list(bbox),
            "track_id": track_id}


@pytest.mark.parametrize("pt,expected", [
    ((50, 50), True),
    ((150, 50), False),
    ((-1, 50), False),
    ((50, 150), False),
])
def test_point_in_polygon(pt, expected):
    assert point_in_polygon(pt, ZONE_A["polygon"]) is expected


def test_point_in_concave_polygon():
    poly = [(0, 0), (100, 0), (100, 100), (60, 100), (60, 40), (40, 40),
            (40, 100), (0, 100)]
    assert point_in_polygon((20, 80), poly) is True
    assert point_in_polygon((50, 80), poly) is False, "inside the notch"


@pytest.mark.parametrize("a,b,expected", [
    ((0, 0, 10, 10), (0, 0, 10, 10), 1.0),
    ((0, 0, 10, 10), (20, 20, 30, 30), 0.0),
    ((0, 0, 10, 10), (5, 0, 15, 10), 1 / 3),
])
def test_iou(a, b, expected):
    assert _iou(a, b) == pytest.approx(expected, abs=1e-6)


def test_intrusion_fires_once_per_track_and_zone():
    engine = ZoneRuleEngine([ZONE_A])
    first = engine.evaluate([track()], ts=0.0)
    assert [e["event_type"] for e in first] == ["intrusion"]
    assert first[0]["zone"] == "zone_A" and first[0]["confidence"] == 0.8
    assert engine.evaluate([track()], ts=1.0) == []


def test_intrusion_requires_a_person_in_a_restricted_zone():
    assert ZoneRuleEngine([ZONE_A]).evaluate([track(cls="backpack")], ts=0.0) == []
    assert ZoneRuleEngine([ENTRY_ZONE]).evaluate([track()], ts=0.0) == []


def test_objects_outside_every_zone_fire_nothing():
    engine = ZoneRuleEngine([ZONE_A])
    assert engine.evaluate([track(bbox=(500, 500, 520, 560))], ts=0.0) == []


def test_untracked_objects_are_ignored():
    assert ZoneRuleEngine([ZONE_A]).evaluate([track(track_id=None)], ts=0.0) == []


def test_rules_use_the_foot_point_not_the_box_centre():
    engine = ZoneRuleEngine([ZONE_A])
    # centre is above the zone, the feet are inside it
    assert engine.evaluate([track(bbox=(10, -80, 30, 20))], ts=0.0)


def test_loitering_fires_after_the_dwell_threshold():
    engine = ZoneRuleEngine([ZONE_A], loiter_seconds=8.0)
    engine.evaluate([track()], ts=0.0)
    assert engine.evaluate([track()], ts=8.0) == [], "boundary is exclusive"
    events = engine.evaluate([track()], ts=9.0)
    assert [e["event_type"] for e in events] == ["loitering"]
    assert 0.5 < events[0]["confidence"] <= 1.0
    assert engine.evaluate([track()], ts=20.0) == [], "fires once"


def test_leaving_the_zone_resets_the_dwell_timer():
    engine = ZoneRuleEngine([ZONE_A], loiter_seconds=8.0)
    engine.evaluate([track()], ts=0.0)
    engine.evaluate([track(bbox=(500, 500, 520, 560))], ts=5.0)
    assert engine.evaluate([track()], ts=9.0) == []
    assert engine.evaluate([track()], ts=18.0)


def test_abandoned_object_fires_for_a_static_non_person():
    engine = ZoneRuleEngine([ZONE_A], abandoned_seconds=10.0)
    bag = track(track_id=7, cls="backpack", bbox=(10, 10, 30, 30))
    engine.evaluate([bag], ts=0.0)
    assert engine.evaluate([bag], ts=5.0) == []
    events = engine.evaluate([bag], ts=11.0)
    assert [e["event_type"] for e in events] == ["abandoned_object"]
    assert events[0]["zone"] is None and events[0]["confidence"] == 0.7
    assert engine.evaluate([bag], ts=30.0) == [], "fires once"


def test_moving_object_never_counts_as_abandoned():
    engine = ZoneRuleEngine([ZONE_A], abandoned_seconds=10.0)
    for i, x in enumerate(range(0, 120, 20)):
        moved = track(track_id=7, cls="backpack", bbox=(x, 10, x + 20, 30))
        assert engine.evaluate([moved], ts=float(i * 5)) == []


def test_persons_are_never_reported_as_abandoned_objects():
    engine = ZoneRuleEngine([ZONE_A], abandoned_seconds=1.0)
    engine.evaluate([track()], ts=0.0)
    later = engine.evaluate([track()], ts=30.0)
    assert [e["event_type"] for e in later] == ["loitering"]


def make_agent(bus, agent_id="cam_01", zones=(ZONE_A,), **kwargs) -> CameraAgent:
    return CameraAgent(agent_id, bus, source="unused.mp4", zones=list(zones),
                       realtime=False, **kwargs)


def fake_yolo(**methods) -> Any:
    return type("FakeYolo", (), {k: staticmethod(v)
                                 for k, v in methods.items()})()


class EmptyResult:
    names: dict = {}
    boxes = None


def test_view_score_prefers_a_camera_that_did_not_originate_the_event():
    bus = LocalBus()
    agent = make_agent(bus)
    other = agent._view_score({"origin_sensor": "cam_02"})
    own = agent._view_score({"origin_sensor": "cam_01"})
    assert other > own


def test_view_score_penalises_a_busy_camera_and_weights_fov_overlap():
    bus = LocalBus()
    agent = make_agent(bus)
    baseline = agent._view_score({"origin_sensor": "cam_02"})
    agent._busy = True
    assert agent._view_score({"origin_sensor": "cam_02"}) < baseline
    agent._busy = False
    assert agent._view_score({"origin_sensor": "cam_02",
                              "fov_overlap": {"cam_01": 0.1}}) == 0.1


def test_task_announcement_triggers_a_bid():
    bus = LocalBus()
    bids = []
    bus.subscribe(TOPIC_BIDS, lambda t, p: bids.append(json.loads(p)))
    agent = make_agent(bus)
    agent._on_task_announce(TOPIC_TASKS, json.dumps(
        {"task_id": "task_1", "origin_sensor": "cam_02"}))
    assert bids[0]["agent_id"] == "cam_01" and bids[0]["task_id"] == "task_1"
    assert bids[0]["bid"] == 0.5


def test_award_to_another_camera_is_ignored(monkeypatch):
    bus = LocalBus()
    results = []
    bus.subscribe(TOPIC_VERIFICATIONS, lambda t, p: results.append(p))
    agent = make_agent(bus)
    monkeypatch.setattr(agent, "_verify",
                        lambda award: pytest.fail("must not verify"))
    agent._on_award(TOPIC_AWARDS, json.dumps({"task_id": "t", "winner": "cam_02"}))
    assert results == []


def test_winning_camera_publishes_a_verification_and_clears_busy(monkeypatch):
    bus = LocalBus()
    results = []
    bus.subscribe(TOPIC_VERIFICATIONS,
                  lambda t, p: results.append(json.loads(p)))
    agent = make_agent(bus)
    monkeypatch.setattr(agent, "_verify", lambda award: {
        "task_id": award["task_id"], "agent_id": agent.agent_id,
        "verified": True, "verification_score": 0.9, "timestamp": 0.0})
    agent._on_award(TOPIC_AWARDS, json.dumps({"task_id": "t1",
                                              "winner": "cam_01"}))
    assert results[0]["verified"] is True and results[0]["task_id"] == "t1"
    assert agent._busy is False


def test_busy_flag_is_cleared_even_when_verification_raises(monkeypatch):
    bus = LocalBus()
    agent = make_agent(bus)
    monkeypatch.setattr(agent, "_verify",
                        lambda award: (_ for _ in ()).throw(RuntimeError("cam down")))
    with pytest.raises(RuntimeError):
        agent._on_award(TOPIC_AWARDS, json.dumps({"task_id": "t",
                                                  "winner": "cam_01"}))
    assert agent._busy is False


def test_verify_without_a_frame_reports_unverified():
    bus = LocalBus()
    agent = make_agent(bus)
    result = agent._verify({"task_id": "t1"})
    assert result["verified"] is False and result["verification_score"] == 0.0


def test_verify_scores_the_best_person_detection(monkeypatch):
    bus = LocalBus()
    agent = make_agent(bus)
    agent._last_frame = np.zeros((48, 64, 3), dtype=np.uint8)

    class Box:
        def __init__(self, cls, conf):
            self.cls = cls
            self.conf = conf

    class Result:
        names = {0: "person", 1: "car"}
        boxes = [Box(0, 0.3), Box(0, 0.75), Box(1, 0.99)]

    agent._model = fake_yolo(predict=lambda *a, **k: [Result()])
    result = agent._verify({"task_id": "t1"})
    assert result["verified"] is True and result["verification_score"] == 0.75


def test_emit_event_publishes_with_anonymized_evidence(tmp_path):
    bus = LocalBus()
    events = []
    bus.subscribe(TOPIC_EVENTS, lambda t, p: events.append(Event.from_json(p)))
    agent = make_agent(bus, evidence_dir=str(tmp_path / "evidence"))
    frame = np.random.default_rng(1).integers(
        0, 255, (60, 80, 3), dtype=np.uint8)
    agent._emit_event(frame, ts=1.0, event_type="intrusion", zone="zone_A",
                      track_id=3, confidence=0.8123)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "intrusion" and ev.confidence == 0.812
    assert ev.modality == "video" and ev.track_id == 3
    assert os.path.exists(ev.evidence_path)
    assert agent.metrics["events"] == 1


def test_process_frame_publishes_detections_and_zone_events(tmp_path):
    bus = LocalBus()
    detections, events = [], []
    bus.subscribe("site/cam_01/detections", lambda t, p: detections.append(
        json.loads(p)))
    bus.subscribe(TOPIC_EVENTS, lambda t, p: events.append(Event.from_json(p)))
    agent = make_agent(bus, evidence_dir=str(tmp_path / "evidence"))

    class Box:
        cls = 0
        conf = 0.9
        id = 4
        xyxy = np.array([[10.0, 10.0, 30.0, 50.0]])

    class Result:
        names = {0: "person"}
        boxes = [Box()]

    agent._model = fake_yolo(track=lambda *a, **k: [Result()])
    agent._process_frame(np.zeros((60, 80, 3), dtype=np.uint8), frame_id=1,
                         ts=1.0, video_ts=0.0)

    assert detections[0]["objects"][0]["track_id"] == 4
    assert agent.metrics["frames"] == 1 and agent.metrics["detections"] == 1
    assert agent.metrics["infer_ms"]
    assert [e.event_type for e in events] == ["intrusion"]


def test_process_frame_handles_boxless_results(tmp_path):
    bus = LocalBus()
    detections = []
    bus.subscribe("site/cam_01/detections",
                  lambda t, p: detections.append(json.loads(p)))
    agent = make_agent(bus, evidence_dir=str(tmp_path / "evidence"))
    agent._model = fake_yolo(track=lambda *a, **k: [EmptyResult()])
    agent._process_frame(np.zeros((60, 80, 3), dtype=np.uint8), frame_id=1,
                         ts=1.0)
    assert detections[0]["objects"] == []
    assert agent.metrics["detections"] == 0


def test_clip_anomaly_is_emitted_on_sampled_frames_only(tmp_path):
    bus = LocalBus()
    events = []
    bus.subscribe(TOPIC_EVENTS, lambda t, p: events.append(Event.from_json(p)))
    agent = make_agent(bus, evidence_dir=str(tmp_path / "evidence"),
                       clip_every_n=5, anomaly_threshold=0.5, zones=())
    agent._model = fake_yolo(track=lambda *a, **k: [EmptyResult()])
    agent._clip = fake_yolo(
        score=lambda frame: (0.9, "people fighting violently"))
    frame = np.zeros((60, 80, 3), dtype=np.uint8)
    agent._process_frame(frame, frame_id=4, ts=1.0)
    assert events == []
    agent._process_frame(frame, frame_id=5, ts=2.0)
    assert [e.event_type for e in events] == ["anomaly"]
    assert events[0].extra["clip_label"] == "people fighting violently"


def test_clip_score_below_threshold_emits_nothing(tmp_path):
    bus = LocalBus()
    events = []
    bus.subscribe(TOPIC_EVENTS, lambda t, p: events.append(p))
    agent = make_agent(bus, evidence_dir=str(tmp_path / "evidence"),
                       clip_every_n=1, anomaly_threshold=0.9, zones=())
    agent._model = fake_yolo(track=lambda *a, **k: [EmptyResult()])
    agent._clip = fake_yolo(score=lambda f: (0.2, "x"))
    agent._process_frame(np.zeros((60, 80, 3), dtype=np.uint8), frame_id=1,
                         ts=1.0)
    assert events == []


def test_run_raises_on_an_unopenable_source():
    agent = CameraAgent("cam_01", LocalBus(), source="does_not_exist.mp4",
                        realtime=False)
    with pytest.raises(RuntimeError, match="cannot open source"):
        agent.run()


def test_warmup_predicts_once_without_seeding_the_tracker(tmp_path):
    bus = LocalBus()
    agent = make_agent(bus)
    calls = []
    agent._model = fake_yolo(
        predict=lambda frame, **k: calls.append(frame.shape),
        track=lambda *a, **k: pytest.fail(
            "warmup must not seed ByteTrack state"))
    agent._clip = fake_yolo(score=lambda f: calls.append("clip"))
    agent.warmup()
    assert calls == [(480, 640, 3), "clip"]
