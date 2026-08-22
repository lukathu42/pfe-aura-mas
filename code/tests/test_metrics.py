"""Evaluation-metric tests.

These guard the numbers the thesis cites: family-level alert matching,
tolerance windows, one-alert-per-GT-event matching, and the aggregate
mean/std rules documented in `aggregate()` (rep=None rows excluded, std
blank for n<2, None latencies excluded rather than counted as zero).
"""
from __future__ import annotations

import csv
import json

import pytest

from aura_mas.eval.metrics import _write_csv, aggregate, evaluate_run, main

T0 = 1_000_000.0


def make_run(alerts=(), gt=(), **kwargs) -> dict:
    run = {"scenario": "intrusion_01", "mode": "mas-auction", "t_start": T0,
           "wall_seconds": 60.0, "ground_truth": list(gt),
           "alerts": list(alerts)}
    run.update(kwargs)
    return run


def alert(offset: float, event_type: str = "intrusion",
          severity: str = "CRITICAL") -> dict:
    return {"t_wall": T0 + offset, "event_type": event_type,
            "severity": severity}


def gt_event(event_type: str = "intrusion", t_start: float = 10.0,
             t_end: float = 20.0) -> dict:
    return {"event_type": event_type, "zone": "zone_A",
            "t_start": t_start, "t_end": t_end}


def test_no_alerts_no_gt_yields_zero_scores_and_no_latency():
    m = evaluate_run(make_run())
    assert (m["tp"], m["fp"], m["fn"]) == (0, 0, 0)
    assert m["precision"] == 0.0 and m["recall"] == 0.0 and m["f1"] == 0.0
    assert m["mean_time_to_alert_s"] is None
    assert m["false_alerts_per_hour"] == 0.0


def test_missed_event_counts_as_false_negative():
    m = evaluate_run(make_run(gt=[gt_event()]))
    assert (m["tp"], m["fp"], m["fn"]) == (0, 0, 1)
    assert m["recall"] == 0.0 and m["precision"] == 0.0


def test_false_alerts_per_hour_scales_with_wall_seconds():
    m = evaluate_run(make_run(alerts=[alert(5.0)], wall_seconds=120.0))
    assert m["fp"] == 1 and m["false_alerts_per_hour"] == 30.0


@pytest.mark.parametrize("offset,is_match", [
    (4.9, False),   # before t_start - tolerance
    (5.0, True),    # exactly on the tolerance boundary
    (25.0, True),   # exactly on t_end + tolerance
    (25.1, False),
])
def test_tolerance_window_boundaries(offset, is_match):
    m = evaluate_run(make_run(alerts=[alert(offset)], gt=[gt_event()]))
    assert m["tp"] == (1 if is_match else 0)


def test_alert_matches_gt_of_the_same_family_not_only_same_type():
    # audio_glass_break and intrusion are both the "security" family
    m = evaluate_run(make_run(alerts=[alert(12.0, "audio_glass_break")],
                              gt=[gt_event("intrusion")]))
    assert m["tp"] == 1 and m["fp"] == 0


def test_alert_of_another_family_is_a_false_positive():
    m = evaluate_run(make_run(alerts=[alert(12.0, "audio_scream")],
                              gt=[gt_event("intrusion")]))
    assert (m["tp"], m["fp"], m["fn"]) == (0, 1, 1)


def test_each_alert_matches_at_most_one_ground_truth_event():
    m = evaluate_run(make_run(
        alerts=[alert(12.0)],
        gt=[gt_event(t_start=10.0, t_end=20.0), gt_event(t_start=11.0, t_end=21.0)]))
    assert (m["tp"], m["fp"], m["fn"]) == (1, 0, 1)


def test_duplicate_alerts_for_one_event_count_as_false_positives():
    m = evaluate_run(make_run(alerts=[alert(12.0), alert(13.0)],
                              gt=[gt_event()]))
    assert (m["tp"], m["fp"], m["fn"]) == (1, 1, 0)
    assert m["precision"] == 0.5 and m["recall"] == 1.0 and m["f1"] == 0.667


def test_time_to_alert_is_clamped_at_zero_for_early_alerts():
    m = evaluate_run(make_run(alerts=[alert(6.0)], gt=[gt_event()]))
    assert m["tp"] == 1 and m["mean_time_to_alert_s"] == 0.0


def test_time_to_alert_averages_over_matched_alerts():
    m = evaluate_run(make_run(
        alerts=[alert(12.0), alert(34.0, "audio_scream")],
        gt=[gt_event(), gt_event("audio_scream", 30.0, 40.0)]))
    assert m["tp"] == 2 and m["mean_time_to_alert_s"] == 3.0


def test_ground_truth_without_t_end_is_treated_as_an_instant():
    m = evaluate_run(make_run(alerts=[alert(12.0)],
                              gt=[{"event_type": "intrusion", "zone": "z",
                                   "t_start": 10.0}]))
    assert m["tp"] == 1


def test_tolerance_argument_is_honoured():
    run = make_run(alerts=[alert(28.0)], gt=[gt_event()])
    assert evaluate_run(run, tolerance=5.0)["tp"] == 0
    assert evaluate_run(run, tolerance=10.0)["tp"] == 1


def test_vision_only_runs_get_a_distinct_mode_label():
    m = evaluate_run(make_run(vision_only=True))
    assert m["mode"] == "mas-auction-visiononly"


