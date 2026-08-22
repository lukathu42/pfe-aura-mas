"""Offline tests for the LLM-as-judge pilot scaffolding
(docs/ai-enhancement-research.md Section 4.1; results/explanation_judge_notes.md).

Covers only the pure logic (fallback-vs-real explanation filtering,
summary stats, human-agreement computation) -- no network calls, no API
keys needed, consistent with the rest of aura_mas/tests.
"""
from __future__ import annotations

import json

from aura_mas.eval.llm_judge import (compare_to_human_labels,
                                     load_real_explanations, summarize)

FALLBACK_TEMPLATE = ("[CRITICAL] intrusion detected in zone 'zone_A' with fused "
                    "confidence 0.78, corroborated by 1 event(s) from 1 sensor(s) "
                    "(video). Evidence attached; awaiting operator acknowledgment.")

REAL_EXPLANATION = ("Person entered restricted zone_A and remained for several "
                    "seconds.\n\nReasoning: video detection confirmed by "
                    "re-verification.\nEvidence: ev_abc123\n"
                    "Recommended action: operator review")


def _write_jsonl(path, rows):
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_load_real_explanations_filters_out_fallback_templates(tmp_path):
    path = tmp_path / "alerts_test.jsonl"
    _write_jsonl(path, [
        {"alert_id": "alt_1", "explanation": FALLBACK_TEMPLATE},
        {"alert_id": "alt_2", "explanation": REAL_EXPLANATION},
    ])
    rows = load_real_explanations(str(tmp_path / "alerts_*.jsonl"))
    assert len(rows) == 1
    assert rows[0]["alert_id"] == "alt_2"


def test_load_real_explanations_respects_limit(tmp_path):
    path = tmp_path / "alerts_test.jsonl"
    _write_jsonl(path, [
        {"alert_id": f"alt_{i}", "explanation": REAL_EXPLANATION} for i in range(5)
    ])
    rows = load_real_explanations(str(tmp_path / "alerts_*.jsonl"), limit=2)
    assert len(rows) == 2


def test_summarize_computes_means_and_pass_rate():
    scored = [
        {"scores": {"grounding": 5, "severity_calibration": 4,
                    "conciseness": 3, "actionability": 5, "passed": True}},
        {"scores": {"grounding": 3, "severity_calibration": 4,
                    "conciseness": 5, "actionability": 3, "passed": False}},
    ]
    summary = summarize(scored)
    assert summary["n"] == 2
    assert summary["grounding_mean"] == 4.0
    assert summary["pass_rate"] == 0.5


def test_compare_to_human_labels_reports_exact_match_rate(tmp_path):
    scored = [
        {"alert_id": "alt_1", "scores": {"grounding": 5, "severity_calibration": 4,
                                         "conciseness": 3, "actionability": 5,
                                         "passed": True}},
        {"alert_id": "alt_2", "scores": {"grounding": 2, "severity_calibration": 2,
                                         "conciseness": 2, "actionability": 2,
                                         "passed": False}},
    ]
    human_path = tmp_path / "human.json"
    with open(human_path, "w") as f:
        json.dump([
            {"alert_id": "alt_1", "grounding": 5, "severity_calibration": 4,
             "conciseness": 3, "actionability": 4, "passed": True},
            {"alert_id": "alt_2", "grounding": 2, "severity_calibration": 3,
             "conciseness": 2, "actionability": 2, "passed": False},
        ], f)

    agreement = compare_to_human_labels(scored, str(human_path))
    assert agreement["n_overlap"] == 2
    assert agreement["grounding_exact_match_rate"] == 1.0
    assert agreement["actionability_exact_match_rate"] == 0.5
    assert agreement["passed_exact_match_rate"] == 1.0
