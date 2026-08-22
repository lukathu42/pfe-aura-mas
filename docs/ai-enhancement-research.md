# AI/RL/Fine-Tuning Enhancement Research — AURA-MAS

**Status:** Research and synthesis pass only. No application code was written or
modified to produce this report; no training run was started. Everything below
is a recommendation for future work by the thesis author, not a description of
work already done.

**Date:** 2026-08-21
**Scope:** Where reinforcement learning, fine-tuning/model adaptation, or other
training-based ML techniques could add genuine technical depth to AURA-MAS —
as opposed to further prompting/orchestration work, which is out of scope here.

**Implementation status (2026-08-21, same day, follow-up pass):** all three
Section 4 "Pursue Now" items have been implemented in code:

1. **LLM-as-judge pilot** — scaffolding built and unit-tested
   (`aura_mas/eval/llm_judge.py`, `judge_schema.py`,
   `aura_mas/scripts/generate_judge_pilot_explanations.py`), but **not yet
   run**: it needs live API keys (`OPENAI_API_KEY` for the generator,
   `ANTHROPIC_API_KEY` for the judge by default) that this environment does
   not have. See `results/explanation_judge_notes.md` for the exact
   two-step procedure to run it.
2. **Toy contextual-bandit auction mode** — implemented and exercised
   end-to-end against the real CPU replay harness (`aura_mas/core/bandit.py`,
   `CoordinatorAgent(mode="auction-bandit")`,
   `aura_mas/scripts/train_auction_bandit.py`). See
   `results/auction_bandit_notes.md` for the same overclaiming warnings
   this report already gives, restated against the actual implementation.
3. **OpenTelemetry span persistence** — implemented
   (`aura_mas/telemetry.py:JsonlSpanExporter`), unit-tested, spans now
   written to `data/otel_spans.jsonl` by default whenever `configure_tracing()`
   runs.

All offline tests pass (`python -m pytest aura_mas/tests -q`, 19/19). The
analysis and recommendations below are unchanged from the original research
pass — this status block is the only addition.

---

## 1. Executive Summary

AURA-MAS today has **zero components that learn from data**: YOLO11n, CLIP,
and YAMNet are all used pretrained/zero-shot, and the coordination logic
(auction bidding, fusion weighting, alert thresholds) is entirely hand-coded
rules. Four parallel research threads (RL for agentic behavior; fine-tuning/
PEFT/distillation; training-data strategy; evaluation/iteration loops)
independently investigated whether any training-based technique could be
honestly demonstrated before the thesis draft deadline, given a CPU-only
production environment, occasional single-session Colab T4 access for
experiments, and a "days, not weeks" time budget.

**The convergent finding across all four threads is a data-volume problem, not
a compute problem.** Every classic training-based technique examined — offline
RL/behavior cloning over the ~373-run evaluation campaign, LoRA fine-tuning of
CLIP/YOLO11n/a local LLM, reward-model training, YAMNet distillation — is
short of sourced minimum-viable-dataset guidance by one to several orders of
magnitude, and in several cases (LoRA/reward-model training for the
`ExplanationAgent`) the real usable data is not "373, but small" — it is
**zero**, because no LLM has ever actually been called in this project.

That last point is a genuine, previously-unknown discovery from this research
pass, independently surfaced by three of the four threads: `OPENAI_API_KEY`
has never been configured in this environment, so `ExplanationAgent` has only
ever exercised its deterministic `_fallback()` template path
(`results/explanation_eval_notes.md`). The evidence-grounding guardrail — a
stated thesis safety claim — has therefore never actually been tested against
real LLM output. This reframes what "pursue now" should mean: not a trained
artifact, but closing this specific, cheap-to-close gap.

**Three items pass the feasibility bar and are recommended (Section 4):**

1. **A small LLM-as-judge evaluation pilot** for `ExplanationAgent` output —
   the only category among the four threads that needs no training-data
   volume or GPU, and which incidentally requires (and thus produces) the
   first real LLM-generated explanations this project has ever had.
2. **A toy contextual-bandit auction mode**, added alongside (not replacing)
   the existing `auction`/`roundrobin`/`off` coordinator modes — the one
   place a genuinely trained/adaptive component is honestly demonstrable at
   toy-PoC scale on CPU alone, framed strictly as illustrative.
3. **Persisting the currently console-only OpenTelemetry spans** — a
   near-zero-effort infrastructure change that costs hours, not days, and is
   a prerequisite for any future (post-thesis) data-driven work on
   `ExplanationAgent`.

