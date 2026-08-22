"""Self-play trainer for the toy `auction-bandit` CoordinatorAgent mode.

Trains a LinUCB contextual bandit (aura_mas.core.bandit) purely against
AURA-MAS's own CPU replay harness -- no live environment, no GPU, no
external training data. Each episode replays one of the existing scenario
manifests in `mas-auction-bandit` mode; the bandit's reward signal is the
in-process verification outcome CoordinatorAgent already computes (see
coordinator_agent.py:request_verification), so no ground-truth labels are
needed beyond what the scenario replay already produces.

This is explicitly a toy proof-of-concept, not a validated improvement over
the hand-coded `mas-auction` heuristic: only 6-9 fixed scenario clips exist
project-wide, so self-play can at best make the bandit qualitatively
rediscover something resembling the existing `_view_score` heuristic, not
demonstrate held-out generalization. See results/auction_bandit_notes.md and
docs/ai-enhancement-research.md Section 4.2 for the full research
justification and the explicit warning against overclaiming these results.

Usage:
  python -m aura_mas.scripts.train_auction_bandit --episodes 40
  python -m aura_mas.scripts.train_auction_bandit --episodes 20 \\
      --scenarios intrusion_01,loitering_01
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import random
from typing import List

from aura_mas.core.bandit import LinUCBBidder
from aura_mas.scenarios.replay import run_scenario
from aura_mas.telemetry import configure_logging

log = logging.getLogger("aura.train_auction_bandit")

DEFAULT_BANDIT_PATH = "results/auction_bandit_weights.json"
DEFAULT_HISTORY_PATH = "results/auction_bandit_train_history.json"


def _camera_ids(manifest_path: str) -> List[str]:
    with open(manifest_path) as f:
        manifest = json.load(f)
    return [s["id"] for s in manifest["sensors"] if s["type"] == "camera"]


def main() -> None:
    configure_logging()
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scenarios", default=None,
                   help="comma-separated scenario names (default: all in scenarios/)")
    p.add_argument("--episodes", type=int, default=40,
                   help="total self-play episodes, drawn with replacement "
                        "across the selected scenarios")
    p.add_argument("--alpha", type=float, default=1.0,
                   help="LinUCB exploration coefficient (only used when "
                        "initializing fresh weights)")
    p.add_argument("--bandit-path", default=DEFAULT_BANDIT_PATH)
    p.add_argument("--history-path", default=DEFAULT_HISTORY_PATH)
    p.add_argument("--fresh", action="store_true",
                   help="discard any existing weights at --bandit-path and "
                        "start over instead of continuing to train them")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    all_paths = sorted(glob.glob("scenarios/*.json"))
    if args.scenarios:
        wanted = set(args.scenarios.split(","))
        all_paths = [p_ for p_ in all_paths
                    if json.load(open(p_))["name"] in wanted]
    if not all_paths:
        raise SystemExit("no scenario manifests found for the requested --scenarios")

    rng = random.Random(args.seed)
    os.makedirs("results", exist_ok=True)

    if args.fresh and os.path.exists(args.bandit_path):
        os.remove(args.bandit_path)

    all_cams: List[str] = []
    for path in all_paths:
        for cam in _camera_ids(path):
            if cam not in all_cams:
                all_cams.append(cam)
    if not os.path.exists(args.bandit_path):
        LinUCBBidder(all_cams, alpha=args.alpha).save(args.bandit_path)
        log.info("initialized fresh bandit weights at %s (arms=%s)",
                 args.bandit_path, all_cams)
    else:
        log.info("continuing training from existing weights at %s",
                 args.bandit_path)

    history = []
    for ep in range(args.episodes):
        manifest_path = rng.choice(all_paths)
        tmp_out = f"results/_bandit_train_ep{ep}.json"
        result = run_scenario(manifest_path, mode="mas-auction-bandit",
                              bus_kind="local", bandit_path=args.bandit_path,
                              out_path=tmp_out)
        coord = result["agent_metrics"]["coordinator"]
        history.append({
            "episode": ep, "scenario": result["scenario"],
            "tasks": coord.get("tasks", 0),
            "bandit_decisions": coord.get("bandit_decisions", 0),
            "verifications": coord.get("verifications", 0),
        })
        log.info("episode %d/%d scenario=%s tasks=%d verifications=%d",
                 ep + 1, args.episodes, result["scenario"],
                 coord.get("tasks", 0), coord.get("verifications", 0))
        if os.path.exists(tmp_out):
            os.remove(tmp_out)

    with open(args.history_path, "w") as f:
        json.dump(history, f, indent=2)

    bandit = LinUCBBidder.load(args.bandit_path)
    log.info("done: %d episodes, %d total bandit updates, weights -> %s, "
             "history -> %s", args.episodes, bandit.n_updates,
             args.bandit_path, args.history_path)
    print(f"\ntoy auction-bandit self-play complete: {args.episodes} episodes, "
         f"{bandit.n_updates} bandit updates.")
    print("This is an illustrative PoC only -- see results/auction_bandit_notes.md "
         "before citing anything from it as a performance result.")


if __name__ == "__main__":
    main()
