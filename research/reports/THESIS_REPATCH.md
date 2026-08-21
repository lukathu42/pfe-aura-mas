# Thesis re-patch list

**No file under `AURA-MAS_Thesis_LaTeX/` was touched to produce this document.**
This is a hand-patch worklist for whoever next edits the manuscript — every
row names the exact file/line, the current text's claim, why it needs to
change, and what to change it to. The v2 campaign (373 runs, N=5 headline
reps + N=3 DSP ablation, 0 failures) is now complete; all numbers below are
final, pulled from `results/summary_agg.csv` and written up in full in
`results/evaluation_campaign_v2_notes.md` — read that file for the complete
picture (including two structural evaluation-methodology findings not
repeated in full here) before patching any chapter text.

Background reading before applying any row: `results/methodology_changes.md`
(what changed and why), `results/yamnet_integration_notes.md` (the audio
fixes), `results/evaluation_campaign_notes.md` (the prior, still-relevant
v1 findings — synthetic-clip bugs, wall-clock timing bug — this document
does not repeat those).

## Priority 1 — a specific factual claim that appears to have been wrong when written

**`AURA-MAS_Thesis_LaTeX/Chapters/chapter6.tex:84`** (RQ3, Multimodality):

> "The glass-break incident is detectable only through the audio agent;
> fusing it into the *security* hypothesis family raised fused confidence
> through the cross-modality corroboration bonus of Equation~\ref{eq:noisyor},
> contributing a true positive in all variants."