**Explicitly not recommended for this pass** (Section 6): MARL (wrong problem
shape for a 2-3-agent single-round auction), QLoRA (no memory-scarcity
problem exists anywhere in this project), and LLM-generated synthetic
explanation pairs used as fine-tuning targets (real, literature-grounded
model-collapse risk with no gold-standard data to validate against).

---

## 2. Scope and Constraints

These constraints were confirmed with the user directly during planning and
apply to every judgment in this report:

- **Production/deployment is permanently CPU-only.** No GPU, no CUDA; torch
  is the `+cpu` build (`requirements.txt`, `CLAUDE.md`). This does not change
  and is not up for reconsideration — any technique intended to run in the
  deployed system must run acceptably on CPU.
- **Research/training experiments only** may use occasional free-tier Google
  Colab GPU access: a single T4-class GPU, **~12-hour hard session cap, no
  guaranteed persistence between sessions.** Feasibility judgments below
  distinguish (a) CPU-only, (b) fits one T4/12h session, (c) needs more than
  that — infeasible here.
- **Time budget to pursue any recommendation (beyond this report) is very
  limited — a few days, must fit before the thesis draft.** Every
  recommendation below is sized to that budget, not to what would be ideal
  with more time.
- **The evidence-grounding guardrail in `ExplanationAgent`
  (`_guardrail_check`, `aura_mas/agents/explanation_agent.py:196-209`) is a
  non-negotiable thesis safety claim.** No recommendation in this report
  proposes loosening, bypassing, or "training around" it.
- **The four coordinator ablation modes (`auction | roundrobin | off |
  centralized` / `mas-nocoord`) are thesis baselines that must stay
  comparable.** Any new coordinator behavior is proposed as an *additional*
  mode, never a replacement.
- This is a **research-and-writing pass only.** No training run, fine-tune,
  or code change was executed to produce this document.

---

## 3. Candidate Techniques Considered

Each subsection reflects one Phase 1 research thread. Feasibility fields use
three tiers: **Demonstrable now** (clears easily within the days budget) /
**Toy PoC only** (a small, explicitly-labeled illustrative result, not a
validated claim) / **Not feasible** (fails outright at this scale/timeline).

### 3a. RL for agentic behavior

**Verdict: no RL technique can be validated with real statistical confidence
at AURA-MAS's current data scale.** The entire logged history of the
coordinator's auction bidding is **~25-62 bid events** (counts vary slightly
by which run corpus is aggregated — see thread detail), drawn from only 2-3
cameras and 6-9 fixed scenario clips, with **zero randomization** in how any
decision was made — every bid used the same deterministic `base × capacity ×
overlap` formula, every gray-zone check used the same fixed `(0.35, 0.75)`
threshold. This absence of exploration is disqualifying for off-policy
methods independent of scale: importance-sampling/doubly-robust estimators
have undefined or near-zero effective sample size when the logging policy
never varied.

| Technique | Why this project | Feasibility – compute | Feasibility – data | Feasibility – schedule | Impact | Risks |
|---|---|---|---|---|---|---|
| Toy contextual bandit (LinUCB/Thompson) for `CameraAgent._view_score`, via self-play against the replay harness as a CPU simulator, as a new `auction-bandit` coordinator mode | `_view_score` (`camera_agent.py:314`) is structurally a 2-3-arm contextual bandit, not a sequential MDP — PPO/MARL would be the wrong tool. The replay harness (`run_campaign.py`) is a deterministic, cheaply re-runnable CPU simulator (measured ~48s/run avg), so hundreds of synthetic self-play episodes are generatable in ~6-7 CPU-hours, no GPU needed. | Demonstrable now (CPU only) | Toy PoC only — self-generated episodes replay only 6-9 fixed clips, so the bandit can only ever qualitatively rediscover the existing heuristic, not demonstrate generalization | Toy PoC only — fits days budget per thread estimate | Genuine adaptive/learned component where prior local-thesis precedent (F2) had none — real novelty lever if honestly framed as illustrative, not as outperforming the baseline | Must not be reported as beating the hand-coded heuristic with statistical confidence (see Section 7); if oversold, invites the same critique as CLIP's AUC=0.308 negative result |
| Adaptive `CoordinatorAgent.gray_zone` thresholding via contextual bandit | `gray_zone` (`coordinator_agent.py:27`, default `(0.35, 0.75)`) gates verification; 942 hypotheses is the largest data pool in the system | N/A | Not feasible — zero randomization in the 942 logged decisions makes any off-policy threshold estimate invalid, independent of count; industrial comparables (Li et al. 2011, Bottou et al. 2013) operate 5+ orders of magnitude larger *and* rely on randomized logging AURA-MAS lacks | Not feasible as RL | Would be valuable if feasible (a genuinely adaptive core decision gate) | — |
| Multi-agent RL (MARL) for 2-3 camera agents bidding | Considered because the auction involves multiple agents | — | — | — | — | **Thread's own conclusion: overkill/wrong fit.** Single-round sealed-bid auction has no multi-step credit assignment or adversarial dynamic; the ingredients that justify MARL's complexity (QMIX/MADDPG/MAPPO) are absent. Toy MARL benchmarks need 1M+ environment steps even in cheap simulators — no path to that on ~30 real episodes or a single T4 session. **Logged as rejected, Section 6.** |
| Offline RL (CQL, IQL, behavior cloning) over existing decision logs | Framed as more realistic than online RL since there's no live environment | (b) T4-feasible for the algorithm itself | Not feasible — D4RL benchmark tasks range 5,000 to ~2M transitions even at the smallest end; AURA-MAS's entire decision history (62-942 records depending on unit) is 3-5 orders of magnitude short, and lacks diversity (5 reps of the same 6-9 scenarios) | Not feasible | — | Conservative offline-RL methods have nothing to safely anchor to with this little, non-diverse data |

