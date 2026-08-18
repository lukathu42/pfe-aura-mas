# Evaluation campaign v2 — YAMNet + N=5 mean±std (code-hardening branch, 2026-08-18)

**Supersedes** `results/evaluation_campaign_notes.md` (v1) as the current
evaluation — the v1 file is kept on disk, not overwritten, since it documents
real bugs (synthetic `intrusion.mp4`, wall-clock timing) that are still
relevant history. This file documents what changed on top of that baseline:
YAMNet installed and wired in, four scoring-affecting bug fixes (see
`results/methodology_changes.md` for the full list with before/after
attribution), two new audio scenarios, and — the headline methodological
change — **N=5 repetitions per (scenario, mode) combination reported as
mean±std**, replacing v1's single-pass numbers.

**Campaign scale**: 373 runs, 0 failures (`results/campaign_log.csv`).
Headline matrix: 9 scenarios × 4 modes × {audio-visual, vision-only where
applicable} × 5 reps = 300 runs. DSP-backend ablation: the 6 audio-capable
scenarios × 4 modes × 3 reps = 72 runs (audio-only, no vision-only variant
needed). Plus 1 rep0 vision-only smoke check already counted in the 300.
Raw data: `results/run_*.json`, `results/summary.csv` (one row per run),
`results/summary_agg.csv` (84 groups, mean/std/n per scenario×mode×backend).

**Important aggregation detail**: `summary_agg.csv` and this document exclude
the 44 v1 (pre-YAMNet, single-pass, `rep=None`) runs from every mean/std —
pooling a single old-methodology run in with 5 real v2 repetitions would
silently corrupt the statistics (this was a real bug caught and fixed during
this pass in `aura_mas/eval/metrics.py:aggregate()` and
`aura_mas/scripts/make_figures.py`, see `methodology_changes.md`). v1 numbers
below come from the preserved `results/summary_v1_dsp_baseline.csv`.

## Headline result: mean F1 roughly doubled on the same 6 scenarios

Averaged over the original 6 scenarios × 4 modes (audio-visual, excluding
the `loitering_01` true-negative probe — same convention as v1 and
`make_figures.py`):

| | mean F1 | n (scenario×mode) |
|---|---|---|
| v1 (single pass, DSP fallback) | **0.245** | 24 |
| v2 (N=5 mean, YAMNet) | **0.498** | 24 |

Per-mode breakdown (v1 single-run → v2 5-rep mean):

| mode | v1 F1 | v2 F1 (mean of per-scenario means) |
|---|---|---|
| centralized | 0.194 | 0.584 |
| mas-nocoord | 0.296 | 0.649 |
| mas-rules | 0.261 | 0.551 |
| mas-auction | 0.229 | 0.508 |

(v2's "centralized"/"mas-nocoord" rows above pool 8 scenarios including the
2 new audio ones; the 24-run apples-to-apples total above uses only the
original 6.)

## Fix 1 verified: `fight_01` cold-start timing artifact resolved

v1: f1 = **0.0** across all 4 modes (`results/summary_v1_dsp_baseline.csv`)
— the CLIP+YOLO cold-start load (~10s on CPU) landed inside the timed
window because the scenario timer started before agents were even
constructed, pushing the alert to t≈15.4s against an 8s scenario's
`[-4.5, 9.5]s` tolerance window.

v2 (N=5 mean±std, `results/summary_agg.csv`):

| mode | f1 mean | f1 std |
|---|---|---|
| centralized | **1.0** | 0.0 |
| mas-nocoord | 0.8 | 0.447 |
| mas-rules | 0.4 | 0.548 |
| mas-auction | 0.2 | 0.447 |

