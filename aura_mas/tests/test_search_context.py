from pathlib import Path

from aura_mas import contextual
from aura_mas.search_index import documents_from_replay, search_documents


DOCS = [
    {"document_id": "a", "title": "Left Bag", "event_type": "abandoned_object",
     "search_text": "left bag abandoned object gate cam_01", "scenario": "bag_01",
     "anomaly_key": "abandoned_object", "zone": "gate", "sensors": ["cam_01"],
     "scene_time_seconds": 12.0},
    {"document_id": "b", "title": "Fight", "event_type": "anomaly",
     "search_text": "fight chase lobby cam_02", "scenario": "fight_01",
     "anomaly_key": "violence", "zone": "lobby", "sensors": ["cam_02"],
     "scene_time_seconds": 4.0},
]


def test_search_ranking_and_filters():
    assert search_documents(DOCS, "bag")[0]["scenario"] == "bag_01"
    assert search_documents(DOCS, "fight", anomaly_key="violence")[0]["scenario"] == "fight_01"
    assert search_documents(DOCS, "", zone="gate", sensor="cam_01")[0]["document_id"] == "a"


def test_audio_search_aliases_are_indexed():
    replay = {"scenario": "audio_distress_01", "metadata": {
        "title": "Distress Vocalization", "anomaly_key": "distress_vocalization",
    }, "timeline": [{"kind": "alert", "scene_time_seconds": 15,
                     "payload": {"event_type": "audio_scream", "sensors": ["mic_01"]}}]}
    document = documents_from_replay(replay)[0]
    assert "cry for help" in document["search_text"]
    assert search_documents([document], "yell")[0]["scenario"] == "audio_distress_01"


def test_context_provider_failure_falls_back(monkeypatch):
    replay = {"scenario": "demo", "metadata": {"description": "Known detector event"}, "alerts": []}
    monkeypatch.setattr(contextual, "vlm_annotation", lambda *_: (_ for _ in ()).throw(RuntimeError("offline")))
    result = contextual.annotation_with_fallback(replay, Path("missing.mp4"), [1.0])
    assert result["source"] == "deterministic"
    assert result["status"] == "failed"
    assert "offline" not in str(result)