**Lighter-weight fallback also identified** (not separately ranked): a pure
off-policy-evaluation analysis script comparing 2-3 hand-picked `gray_zone`
alternatives against the logged baseline via IPS/doubly-robust estimators —
zero new runtime code, purely analysis over `results/run_*.json`. Must
prominently carry the "no randomization in the logging policy" caveat; the
resulting numbers are illustrative, not trustworthy point estimates.

### 3b. Fine-tuning strategies

**Verdict: none of the five components examined justify fine-tuning within
the available days**, for two recurring reasons: either the compute is fine
but the labeled data is 2-3 orders of magnitude short (CLIP, YOLO11n), or the
technique doesn't actually address a real constraint in this project (QLoRA,
YAMNet distillation), or the raw training-target data doesn't exist at all
yet (LoRA for `ExplanationAgent`).

| Technique | Why this project | Feasibility – compute | Feasibility – data | Feasibility – schedule | Impact | Risks |
|---|---|---|---|---|---|---|
| CoOp/CoCoOp-style prompt-tuning for `ClipAnomalyScorer` (`camera_agent.py:117-161`) | Directly targets the measured AUC=0.308 domain-mismatch failure (`results/clip_anomaly_calibration_notes.md`) — a real, diagnosed problem | Demonstrable now — frozen backbone, only continuous prompt vectors trained, comfortably fits a T4/12h session with large margin | Not feasible — only 2 distinct anomaly source videos exist (`data/clips_real/manifest.json`); any learned prompt risks memorizing those 2 clips rather than generalizing, with no held-out anomaly video to validate against | Toy PoC only, but not worth it — the calibration notes' own cheaper non-training fix (rewrite `NORMAL_PROMPTS` to include an outdoor/CCTV-domain prompt, re-evaluate) addresses the same root cause in hours, not a training run | Would be meaningful if data existed | Training-on-2-clips risk of overfitting the exact evaluation set, which the calibration notes explicitly warn against |
| Fine-tuning YOLO11n on AIRTLab/ABODA footage | Considered as a general detection-quality lever | (b) T4-feasible for training mechanics | Not feasible — Ultralytics' own published guidance recommends ≥1,500 images/class, ≥10,000 instances/class; this project has at most a few hundred unlabeled frames across ~80s of footage, with zero bounding-box annotations existing yet | Not feasible — annotation alone would consume much of the available days before any training starts | Low even if feasible — no diagnosed YOLO detection-accuracy problem exists in `results/`; documented failures were data/timing bugs, not detector quality | — | Time sunk into annotating a dataset that would still be 2-3 orders of magnitude short |
| QLoRA anywhere in the pipeline | Considered because it's a prominent PEFT technique | — | — | — | — | **No genuine application.** QLoRA exists to fit *large* models into *scarce* GPU memory; every local model here (CLIP ~151M params, YOLO11n nano, YAMNet ~3.7M params) already fits a T4 in plain fp16/fp32, and `ExplanationAgent`'s LLM is API-based by default, not locally hosted. **Logged as rejected, Section 6.** |
| LoRA fine-tuning a local LLM for `ExplanationAgent` | Could reduce guardrail-rejection/fallback rate for generated reports | (b) T4-feasible for a small (7-8B-class) local model | Not feasible — **zero** real (alert, explanation) pairs exist, not "373 but small": `OPENAI_API_KEY` has never been configured, so every logged explanation is the deterministic fallback template, confirmed independently by two other threads | Not feasible pre-deadline — manufacturing supervision via distillation first would itself consume much of the remaining budget for a still-small, low-diversity resulting set | The property this would target (reliable evidence citation) is **already fully guaranteed by the existing rule-based guardrail at zero training cost** — fine-tuning here would only reduce fallback *rate*, not enable anything the system can't already do safely | Guardrail must never be loosened to accommodate a fine-tuned model's mistakes — reaffirmed, not at risk, but worth stating explicitly |
| Distilling YAMNet to a `SURVEILLANCE_CLASSES`-only student model | Considered as a CPU-latency optimization | (b) T4-feasible for the training mechanics | Not feasible — only 3 ESC-50 audio clips exist as source material, several orders short of a generalizable distillation set | Not worth it regardless of data | No CPU-latency problem is documented anywhere to justify this — YAMNet is already a ~3.7M-param MobileNet-class model; published distillation work in this space targets microcontroller-class hardware (ESP32), far below this project's actual server/edge-CPU deployment target | **Logged as rejected, Section 6** — wrong problem to solve, not just infeasible |

