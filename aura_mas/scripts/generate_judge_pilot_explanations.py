"""Day-1 step of the LLM-as-judge pilot: generate real ExplanationAgent
output for the first time in this project's history.

docs/ai-enhancement-research.md Section 4.1 and results/explanation_judge_notes.md
explain why this script exists: three independent research threads found
that `OPENAI_API_KEY` has never been configured in this environment, so
every `explanation` field ever written to data/alerts_*.jsonl is the
deterministic fallback template, not a real LLM generation. This script
replays scenarios with `--llm` enabled to produce the first real
explanations, so aura_mas.eval.llm_judge has something to judge.

Writes to DISTINCT output paths (rep offset 900+) so it can never collide
with or overwrite the cited evaluation-campaign run/alert files (reps 0-4).
These runs are NOT part of the evaluation campaign and must not be included
in results/summary.csv or any results table -- they exist purely to produce
judge-pilot input data.

Usage:
  export OPENAI_API_KEY=...
  python -m aura_mas.scripts.generate_judge_pilot_explanations
  python -m aura_mas.scripts.generate_judge_pilot_explanations \\
      --scenarios intrusion_01,fight_01 --reps 2
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os

from aura_mas.scenarios.replay import run_scenario
from aura_mas.telemetry import configure_logging, configure_tracing

log = logging.getLogger("aura.generate_judge_pilot_explanations")

REP_OFFSET = 900  # far outside the real campaign's 0-4 rep range, see module docstring


def main() -> None:
    configure_logging()
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scenarios", default=None,
                   help="comma-separated scenario names (default: all in scenarios/)")
    p.add_argument("--reps", type=int, default=3,
                   help="repetitions per scenario (more reps -> more alerts "
                        "-> more judge-pilot samples, at proportional API cost)")
    p.add_argument("--mode", default="mas-auction",
                   choices=["mas-auction", "mas-rules", "mas-nocoord"],
                   help="coordinator mode (default: the thesis's main mode)")
    args = p.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. ExplanationAgent's default generator "
            "path needs it -- see aura_mas/agents/explanation_agent.py:_get_client. "
            "Without it every run below would just repeat the fallback-template "
            "situation this script exists to fix.")

    configure_tracing()  # also now persists spans to data/otel_spans.jsonl

    all_paths = sorted(glob.glob("scenarios/*.json"))
    if args.scenarios:
        wanted = set(args.scenarios.split(","))
        all_paths = [p_ for p_ in all_paths
                    if json.load(open(p_))["name"] in wanted]
    if not all_paths:
        raise SystemExit("no scenario manifests found for the requested --scenarios")

    total_alerts = 0
    for path in all_paths:
        for r in range(args.reps):
            rep = REP_OFFSET + r
            result = run_scenario(path, mode=args.mode, bus_kind="local",
                                  use_llm=True, rep=rep)
            n = len(result["alerts"])
            total_alerts += n
            log.info("scenario=%s rep=%d: %d alert(s) -> data/alerts_%s_%s-r%d.jsonl",
                     result["scenario"], rep, n, result["scenario"], args.mode, rep)

    print(f"\ngenerated {total_alerts} alert(s) across {len(all_paths)} "
         f"scenario(s) x {args.reps} rep(s), tagged rep>=900 (judge-pilot "
         "only, not part of the evaluation campaign).")
    print("Next: python -m aura_mas.eval.llm_judge --limit 30")


if __name__ == "__main__":
    main()
