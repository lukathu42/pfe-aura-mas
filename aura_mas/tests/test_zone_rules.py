"""Offline tests for ZoneRuleEngine, including the two opt-in zone rules.

No model is loaded: `evaluate()` consumes the same plain track dicts that
`CameraAgent._process_frame` builds from YOLO output, so the rules can be
exercised deterministically without video.

The backward-compatibility tests matter more than the new-rule tests: nine
existing scenarios ship zone dicts written before `max_occupancy` /
`flow_direction` existed, and their alert counts are cited evaluation
artifacts.
"""
import pytest

from aura_mas.agents.camera_agent import ZoneRuleEngine

POLY = [[0, 0], [400, 0], [400, 400], [0, 400]]


def _person(track_id, x, y, conf=0.8):
    return {"class": "person", "confidence": conf, "track_id": track_id,
            "bbox": [x - 10.0, y - 40.0, x + 10.0, y]}


def _zone(name="entry", ztype="entry", **extra):
    z = {"name": name, "type": ztype, "polygon": POLY}
    z.update(extra)
    return z


def _types(events):
    return [e["event_type"] for e in events]


# ------------------------------------------------------- configurable dwell
def test_loiter_seconds_is_configurable():
    eng = ZoneRuleEngine([_zone()], loiter_seconds=2.0)
    assert _types(eng.evaluate([_person(1, 100, 200)], 0.0)) == []
    assert "loitering" in _types(eng.evaluate([_person(1, 100, 200)], 2.5))


def test_default_loiter_seconds_unchanged():
    eng = ZoneRuleEngine([_zone()])
    eng.evaluate([_person(1, 100, 200)], 0.0)
    assert _types(eng.evaluate([_person(1, 100, 200)], 5.5)) == []
    assert "loitering" in _types(eng.evaluate([_person(1, 100, 200)], 8.5))


def test_leaving_the_zone_resets_dwell():
    eng = ZoneRuleEngine([_zone()], loiter_seconds=3.0)
    eng.evaluate([_person(1, 100, 200)], 0.0)
    eng.evaluate([_person(1, 900, 200)], 2.0)
    assert _types(eng.evaluate([_person(1, 100, 200)], 4.0)) == []


# ------------------------------------------------------------ zone occupancy
def test_zone_occupancy_fires_above_limit():
    eng = ZoneRuleEngine([_zone(max_occupancy=2)])
    tracks = [_person(1, 50, 100), _person(2, 150, 100), _person(3, 250, 100)]
    events = [e for e in eng.evaluate(tracks, 0.0)
              if e["event_type"] == "zone_occupancy"]
    assert len(events) == 1
    assert events[0]["zone"] == "entry"
    assert events[0]["track_id"] in (1, 2, 3)
    assert events[0]["confidence"] == pytest.approx(0.8, abs=1e-6)


def test_zone_occupancy_silent_at_limit():
    eng = ZoneRuleEngine([_zone(max_occupancy=2)])
    tracks = [_person(1, 50, 100), _person(2, 150, 100)]
    assert "zone_occupancy" not in _types(eng.evaluate(tracks, 0.0))


def test_zone_occupancy_escalates_once_per_level():
    eng = ZoneRuleEngine([_zone(max_occupancy=1)])
    two = [_person(1, 50, 100), _person(2, 150, 100)]
    three = two + [_person(3, 250, 100)]
    first = [e for e in eng.evaluate(two, 0.0) if e["event_type"] == "zone_occupancy"]
    repeat = [e for e in eng.evaluate(two, 1.0) if e["event_type"] == "zone_occupancy"]
    escalated = [e for e in eng.evaluate(three, 2.0) if e["event_type"] == "zone_occupancy"]
    assert len(first) == 1 and repeat == [] and len(escalated) == 1
    assert escalated[0]["confidence"] > first[0]["confidence"]


def test_zone_occupancy_counts_only_persons_inside():
    eng = ZoneRuleEngine([_zone(max_occupancy=1)])
    tracks = [_person(1, 50, 100), _person(2, 900, 100),
              {"class": "suitcase", "confidence": 0.9, "track_id": 3,
               "bbox": [100.0, 60.0, 140.0, 100.0]}]
    assert "zone_occupancy" not in _types(eng.evaluate(tracks, 0.0))


def test_zone_occupancy_deduplicates_track_identities():
    eng = ZoneRuleEngine([_zone(max_occupancy=1)])
    duplicate = [_person(7, 50, 100, 0.7), _person(7, 55, 100, 0.9)]
    assert "zone_occupancy" not in _types(eng.evaluate(duplicate, 0.0))


def test_zone_without_max_occupancy_never_fires_occupancy():
    eng = ZoneRuleEngine([_zone()])
    tracks = [_person(i, 20 * i, 100) for i in range(1, 6)]
    assert "zone_occupancy" not in _types(eng.evaluate(tracks, 0.0))


