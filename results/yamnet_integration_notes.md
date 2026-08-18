# YAMNet integration — findings (code-hardening branch, 2026-08-18)

Closes the gap flagged in `CLAUDE.md`'s "Current state" section and
`EXECUTION_PLAN.md` §5: YAMNet was not installed, so `AudioAgent` always ran
its DSP fallback and emitted generic `audio_anomaly` instead of
class-specific events (`audio_glass_break`, `audio_alarm`, ...), which broke
the cross-modality family match the fusion-corroboration claim (C3) needs.

## Install route

`tensorflow-cpu==2.21.0` via a dry-run-gated pip install (see
`results/env/`). Confirmed before installing: its pins (`numpy>=1.26.0`,
`protobuf<8.0.0,>=6.31.1`) were already satisfied by the installed
numpy 2.4.4 / protobuf 7.35.1 — the install added 20 new packages and
changed **zero** existing pins (verified via `pip freeze` diff), and pulled
no `nvidia-*`/`triton` packages (the CUDA trap `CLAUDE.md` already documents
from the 2026-08-13 pass — never `pip install tensorflow`, only
`tensorflow-cpu`). `.venv` grew from 2.4G to 3.8G; disk stayed at 17G free
after a `pip cache purge` reclaimed 660M first. `torch`, `torchvision`,
`ultralytics`, `librosa`, `clip` all re-verified working afterward, and
`pytest aura_mas/tests` stayed 6/6.

## Why not `tensorflow_hub`

The code AudioAgent used to call —
`tensorflow_hub.load("https://tfhub.dev/google/yamnet/1")` — **cannot work
at all as of 2026-08-18**: `tfhub.dev` returns HTTP 404 (verified directly).
The prior silent `except Exception` in `audio_agent.py:setup()` was masking
a dead URL, not just a missing package — this had never worked, with or
without `tensorflow_hub` installed.

Instead, `aura_mas/scripts/fetch_yamnet.py` downloads the YAMNet TF2
SavedModel directly from its Kaggle Models mirror
(`kaggle.com/api/v1/models/google/yamnet/tensorFlow2/yamnet/1/download`,
14,242,921 bytes, sha256-verified, unauthenticated GET) to `models/yamnet/`
and loads it with `tf.saved_model.load()`. This avoids: (a) the dead
tfhub.dev URL, (b) `tensorflow_hub>=0.16`'s dependency on the `tf-keras`
compatibility package under TF 2.21's Keras 3 (an extra ~dependency this
disk-constrained environment doesn't need), and (c) any network dependency
at scenario-run time — every run is now offline and reproducible from the
pinned, sha256-recorded model bytes (`models/yamnet/PROVENANCE.json`).
`models/yamnet/` is gitignored (fetched, not committed); only the
provenance file is tracked.

## A real accuracy bug found and fixed while wiring this up: mean-pooling dilutes short transients

Getting YAMNet loading was not sufficient — the first end-to-end test
against `data/clips_real/audio/glass_breaking_esc50.wav` produced **zero**
`audio_glass_break` events even with the model loaded and the right classes
present. Root cause, verified empirically:

- `AudioAgent` processes audio in independent, non-overlapping 1-second
  chunks (needed for the DSP fallback's realtime chunking). The original
  code called `scores.numpy().mean(axis=0)` on each chunk in isolation.
- A single continuous YAMNet pass over the whole 5s clip does detect the
  break cleanly — its internal frame at t≈1.44-2.4s scores `Breaking=0.56`,
  `Glass=0.50` (max over the clip's ~10 internal 0.96s/0.48s-hop frames).
- But independently re-windowing on fixed 1-second boundaries resets
  YAMNet's internal frame positions every chunk. The clip's ~0.5s glass-break
  transient straddles the `[1,2)s`/`[2,3)s` chunk boundary, so **no**
  internal frame in either independently-processed chunk is well-centered on
  it — averaged (mean) scores in the best chunk only reached `Glass=0.069`,
  `Breaking=0.042`, both well under the `SURVEILLANCE_CLASSES` thresholds
  (0.25/0.3).

**Fix** (`audio_agent.py:_process_chunk`, `run()`): each 1s chunk is now
scored over a lookback-extended window (the chunk plus the trailing half of
the *previous* chunk — a cheap, DSP-path-unaffected change since only the
YAMNet inference input changes, not the chunk passed to
`DspAnomalyScorer`), and aggregation switched from `mean(axis=0)` to
`max(axis=0)` across internal frames. Verified before/after on the same
clip:

| windowing | pooling | Glass | Breaking |
|---|---|---|---|
| independent 1s chunks (original) | mean | 0.069 | 0.042 |
| independent 1s chunks | max | 0.11 | 0.07 |
| lookback-extended (half-chunk overlap) | max | **0.75** | **0.69** |

This is a standard sliding-window event-spotting fix (overlap + max-pooling
to avoid boundary-splitting a transient), not threshold tuning — no
`SURVEILLANCE_CLASSES` confidence threshold was touched.

## End-to-end verification (real scenario runs, `--bus local`)

- `audio_glass_break_01`: fires `audio_glass_break` at conf 0.54 and 0.75
  (previously: generic `audio_anomaly` at conf 0.973 under DSP, which never
  matched the `security` family of the ground truth). One genuine extra
  false positive also appears: `audio_explosion` conf=0.49 near the
  noise-to-signal transition (t≈15s, where the synthetic uniform-noise
  prefix meets the real recording) — left as-is rather than suppressed;
  it's a real YAMNet misclassification on a real (if synthetic-prefixed)
  waveform, not a bug to hide.
- `audio_alarm_siren_01` (new scenario): fires `audio_alarm` at conf 0.67,
  0.80 (YAMNet class `Siren`).
- `audio_alarm_clock_01` (new scenario): fires `audio_alarm` at conf 0.88
  (YAMNet class `Alarm`).

All three confirm `AudioAgent.metrics["backend"] == "yamnet"` in the run
JSON, and the emitted `event_type` is the class-specific label, not
`audio_anomaly` — the machine-checkable answer to `CLAUDE.md`'s standing
instruction to "verify which audio path actually ran before citing
results."

## A second, independent bug blocking claim C3, found while testing `combined_audio_video_01`

Installing YAMNet alone does not make cross-modal fusion corroboration
(thesis claim C3) demonstrable on `combined_audio_video_01`. `AudioAgent`
never set `zone` on emitted `Event`s (always `None`), while `FusionAgent`
keys hypotheses by `f"{family}:{zone or 'site'}"`. Even with matching
families (`security` for both `intrusion` and `audio_glass_break`), the
video event (zone `zone_A`) and audio event (zone `None` → `"site"`) landed
in **different hypotheses** and could never corroborate, regardless of the
family-mapping fix in Phase 3/4. Fixed by adding `zone` to `AudioAgent`'s
constructor (propagated from the scenario manifest's per-sensor `"zone"`
key) and setting `"zone": "zone_A"` on `combined_audio_video_01.json`'s
audio sensor. See `results/methodology_changes.md` for the measured effect.

## Remaining limitation: FusionAgent window latency on short audio-only scenarios

Even with both bugs fixed, `audio_glass_break_01` and `audio_alarm_clock_01`
were observed to still miss the ±5s scoring tolerance in some runs — not
from detection failure (the correct class-specific event fires with high
confidence, well inside the ground-truth window) but from
`FusionAgent.window_seconds=6.0` (a hypothesis only flushes once 6s have
elapsed since its last contributing event) stacking with 1s tick
granularity and, in `mas-auction` mode, an auction round-trip
(`bid_window=1.0s` + up to `3.0s` verification timeout, even when there are
no cameras to bid on an audio-only scenario). Combined, this pushes the
final alert 7-10s past the raw detection event. This is a real,
scenario-timing characteristic of the architecture, not a scoring bug —
consistent with the same latency chain implicated in the pre-existing
`fight_01` cold-start finding (`results/evaluation_campaign_notes.md`).
**Not tuned away**: `window_seconds`, `bid_window`, and the metrics
tolerance were deliberately left untouched, since narrowing them to fit
these two scenarios would silently move every other scenario's numbers.
See `results/evaluation_campaign_v2_notes.md` for the measured effect
across the full campaign and a recommendation for how the thesis should
discuss it (likely: report verification latency as its own metric rather
than folding it into a pass/fail alert-timing tolerance).
