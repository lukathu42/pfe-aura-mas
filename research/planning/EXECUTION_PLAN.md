# AURA-MAS — Execution Plan (status check vs. the 30-day schedule)

This supersedes nothing in `One-Month Execution Schedule — AURA-MAS PFE.md` —
it's a reality check against it, written after reading the actual repo state,
`STATE_NOTES.md`, and the existing critical audit in
`research/aura-mas-landscape-positioning/` (findings F1-F6). Re-read those
findings before trusting any number or citation currently in the thesis.

## 0. Blocking issue — fix before anything else

**The compiled thesis (`AURA-MAS_Thesis_LaTeX/main.pdf` — the stale root-level
duplicate `AURA-MAS_Thesis.pdf` this note originally also named has since been
deleted as part of a repo cleanup pass; `AURA-MAS_Thesis_LaTeX/main.pdf` is the
only compiled copy now) carries the name "BELMANA Soufyane" and supervisor
"Pr. AMAR BENSABER Djamel",
inherited unmodified from the LaTeX template used by a prior AI session.**
Per `research/.../plan.md`, this was apparently never overwritten with the
real author's identity. Confirm your actual name, supervisor, jury, and
institution details and get them into `AURA-MAS_Thesis_LaTeX/main.tex`
before this PDF is shown to anyone. This is a five-minute fix but a
zero-tolerance one — do it first.

## 1. What "done" actually means here

Everything in this repo that looks finished (working code, passing tests, a
compiled thesis, a results table) was produced in one fast automated pass by
a prior agent session, not through 30 days of iterative engineering. That
means:

- The **code is real and runs** — six agents, MQTT/Redis/LocalBus transport,
  auction coordination, Streamlit dashboard, 6/6 unit tests pass (verified
  today). This is a legitimate engineering foundation, not vaporware.
- The **evaluation is not** — `results/summary.csv` is one scenario
  (`demo_site_01`), 2 real clips + 1 synthetic audio event, self-defined
  ground truth (finding F6). The "MAS reduces time-to-alert 36%" claim in
  `STATE_NOTES.md` is internally consistent demo output, not a validated
  comparative result. A jury will treat n=1 as a red flag.
- The **bibliography needs a verification pass** — 94 entries, only 6
  spot-checked so far; corrupted author fields and at least one wrong year
  already found (finding F5). Treat `bibliography.bib` / `chapter_sota.tex`
  as a citation-discovery draft, not submission-ready.
- CLIP anomaly scoring and YAMNet are wired in but optional/lazily
  imported — confirm which path actually produced any given result before
  citing it in a chapter.

None of this means start over. It means: **the schedule's Week 1-3 tasks are
"prototyped," not "done"** — closing that gap is real, scoped work, and it's
what should replace re-doing Days 1-14 from scratch.

## 2. Schedule status, mapped