This claim requires the audio agent's glass-break event to land in the
`security` family so it can share a `FusionAgent` hypothesis with the
video `intrusion` event. Checking the code as it existed before this pass:
`AudioAgent` had never successfully loaded YAMNet (its `tensorflow_hub` call
targets `tfhub.dev`, which returns HTTP 404 — see
`results/yamnet_integration_notes.md`), so it only ever emitted generic
`audio_anomaly` events. `audio_anomaly` has been mapped to family
`violence_or_hazard` (not `security`) since the *original* `EVENT_FAMILIES`
dict — this was true from the very first version of `fusion_agent.py`, not
a regression introduced later. A generic-fallback audio event could
therefore never have joined the same hypothesis as a video `intrusion`
event under the code as it actually ran. Additionally, `AudioAgent` never
set `zone` on emitted events (fixed in this pass, see
`methodology_changes.md` #5) — a second, independent reason corroboration
was structurally impossible.

**Action — resolved, here is what the v2 data actually shows.** Do not
restate the original claim even with new numbers substituted in; the claim
itself needs restructuring. Directly inspected
`results/run_combined_audio_video_01_mas-nocoord-r0.json` (pattern confirmed
identical across all 5 reps): `mic_01` fires 3 audio events, `cam_01` fires
9 video events, `FusionAgent` correctly merges them
(`events_in: 12 -> hypotheses_out: 5`), and the resulting alert's confidence
(0.78) does reflect the audio+video corroboration bonus — cross-modal fusion
**does now work**, for the first time, as a direct result of this pass's
zone fix and taxonomy unification.

But the emitted alert's `event_type` field reads `"intrusion"`, not
`"audio_glass_break"` — `Hypothesis.dominant_type()` (`fusion_agent.py`)
returns whichever single contributing event has the highest individual
confidence, and video's `intrusion` (conf 0.78-0.994) always outscores
audio's `audio_glass_break` (conf ~0.5-0.75) within the merged hypothesis.
So a reader of the raw alert log sees only "intrusion", with the audio
contribution invisible except in the boosted confidence number. Rewrite this
paragraph to describe the mechanism precisely: fusion *raises confidence and
survives in the alert's confidence value*, but does not currently produce a
labeled "this was audio+video corroborated" alert — a genuine, citable
limitation of `dominant_type()`'s single-winner labeling, worth naming
explicitly as future work (e.g. a `contributing_types` field on the alert).

Quantitatively (`results/summary_agg.csv`, `combined_audio_video_01`, N=5):
f1 ranges 0.1-0.467 across modes with std often >=0.2 — noisy and modest,
*not* because corroboration fails, but because of the metric-matching effect
in the next section. Do not cite a single "true positive in all variants"
claim; state the mean±std and explain the matching effect.

## Priority 1b — new finding: the evaluation metric under-credits successful fusion (worth a sentence in the limitations section)

Directly caused by the mechanism above: `metrics.py`'s greedy, ground-truth-order-dependent
1:1 alert-to-GT matching processes `combined_audio_video_01`'s ground truth
in manifest order (`intrusion` first, `audio_glass_break` second, both
family `security`). The single merged alert satisfies the `intrusion` GT
entry first, leaving nothing to match the `audio_glass_break` GT entry
against — even though the same alert already reflects that evidence via its
confidence. This structurally caps `combined_audio_video_01`'s measured
recall below what the system actually achieves whenever fusion succeeds.
**Not something this pass changed in code** (changing `metrics.py`'s
matching logic now would move every scenario's numbers without a clear
attribution boundary) — but it is a real, citable limitation of naive
per-alert scoring for late-fusion multi-agent systems, and belongs in the
evaluation-methodology / limitations discussion (chapter6, or a new
subsection) as its own point, independent of any specific F1 number.

## Priority 2 — chapter 6's entire RQ1-RQ5 analysis is sourced from the original n=1 sandbox run, not any campaign on this branch

`STATE_NOTES.md:19-25` documents the origin: a single run of `demo_site_01`
(the original, single-scenario, 2-camera-1-synthetic-audio version, before
the real 6-scenario pack existed). Every number in chapter6's RQ1/RQ2/RQ3
paragraphs traces back to that one run — not `results/summary.csv` (the v1
44-run campaign already on this branch), and not the v2 campaign this pass
adds. Concretely:

| Location | Current text | Source | v2 replacement (N=5, `demo_site_01`, `results/summary_agg.csv`) |
|---|---|---|---|
| `chapter6.tex:72` (RQ1) | "reduces mean time-to-alert from 21.6s to 13.3-13.8s, a ~36-38% improvement" | `STATE_NOTES.md:21-24` | centralized **15.07±3.11s** vs mas-auction **2.96±0.14s** — an **80.4% reduction**, larger than either the original (36-38%) or v1's single-pass number, because the warm-up fix (methodology change #6) removes a cold-start confound that previously landed unevenly across modes. mas-nocoord 5.60±3.14s, mas-rules 3.64±0.27s. Use these mean±std values, not the point estimates. |
| `chapter6.tex:74` (RQ2) | "FA/h nearly doubles versus centralized (107.5 vs 67.9)... round-robin 106.9 FA/h... auction restores precision to 0.667... 53.6 vs 107.5 FA/h... 21% better than centralized" | same n=1 run | **The v2 numbers do not support this narrative and it needs rethinking, not renumbering.** Measured: centralized FA/h **7.4±16.5**, mas-nocoord **29.8±36.5**, mas-rules **61.4±21.4**, mas-auction **52.6±5.9**. Precision: centralized **0.933±0.149**, mas-nocoord **0.767±0.224**, mas-rules **0.6±0.091**, mas-auction **0.667±0.0** (perfectly stable across reps). Auction is *not* lower-FA/h than nocoord here, and its precision is *not* higher than nocoord's mean (though nocoord's std is huge — 36.5 on a mean of 29.8 — meaning nocoord is wildly inconsistent run-to-run while auction is rock-stable at 0.667±0.0). The honest RQ2 story from this data is about **stability**, not raw precision/FA-h ranking: auction trades a possibly-higher point-estimate FA/h for dramatically lower variance. Do not force-fit the old "auction wins on every metric" narrative. |
| `chapter6.tex:76` ("+0.5s mean TTA... the auction's bidding window") | specific latency delta | same n=1 run | mas-auction TTA (2.96±0.14s) is actually *lower* than mas-nocoord (5.60±3.14s) and mas-rules (3.64±0.27s) in v2 — the bidding-window framing ("+0.5s cost") no longer fits; auction is the fastest coordinated mode here, not the slowest. Re-derive the sentence from scratch rather than patching the number. |
| `chapter6.tex:88` (RQ5) | "61 records in the auction run" | same n=1 run | Drop the specific count; state the invariant only (every alert/suppression/operator action is audited — still true, verified by the audit JSONL files accompanying every one of the 373 v2 runs). A magic number tied to one run does not generalize across N=5 reps of 9 scenarios. |

**Action**: Rewrite chapter6 §"Analysis by Research Question" entirely from
`results/summary_agg.csv` (v2, mean±std), not by find-and-replacing
individual numbers — RQ2 in particular needs a different *argument*, not
just different numbers (see above). The paragraphs' overall structure (RQ1
architecture/latency, RQ2 coordination, RQ3 multimodality, RQ4 explanation,
RQ5 governance) is still a reasonable frame. For RQ1/RQ2, decide whether to
report `demo_site_01` alone (closest to the original single-scenario framing)
or the full 6-9-scenario aggregate from `results/evaluation_campaign_v2_notes.md`
("Headline result" section, mean F1 0.245->0.498) — the aggregate is the
more defensible number for a thesis claim, `demo_site_01` alone is closer to
continuity with the existing prose.

