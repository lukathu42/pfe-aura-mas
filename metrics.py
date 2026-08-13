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
from typing import Dict, List

FAMILY = {
    "intrusion": "security", "loitering": "security",
    "abandoned_object": "security", "anomaly": "violence_or_hazard",
    "audio_scream": "violence_or_hazard", "audio_glass_break": "security",
    "audio_gunshot": "violence_or_hazard", "audio_alarm": "hazard",
    "audio_anomaly": "violence_or_hazard",
}


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

    return {
        "scenario": run["scenario"], "mode": run["mode"],
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


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+", help="run JSON files or globs")
    p.add_argument("--out", default="results/summary.csv")
    p.add_argument("--tolerance", type=float, default=5.0)
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

    import csv
    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # pretty print
    cols = ["scenario", "mode", "f1", "precision", "recall",
            "mean_time_to_alert_s", "false_alerts_per_hour", "coord_messages"]
    widths = {c: max(len(c), *(len(str(r.get(c))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c)).ljust(widths[c]) for c in cols))
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
