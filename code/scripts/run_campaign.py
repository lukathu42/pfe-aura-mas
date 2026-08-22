"""Campaign v2 driver: runs the full scenario x mode x ablation x rep matrix.

No shell/Makefile driver existed anywhere in the repo before this; the v1
campaign (results/evaluation_campaign_notes.md) was a hand-typed loop. This
script owns the grid, runs each combination as a FRESH subprocess (not an
in-process loop) so TF/YOLO/CLIP thread pools, ByteTrack state, and
PYTHONHASHSEED don't leak between runs and one crashing run doesn't take
down the campaign, resumes by skipping any (scenario, mode, ...) combo whose
output JSON already exists, and aborts if free disk drops below a floor.

Usage:
  python -m aura_mas.scripts.run_campaign --reps 5                  # headline
  python -m aura_mas.scripts.run_campaign --reps 3 --audio-backend dsp \\
      --scenarios audio_glass_break_01,combined_audio_video_01,...   # ablation
  python -m aura_mas.scripts.run_campaign --dry-run                 # print the grid
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from aura_mas.core.utils import run_output_path, run_tag

MODES = ["mas-auction", "mas-rules", "mas-nocoord", "centralized"]
LOG_PATH = "results/campaign_log.csv"
LOG_FIELDS = ["tag", "scenario", "mode", "vision_only", "audio_backend",
             "rep", "rc", "seconds", "started_iso", "out_path"]


def scenario_has_audio(manifest_path: str) -> bool:
    with open(manifest_path) as f:
        manifest = json.load(f)
    return any(s["type"] == "audio" for s in manifest["sensors"])


def build_grid(scenario_paths: List[str], modes: List[str], reps: List[int],
               audio_backend: str, include_vision_only: bool) -> List[dict]:
    grid = []
    for path in scenario_paths:
        with open(path) as f:
            name = json.load(f)["name"]
        has_audio = scenario_has_audio(path)
        vo_options = [False, True] if (has_audio and include_vision_only) else [False]
        for mode in modes:
            for vision_only in vo_options:
                for rep in reps:
                    grid.append({
                        "manifest": path, "scenario": name, "mode": mode,
                        "vision_only": vision_only,
                        "audio_backend": audio_backend if has_audio else "auto",
                        "rep": rep,
                    })
    return grid


def tag_for(run: dict) -> str:
    return run_tag(run["mode"], run["vision_only"], run["audio_backend"],
                   run["rep"])


def out_path_for(run: dict) -> str:
    return run_output_path(run["scenario"], tag_for(run))


def free_gb(path: str = ".") -> float:
    return shutil.disk_usage(path).free / 1e9


def append_log(row: dict) -> None:
    Path("results").mkdir(exist_ok=True)
    new_file = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)


def run_one(run: dict, min_free_gb: float) -> int:
    out = out_path_for(run)
    if os.path.exists(out):
        print(f"skip (exists): {out}")
        return 0

    free = free_gb()
    if free < min_free_gb:
        print(f"ABORT: free disk {free:.1f}G < floor {min_free_gb}G")
        raise SystemExit(1)

    cmd = [sys.executable, "-m", "aura_mas.scenarios.replay", run["manifest"],
           "--mode", run["mode"], "--bus", "local",
           "--audio-backend", run["audio_backend"]]
    if run["vision_only"]:
        cmd.append("--vision-only")
    if run["rep"] is not None:
        cmd += ["--rep", str(run["rep"])]

    started = time.time()
    started_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started))
    print(f"RUN {out} :: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    seconds = round(time.time() - started, 1)

    append_log({
        "tag": tag_for(run), "scenario": run["scenario"], "mode": run["mode"],
        "vision_only": run["vision_only"], "audio_backend": run["audio_backend"],
        "rep": run["rep"], "rc": proc.returncode, "seconds": seconds,
        "started_iso": started_iso, "out_path": out,
    })
    if proc.returncode != 0:
        print(f"FAILED rc={proc.returncode} ({seconds}s): {out}")
        print(proc.stderr[-3000:])
    else:
        print(f"ok ({seconds}s): {out}")
    return proc.returncode


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenarios", default=None,
                   help="comma-separated scenario names (default: all in scenarios/)")
    p.add_argument("--modes", default=",".join(MODES))
    p.add_argument("--reps", default="0,1,2,3,4",
                   help="comma-separated rep indices")
    p.add_argument("--audio-backend", default="auto", choices=["auto", "yamnet", "dsp"])
    p.add_argument("--no-vision-only", action="store_true",
                   help="skip the vision-only ablation runs")
    p.add_argument("--min-free-gb", type=float, default=5.0)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    all_paths = sorted(glob.glob("scenarios/*.json"))
    if args.scenarios:
        wanted = set(args.scenarios.split(","))
        paths = [p_ for p_ in all_paths
                if json.load(open(p_))["name"] in wanted]
    else:
        paths = all_paths

    modes = args.modes.split(",")
    reps = [int(r) for r in args.reps.split(",")]
    grid = build_grid(paths, modes, reps, args.audio_backend,
                      include_vision_only=not args.no_vision_only)

    print(f"Grid: {len(grid)} runs "
          f"({len(paths)} scenarios x {len(modes)} modes x {len(reps)} reps, "
          f"audio_backend={args.audio_backend}, "
          f"vision_only={'off' if args.no_vision_only else 'on'})")
    if args.dry_run:
        for r in grid:
            print(" ", out_path_for(r))
        return

    failures = 0
    for i, run in enumerate(grid):
        print(f"[{i + 1}/{len(grid)}]", end=" ")
        rc = run_one(run, args.min_free_gb)
        if rc != 0:
            failures += 1
    print(f"\nCampaign done: {len(grid)} runs, {failures} failures. "
         f"Log: {LOG_PATH}")


if __name__ == "__main__":
    main()