### 3c. Training-data strategy

**Verdict: no training-data strategy examined can produce a genuinely
*trained* (not merely training-ready) artifact before the deadline.** The
one legitimate, cheap, and honest action available in this category is
infrastructure, not data generation.

| Technique | Why this project | Feasibility – compute | Feasibility – data | Feasibility – schedule | Impact | Risks |
|---|---|---|---|---|---|---|
| **Persist OpenTelemetry spans** (`aura_mas/telemetry.py`) to a durable JSONL/file store instead of console-only | Closes a documented, real gap — `ExplanationAgent` already emits per-call latency/token/guardrail-outcome spans that are currently unrecoverable | Demonstrable now — CPU only, no model involved | N/A (infra, not data-dependent to build) | Demonstrable now — estimated hours: swap/subclass `ConsoleSpanExporter`, redirect to a JSONL writer | Directly enables all future data-driven work on `ExplanationAgent`, including the LLM-as-judge pilot below and any future fine-tuning attempt; near-zero risk | None significant; note the honest framing correction below |
| Offline RL / behavior cloning over agent decision traces | Covered in 3a | — | — | — | — | Duplicate of 3a's offline-RL row; not re-scored here |
| LoRA fine-tuning (general) | Covered in 3b | — | — | — | — | Duplicate of 3b's LoRA row |
| Reward-model training over logged decisions | Considered as a path toward learned confidence/severity calibration | (b) T4-feasible mechanically | Not feasible — **zero preference pairs exist anywhere in the data**; nothing to even begin from (InstructGPT's RM used 33k prompts; even the smallest academic RM work sits in the low thousands of pairs) | Not feasible | Would be valuable if a data source existed | Nonexistent starting point, not merely small |
| Synthetic LLM-generated (alert, ideal-explanation) pairs for `ExplanationAgent` fine-tuning | Proposed as a way to manufacture the missing supervision from 3b | Demonstrable now, mechanically | Toy PoC only for generation itself, but **not results-defensible as a fine-tuning source** | Fast to generate, but not worth doing for this purpose | — | **Logged as rejected for this specific use, Section 6** — real, literature-grounded self-distillation/model-collapse risk (Shumailov et al. 2024, Nature) with no gold-standard explanation anywhere in the repo to validate against |
| Procedural re-mixing of existing AIRTLab/ABODA/ESC-50 clips | Proposed as a way to multiply effective scenario count | Demonstrable now, mechanically trivial | Does not close the real gap — the underlying event count stays at 7 unique recorded events regardless of re-cutting/re-timing | Fast | Legitimate for ablation/stress-testing the fusion logic; **must not be reported as expanding real evaluation diversity** | Synthetic audio-video pairings that never co-occurred in reality could be mistaken for additional real evidence if not clearly labeled as synthetic in any results table |

**Framing correction surfaced by this thread:** the console-only OTel gap is
not "data we lost" — no LLM call has ever been made in this project, so no
span with real latency/token/guardrail data was ever emitted in the first
place. This is instrumentation for a code path that has never executed
end-to-end, not data recovery.

### 3d. Evaluation / iteration loops

**Verdict: this is the most feasible category of all four threads**, and the
thread's own reasoning for why is worth stating plainly: LLM-as-judge work
needs no training-data volume and no GPU — its bottleneck is methodology and
API calls, both fixable within the days budget, unlike the other three
threads' bottlenecks (data volume, sustained compute) which cannot be
manufactured in that window.

| Technique | Why this project | Feasibility – compute | Feasibility – data | Feasibility – schedule | Impact | Risks |
|---|---|---|---|---|---|---|
| **LLM-as-judge pilot for `ExplanationAgent` output quality**, reference-based/rubric scoring (not pairwise), cross-model-family judge, small human-labeled-subset agreement check | Evaluates explanation quality beyond what the existing rule-based `evidence_id` guardrail catches (grounding, severity calibration, conciseness, actionability) | Demonstrable now — API calls only, no GPU; cost is a few cents/sample | Toy PoC only — requires first generating ~20-40 real explanations (Day 1 of the pilot, since none currently exist — see 3c framing correction), then judging them; this closes the "never actually called an LLM" gap as a side effect | Toy PoC only — thread's own estimate: 2-4 days end-to-end | High — a genuinely new evaluation methodology, not previously part of the thesis; also the only way to find out whether the guardrail behaves correctly against real (non-fallback) LLM output, which has never been tested | Self-preference bias if judge and generator share a model family (mitigated by picking a different-family judge, e.g. Claude vs. the `gpt-4.1-mini` generator); must be framed as a pilot with stated limitations (single judge, small N, no second human rater), not a validated methodology |
| Statistically confident before/after comparison of any newly introduced trained component, using the 373-run campaign | Considered as the way to validate any of the other threads' proposals | — | Not feasible — the effective independent sample size for a *new* intervention is scenario-cluster-sized (~6-9), not run-count-sized (373), since reps/modes are correlated by construction on the same fixed scenarios; underpowered per standard NLP statistical-power guidance (Card et al. 2020) | — | — | Any "trained-vs-baseline" claim in the thesis should report paired bootstrap CIs and effect size, not a bare significance claim — flagged as a general risk in Section 7 |

---

## 4. Recommendation: Pursue Now

All three items below pass every feasibility axis at minimum "toy PoC
demonstrable," per the decision rule (impact alone never qualifies a
technique that fails a feasibility axis). Ranked by expected thesis-
contribution impact.

