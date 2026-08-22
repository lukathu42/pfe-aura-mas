"""Small shared helpers for run naming and tabular output.

`run_tag` / `run_output_path` are the single source of truth for the
filenames of run artifacts (results/run_*.json, data/alerts_*.jsonl,
results/campaign_log.csv rows). The same logic previously lived in three
places (scenarios/replay.py and twice in scripts/run_campaign.py); a drift
between them would silently break the campaign driver's skip-if-exists
resume logic. The tag format itself must stay stable — it is embedded in
already-cited artifact filenames.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional


def run_tag(mode: str, vision_only: bool = False, audio_backend: str = "auto",
            rep: Optional[int] = None) -> str:
    tag = mode
    if vision_only:
        tag += "-visiononly"
    if audio_backend != "auto":
        tag += f"-{audio_backend}"
    if rep is not None:
        tag += f"-r{rep}"
    return tag


def run_output_path(scenario: str, tag: str) -> str:
    return f"results/run_{scenario}_{tag}.json"


def round_mean(vals: List[float], ndigits: int = 1) -> Optional[float]:
    """Rounded arithmetic mean; None (not 0.0) for an empty list."""
    if not vals:
        return None
    return round(sum(vals) / len(vals), ndigits)


def write_csv(rows: List[Dict], out_path: str) -> None:
    """Write dict rows to CSV, creating parent directories as needed."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
