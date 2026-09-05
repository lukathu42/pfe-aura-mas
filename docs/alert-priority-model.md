# Learned Alert Priority Model

This is the recommended ML-engineering addition for AURA-MAS: a small
supervised alert-priority model trained from scenario replay artifacts. It is
not a perception fine-tune and it does not replace deterministic safety rules.
It ranks accepted alerts for operator triage.

## What It Learns

Training examples come from `results/run_*.json`. Each emitted alert is labeled
with the same family/time-window matching rule used by
`aura_mas.eval.metrics.evaluate_run`:

- matched to a ground-truth event: useful alert (`1`)
- unmatched alert: false-positive-risk example (`0`)

Features are intentionally auditable: confidence, severity, number of sensors,
number of evidence items, number of fused events, modality hints, composite
event flag, verification hint, and hashed categorical features for event type,
event family, and zone.

## Train

```bash
python -m aura_mas.scripts.train_alert_priority "results/run_*.json" \
  --out results/alert_priority_model.json
```

The trainer is a compact pure-Python logistic regression implementation with
balanced positive/negative loss. No new ML dependency is required.

## Use In Replay

```bash
python -m aura_mas.scenarios.replay scenarios/intrusion_01.json \
  --mode mas-auction \
  --priority-model results/alert_priority_model.json
```

Alerts produced with a model include:

- `priority_score`: estimated probability that the alert is useful
- `false_positive_risk`: `1 - priority_score`
- `priority_label`: `HIGH`, `MEDIUM`, or `LOW`
- `priority_model_version`: model identifier

The dashboard sorts by `priority_score` when the field is present, then falls
back to timestamp order.

## Thesis Framing

The defensible claim is: AURA-MAS adds a learned operator-triage layer trained
from replay evidence and integrated into the alert workflow. Do not frame this
as a statistically validated generalization result beyond the current scenario
corpus; report the corpus size, matching rule, and train/evaluation limitations.
