"""Static acceptance checks for the expanded prepared-demo catalogue."""
from __future__ import annotations

import json
from pathlib import Path

from aura_mas.core.taxonomy import EVENT_FAMILIES
from aura_mas.scenarios.demo_catalog import DEMO_SCENARIOS


ROOT = Path(__file__).resolve().parents[2]
NEW_MULTI_CAMERA = {
    "perimeter_chain_01": "intrusion",
    "loitering_multizone_01": "loitering",
    "zone_occupancy_01": "zone_occupancy",
    "wrong_direction_01": "wrong_direction",
}


def _manifest(name: str) -> dict:
    return json.loads((ROOT / "scenarios" / f"{name}.json").read_text())


def test_catalogue_has_three_examples_for_each_of_twelve_families():
    grouped = {}
    for metadata in DEMO_SCENARIOS.values():
        grouped.setdefault(metadata["anomaly_key"], []).append(metadata["sample_id"])
    assert len(DEMO_SCENARIOS) == 36
    assert len(grouped) == 12
    assert all(sorted(ids) == ["01", "02", "03"] for ids in grouped.values())


def test_new_audio_families_are_registered_and_critical():
    from aura_mas.agents.policy_agent import SEVERITY_MAP

    expected = {"distress_vocalization": "audio_scream",
                "gunshot_impulse": "audio_gunshot"}
    for anomaly_key, event_type in expected.items():
        entries = [item for item in DEMO_SCENARIOS.values()
                   if item["anomaly_key"] == anomaly_key]
        assert len(entries) == 3
        assert all(item["detected_event_types"] == [event_type] for item in entries)
        assert EVENT_FAMILIES[event_type] == "violence_or_hazard"
        assert SEVERITY_MAP[event_type] == "CRITICAL"


def test_new_scenarios_are_multicamera_aligned_and_registered():
    assert len(set(NEW_MULTI_CAMERA.values())) == 4
    for name, event_type in NEW_MULTI_CAMERA.items():
        manifest = _manifest(name)
        cameras = [sensor for sensor in manifest["sensors"] if sensor["type"] == "camera"]
        assert len(cameras) >= 2
        assert manifest["ground_truth"]
        assert {gt["event_type"] for gt in manifest["ground_truth"]} == {event_type}
        assert event_type in EVENT_FAMILIES
        shared_zones = set.intersection(
            *({zone["name"] for zone in camera["zones"]} for camera in cameras)
        )
        assert shared_zones
        for camera in cameras:
            source = ROOT / camera["source"]
            assert source.is_file() and source.stat().st_size > 0


def test_real_media_provenance_covers_demo_sources_and_citations():
    provenance = json.loads((ROOT / "data" / "clips_real" / "manifest.json").read_text())
    serialized = json.dumps(provenance)
    assert "CAVIARDATA1" in serialized
    assert "Creative Commons BY-SA" in serialized
    assert "10.1016/j.dib.2020.106587" in serialized
    assert "ABODA" in serialized
    report = (ROOT / "research" / "reports" / "anomaly_type_survey_multizone.md").read_text()
    for citation in (
        "ultralytics.com/models/yolo11",
        "2110.06864",
        "WACV Workshops 2024",
        "10.1016/j.anucene.2017.11.026",
        "1803.01160",
        "10.1016/j.dib.2020.106587",
    ):
        assert citation in report