| Week | Original goal | Status |
|---|---|---|
| W1 (skeleton) | End-to-end video→alert pipeline, dashboard, schemas doc | **Prototyped.** Runs, tested. Real UCF-Crime/ESC-50 assets from W1.2 were never fetched — only 2 pedestrian clips + 1 synthetic audio clip exist in `data/clips/`. |
| W2 (anomaly, fusion, coordination) | CLIP anomaly scorer + calibration, late fusion, auction protocol + rule baseline, 6-scenario pack | **Code prototyped**, calibration/AUC sweep (W2.2) and the 6-scenario pack (W2.6) not actually run — only 2 scenario manifests exist (`intrusion_01`, `demo_site_01`), not 6, and no AUC table exists in `results/`. |
| W3 (explanation, privacy, evaluation campaign) | Guardrailed ExplanationAgent, blurring, centralized baseline, **full evaluation campaign**, explanation-quality eval | ExplanationAgent + guardrails + privacy blurring **prototyped**. The "full evaluation campaign" (W3.5, the thesis's actual results chapter data) ran on **one scenario only** — this is the single biggest gap versus the schedule. |
| W4 (writing) | 7 thesis chapters + figures + defense prep | Chapters 1-7 **drafted and compiled** (53 pages), figures rendered. Content quality depends entirely on closing the W2/W3 evaluation and bibliography gaps above — the prose currently describes results that don't have the evidence base the schedule intended. |

## 3. Revised near-term plan

Priority order, each with a concrete exit criterion:

1. **Identity fix** (§0). Exit: title page shows correct author/supervisor/jury.
2. **Bibliography verification pass** (closes F5). Spot-check or re-derive
   all 94 `bibliography.bib` entries against real sources; fix corrupted
   author fields and the known wrong year (Murakkab). Exit: every citation
   in `chapter_sota.tex` traceable to a verified source.
3. **Real dataset acquisition** (closes the W1.2/W2.6 gap). Pull the
   UCF-Crime subset + ESC-50/UrbanSound8K clips the schedule specified;
   build the 6-scenario pack from W2.6 with real ground-truth timestamps,
   not just the existing 2 manifests.
4. **Re-run the evaluation campaign at real scale** (closes F6, W3.5). All
   scenarios × {centralized, mas-nocoord, mas-rules, mas-auction} ×
   {vision-only, audio-visual}, regenerate `results/summary.csv` and figures
   from that, not from the n=1 run.
5. **CLIP/YAMNet calibration** (W2.1/W2.2): confirm which optional deps are
   actually installed and used; if CLIP AUC is weak or untested, fall back
   to the plan's own documented fallback — "semantic tagger" framing, lean
   novelty on zone rules + fusion + coordination — rather than overclaiming.
6. **Only then**, revise chapters 5-6 (implementation, evaluation) to match
   the real numbers, and treat chapters 1-4 as stable pending the identity
   and citation fixes.

This is deliberately not a day-by-day rewrite of the original schedule — the
skeleton exists, so the remaining month is a validation-and-hardening pass
rather than a from-scratch build. Re-derive a day-by-day breakdown once step
3 (dataset acquisition) gives a real sense of how long the evaluation rebuild
takes.

## 4. Immediate next actions

- [ ] Fix author/supervisor identity in `AURA-MAS_Thesis_LaTeX/main.tex` (manuscript — out of scope for the `code-hardening` branch, see §5)
- [x] Pick and download real dataset/audio assets (W1.2) — done on `code-hardening`, see `data/clips_real/manifest.json` for what was substituted and why (UCF-Crime/Avenue were impractical here)
- [ ] Spot-check the remaining 88 unchecked `bibliography.bib` entries (manuscript — out of scope for `code-hardening`)
- [x] Build out `scenarios/` to the 6-scenario pack from W2.6 — done

## 5. `code-hardening` branch — what actually got done (code only, no manuscript changes)

Per explicit instruction, this branch only touches `aura_mas/`, `scenarios/`,
`data/`, and `results/` — items 1, 2, and 6 above (identity fix, bibliography,
chapter rewrites) are still open and untouched.

- Steps 3-5 from §3 above are done: real dataset acquisition, the 6-scenario
  pack, CLIP calibration, and a full 44-run evaluation campaign (7 scenarios
  × 4 modes × vision-only/audio-visual where applicable). See
  `results/evaluation_campaign_notes.md` for the full writeup — short version:
  found and fixed 3 real pre-existing bugs (`.venv` silently broken and about
  to pollute the global Python env; `centralized` mode's timing rules used
  wall-clock instead of video time, meaning it could never detect
  loitering/abandoned-object; `intrusion_01`'s video sources were synthetic
  placeholder graphics that YOLO can never detect a person in, so that
  scenario never worked, including in the original pre-existing results
  already on disk before this branch started).
- `results/clip_anomaly_calibration_notes.md`: CLIP zero-shot AUC = 0.308
  (worse than random) on the fetched clips, root-caused to a prompt/scene
  domain mismatch (`NORMAL_PROMPTS` assume indoor warehouse scenes, test
  clips are outdoor street CCTV) — not a broken scorer. Documented, not
  hand-tuned away.
- `results/explanation_eval_notes.md`: template-fallback explanations (no
  LLM key in this environment) are evidence-complete on the alerts checked.
- Still open even within code scope (as of the 2026-08-13 pass): YAMNet not
  installed (disk-constrained; audio events degrade to generic
  `audio_anomaly`, which breaks the cross-modality family match needed for
  the C3 fusion-corroboration story — see campaign notes), and detection
  showed real run-to-run non-determinism that a single-pass campaign can't
  average out. Both are called out explicitly in
  `results/evaluation_campaign_notes.md` rather than papered over with a
  cherry-picked run.

### 2026-08-18 follow-up (same branch): YAMNet installed, campaign v2

Closes the YAMNet gap and the single-pass-only gap from the previous entry:

- YAMNet installed (`tensorflow-cpu`, local SavedModel — `tensorflow_hub`'s
  `tfhub.dev` URL turned out to be dead, HTTP 404) and wired into
  `AudioAgent` with two real bugs found and fixed along the way (transient-
  diluting mean-pooling on independently-rewindowed chunks; a missing `zone`
  on emitted audio events that independently blocked C3's corroboration
  claim even after the family-mapping fix). See
  `results/yamnet_integration_notes.md`.
- `results/eval/metrics.py` FAMILY dict and `fusion_agent.EVENT_FAMILIES`
  (previously duplicated and drifted out of sync) unified into
  `aura_mas/core/taxonomy.py`.
- `aura_mas/scenarios/replay.py` gained `--rep`/`--out`/`--audio-backend`
  and a warm-up pass moved before the scenario timer starts (closes the
  `fight_01` cold-start artifact from the previous campaign notes).
  `aura_mas/eval/metrics.py` gained a `summary_agg.csv` mean±std aggregation
  stage. `aura_mas/scripts/run_campaign.py` is the first campaign driver —
  previously a hand-typed loop.
- Two new audio scenarios (`audio_alarm_siren_01`, `audio_alarm_clock_01`)
  exercise the `hazard`-family `audio_alarm` class — every prior audio
  scenario used `audio_glass_break` only.
- Full change list, with expected direction of effect on each score, in
  `results/methodology_changes.md`. Re-run campaign numbers (multi-rep
  mean±std, replacing the single-pass v1 numbers) in
  `results/evaluation_campaign_v2_notes.md`.
- `results/summary_v1_dsp_baseline.csv` preserves the pre-YAMNet numbers
  for before/after comparison.