### 1. LLM-as-judge evaluation pilot for `ExplanationAgent`

**Concrete first step:** obtain an OpenAI API key (for the existing
`gpt-4.1-mini` generator path) and a second key from a different model
family (e.g., Anthropic) for the judge. Run `python -m aura_mas.scenarios.replay
scenarios/*.json --mode mas-auction --llm` across the 6-9 scenarios to
generate ~20-40 real alert/explanation pairs — the first real LLM
generations this project will have produced.

**Expected demonstrable outcome:** a documented pilot with (a) a stated
rubric (grounding, severity calibration, conciseness, actionability), (b) a
cross-family judge model chosen explicitly to avoid self-preference bias,
(c) reference-based (not pairwise) scoring to sidestep position bias, (d) a
small (~8-10 sample) human-labeled subset reported as a rough agreement
check, and (e) explicitly stated limitations (single judge, small N, pilot
not validated methodology). This also, as a direct side effect, is the first
real end-to-end test of the evidence-grounding guardrail against actual LLM
output rather than only the fallback template — worth flagging to the
thesis committee as a genuine new finding regardless of the judge results.

### 2. Toy contextual-bandit auction mode

**Concrete first step:** implement a `auction-bandit` `CoordinatorAgent`
mode (additive, alongside — not replacing — `auction`/`roundrobin`/`off`)
using a LinUCB or Thompson-sampling bandit over the same context
(`origin_sensor`, `event_type`, `zone`, `fov_overlap`, `busy`) that
`_view_score` already uses. Train via self-play against the existing replay
harness (`run_campaign.py`) as a CPU simulator — no GPU needed, no live
environment required.

**Expected demonstrable outcome:** a small, explicitly-labeled illustrative
result showing the bandit's learned weights qualitatively converge toward
something resembling the hand-coded `base × capacity × overlap` heuristic.
**This must be reported as a mechanism demonstration, not a performance
claim** — with only 6-9 fixed scenario clips there is no held-out
generalization test possible, and claiming the learned policy "outperforms"
the baseline would not survive scrutiny (see Section 7). The genuine value
is architectural: it demonstrates AURA-MAS *can* accommodate a learned
component in its coordination layer, directly speaking to the novelty
framing in `research/aura-mas-landscape-positioning/findings/F2` (prior
local-thesis precedent had zero learned/adaptive components at all).

### 3. Persist OpenTelemetry spans to a durable store

**Concrete first step:** replace the console-only `SimpleSpanProcessor` /
`ConsoleSpanExporter` in `aura_mas/telemetry.py:configure_tracing()` with a
JSONL-writing exporter (either redirecting `ConsoleSpanExporter`'s `out`
parameter to an open file with a JSON-lines formatter, or a small ~20-40
line custom `SpanExporter` subclass) capturing trace_id, span name,
timestamps, and the existing latency/token/guardrail-outcome attributes.