# ----------------------------------------------------------- wrong direction
def test_wrong_direction_fires_against_flow():
    eng = ZoneRuleEngine([_zone(flow_direction=[1, 0])], min_flow_px=40.0)
    eng.evaluate([_person(1, 300, 200)], 0.0)
    events = eng.evaluate([_person(1, 200, 200)], 1.0)
    assert "wrong_direction" in _types(events)
    ev = next(e for e in events if e["event_type"] == "wrong_direction")
    assert ev["zone"] == "entry" and ev["track_id"] == 1


def test_wrong_direction_silent_when_moving_with_flow():
    eng = ZoneRuleEngine([_zone(flow_direction=[1, 0])], min_flow_px=40.0)
    eng.evaluate([_person(1, 100, 200)], 0.0)
    assert "wrong_direction" not in _types(eng.evaluate([_person(1, 300, 200)], 1.0))


def test_wrong_direction_ignores_jitter_below_min_flow():
    eng = ZoneRuleEngine([_zone(flow_direction=[1, 0])], min_flow_px=40.0)
    eng.evaluate([_person(1, 300, 200)], 0.0)
    assert "wrong_direction" not in _types(eng.evaluate([_person(1, 285, 200)], 1.0))


def test_wrong_direction_uses_the_flow_axis_not_raw_sign():
    eng = ZoneRuleEngine([_zone(flow_direction=[0, 1])], min_flow_px=40.0)
    eng.evaluate([_person(1, 100, 300)], 0.0)
    across = eng.evaluate([_person(1, 300, 300)], 1.0)
    assert "wrong_direction" not in _types(across)
    against = eng.evaluate([_person(1, 300, 200)], 2.0)
    assert "wrong_direction" in _types(against)


def test_wrong_direction_resets_on_zone_exit():
    eng = ZoneRuleEngine([_zone(flow_direction=[1, 0])], min_flow_px=40.0)
    eng.evaluate([_person(1, 300, 200)], 0.0)
    eng.evaluate([_person(1, 900, 200)], 1.0)
    assert "wrong_direction" not in _types(eng.evaluate([_person(1, 260, 200)], 2.0))


def test_zone_without_flow_direction_never_fires_wrong_direction():
    eng = ZoneRuleEngine([_zone()], min_flow_px=40.0)
    eng.evaluate([_person(1, 300, 200)], 0.0)
    assert "wrong_direction" not in _types(eng.evaluate([_person(1, 100, 200)], 1.0))


# ------------------------------------------------------ backward compatibility
def test_legacy_zone_dict_still_yields_intrusion_only():
    legacy = {"name": "zone_A", "type": "restricted",
              "polygon": [[380, 220], [768, 220], [768, 432], [380, 432]]}
    eng = ZoneRuleEngine([legacy])
    events = eng.evaluate([_person(7, 500, 300)], 0.0)
    assert _types(events) == ["intrusion"]
    assert events[0]["zone"] == "zone_A"


def test_intrusion_still_fires_once_per_track_and_zone():
    eng = ZoneRuleEngine([_zone(ztype="restricted")])
    assert _types(eng.evaluate([_person(1, 100, 200)], 0.0)) == ["intrusion"]
    assert _types(eng.evaluate([_person(1, 110, 200)], 1.0)) == []


def test_abandoned_seconds_is_configurable():
    bag = {"class": "suitcase", "confidence": 0.7, "track_id": 9,
           "bbox": [100.0, 60.0, 140.0, 100.0]}
    eng = ZoneRuleEngine([_zone()], abandoned_seconds=3.0)
    eng.evaluate([bag], 0.0)
    events = eng.evaluate([bag], 3.5)
    assert _types(events) == ["abandoned_object"]
    assert events[0]["zone"] is None


def test_person_down_requires_persistence_and_resets_after_recovery():
    eng = ZoneRuleEngine([_zone(down_aspect_ratio=1.2)], person_down_seconds=1.0)
    down = {"class": "person", "confidence": 0.8, "track_id": 3,
            "bbox": [50.0, 150.0, 190.0, 220.0]}
    upright = _person(3, 100, 220)
    assert "person_down" not in _types(eng.evaluate([down], 0.0))
    eng.evaluate([upright], 0.6)
    assert "person_down" not in _types(eng.evaluate([down], 1.0))
    assert "person_down" in _types(eng.evaluate([down], 2.1))


def test_rapid_movement_is_zone_normalized_persistent_and_resets_on_exit():
    eng = ZoneRuleEngine([_zone(max_speed_zone_lengths_per_second=0.2)],
                         rapid_window_seconds=1.0, rapid_min_duration=0.5)
    assert "rapid_movement" not in _types(eng.evaluate([_person(8, 20, 200)], 0.0))
    assert "rapid_movement" not in _types(eng.evaluate([_person(8, 180, 200)], 0.5))
    assert "rapid_movement" in _types(eng.evaluate([_person(8, 340, 200)], 1.0))

    other = ZoneRuleEngine([_zone(max_speed_zone_lengths_per_second=0.2)],
                           rapid_window_seconds=1.0, rapid_min_duration=0.5)
    other.evaluate([_person(9, 20, 200)], 0.0)
    other.evaluate([_person(9, 180, 200)], 0.5)
    other.evaluate([_person(9, 900, 200)], 0.8)
    assert "rapid_movement" not in _types(other.evaluate([_person(9, 340, 200)], 1.0))
