from __future__ import annotations

import json
import time

from aura_mas.alert_priority import (
    AlertPriorityScorer,
    FEATURE_NAMES,
    build_dataset,
    evaluate_weights,
    label_alerts,
    save_model,
    train_logreg,
)
from aura_mas.agents.policy_agent import PolicyAgent
from aura_mas.core.bus import AlertStore, Event, LocalBus, new_id, now_ts


def _run_payload() -> dict:
    t0 = time.time()
    return {
        "scenario": "unit",
        "mode": "mas-auction",
        "t_start": t0,
        "ground_truth": [
            {"event_type": "intrusion", "zone": "zone_A", "t_start": 5.0, "t_end": 12.0}
        ],
        "alerts": [
            {
                "t_wall": t0 + 6.0,
                "alert_id": "alt_tp",
                "severity": "CRITICAL",
                "event_type": "intrusion",
                "confidence": 0.86,
                "zone": "zone_A",
                "sensors": ["cam_01"],
                "evidence": ["e.jpg"],
                "fused_events": ["ev_1"],
            },
            {
                "t_wall": t0 + 40.0,
                "alert_id": "alt_fp",
                "severity": "INFO",
                "event_type": "loitering",
                "confidence": 0.72,
                "zone": "zone_A",
                "sensors": ["cam_01"],
                "evidence": [],
                "fused_events": ["ev_2"],
            },
        ],
    }


def test_label_alerts_matches_eval_family_and_time_window():
    labels = {alert["alert_id"]: label for alert, label in label_alerts(_run_payload())}
    assert labels == {"alt_tp": 1, "alt_fp": 0}


def test_train_save_load_and_predict_alert_priority(tmp_path):
    run_path = tmp_path / "run.json"
    run_path.write_text(json.dumps(_run_payload()))
    rows = build_dataset([str(run_path)])

    weights = train_logreg(rows, epochs=80)
    metrics = evaluate_weights(rows, weights)
    assert metrics["n"] == 2
    assert metrics["positives"] == 1

    model_path = tmp_path / "priority.json"
    save_model(str(model_path), weights, metrics, [str(run_path)])
    scorer = AlertPriorityScorer.load(str(model_path))

    tp = scorer.predict(_run_payload()["alerts"][0])
    fp = scorer.predict(_run_payload()["alerts"][1])
    assert tp.priority_score > fp.priority_score
    assert tp.false_positive_risk < fp.false_positive_risk


def test_policy_agent_adds_priority_fields(tmp_path):
    scorer = AlertPriorityScorer(weights=[0.0] * len(FEATURE_NAMES))
    ev = Event(event_id=new_id("ev"), sensor_id="cam_01", timestamp=now_ts(),
               event_type="intrusion", confidence=0.9, modality="video",
               zone="zone_A")

    class Hyp:
        hypothesis_id = "hyp_priority"
        zone = "zone_A"
        confidence = 0.9
        events = [ev]
        sensors = {"cam_01"}

        def dominant_type(self) -> str:
            return "intrusion"

    store = AlertStore(redis_url=None, jsonl_path=str(tmp_path / "alerts.jsonl"),
                       db_path=None)
    policy = PolicyAgent("policy", LocalBus(), store, priority_scorer=scorer)
    alert = policy.on_hypothesis(Hyp())

    assert alert is not None
    assert alert.priority_model_version == "alert-priority-logreg-v1"
    assert alert.priority_score == 0.5
    assert alert.false_positive_risk == 0.5
    assert alert.priority_label == "MEDIUM"