**Expected demonstrable outcome:** every future `--llm` run (starting with
item 1 above) now durably logs its LLM-call telemetry. This produces zero
data by itself — it is explicitly infrastructure, not a trained artifact —
but is the single cheapest, lowest-risk action in this entire report and is
a direct prerequisite for any future (post-thesis) attempt at the
fine-tuning or reward-modeling directions logged as "worth noting" below.

---

## 5. Worth Noting, Not Now

Well-sourced candidates that fail at least one feasibility axis today, with
the blocking axis named. These could become viable with more real data
(e.g., after the OTel persistence + LLM-as-judge pilot above start
accumulating real `ExplanationAgent` interaction data) or more time.

| Technique | Blocking feasibility axis | Note |
|---|---|---|
| CoOp/CoCoOp prompt-tuning for `ClipAnomalyScorer` | Data — only 2 distinct anomaly source clips exist | Compute is not the blocker; the calibration notes' own non-training prompt-rewrite fix addresses the same root cause more cheaply |
| Fine-tuning YOLO11n on project footage | Data + no diagnosed problem — 2-3 orders of magnitude below Ultralytics' published minimums, zero bounding-box labels exist | Revisit only if a real detection-accuracy problem is ever diagnosed and a much larger labeled set becomes available |
| Adaptive `gray_zone` thresholding via contextual bandit | Data validity — zero randomization in 942 logged decisions makes off-policy estimation invalid regardless of count | A plain grid/Bayesian-optimization sweep (not RL) re-running the existing eval harness at candidate threshold values is a legitimate, cheap alternative if threshold tuning is wanted — but it is hyperparameter search, not a training technique, and outside this report's RL/fine-tuning scope |
| LoRA fine-tuning a local LLM for `ExplanationAgent` | Data — zero real (alert, explanation) pairs exist today | Becomes conceivable only after the LLM-as-judge pilot (Section 4.1) and OTel persistence (Section 4.3) have run for a while and accumulated real interaction data; even then, revisit whether it's worth it given the guardrail already provides the safety property at zero training cost |
| Reward-model training over logged decisions | Data — zero preference pairs exist anywhere | Same prerequisite as above: needs real accumulated interaction data first |
| Offline RL / behavior cloning over auction decision traces | Data — 62-942 logged decisions (depending on unit) vs. thousands-to-millions in D4RL-class benchmarks, 2+ orders of magnitude short | The toy self-play bandit (Section 4.2) is the honest, right-sized substitute for now |

---

## 6. Rejected / Not a Fit

Techniques a research thread itself concluded were a poor fit for this
project's problem structure — logged explicitly rather than silently
dropped.

| Technique | Why rejected |
|---|---|
| Multi-agent RL (MARL / QMIX / MADDPG / MAPPO) for camera auction bidding | Wrong problem shape: a single-round sealed-bid auction between 2-3 cooperative (not adversarial) agents has none of the multi-step credit-assignment or non-stationary co-learning dynamics that justify MARL's complexity. This is closer to mechanism design (Vickrey-style sealed-bid auctions) than a Markov game. Even toy MARL benchmarks in cheap simulators typically need 1M+ environment steps to show improvement — infeasible on ~30 real episodes or a single T4 session regardless of framing. |
| QLoRA anywhere in this pipeline | QLoRA's entire reason to exist is fitting *large* models into *scarce* GPU memory. Every locally-present model in AURA-MAS (CLIP ViT-B/32 ~151M params, YOLO11n, YAMNet ~3.7M params) already fits a T4's 16GB in plain fp16/fp32, and the default `ExplanationAgent` LLM path is API-based, not locally hosted. No memory-scarcity problem exists anywhere in this project for QLoRA to solve. |
| YAMNet distillation to a `SURVEILLANCE_CLASSES`-only student model | Not just infeasible on data (3 source clips) but solving a problem that doesn't exist: no CPU-latency issue is documented anywhere for YAMNet, which is already a ~3.7M-parameter MobileNet-class model. Comparable published distillation work targets microcontroller-class hardware (ESP32), far below this project's actual server/edge-CPU deployment target. |
| Synthetic LLM-generated (alert, ideal-explanation) pairs as a fine-tuning source | Technically fast to generate, but a real, literature-grounded self-distillation/model-collapse risk (Shumailov et al. 2024, *Nature* 631) applies directly: training on a model's own invented supervision with no independent gold standard to validate against would disproportionately erode exactly the rare, borderline-confidence explanations this system most needs to get right. Not results-defensible as a "trained on real data" claim in a thesis, independent of how fast it is to produce. |

---

## 7. Risks and Open Questions