def test_coordination_overhead_is_reported():
    m = evaluate_run(make_run(agent_metrics={"coordinator": {
        "messages": 12, "tasks": 3, "allocation_ms": [100.0, 200.0]}}))
    assert m["coord_messages"] == 12 and m["coord_tasks"] == 3
    assert m["mean_allocation_ms"] == 150.0


def test_missing_coordinator_metrics_default_to_zero():
    m = evaluate_run(make_run())
    assert m["coord_messages"] == 0 and m["coord_tasks"] == 0
    assert m["mean_allocation_ms"] is None
    assert m["audio_backend"] == "auto"


def agg_row(rep, f1, mtta=2.0, backend="yamnet", mode="mas-auction"):
    return {"scenario": "s1", "mode": mode, "audio_backend": backend,
            "rep": rep, "f1": f1, "precision": f1, "recall": f1,
            "mean_time_to_alert_s": mtta, "false_alerts_per_hour": 0.0,
            "coord_messages": 4, "mean_allocation_ms": 10.0,
            "wall_seconds": 60.0}


def test_aggregate_groups_reps_and_reports_mean_and_std():
    rows = aggregate([agg_row(0, 0.4), agg_row(1, 0.8)])
    assert len(rows) == 1
    assert rows[0]["n_reps"] == 2
    assert rows[0]["f1_mean"] == 0.6
    assert rows[0]["f1_std"] == pytest.approx(0.283, abs=1e-3)
    assert "rep" not in rows[0]


def test_aggregate_leaves_std_blank_for_a_single_rep():
    rows = aggregate([agg_row(0, 0.4)])
    assert rows[0]["n_reps"] == 1 and rows[0]["f1_std"] is None


def test_aggregate_excludes_untagged_runs():
    assert aggregate([agg_row(None, 0.9)]) == []
    rows = aggregate([agg_row(None, 0.9), agg_row(0, 0.4)])
    assert rows[0]["n_reps"] == 1 and rows[0]["f1_mean"] == 0.4


def test_aggregate_ignores_none_latencies_instead_of_counting_them_as_zero():
    rows = aggregate([agg_row(0, 0.4, mtta=None), agg_row(1, 0.8, mtta=4.0)])
    assert rows[0]["mean_time_to_alert_s_mean"] == 4.0
    assert rows[0]["mean_time_to_alert_s_std"] is None


def test_aggregate_all_none_metric_stays_none():
    rows = aggregate([agg_row(0, 0.4, mtta=None), agg_row(1, 0.8, mtta=None)])
    assert rows[0]["mean_time_to_alert_s_mean"] is None


def test_aggregate_separates_backends_and_sorts_groups():
    rows = aggregate([agg_row(0, 0.4, backend="yamnet"),
                      agg_row(0, 0.9, backend="dsp")])
    assert [r["audio_backend"] for r in rows] == ["dsp", "yamnet"]


def test_aggregate_supports_custom_group_keys():
    rows = aggregate([agg_row(0, 0.4, backend="dsp"),
                      agg_row(1, 0.8, backend="yamnet")], keys=("scenario",))
    assert len(rows) == 1 and rows[0]["n_reps"] == 2


def test_write_csv_creates_parent_directory(tmp_path):
    out = tmp_path / "nested" / "summary.csv"
    _write_csv([{"a": 1, "b": None}], str(out))
    rows = list(csv.DictReader(out.open()))
    assert rows == [{"a": "1", "b": ""}]


def write_run(tmp_path, name, **kwargs):
    path = tmp_path / f"run_{name}.json"
    path.write_text(json.dumps(make_run(**kwargs)))
    return path


def test_main_writes_summary_and_aggregate(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_run(tmp_path, "r0", alerts=[alert(12.0)], gt=[gt_event()], rep=0)
    write_run(tmp_path, "r1", alerts=[alert(13.0)], gt=[gt_event()], rep=1)
    monkeypatch.setattr("sys.argv",
                        ["metrics", str(tmp_path / "run_*.json"),
                         "--out", "results/summary.csv"])
    main()

    summary = list(csv.DictReader((tmp_path / "results" / "summary.csv").open()))
    assert len(summary) == 2 and {r["scenario"] for r in summary} == {"intrusion_01"}
    agg = list(csv.DictReader((tmp_path / "results" / "summary_agg.csv").open()))
    assert len(agg) == 1 and agg[0]["n_reps"] == "2"
    out = capsys.readouterr().out
    assert "summary.csv" in out and "summary_agg.csv" in out


def test_main_skips_aggregate_when_asked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_run(tmp_path, "r0", rep=0)
    write_run(tmp_path, "r1", rep=1)
    monkeypatch.setattr("sys.argv",
                        ["metrics", str(tmp_path / "run_*.json"),
                         "--out", "out.csv", "--agg-out", "none"])
    main()
    assert (tmp_path / "out.csv").exists()
    assert not (tmp_path / "results").exists()


def test_main_reports_when_no_rep_tagged_runs_exist(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_run(tmp_path, "single")
    monkeypatch.setattr("sys.argv",
                        ["metrics", str(tmp_path / "run_*.json"),
                         "--out", "out.csv", "--agg-out", "agg.csv"])
    main()
    assert "no rep-tagged runs found" in capsys.readouterr().out
    assert not (tmp_path / "agg.csv").exists()


def test_main_with_no_matching_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["metrics", str(tmp_path / "nothing_*.json")])
    main()
    assert capsys.readouterr().out.strip() == "no runs found"
