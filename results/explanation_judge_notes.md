# LLM-as-judge pilot — scaffolding status and procedure

**Status: scaffolding only, not yet run.** Pursue-Now item #1 from
`docs/ai-enhancement-research.md` Section 4.1. The code is complete and
unit-tested (`aura_mas/tests/test_llm_judge.py`), but actually running the
pilot needs live API keys this environment does not have, and was out of
scope for a code-implementation pass to acquire on your behalf.

## Why this is needed before anything can be judged

Three independent research threads (RL, training-data strategy, and
evaluation-loops — see `docs/ai-enhancement-research.md` Sections 3c/3d)
each independently confirmed the same fact by reading
`results/explanation_eval_notes.md` and grepping the actual alert logs:
**`OPENAI_API_KEY` has never been configured in this environment, so every
`explanation` field ever written to `data/alerts_*.jsonl` is
`ExplanationAgent._fallback()`'s deterministic template, not a real LLM
generation.** The evidence-grounding guardrail (a stated thesis safety
claim) has therefore never been exercised against real LLM output.

## The two-step procedure, once you have API keys

### Step 1 — generate real explanations (needs `OPENAI_API_KEY`)

```bash
source .venv/bin/activate
export OPENAI_API_KEY=...
python -m aura_mas.scripts.generate_judge_pilot_explanations --reps 3
```

This replays every scenario in `mas-auction` mode with `--llm` enabled,
`rep` offset at 900+ so it writes to distinct `data/alerts_*-r9NN.jsonl` /
`results/run_*-r9NN.json` files that **cannot collide with or overwrite**
the cited evaluation-campaign artifacts (reps 0-4). These pilot-generation
runs are not part of the campaign and must not be folded into
`results/summary.csv` or any results table.

As a side effect, this also now persists every LLM-call span (latency,
token counts, `aura.guardrail.passed`, `aura.explanation.fallback_triggered`)
to `data/otel_spans.jsonl` (Pursue-Now item #3 — see `aura_mas/telemetry.py`),
so the run is durably auditable, not just console-printed.

### Step 2 — judge them (needs `ANTHROPIC_API_KEY` by default)

```bash
export ANTHROPIC_API_KEY=...
python -m aura_mas.eval.llm_judge --limit 30
```

Default judge is Anthropic (`claude-sonnet-4-5-20250929`) against the
OpenAI-family (`gpt-4.1-mini`) generator — a deliberate different-model-
family choice. **Do not change `--backend` to `openai` without a documented
reason in the writeup** — using the same family as the generator reopens
the self-preference-bias risk the report specifically flags (Panickssery et
al. 2024; Zheng et al. 2023, arXiv:2306.05685).

Scoring is reference-based against the alert's own JSON payload (severity,
event_type, confidence, zone, sensors, fused_events), not pairwise
comparison against another model's output — this sidesteps position bias
entirely (nothing to swap) and reduces verbosity-bias sensitivity versus a
free-form A/B judge prompt. Rubric axes (`aura_mas/eval/judge_schema.py`):
grounding, severity_calibration, conciseness, actionability, plus an
overall `passed` rollup and a short rationale.

Output: `results/explanation_judge_scores.jsonl` (one row per judged alert)
plus a printed summary (per-axis means, overall pass rate).

### Step 3 (recommended) — a small human-agreement check

Hand-score ~8-10 of the judged alerts yourself (same four axes + `passed`),
save as a JSON list of `{"alert_id": ..., "grounding": ..., ...}` objects,
then:

```bash
python -m aura_mas.eval.llm_judge --limit 30 --human-labels my_labels.json
```

This reports simple exact-match agreement per axis between your labels and
the judge's — a rough sanity check, **not** a substitute for real
inter-rater-reliability statistics (Cohen's kappa etc.). Report it as
exactly that in the writeup.

## Required limitations framing for the thesis

Per `docs/ai-enhancement-research.md` Section 4.1, any writeup of pilot
results must state explicitly:

- Single judge model, small N (≤30 by default), no second human rater for
  full inter-rater reliability — this is a **pilot**, not a validated
  evaluation methodology.
- The judge was chosen from a different model family than the generator
  specifically to reduce self-preference bias, but that does not eliminate
  every possible judge bias (position bias is structurally avoided by the
  reference-based design; verbosity bias is only partially mitigated by the
  explicit `conciseness` rubric axis).
- This pilot evaluates explanation *quality* beyond what the existing
  `_guardrail_check` evidence-ID check already catches — it does not
  replace or weaken that guardrail, which remains the hard safety
  invariant.
- The fact that real LLM output had never been tested against the guardrail
  before this pilot is itself worth stating plainly in the thesis, not
  glossed over.
