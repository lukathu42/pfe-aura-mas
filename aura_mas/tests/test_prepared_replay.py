from aura_mas.agents.fusion_agent import Hypothesis
from aura_mas.core.bus import Alert, Event
from aura_mas.eval.metrics import evaluate_run
from aura_mas.scenarios.replay import normalize_timeline


def _event(scene_time):
    return Event(
        event_id=f"ev_{scene_time}", sensor_id="cam_01", timestamp=100 + scene_time,
        event_type="intrusion", confidence=0.8, modality="video",
        scene_time_seconds=scene_time,
    )


def test_scene_time_round_trips_through_event_and_alert_json():
    event = Event.from_json(_event(4.25).to_json())
    assert event.scene_time_seconds == 4.25
    alert = Alert(
        alert_id="alt_1", timestamp=110, severity="CRITICAL",
        event_type="intrusion", confidence=0.8, zone="gate",
        sensors=["cam_01"], evidence=[], fused_events=[event.event_id],
        scene_time_seconds=4.25,
    )
    assert Alert.from_json(alert.to_json()).scene_time_seconds == 4.25


def test_hypothesis_uses_earliest_source_scene_time():
    hyp = Hypothesis("hyp_1", "security", "gate", 100, 110,
                     events=[_event(7.0), _event(4.0)])
    assert hyp.scene_time_seconds == 4.0


def test_metrics_prefer_scene_time_over_wall_clock():
    row = evaluate_run({
        "scenario": "demo", "mode": "mas-auction", "t_start": 100.0,
        "wall_seconds": 30.0,
        "ground_truth": [{"event_type": "intrusion", "t_start": 4.0, "t_end": 6.0}],
        "alerts": [{"event_type": "intrusion", "t_wall": 999.0,
                    "scene_time_seconds": 5.0}],
    })
    assert row["tp"] == 1
    assert row["mean_time_to_alert_s"] == 1.0


def test_prepared_timeline_orders_scene_time_then_wall_fallback():
    items = [
        {"kind": "award", "scene_time_seconds": 8.0, "wall_timestamp": 120.0,
         "payload": {"task_id": "t1"}},
        {"kind": "event", "scene_time_seconds": 3.0, "wall_timestamp": 110.0,
         "payload": {"event_id": "e1"}},
        {"kind": "task", "scene_time_seconds": None, "wall_timestamp": 105.0,
         "payload": {"task_id": "t2"}},
    ]
    result = normalize_timeline(items, 100.0)
    assert [item["kind"] for item in result] == ["event", "task", "award"]
    assert result[1]["wall_offset_seconds"] == 5.0