- **Do not overclaim the toy bandit's results.** With only 6-9 fixed
  scenario clips, there is no held-out generalization test possible for the
  auction-bandit mode (Section 4.2). Any writeup must report it as a
  mechanism/architecture demonstration ("the system can accommodate a
  learned coordination component") and explicitly avoid any "outperforms
  the baseline" framing — the data cannot support that claim, and reviewers
  who check the sample size would be right to challenge it.
- **Any before/after comparison involving a trained component should use
  paired bootstrap confidence intervals and report effect size, not a bare
  significance claim.** The 373-run campaign's effective independent sample
  size for evaluating a *new* intervention is scenario-cluster-sized
  (~6-9), not run-count-sized, since repetitions and modes are correlated
  by construction on the same fixed scenarios (Section 3d; Card et al. 2020
  on underpowered NLP comparisons).
- **The LLM-as-judge pilot depends on getting real API access working.**
  If API keys or rate limits become a blocker, the pilot's Day 1
  (generating real explanations) is itself the critical path — budget
  accordingly.
- **A previously-unknown gap surfaced during this research pass, not
  proposed as work but worth flagging to the user directly:** the
  evidence-grounding guardrail — a stated thesis safety claim — has never
  been tested against real LLM output, because `OPENAI_API_KEY` has never
  been configured in this environment. Every `--llm` run to date has gone
  through the deterministic fallback path. This is worth deciding on
  explicitly and soon: either the thesis text should be corrected to
  reflect that the guardrail's *real-LLM* behavior is untested (as opposed
  to implying it has been validated against live generations), or the
  Section 4.1 pilot (which requires exercising this path for real) should
  be prioritized specifically to close this gap before the draft is
  written.
- **Clip re-mixing/augmentation (Section 3c) must be clearly labeled as
  synthetic if used anywhere in results.** It is a legitimate stress-test
  tool for the fusion logic but must never be presented as expanding real
  evaluation diversity — the underlying event count stays at 7 unique
  recordings regardless of how many re-cut variants are produced.
- **Run-to-run non-determinism** (documented in
  `results/evaluation_campaign_v2_notes.md`, likely PyTorch CPU-threading
  float non-determinism near confidence-threshold boundaries) affects any
  future evaluation of a trained component exactly as it already affects
  the existing ablation comparisons — rerun N≥3 times before citing any
  number as final, as the existing project guidance already states.

---

## 8. Sources

*Deduplicated across all four research threads. `[uncertain]` tags from the
original threads are preserved where the underlying claim could not be
independently verified in this pass.*

**RL / bandits / offline RL:**
- Kumar, A. et al. (2020). *Conservative Q-Learning for Offline Reinforcement
  Learning.* NeurIPS. https://papers.neurips.cc/paper_files/paper/2020/file/0d2b2061826a5df3221116a5085a6052-Paper.pdf
- Kostrikov, I. et al. (2021). *Offline RL with Implicit Q-Learning.*
  https://arxiv.org/abs/2110.06169 [uncertain: exact arXiv id not
  re-verified]
- Fu, J. et al. — D4RL benchmark suite dataset scale (~5,000 to ~2M
  transitions per task, smallest widely-used sets ~25 trajectories).
  https://arxiv.org/pdf/1907.04543 [uncertain: exact current per-split
  counts]
- Li, L., Chu, W., Langford, J., Wang, X. (2011). *Unbiased Offline
  Evaluation of Contextual-bandit-based News Article Recommendation
  Algorithms.* WSDM. https://arxiv.org/abs/1003.5956
- Bottou, L. et al. (2013). *Counterfactual Reasoning and Learning Systems:
  The Example of Computational Advertising.* JMLR 14.
  https://arxiv.org/abs/1209.2355
- Smith, R. G. (1980). *The Contract Net Protocol.* IEEE Transactions on
  Computers (secondary reference via
  https://en.wikipedia.org/wiki/Contract_Net_Protocol; primary paper not
  re-fetched).
- Vickrey, W. (1961) — sealed-bid auction / mechanism-design foundation
  [uncertain: standard textbook attribution, not re-verified this pass].

**Fine-tuning / PEFT / distillation:**
- Zhou, K. et al. (2022). *Learning to Prompt for Vision-Language Models
  (CoOp).* IJCV. https://arxiv.org/pdf/2109.01134
- Zhou, K. et al. (2022). *Conditional Prompt Learning for Vision-Language
  Models (CoCoOp).* CVPR. https://arxiv.org/abs/2203.05557
- Dettmers, T., Pagnoni, A., Holtzman, A., Zettlemoyer, L. (2023). *QLoRA:
  Efficient Finetuning of Quantized LLMs.* NeurIPS.
  https://huggingface.co/papers/2305.14314
