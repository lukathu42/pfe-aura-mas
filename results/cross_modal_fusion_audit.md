# Cross-modal fusion audit — what the 0.78 alert on `combined_audio_video_01` actually is

**Date:** 2026-08-26 · **Branch:** `thesis-v3-update` · **Scope:** read-only analysis of
existing `results/run_*.json`; no code changed, no run re-executed.

This file exists because writing chapter 6's RQ3 paragraph required checking a
specific claim, and the claim did not survive the check. It corrects
`results/../research/reports/THESIS_REPATCH.md` Priority 1 and the current
`thesis/Chapters/chapter6.tex:96`.

## The claim under test

`THESIS_REPATCH.md` (Priority 1, "Action — resolved, here is what the v2 data
actually shows") instructs the thesis writer to state:

> Directly inspected `results/run_combined_audio_video_01_mas-nocoord-r0.json`
> (pattern confirmed identical across all 5 reps): `mic_01` fires 3 audio
> events, `cam_01` fires 9 video events, `FusionAgent` correctly merges them
> (`events_in: 12 -> hypotheses_out: 5`), and the resulting alert's confidence
> (0.78) does reflect the audio+video corroboration bonus — cross-modal fusion
> **does now work**, for the first time [...]

`thesis/Chapters/chapter6.tex:96` repeats it: "the resulting alert's confidence
(0.78) reflects the audio+video corroboration bonus of
Equation~\ref{eq:noisyor}".

## What the artifact actually contains

`results/run_combined_audio_video_01_mas-nocoord-r0.json`, first alert:

```json
{"alert_id": "alt_8e5fd4dc69", "severity": "CRITICAL", "event_type": "intrusion",
 "confidence": 0.78, "zone": "zone_A",
 "sensors": ["cam_01"], "fused_events": ["ev_880a330f80"]}
```

`sensors` has length 1 and `fused_events` has length 1. A hypothesis built from
a single event contributed by a single sensor cannot receive either bonus term
in Equation 4.1: both are gated on `|M(H)|>1` and `|S(H)|>1` respectively
(`aura_mas/agents/fusion_agent.py`, the `+0.05` guards). The `events_in: 12 ->
hypotheses_out: 5` figure quoted in THESIS_REPATCH is a **run-level** counter
over the whole replay; it does not describe the composition of this alert.

0.78 is exactly what one unaided video event produces:

```
1 - (1 - w_video * c_e) = 1 - (1 - 0.9 * 0.8667) = 0.780
```

## Campaign-wide count

Across all 240 alerts in the v2 audio-visual (`audio_backend=auto`, `rep` set,
non-vision-only) runs:

| Quantity | Count |
|---|---|
| Total alerts | 240 |
| Alerts with more than one contributing **sensor** | **4** |
| Of those, genuinely cross-modal (`cam_*` + `mic_*`) | **4** |
| Alerts at `confidence = 0.78` | 37 — **all** single-sensor, single-event |

The 4 cross-modal alerts all occur in `combined_audio_video_01`, all in
**`centralized`** mode, and all carry `confidence = 1.0` with 3–11 fused events
(`centralized-r1`: 8 events; `-r2`: 11; `-r3`: 3; `-r4`: 8).

## Why the bonus is unobservable even when fusion succeeds

The noisy-OR saturates long before the corroboration bonus is reached, because
repeated detections from the *same* camera enter the product as if they were
independent evidence:

| Evidence set | noisy-OR | + bonuses | reported |
|---|---|---|---|
| 5 video events at c≈0.87 | 0.9995 | n/a (single modality/sensor) | 0.999 |
| 5 video (0.87) + 3 audio (0.6) | 0.9999 | +0.05 +0.05 → 1.0999 | **clamped to 1.0** |

Video-only already reaches 0.9995. Adding a second modality moves the product
by 4e-4 and the bonus is then absorbed entirely by the clamp to `[0,1]`. So on
this scenario the cross-modal contribution is **arithmetically present but
numerically invisible** in the emitted confidence.

## The defensible RQ3 statement

1. Cross-modal fusion is **wired correctly** and demonstrably fires: 4 alerts
   carry both a camera and a microphone in `sensors`. The zone-tagging and
   taxonomy-unification fixes (`results/methodology_changes.md` #4, #5) were
   necessary and sufficient for that.
2. It is **rare** — 4 of 240 alerts — because audio and video events must land
   in the same `(family, zone)` key inside the same 6 s window.
3. Its effect on the reported confidence is **not measurable at these event
   confidences**, because the noisy-OR saturates and the clamp absorbs the
   bonus. This is a consequence of treating repeated same-camera detections as
   conditionally independent, which they are not.
4. `Hypothesis.dominant_type()` labels every one of the 4 cross-modal alerts
   `intrusion`, never `audio_glass_break`, so the audio contribution is also
   invisible in the alert's headline type. (This part of THESIS_REPATCH's
   analysis is correct and is retained.)

Points 2 and 3 are limitations of contribution C3 as implemented. Neither is
fixed by this pass; both are stated in the thesis rather than worked around.

## Reproduction

```bash
python3 - <<'EOF'
import json, glob
rows = []
for f in sorted(glob.glob('results/run_*.json')):
    if 'visiononly' in f: continue
    d = json.load(open(f))
    if d.get('audio_backend') != 'auto' or d.get('rep') is None: continue
    for a in d.get('alerts', []):
        rows.append((tuple(a.get('sensors', [])), len(a.get('fused_events', [])),
                     a['confidence']))
multi = [r for r in rows if len(r[0]) > 1]
print(len(rows), 'alerts;', len(multi), 'multi-sensor')
print('conf=0.78 all single-sensor:',
      all(len(r[0]) == 1 for r in rows if abs(r[2]-0.78) < 1e-9))
EOF
```