The warm-up fix (methodology change #6) completely removes the systematic
zero — `centralized` now hits the tolerance window in all 5/5 reps. But this
also surfaces a second, honest finding the single-rep rep0 check (which
happened to show 1.0 across all modes) did not: **MAS coordination modes
show real run-to-run variance on this tightly-timed 8s scenario** —
`mas-auction` only lands inside tolerance in 1/5 reps. `fight_01`'s 8s
duration leaves very little margin once the FusionAgent window (6s) plus an
auction round-trip (up to ~4s: 1s bid window + up to 3s verification
timeout) is added on top of detection latency; small scheduling jitter
between runs is enough to push the alert in or out of the ±5s tolerance.
`centralized` has no coordination round-trip and is correspondingly
perfectly stable (std=0.0). **This is why N=5 matters**: a single rep's
"f1=1.0 everywhere" result (which is what this session's rep0 validation
pass showed) would have been a materially misleading headline number.

## Fix 2 verified: class-specific audio detection, DSP-vs-YAMNet ablation

The DSP-backend ablation (`--audio-backend dsp`, N=3) makes the fix's effect
unambiguous. For every audio-only scenario, DSP-fallback f1 is **exactly
0.0±0.0 in all 3 reps, every mode** — the generic `audio_anomaly` event
never matches any class-specific ground truth family, regardless of how
confidently the DSP scorer fires (previously verified at conf=0.973 on the
same underlying clip, see `yamnet_integration_notes.md`):

| scenario | DSP f1 (all modes) | YAMNet (`auto`) f1 mean, range across modes |
|---|---|---|
| `audio_glass_break_01` | 0.0 | 0.0 (centralized) – 0.8 (MAS modes) |
| `audio_alarm_clock_01` | 0.0 | **1.0±0.0, all 4 modes** |
| `audio_alarm_siren_01` | 0.0 | 0.2 (centralized) – 0.8 (mas-auction/mas-rules) |

`audio_alarm_clock_01` is the cleanest result in the whole campaign: perfect
1.0±0.0 across every coordination mode, N=5. `audio_glass_break_01` and
`audio_alarm_siren_01` show the fusion-window-latency effect below —
`centralized` in particular is weak on `audio_glass_break_01` (f1=0.0±0.0)
even under YAMNet; investigated and explained next.

Video-carrying multi-modal scenarios (`demo_site_01`, `intrusion_01`,
`combined_audio_video_01`) stay well above 0 even under DSP fallback,
because their video-only events (independent of audio) can still match
GT — e.g. `demo_site_01` DSP mas-rules hits f1=1.0. This is expected and
consistent: DSP failure zeroes only the *audio* contribution, not the
system.

## Finding: FusionAgent window latency, not detection failure, explains some audio-only misses

Investigated directly (`results/run_audio_glass_break_01_mas-auction-r0.json`):
the audio agent fires the *correct* event — `audio_glass_break`, conf 0.702,
`backend=yamnet` — well inside the ground-truth window. The alert, however,
lands at **t=26.47s** against a GT window of `[15.0, 19.5]` and a ±5s
tolerance of `[10, 24.5]` — a 1.97s miss, purely from latency stacking:
`FusionAgent.window_seconds=6.0` (a hypothesis only flushes 6s after its
last contributing event) + ~1s tick granularity + (`mas-auction` only) an
auction round-trip that still runs even with zero cameras to bid on an
audio-only scenario. `centralized`'s consistent 0.0 on this scenario across
all 5 reps is consistent with this: centralized has no auction round-trip,
but is also unpaced (processes the file as fast as possible with no
real-time sleep), which changes the coordination-independent timing profile
in a way not yet root-caused separately from this latency stack.

**Not tuned away** — `FusionAgent.window_seconds`, `CoordinatorAgent.bid_window`,
and the metrics `--tolerance` were deliberately left untouched (see
`methodology_changes.md`, "Explicitly NOT changed"). Narrowing them to fit
these specific scenarios would silently move every other scenario's timing
numbers. This is reported as a genuine architecture characteristic:
verification/fusion latency can exceed a ±5s scoring tolerance on short,
single-incident audio-only scenarios, and is a candidate for the thesis to
discuss as future work (e.g. scoring "detected" separately from "alerted
within tolerance," or scaling tolerance with `window_seconds`).

## Finding: `combined_audio_video_01` shows fusion succeeding, but the metric can't fully credit it

Directly inspected `results/run_combined_audio_video_01_mas-nocoord-r0.json`
(and confirmed identical structure across all 5 reps): `mic_01` fires 3
audio events, `cam_01` fires 9 video events, and `FusionAgent` correctly
combines them — `events_in: 12` → `hypotheses_out: 5`. But the final
**alert** for the merged security-family, zone_A hypothesis reports
`event_type: "intrusion"` (not `audio_glass_break`), because
`Hypothesis.dominant_type()` returns the event type of whichever single
contributing event has the highest confidence — and the video `intrusion`
event (conf 0.78–0.994) consistently outscores the audio `audio_glass_break`
event (conf ~0.5–0.75) within the merged hypothesis.

This alert *is* the corroborated, cross-modal detection the C3 claim is
about — its confidence (0.78) reflects both modalities via the zone fix
(methodology change #5). But `metrics.py`'s greedy, order-dependent 1:1
alert-to-GT matching processes ground truth in manifest order (`intrusion`
first, `audio_glass_break` second): the merged alert satisfies the
`intrusion` GT entry first (both share family `security`), leaving nothing
for the `audio_glass_break` GT entry to match against, even though the same
alert already reflects that evidence. Result: `combined_audio_video_01`'s
recall is structurally capped below what the system actually achieved.

**Not fixed by changing `metrics.py`'s matching logic** — that would need a
many-to-one or evidence-aware matching scheme, a real but separate piece of
future work, and changing it now would move every scenario's numbers in a
way that's hard to attribute cleanly. Documented here and in
`THESIS_REPATCH.md` as an evaluation-methodology finding: **the current
metric under-credits successful multi-modal fusion**, which is a novel and
citable observation in its own right (a limitation of naive per-alert
scoring for late-fusion multi-agent systems), not a system defect.

`combined_audio_video_01`'s f1 accordingly stays modest and noisy across
modes (0.1–0.467, std often ≥0.2) — consistent with this structural
under-crediting rather than indicating detection failure.

## `loitering_01` true-negative probe: still clean

`gt_events=0, alerts=0, fp=0` in **all 24 runs** (v1's single pass + all 5
v2 reps, every mode) — zero false positives on brief zone crossings, exactly
as the probe is designed to verify (`scenarios/loitering_01.json`'s
documented finding that no clip in the pack has a continuous single-track
presence ≥8s). Unchanged by this pass; included here only to confirm it
remained clean under the timer/warm-up and taxonomy changes.

## What this means for citing numbers

`results/summary_agg.csv`'s mean±std is now the citable per-condition
number, not any single `results/run_*.json`. Every headline figure in
`results/figures/` was regenerated from it with error bars
(`fig_detection_quality.png`, `fig_system_metrics.png`,
`fig_coordination_overhead.png`, `fig_modality_ablation.png`, and the new
`fig_audio_backend_ablation.png`). See `THESIS_REPATCH.md` for exactly which
thesis claims/numbers these supersede.