- Ultralytics. *Tips for Best YOLOv5 Training Results* (dataset-size
  guidance carried through current YOLO11 docs).
  https://docs.ultralytics.com/yolov5/tutorials/tips-for-best-training-results
- Ultralytics. *Object Detection Datasets Overview.*
  https://docs.ultralytics.com/datasets/detect
- *KD-LoRA: A Hybrid Approach to Efficient Fine-Tuning with LoRA and
  Knowledge Distillation.* https://arxiv.org/pdf/2410.20777
- YAMNet CPU/TFLite latency benchmarks: *Evaluating the Performance of
  Pre-Trained CNNs for Audio Classification on Embedded Systems.*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10347208/ [uncertain: measured
  via TFLite delegate, not the plain `tf.saved_model.load` path this
  project uses]

**Training-data strategy / dataset sizing:**
- Zhou, C. et al. (2023). *LIMA: Less Is More for Alignment.* NeurIPS.
  https://arxiv.org/abs/2305.11206
- Ouyang, L. et al. (2022). *Training language models to follow
  instructions with human feedback (InstructGPT).* NeurIPS.
  https://ar5iv.labs.arxiv.org/html/2203.02155
- Anthropic HH-RLHF preference dataset scale (~112k-161k pairs), via
  https://github.com/RLHFlow/RLHF-Reward-Modeling and related survey
  citations.
- Shumailov, I. et al. (2024). *AI models collapse when trained on
  recursively generated data.* Nature 631, 755-759.
  https://pubmed.ncbi.nlm.nih.gov/39048682/
- Sadasivan, V. S. et al. (2024). *A Note on Shumailov et al. (2024).*
  https://arxiv.org/abs/2410.12954
- Practitioner minimum-viable-dataset guidance (200-500 narrow-task,
  1,000-5,000 minimum viable, 10,000-50,000 production):
  https://introl.com/blog/fine-tuning-infrastructure-lora-qlora-peft-scale-guide-2025 ,
  https://particula.tech/blog/how-much-data-fine-tune-llm [uncertain:
  industry blog sources, not peer-reviewed]
- Thinking Machines Lab (2025). *LoRA Without Regret.*
  https://thinkingmachines.ai/blog/lora/ [uncertain: recent practitioner
  source]

**Evaluation / LLM-as-judge:**
- Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and
  Chatbot Arena.* NeurIPS Datasets & Benchmarks.
  https://arxiv.org/abs/2306.05685 — position bias (65.0%→77.5%
  self-consistency with few-shot), verbosity bias (91% vs. 8.7% failure
  rate for weaker vs. GPT-4 judges), GPT-4/human agreement (~85% vs. ~81%
  human-human).
- Panickssery, A. et al. (2024). *LLM Evaluators Recognize and Favor Their
  Own Generations.* NeurIPS.
  https://proceedings.neurips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html
- *Self-Preference Bias in LLM-as-a-Judge.*
  https://arxiv.org/pdf/2410.21819
- *A Survey on LLM-as-a-Judge.* https://arxiv.org/html/2411.15594v6
- Card, D., Henderson, P., Khandelwal, U., Jia, R., Mahowald, K., Jurafsky,
  D. (2020). *With Little Power Comes Great Responsibility.* EMNLP.
  https://arxiv.org/abs/2010.06595
- Dror, R., Baumer, G., Shlomov, S., Reichart, R. (2018). *The Hitchhiker's
  Guide to Testing Statistical Significance in NLP.* ACL.
  https://aclanthology.org/P18-1128/
- Cross-family judge-selection practitioner guidance:
  https://futureagi.com/blog/llm-as-a-judge/ ,
  https://www.evidentlyai.com/blog/llm-judges-faq [uncertain: practitioner
  sources, cited for the practical recommendation only]

**Project-internal grounding** (repository evidence, not external sources):
`aura_mas/agents/camera_agent.py`, `aura_mas/agents/audio_agent.py`,
`aura_mas/agents/fusion_agent.py`, `aura_mas/agents/coordinator_agent.py`,
`aura_mas/agents/explanation_agent.py`, `aura_mas/agents/explanation_schema.py`,
`aura_mas/telemetry.py`, `aura_mas/scripts/run_campaign.py`,
`results/clip_anomaly_calibration_notes.md`,
`results/yamnet_integration_notes.md`,
`results/evaluation_campaign_v2_notes.md`, `results/explanation_eval_notes.md`,
`data/clips_real/manifest.json`, `results/run_*.json` (416 files on disk, 373
in the current v2 campaign per `evaluation_campaign_v2_notes.md`),
`data/alerts_*.jsonl`, `data/audit_*.jsonl`,
`research/aura-mas-landscape-positioning/findings/F2`.
