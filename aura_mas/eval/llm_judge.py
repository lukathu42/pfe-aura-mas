"""LLM-as-judge pilot for `ExplanationAgent` output quality.

Pursue-Now item #1 from docs/ai-enhancement-research.md (Section 4.1). This
is scaffolding that needs a live API key to actually run -- see
results/explanation_judge_notes.md for the exact two-step pilot procedure
(generate real explanations first, then judge them) and its explicit
limitations framing.

Design, per the research report's own reasoning:
- Reference-based scoring against the alert's own JSON payload, NOT
  pairwise A/B comparison -- sidesteps position bias entirely (no pair to
  swap) and reduces verbosity-bias sensitivity vs. free-form comparison.
- Default judge backend is Anthropic while the default generator
  (ExplanationAgent's `gpt-4.1-mini`) is OpenAI -- a deliberate
  different-model-family choice to avoid the "grading your own homework"
  self-preference-bias risk documented in Zheng et al. 2023 (arXiv:2306.05685)
  and Panickssery et al. 2024. Do not point --backend at the same family as
  the generator without a documented reason in the writeup.
- Only judges alerts whose `explanation` field is a REAL LLM generation
  (detected via the "\\n\\nReasoning: " marker that only `ExplanationAgent.explain()`'s
  real path emits -- both the ExplanationAgent and PolicyAgent fallback
  templates start with "[SEVERITY]" and never contain that marker). As of
  this research pass every alert on disk is a fallback template
  (`results/explanation_eval_notes.md`), so this filter will discard
  everything until real explanations are generated -- that is expected, not
  a bug; see aura_mas/scripts/generate_judge_pilot_explanations.py.

Usage (once an API key is available):
  export ANTHROPIC_API_KEY=...
  python -m aura_mas.eval.llm_judge --limit 30
  python -m aura_mas.eval.llm_judge --limit 30 --human-labels my_labels.json
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Optional

from aura_mas.eval.judge_schema import JudgeScore
from aura_mas.telemetry import configure_logging

log = logging.getLogger("aura.llm_judge")

REAL_EXPLANATION_MARKER = "\n\nReasoning: "

JUDGE_SYSTEM_PROMPT = """You are an independent quality reviewer for a physical-\
security surveillance system's automatically generated incident-alert \
explanations. You did NOT write the explanation you are reviewing. Score it \
strictly against the alert data provided -- do not reward confident or \
well-written prose that isn't actually supported by the data. Be skeptical: \
your job is to catch overclaiming, miscalibrated severity language, padding, \
and inappropriate recommended actions, not to be lenient."""


def _judge_user_prompt(alert: Dict, explanation: str) -> str:
    payload = {
        "alert": {
            "severity": alert.get("severity"),
            "event_type": alert.get("event_type"),
            "confidence": alert.get("confidence"),
            "zone": alert.get("zone"),
            "sensors": alert.get("sensors"),
            "fused_events": alert.get("fused_events"),
        },
        "explanation_to_review": explanation,
    }
    return json.dumps(payload, indent=2)


def load_real_explanations(alerts_glob: str, limit: Optional[int] = None) -> List[Dict]:
    """Reads data/alerts_*.jsonl-style files and returns only alerts whose
    explanation is a real LLM generation, not a fallback template."""
    rows: List[Dict] = []
    for path in sorted(glob.glob(alerts_glob)):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                alert = json.loads(line)
                explanation = alert.get("explanation") or ""
                if REAL_EXPLANATION_MARKER in explanation:
                    alert["_source_file"] = path
                    rows.append(alert)
    if limit is not None:
        rows = rows[:limit]
    return rows


def _get_judge_client(backend: str, model: str):
    import instructor
    if backend == "anthropic":
        from anthropic import Anthropic
        return instructor.from_anthropic(Anthropic()), model
    if backend == "openai":
        from openai import OpenAI
        return instructor.from_openai(OpenAI()), model
    raise ValueError(f"unknown judge backend: {backend!r}")


def judge_one(client, model: str, backend: str, alert: Dict, explanation: str,
              max_tokens: int = 500) -> JudgeScore:
    user_prompt = _judge_user_prompt(alert, explanation)
    if backend == "anthropic":
        return client.messages.create(
            model=model, max_tokens=max_tokens,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            response_model=JudgeScore,
        )
    return client.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                 {"role": "user", "content": user_prompt}],
        response_model=JudgeScore,
    )


def summarize(scored: List[Dict]) -> Dict:
    if not scored:
        return {"n": 0}
    axes = ("grounding", "severity_calibration", "conciseness", "actionability")
    out = {"n": len(scored)}
    for axis in axes:
        vals = [s["scores"][axis] for s in scored]
        out[f"{axis}_mean"] = round(statistics.mean(vals), 2)
    out["pass_rate"] = round(sum(1 for s in scored if s["scores"]["passed"]) / len(scored), 3)
    return out


def compare_to_human_labels(scored: List[Dict], human_labels_path: str) -> Dict:
    """Rough agreement check against a small human-labeled subset -- NOT a
    substitute for real inter-rater-reliability statistics (Cohen's kappa
    etc.), just a sanity signal for a small-N pilot. Expected format: a JSON
    list of objects with alert_id + the same axes as JudgeScore."""
    with open(human_labels_path) as f:
        human = {row["alert_id"]: row for row in json.load(f)}
    by_id = {s["alert_id"]: s for s in scored}
    overlap = [aid for aid in human if aid in by_id]
    if not overlap:
        return {"n_overlap": 0, "note": "no alert_ids in human_labels matched judged alerts"}

    axes = ("grounding", "severity_calibration", "conciseness", "actionability")
    agreement: Dict[str, float] = {}
    for axis in axes:
        exact = sum(1 for aid in overlap
                   if human[aid][axis] == by_id[aid]["scores"][axis])
        agreement[f"{axis}_exact_match_rate"] = round(exact / len(overlap), 3)
    pass_exact = sum(1 for aid in overlap
                     if bool(human[aid].get("passed")) == by_id[aid]["scores"]["passed"])
    agreement["passed_exact_match_rate"] = round(pass_exact / len(overlap), 3)
    agreement["n_overlap"] = len(overlap)
    return agreement


def main() -> None:
    configure_logging()
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alerts", default="data/alerts_*.jsonl",
                   help="glob for alert JSONL files to judge")
    p.add_argument("--backend", default="anthropic", choices=["anthropic", "openai"],
                   help="judge model provider (default: anthropic, a "
                        "different family than the gpt-4.1-mini generator "
                        "-- see module docstring)")
    p.add_argument("--model", default="claude-sonnet-4-5-20250929",
                   help="judge model name (pick one matching --backend)")
    p.add_argument("--limit", type=int, default=30,
                   help="max alerts to judge (cost/rate-limit control)")
    p.add_argument("--out", default="results/explanation_judge_scores.jsonl")
    p.add_argument("--human-labels", default=None,
                   help="optional path to a small human-labeled JSON subset "
                        "for a rough agreement check (see compare_to_human_labels)")
    args = p.parse_args()

    real = load_real_explanations(args.alerts, limit=args.limit)
    log.info("found %d alerts with real (non-fallback) explanations "
             "matching %s", len(real), args.alerts)
    if not real:
        print("No real LLM-generated explanations found. As of the research "
             "pass that produced this scaffolding, every alert on disk went "
             "through the fallback template (OPENAI_API_KEY was unset -- see "
             "results/explanation_eval_notes.md). Generate real explanations "
             "first:\n"
             "  export OPENAI_API_KEY=...\n"
             "  python -m aura_mas.scripts.generate_judge_pilot_explanations")
        return

    client, model = _get_judge_client(args.backend, args.model)
    scored: List[Dict] = []
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as out_f:
        for alert in real:
            explanation = alert["explanation"]
            score = judge_one(client, model, args.backend, alert, explanation)
            row = {
                "alert_id": alert.get("alert_id"), "source_file": alert["_source_file"],
                "severity": alert.get("severity"), "event_type": alert.get("event_type"),
                "explanation": explanation,
                "scores": score.model_dump(),
                "judge_backend": args.backend, "judge_model": model,
            }
            scored.append(row)
            out_f.write(json.dumps(row) + "\n")
            log.info("judged %s: grounding=%d severity_calibration=%d "
                     "conciseness=%d actionability=%d passed=%s",
                     alert.get("alert_id"), score.grounding, score.severity_calibration,
                     score.conciseness, score.actionability, score.passed)

    summary = summarize(scored)
    print(f"\njudged {summary['n']} alerts -> {args.out}")
    for k, v in summary.items():
        if k != "n":
            print(f"  {k}: {v}")

    if args.human_labels:
        agreement = compare_to_human_labels(scored, args.human_labels)
        print(f"\nhuman-agreement check ({args.human_labels}):")
        for k, v in agreement.items():
            print(f"  {k}: {v}")

    print("\nThis is a small-N pilot -- report it with the limitations "
         "framing in results/explanation_judge_notes.md, not as a validated "
         "evaluation methodology.")


if __name__ == "__main__":
    main()