## Priority 3 — audio path description needs the backend-selection caveat

**`AURA-MAS_Thesis_LaTeX/Chapters/chapter4.tex:83`**:

> "AudioAgents process 1-second chunks. In YAMNet mode..., a curated mapping
> from AudioSet classes to surveillance event types... produces typed
> events. In DSP fallback mode, rolling z-scores... produce generic
> `audio_anomaly` events..."

This description is now *accurate* (previously it described a code path
that had never actually run against a real evaluation, since YAMNet had
never loaded — it now has, across all 373 v2 campaign runs). Two things
worth adding:
- A footnote or sentence that the fallback triggers not just when
  `tensorflow`/`tensorflow_hub` are absent but also transiently on load
  failure (the original silent `except Exception` masked a dead URL for an
  unknown period — worth a sentence on why `backend="yamnet"` now exists to
  make failures loud instead of silent, see `yamnet_integration_notes.md`).
- The 1-second chunking description should mention the lookback-extended
  window (methodology change #2) if the thesis wants to describe the
  detector's temporal resolution accurately — a short transient event is
  scored over up to 1.5s of context, not a bare 1s window.

**`chapter5.tex:22`** (implementation stack table) cites `tensorflow_yamnet`
as the audio SED backend — this is now actually true rather than aspirational
(previously it was documented as configured but never verified running).
No change needed to the citation itself, but chapter5/6 should stop hedging
language like "if installed" wherever it currently exists, IF `tensorflow_yamnet` is present in the final environment cited for the defense — confirm before removing any hedge.

**New evidence for this section — the DSP-vs-YAMNet ablation (N=3,
`results/summary_agg.csv`, `audio_backend=dsp` rows)**: for every audio-only
scenario, DSP-fallback f1 is **exactly 0.0±0.0 in all 3 reps, every mode** —
`audio_glass_break_01`, `audio_alarm_clock_01`, `audio_alarm_siren_01` all
score zero under DSP regardless of coordination mode, because the generic
`audio_anomaly` label never matches a class-specific ground-truth family.
Under YAMNet the same scenarios score 0.0-1.0 (mean 0.6-1.0 for most
mode/scenario pairs; `audio_alarm_clock_01` hits a clean **1.0±0.0 across
all 4 modes**). This is the single most quantitatively dramatic result in
the v2 campaign and the clearest evidence for the audio-integration claim —
worth a table or the new `results/figures/fig_audio_backend_ablation.png`
figure in chapter5 or chapter6, not just prose.

## Priority 4 — carryover items, not new to this pass (already flagged, still open)

These were already documented as open before this pass and remain open —
listed here only so a single re-patch pass can close them alongside the
items above, not because this pass changed anything about them:

- **CLIP AUC = 0.308** (`results/clip_anomaly_calibration_notes.md`) is not
  mentioned anywhere in the current chapter text (checked: no `AUC` or
  `calibrat` hits in `AURA-MAS_Thesis_LaTeX/Chapters/*.tex`). The thesis
  currently describes `ClipAnomalyScorer` (`chapter5.tex:67`) purely
  mechanically, without stating that its zero-shot calibration measured
  worse than random. This should be added to the evaluation/limitations
  chapter regardless of the v2 campaign outcome — it is an existing,
  already-final finding.
- Author/supervisor identity fix (`EXECUTION_PLAN.md` §0) — still open,
  out of scope for this branch.
- 88/94 unverified `bibliography.bib` entries — still open, out of scope
  for this branch.

## What does NOT need re-patching

- `chapter4.tex:88-95` (FusionAgent hypothesis mechanics, noisy-OR formula,
  modality reliability weights 0.9/0.7, corroboration bonuses 0.05/0.05):
  mechanically unchanged by this pass. Only the *empirical claim* that this
  mechanism was exercised end-to-end (Priority 1) needs revisiting, not the
  formula or its description.
- `chapter3.tex:36` (late-fusion design rationale): a methodology
  justification, not an empirical claim — unaffected.
- Chapters 1, 2, 7: no scenario-specific numbers found (chapter1's C1-C5
  contributions list and RQ framing are unaffected; C3's description at
  `chapter1.tex:39` is still accurate as an architectural claim, independent
  of whether any single run demonstrates it).
