# CLIP zero-shot anomaly scorer calibration — findings (W2.1/W2.2)

Ran via `python -m aura_mas.scripts.calibrate_clip` on 2026-08-13. Full numbers
in `clip_anomaly_calibration.csv` / `clip_anomaly_threshold_sweep.csv`.

## Result

**Frame-level AUC = 0.308** (n_pos=67 anomaly frames, n_neg=482 normal frames)
— worse than random (0.5). This is a real, verified result (manually spot-checked
individual frame scores below, not a scoring bug), and it's an unflattering one:
as configured, `ClipAnomalyScorer` does not separate "fight" frames from "normal"
frames on this clip set.

| clip | label | mean score | top predicted label |
|---|---|---|---|
| violent_1.mp4 | anomaly | 0.399 | a person falling on the ground |
| violent_10.mp4 | anomaly | 0.601 | a person falling on the ground |
| nonviolent_1.mp4 | normal | 0.644 | a person breaking into a restricted area |
| overview.mp4 | normal | 0.880 | a person breaking into a restricted area |
| street.mp4 | normal | 0.919 | a person falling on the ground |
| people.mp4 | normal | 0.090 | a person falling on the ground |

## Root cause (spot-checked, not just inferred from the table)

`ClipAnomalyScorer.NORMAL_PROMPTS` (`camera_agent.py`) are indoor-scene text
("a normal scene of a warehouse with workers", "an empty corridor under
surveillance", "people walking calmly in a building") — matching the thesis's
stated warehouse/campus deployment context. But `overview.mp4` and `street.mp4`
are **outdoor street CCTV** footage. CLIP correctly finds them visually
dissimilar from every NORMAL_PROMPT, so softmax mass spills onto the anomaly
prompts almost by default — high anomaly score with no anomaly present. This
is a prompt/scene domain mismatch, not a fundamentally broken scorer:
`people.mp4` (an indoor-ish pedestrian clip, closer to the prompt domain)
scores low (0.090) as expected.

Manually re-checked two single frames outside the aggregate script to rule out
a scoring-loop bug: `violent_10.mp4` frame → anomaly_mass 0.335; `street.mp4`
frame → anomaly_mass 0.897, top label "a person falling on the ground" (no one
is falling). Confirms the pattern is a genuine property of these prompts
against this footage, not a script defect.

## What this means for the thesis (per the schedule's own risk table)

The original schedule anticipated exactly this outcome: *"CLIP anomaly AUC
weak → Keep it as a 'semantic tagger', lean thesis contribution on zone rules
+ fusion + coordination."* That's the honest framing to use. Two concrete,
non-cosmetic paths to actually improve the number (neither attempted here —
out of scope for a calibration pass, and tuning prompts against this exact
6-clip set would just be overfitting a tiny sample):

1. Rewrite `NORMAL_PROMPTS` to match the *actual* deployment scene(s) used in
   evaluation (e.g. add an outdoor/street-CCTV normal prompt) rather than
   assuming indoor-only.
2. Evaluate CLIP on a same-domain positive/negative pair (e.g. UCF-Crime clips
   filmed in comparable outdoor CCTV settings) instead of mixing an indoor-
   prompt-tuned scorer with a domain-mismatched normal set — this was the
   original plan's intent with UCF-Crime, which wasn't downloadable here (see
   `data/clips_real/manifest.json`).

Do not hand-tune the threshold or prompts just to make this number look
better without one of the above changes — that would be fitting the metric,
not the model.
