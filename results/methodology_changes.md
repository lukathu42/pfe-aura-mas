# Methodology changes — v1 → v2 campaign (code-hardening branch, 2026-08-18)

Every change below can move a number in `results/summary.csv` relative to
`results/summary_v1_dsp_baseline.csv` (preserved copy of the pre-YAMNet
campaign). Listed so any score delta between v1 and v2 is attributable to a
named, documented cause — not silent renumbering. See
`results/evaluation_campaign_v2_notes.md` for the measured before/after
numbers once the v2 campaign completes.

| # | Change | File(s) | Why | Expected direction |
|---|---|---|---|---|
| 1 | YAMNet installed and wired via a local SavedModel (was: DSP fallback only, `tensorflow_hub` URL was dead) | `aura_mas/agents/audio_agent.py`, `aura_mas/scripts/fetch_yamnet.py` | `CLAUDE.md`/`evaluation_campaign_notes.md` documented this as the #1 gap blocking claim C3 | audio-scenario recall/precision up (class-specific `audio_glass_break`/`audio_alarm` now matches GT family instead of generic `audio_anomaly`) |
| 2 | YAMNet scoring: lookback-extended window + max-pooling (was: independent 1s chunks + mean-pooling) | `aura_mas/agents/audio_agent.py` `_process_chunk`/`run` | mean-pooling on independently re-windowed 1s chunks diluted short transients below detection threshold — verified 0.069 vs 0.75 confidence on the same clip (see `yamnet_integration_notes.md`) | audio recall up; without this fix, change #1 alone would not have produced any audio_glass_break events at all |
| 3 | Per-chunk event dedup: one event per `event_type` per chunk (max confidence), was: one event per matching YAMNet class (Glass+Shatter+Breaking could all fire from one chunk) | `aura_mas/agents/audio_agent.py` `_process_chunk` | un-deduped events feed FusionAgent's noisy-OR as independent evidence, inflating confidence for what is really one detection (e.g. 3 near-duplicate events at conf 0.3 → fused ~0.51 vs the correct ~0.21) | audio-scenario false-positive count / inflated confidence down |
| 4 | `metrics.FAMILY` and `fusion_agent.EVENT_FAMILIES` unified into one source of truth (`aura_mas/core/taxonomy.py`) — `metrics.FAMILY` was missing `audio_explosion`/`audio_breaking` | `aura_mas/eval/metrics.py`, `aura_mas/agents/fusion_agent.py` | the two dicts had drifted out of sync; unmapped event types could only ever score as false positives even when FusionAgent already treated them as corroborating evidence | any run where YAMNet fires `audio_explosion`/`audio_breaking`: recall up, false-alert rate down for that alert |
| 5 | `AudioAgent` now sets `zone` on emitted events (was: always `None`); `combined_audio_video_01.json`'s audio sensor given `"zone": "zone_A"` matching its camera | `aura_mas/agents/audio_agent.py`, `scenarios/combined_audio_video_01.json` | `FusionAgent` keys hypotheses by `f"{family}:{zone or 'site'}"` — without a matching zone, audio and video events land in different hypotheses and can never corroborate, independent of the family-mapping fix (#4). Second, independent bug blocking claim C3. | `combined_audio_video_01` fused confidence up specifically where video+audio events overlap in time and zone |
| 6 | Scenario timer moved to after all agents warm up (one dummy inference each), was: timer started before agents were even constructed | `aura_mas/scenarios/replay.py`, `aura_mas/agents/camera_agent.py` (`warmup()`), `aura_mas/agents/audio_agent.py` (`warmup()`) | YOLO/CLIP/YAMNet cold-start load latency (~seconds to ~14s on CPU) was counted against time-to-alert, penalizing short scenarios — documented root cause of the pre-existing `fight_01` f1=0 artifact | `wall_seconds` drops for every scenario/mode; `mean_time_to_alert_s` drops for scenarios with `enable_clip` or audio sensors; short scenarios' pass/fail against the ±5s tolerance may flip |
| 7 | Repetition plumbing: `--rep`/`--out` on `replay.py`, rep-suffixed filenames, `rep`/`audio_backend`/`tag` recorded in run JSON (was: fixed per-(scenario,mode) filename, reruns silently overwrote) | `aura_mas/scenarios/replay.py` | needed for N-rep mean±std reporting; v1 was a single, unrepeatable pass with no variance estimate | not scoring-affecting per se, but changes what "the number" means: v2 reports mean±std, v1 reported one sample |
| 8 | `metrics.py` aggregation stage (`summary_agg.csv`, mean/std/n per scenario×mode×audio_backend group) | `aura_mas/eval/metrics.py` | same as #7 | not scoring-affecting; new output artifact alongside the unchanged per-run `summary.csv` |
| 9 | Two new audio scenarios (`audio_alarm_siren_01`, `audio_alarm_clock_01`) using previously-unused ESC-50 assets | `scenarios/audio_alarm_siren_01.json`, `scenarios/audio_alarm_clock_01.json`, `aura_mas/scripts/make_audio_baselines.py` | every prior audio scenario used `audio_glass_break` GT only — no scenario exercised the `hazard`-family `audio_alarm` class; needed to demonstrate class *discrimination*, not just class presence | new rows in `summary.csv`; does not change any existing scenario's score |
| 10 | `anomaly_threshold` (CLIP) now readable from scenario manifest (was: hardcoded `CameraAgent.__init__` default, unreachable from manifest/CLI) | `aura_mas/scenarios/replay.py` | `results/clip_anomaly_threshold_sweep.csv` already exists but nothing could act on it | no effect unless a manifest sets `"anomaly_threshold"` explicitly — none currently do, so v1/v2 CLIP behavior is unchanged by this alone |

## Note on root-level duplicate files

`CLAUDE.md` documents that root-level `.py` files (`fusion_agent.py`,
`metrics.py`, `audio_agent.py`, `camera_agent.py`, `replay.py`, etc.) are
byte-identical copies of `aura_mas/` from a prior flattened delivery bundle,
and that `aura_mas/` is canonical. This pass edited only `aura_mas/` (and
added new files there), per that guidance. The root copies now have the
**pre-fix** `FAMILY`/`EVENT_FAMILIES` dicts and the old `AudioAgent`/
`CameraAgent`/`replay.run_scenario` — anyone diffing the root copies against
`aura_mas/` after this pass will see real divergence, not accidental drift.
Do not run anything from the root-level copies expecting v2 behavior.

## Explicitly NOT changed (and why)

- **`FusionAgent.window_seconds` (6.0) and `CoordinatorAgent.bid_window`/verification timeout** were left untouched despite directly explaining why `audio_glass_break_01` and `audio_alarm_clock_01` can still miss the ±5s tolerance in some runs (see `yamnet_integration_notes.md`, "Remaining limitation"). Narrowing them to fit these two scenarios would silently move every other scenario's timing numbers. Reported as a finding instead.
- **`SURVEILLANCE_CLASSES` confidence thresholds** (0.25-0.3) were not touched. Change #2 (windowing/pooling) fixed the actual signal being fed into these thresholds rather than lowering the thresholds to compensate for a diluted signal.
- **`results/clip_anomaly_calibration_notes.md`'s AUC=0.308 finding** (CLIP prompt/domain mismatch) is untouched — out of scope for this pass, already correctly documented as a real weakness, not something to hand-tune away.
