"""System-level evaluation metrics for AURA-MAS.

Computes, from scenario run JSONs produced by `scenarios/replay.py`:
- event-level precision / recall / F1 (alert matched to a GT event if same
  family and alert time within [t_start - tol, t_end + tol]),
- mean time-to-alert (alert wall time minus GT event start),
- false alerts per hour,
- coordination overhead (messages, allocation latency),
- per-agent inference latency.

Usage:
  python -m aura_mas.eval.metrics results/run_*.json --out results/summary.csv
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
from typing import Dict, List

from aura_mas.core.taxonomy import EVENT_FAMILIES as FAMILY

AGG_METRICS = (
    "precision", "recall", "f1", "mean_time_to_alert_s",
    "false_alerts_per_hour", "coord_messages", "mean_allocation_ms",
    "wall_seconds",
)
GROUP_KEYS = ("scenario", "mode", "audio_backend")


def evaluate_run(run: Dict, tolerance: float = 5.0) -> Dict:
    gt = run.get("ground_truth", [])
    alerts = run.get("alerts", [])
    t0 = run["t_start"]

    matched_gt, matched_alerts = set(), set()
    time_to_alert: List[float] = []

    for gi, g in enumerate(gt):
        g_fam = FAMILY.get(g["event_type"], g["event_type"])
        for ai, a in enumerate(alerts):
            if ai in matched_alerts:
                continue
            a_fam = FAMILY.get(a["event_type"], a["event_type"])
            a_t = a["t_wall"] - t0
            if a_fam == g_fam and (g["t_start"] - tolerance) <= a_t <= (
                    g.get("t_end", g["t_start"]) + tolerance):
                matched_gt.add(gi)
                matched_alerts.add(ai)
                time_to_alert.append(max(0.0, a_t - g["t_start"]))
                break

    tp = len(matched_gt)
    fp = len(alerts) - len(matched_alerts)
    fn = len(gt) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    hours = max(run.get("wall_seconds", 1) / 3600.0, 1e-6)

    coord = run.get("agent_metrics", {}).get("coordinator", {})
    alloc = coord.get("allocation_ms", [])

    mode_label = run["mode"] + ("-visiononly" if run.get("vision_only") else "")
    return {
        "scenario": run["scenario"], "mode": mode_label,
        "audio_backend": run.get("audio_backend", "auto"),
        "rep": run.get("rep"), "tag": run.get("tag"),
        "gt_events": len(gt), "alerts": len(alerts),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3), "recall": round(recall, 3),
        "f1": round(f1, 3),
        "mean_time_to_alert_s": round(sum(time_to_alert) / len(time_to_alert), 2)
        if time_to_alert else None,
        "false_alerts_per_hour": round(fp / hours, 1),
        "coord_messages": coord.get("messages", 0),
        "coord_tasks": coord.get("tasks", 0),
        "mean_allocation_ms": round(sum(alloc) / len(alloc), 1) if alloc else None,
        "wall_seconds": round(run.get("wall_seconds", 0), 1),
    }


def aggregate(rows: List[Dict], keys=GROUP_KEYS) -> List[Dict]:
    """Group per-run rows by `keys` (default scenario/mode/audio_backend) and
    emit mean/std/n for each metric in AGG_METRICS. Reps of the same
    (scenario, mode, audio_backend) combination are what get grouped -- `rep`
    itself is not a group key. std is the sample stdev (n-1); blank when
    n<2 rather than 0.0, since a single rep has no variance estimate, not
    zero variance. mean_time_to_alert_s excludes None entries (no TP, not a
    zero latency) before averaging.

    Rows with rep=None are excluded entirely -- those are single, ad-hoc
    runs from before the --rep campaign infrastructure existed (the v1
    pre-YAMNet campaign, or a one-off manual run). Pooling a single
    old-methodology run in with N real repetitions of a different
    methodology would silently corrupt the mean/std -- e.g. a v1 DSP-fallback
    run averaged together with v2 YAMNet reps as if it were just another
    sample of the same thing. Use results/summary.csv (unfiltered, one row
    per file) to see those runs individually instead."""
    rows = [r for r in rows if r.get("rep") is not None]
    groups: Dict[tuple, List[Dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r.get(k) for k in keys), []).append(r)

    agg_rows = []
    for key, group in groups.items():
        out = dict(zip(keys, key))
        out["n_reps"] = len(group)
        for metric in AGG_METRICS:
            vals = [r[metric] for r in group if r.get(metric) is not None]
            if not vals:
                out[f"{metric}_mean"] = None
                out[f"{metric}_std"] = None
            else:
                out[f"{metric}_mean"] = round(statistics.mean(vals), 3)
                out[f"{metric}_std"] = (
                    round(statistics.stdev(vals), 3) if len(vals) >= 2 else None)
        agg_rows.append(out)
    agg_rows.sort(key=lambda r: tuple(str(r[k]) for k in keys))
    return agg_rows


def _write_csv(rows: List[Dict], out_path: str) -> None:
    import csv
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+", help="run JSON files or globs")
    p.add_argument("--out", default="results/summary.csv")
    p.add_argument("--tolerance", type=float, default=5.0)
    p.add_argument("--agg-out", default=None,
                   help="write mean/std aggregated CSV here (default: "
                        "results/summary_agg.csv, auto-written whenever "
                        ">1 rep exists; pass 'none' to skip)")
    args = p.parse_args()

    paths: List[str] = []
    for pattern in args.runs:
        paths.extend(sorted(glob.glob(pattern)))

    rows = []
    for path in paths:
        with open(path) as f:
            rows.append(evaluate_run(json.load(f), args.tolerance))

    if not rows:
        print("no runs found")
        return

    _write_csv(rows, args.out)

    # pretty print
    cols = ["scenario", "mode", "f1", "precision", "recall",
            "mean_time_to_alert_s", "false_alerts_per_hour", "coord_messages"]
    widths = {c: max(len(c), *(len(str(r.get(c))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c)).ljust(widths[c]) for c in cols))
    print(f"\nsaved -> {args.out}")

    n_reps = len({r.get("rep") for r in rows if r.get("rep") is not None})
    agg_out = args.agg_out
    if agg_out is None and n_reps > 1:
        agg_out = "results/summary_agg.csv"
    if agg_out and agg_out.lower() != "none":
        agg_rows = aggregate(rows)  # excludes rep=None rows -- see aggregate() docstring
        if agg_rows:
            _write_csv(agg_rows, agg_out)
            print(f"saved -> {agg_out} ({len(agg_rows)} groups, up to {n_reps} reps each)")
        else:
            print("no rep-tagged runs found; skipping aggregate output")


if __name__ == "__main__":
    main()
