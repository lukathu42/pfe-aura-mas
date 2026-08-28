# Ground truth is authored in video seconds but scored against wall seconds

**Date:** 2026-08-26
**Branch:** `multi-zone-demo-scenarios`
**Status:** discrepancy **surfaced, not fixed** — per `CLAUDE.md` ("don't
silently rewrite evaluation numbers… surface discrepancies to the user").
Nothing in `eval/metrics.py`, nothing in any existing scenario, and nothing in
any existing results artifact was changed on account of this note.

---

## 1. The claim

Every `scenarios/*.json` ground-truth window is authored in **video seconds**.
`eval/metrics.py` matches alerts using **wall seconds since run start**. On
this machine the two differ by a factor of roughly **1.2×**, and the error
**accumulates over the length of a clip**, so events late in a clip are
systematically penalised.

## 2. Why the two clocks diverge

Three independent facts, each read directly from the code:

**(a) Rules fire on video time.** `camera_agent.py:412` calls
`self.rule_engine.evaluate(objects, video_ts …)` where
`video_ts = frame_id / src_fps` (`camera_agent.py:344`). So a rule's notion of
"8 seconds of dwell" is 8 seconds *of footage*, which is correct and is what
the 2026-08-13 campaign fixed for `centralized` mode.

**(b) Alerts are stamped in wall time.** `replay.py:119` records
`{"t_wall": time.time(), …}` for each alert, and `metrics.py:45` computes
`a_t = a["t_wall"] - t0` with `t0 = run["t_start"]`. The comparison at
`metrics.py:46-47` is then

```python
if a_fam == g_fam and (g["t_start"] - tolerance) <= a_t <= (g["t_end"] + tolerance):
```

— a **wall-clock** `a_t` against a **video-time** `g["t_start"]`/`g["t_end"]`.

**(c) The realtime pacer can only slow playback down, never speed it up.**
`camera_agent.py:349-352`:

```python
if self.realtime:
    budget = frame_id / src_fps - (time.time() - t_start)
    if budget > 0:
        time.sleep(min(budget, 0.5))
```

There is no catch-up branch. Once inference is slower than the frame budget,
`budget` goes negative, the `sleep` is skipped, and the deficit is **never
repaid** — it accumulates for the rest of the clip.

And inference *is* slower than the budget. With `infer_fps = 5.0` the stride
budget is 200 ms/frame, but the measured mean in
`results/run_demo_site_01_mas-auction-r0.json` is **`infer_ms` 241.6 for
cam_01 and 230.9 for cam_02** — YOLO11n on CPU. So

```
wall_elapsed ≈ video_elapsed × (infer_ms × infer_fps / 1000)
             ≈ video_elapsed × 1.21   (cam_01)
             ≈ video_elapsed × 1.16   (cam_02)
```

Note this affects `mas-auction`/`mas-rules`/`mas-nocoord` (`realtime=True`)
**and** `centralized` (`realtime=False`, so no sleeping at all) — both are
compute-bound, so both drift. It is not a mode-specific artifact.

## 3. Arithmetic check against a real artifact

From `results/run_demo_site_01_mas-auction-r0.json`
(`t_start = 1787063872.5125`):

| quantity | value | wall offset |
|---|---|---|
| cam_01 frames | 298 @ stride 5 fps | video length 59.6 s |
| `wall_seconds` | 83.43 | — |
| 3rd alert's evidence frames | `…_1787063917`, `…_918`, `…_919` | +44.5, +45.5, +46.5 |
| 3rd alert `t_wall` | 1787063925.4545 | **+52.94** |

Two things fall out, both confirming the model:

1. **Fusion delay.** Last contributing event at wall +46.5, alert at +52.94 →
   **6.4 s**. `FusionAgent` only emits a hypothesis once
   `now - hyp.last_ts > window_seconds` (`fusion_agent.py:150`, default
   `6.0`). So alert wall time ≈ last-event wall time **+ 6 s**, plus ~1.5 s
   more when the hypothesis lands in the auction gray zone (the same run
   records `allocation_ms: [1527.5]`).
2. **Drift.** 298 processed frames × 241.6 ms ≈ 72.0 s of compute for 59.6 s
   of video; `wall_seconds` 83.4 = that plus the
   `time.sleep(fusion.window_seconds + 1.5)` tail at `replay.py:177` and
   thread-join overhead. Consistent.

So the end-to-end relation an author needs is:

```
a_t  ≈  video_ts_of_event × 1.2   +   6.0   [ + ~1.5 if auctioned ]
```

## 4. Consequence for that run's score

`demo_site_01`'s intrusion GT window is `t_start: 3.0, t_end: 35.0`, so with
`tolerance = 5.0` the accepted band is `[-2.0, 40.0]`. The third alert is a
`zone_A` **intrusion** — a genuine, correct detection of a person entering the
restricted quadrant — but its `a_t` is **52.94**, i.e. **12.9 s outside** the
band. `metrics.evaluate_run` therefore books it as a **false positive**, not a
true positive.

Its underlying event is at video ≈ 46.5 / 1.2 ≈ **38.7 s**, which is itself
already past `t_end = 35.0`. So part of this is GT that genuinely stops too
early, and part is drift pushing it further out. **Both** point the same way:
the run is being scored more harshly than the system actually performed.

This is very likely a contributing mechanism behind the run-to-run
non-determinism `CLAUDE.md` warns about ("rerun N≥3 times before citing a
number as final"). Alerts whose `a_t` sits within a few seconds of a window
edge flip between TP and FP depending on how loaded the machine was — which
looks like detector non-determinism but is really a clock mismatch. It is
**not** a full explanation, and this note does not claim it is: PyTorch CPU
float non-determinism at borderline confidence thresholds is independently
documented and remains a real second cause.

## 4b. The `centralized` baseline is penalised far worse than the MAS modes

This is the most consequential consequence, because it lands directly on the
thesis's headline comparison.

`replay.py:165-169` runs the `centralized` baseline **strictly sequentially**:

```python
if mode == "centralized":
    # centralized baseline: process sources sequentially in ONE process,
    # no edge parallelism -> measures the architectural benefit of the MAS
    for th in threads:
        th.start()
        th.join()
```

`th.join()` blocks, so camera 2's *video clock starts from zero only after
camera 1's clip has been fully consumed* — while camera 2's ground truth is
still expressed in its own video seconds. The second camera's alerts are
therefore shifted by the **entire wall duration of the first camera's clip**.

Measured, in the two runs of `demo_site_01` on disk — the *same physical
`zone_B` intrusion*, detected by the same `cam_02` on the same footage:

| mode | execution | `zone_B` intrusion alert `a_t` |
|---|---|---|
| `mas-auction` | cameras in parallel | **+9.4 s** |
| `centralized` | cameras sequential | **+49.05 s** |

A **~40-second** difference that is entirely an artifact of execution order.
Nothing about `centralized`'s *detection* was worse; its clock was simply
offset by cam_01's runtime. With GT bands of `[-2, 40]` and `[11, 51]`, a 40 s
shift is the difference between landing inside a window and falling off the
end of the scenario.

This affects exactly the two multi-camera scenarios — `demo_site_01` and
`intrusion_01` (verified: all other seven manifests have ≤1 camera) — and it
biases them **against `centralized`**, which is the baseline the MAS modes are
being claimed to beat. The bias is invisible in the single-camera scenarios,
so it does not show up as an obvious outlier.

To be careful about what this does and does not say: sequential execution is a
**legitimate and deliberate** property of the centralized baseline — it is the
architectural difference being measured, and `replay.py`'s own comment says so.
The defect is not the sequential execution. It is that GT is compared against a
wall clock that sequential execution stretches, so the measurement conflates
"this architecture is slower" with "this architecture failed to detect." The
first is a real, citable result; the second is an artifact.

## 4c. The zone-blind matcher makes multi-camera scores insensitive to *which* camera was right

Worked example, from the same two runs. `demo_site_01`'s GT is:

| # | event | zone | window | family | band (±5 s) |
|---|---|---|---|---|---|
| 1 | `intrusion` | `zone_A` | 3.0–35.0 | `security` | [-2, 40] |
| 2 | `loitering` | `entry` | 16.0–46.0 | `security` | [11, 51] |
| 3 | `audio_glass_break` | `null` | 14.0–16.0 | `hazard` | [9, 21] |

GT 1 and GT 2 are **both family `security`** with **overlapping bands**, and
`metrics.py:40-52` compares family and time only — never zone. So:

- In `centralized`, the `zone_A` intrusion alert at +32.04 is booked as a true
  positive for GT 2 — a **`loitering` event in zone `entry`**. Wrong zone,
  wrong event type; scored correct because the family and time matched.
- In `mas-auction`, the **`zone_B`** intrusion alert at +9.4 is booked as the
  true positive for GT 1, which is a **`zone_A`** event.

Both runs score TP=2, FP=1, FN=1 → precision 0.667, recall 0.667, **F1
0.667** — which is the median F1 reported in `results/thesis_stats.json`. The
two runs reach the same score through *different, mutually inconsistent*
matchings.

The consequence for this branch's purpose is direct: **the existing metrics
cannot distinguish correct cross-camera attribution from a lucky
same-family time collision.** Any claim that coordination improved
*cross-camera* behaviour cannot be supported by these numbers, whichever way
they come out. That is an independent reason — beyond the coverage gap — why
the new scenario pack keeps same-family GT events > 5 s apart and never puts
two same-family GT windows in overlap.

## 5. What was *not* done, and why

No fix was applied. The options each have a cost that is the repo owner's call,
not this pass's:

- **Stamp alerts with video time.** Most correct, but `Alert` has no video-time
  field, several agents would need to thread it through, and it would change
  the meaning of `t_wall` in **373 existing run JSONs** that are cited
  evaluation artifacts.
- **Convert in `metrics.py`.** Cheapest, but `eval/metrics.py` is shared
  scoring code for every existing result; touching it silently re-scores the
  whole campaign. Explicitly out of scope for this branch
  (`docs/HANDOFF_multi-zone-demo-scenarios.md` lists `eval/metrics.py` as
  untouched).
- **Widen every existing GT window.** Rewrites cited ground truth — precisely
  what `CLAUDE.md` forbids doing unilaterally.
- **Raise `tolerance`.** A one-line change with a global effect on precision;
  it would also mask genuine latency regressions.

## 6. How the new scenarios handle it

The four new manifests keep the **existing convention** (GT authored in video
seconds — no parallel format is introduced), and additionally:

1. Choose GT windows wide enough that `video_ts × 1.2 + 6.0` lands inside
   `[t_start - 5, t_end + 5]`, with the arithmetic written out in each
   manifest's `notes` so the choice is auditable instead of magic.
2. Place the intended events **early in each clip** where accumulated drift is
   smallest, rather than near the end where it is worst.
3. Keep same-family GT events > 5 s apart, so the greedy zone-blind matcher
   (`metrics.py:40-52` compares family and time only, never zone) cannot
   satisfy one zone's GT with another zone's alert.

That makes the new scenarios scoreable *without* changing shared scoring code
— but it does **not** repair the existing 373-run campaign, and no number in
`results/summary.csv` or `results/summary_agg.csv` should be treated as
corrected by this note.

## 6b. Live impact on the in-progress v3 thesis statistics — read this first

This matters **now**, not eventually, because uncommitted work on the
`thesis-v3-update` branch is actively consuming the affected numbers:

- `aura_mas/scripts/thesis_stats.py:49` reads `results/summary.csv`.
- `aura_mas/scripts/make_thesis_figures.py:43-44` reads
  `results/thesis_stats.json` and `results/summary.csv`, and its docstring
  states "nothing is hard-coded" — so every figure inherits whatever the CSV
  says.
- `results/thesis_stats.json` records `n_rows_used: 180`, 10 000 bootstrap
  resamples, `seed: 20260826`, Wilcoxon signed-rank paired on
  `(scenario, rep)`, Holm–Bonferroni over 6 pairwise mode comparisons, Cliff's
  delta. Six figures are already generated in `results/figures/`.

That is a careful, properly-corrected analysis — the statistics are not the
problem. The problem is what they are computed *over*. Two of the affected
quantities are load-bearing:

1. **`mean_time_to_alert_s`** (`metrics.py:51`,
   `time_to_alert.append(max(0.0, a_t - g["t_start"]))`) is a **wall-clock**
   latency measured against a **video-time** origin. It therefore includes the
   6 s `FusionAgent` window, the ~1.5 s auction, the ~1.2× compute drift, and —
   in `centralized` on multi-camera scenarios — the whole of the preceding
   camera's runtime. `results/figures/fig_tta_per_scenario.png` plots this
   directly.
2. **F1 / precision / recall** inherit the TP/FP/FN misclassifications in §4,
   §4b and §4c.

Because §4b's bias runs **against `centralized`** specifically, and only on the
two multi-camera scenarios, the paired mode comparisons are affected
**asymmetrically** — which is precisely the kind of confound a paired test is
otherwise good at removing. `fig_mode_ci.png` and `fig_paired_forest.png` are
the two figures where this would show up.

**Recommendation, and it is deliberately conservative:** do not regenerate or
adjust any of these figures on the strength of this note. The direction of the
effect is knowable (`centralized` is penalised, absolute TTA is inflated) but
the magnitude is not, without a re-run. The honest options are to re-run with a
video-time field (§7) and report the delta, or to keep the current numbers and
state the limitation explicitly in the Results/Threats-to-Validity section.
Either is defensible. Silently keeping the numbers while claiming they measure
detection quality on multi-camera scenarios is not.

## 7. Recommended follow-up for the repo owner

Cheapest honest path, in order:

1. Add a `video_ts` field to `Event`/`Alert` alongside the existing wall
   timestamp — **additive**, so the 373 existing artifacts stay readable.
2. Have `metrics.py` prefer `video_ts` when present and fall back to
   `t_wall - t_start` when absent, so old and new artifacts both score.
3. Re-run the campaign and publish both columns, with the delta reported as a
   methodology correction in `results/methodology_changes.md` (which already
   exists for exactly this purpose and maps old→new for every
   scoring-affecting change).

Step 3 is the one that matters for the defence: the direction of the
correction is that **current published recall is an underestimate**, which is
a safe way to be wrong but still needs stating rather than quietly fixing.
