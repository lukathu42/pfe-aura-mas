# Toy `auction-bandit` mode — notes and explicit limitations

**Read this before citing anything from `mas-auction-bandit` runs or
`results/auction_bandit_train_history.json` in the thesis.** This mode is
Pursue-Now item #2 from `docs/ai-enhancement-research.md` (Section 4.2),
implemented as an illustrative research-pass artifact, not a fifth thesis
ablation baseline.

## What this is

`aura_mas/core/bandit.py` implements a disjoint LinUCB contextual bandit
(Li, Chu, Langford, Wang, WSDM 2011). `CoordinatorAgent(mode="auction-bandit")`
uses it to pick which camera verifies a gray-zone hypothesis, in place of the
`_view_score` hand-coded heuristic (`base × capacity × overlap`,
`camera_agent.py:314`) that `mode="auction"` uses. Selection happens
centrally in the coordinator (no bid messages exchanged over the bus,
mirroring the existing `roundrobin` mode's no-broadcast pattern) using
context features the coordinator already has: whether the candidate camera
is the event's origin sensor, the zone, and the event type (hashed into a
small fixed-size feature vector — see `aura_mas/core/bandit.py:build_context`).

The reward signal is the in-process verification outcome
(`result["verified"]`) already computed by `CoordinatorAgent.request_verification`
— no external ground truth is needed, so this trains purely against the
existing CPU replay harness.

`aura_mas/scripts/train_auction_bandit.py` runs self-play episodes (repeated
scenario replays in `mas-auction-bandit` mode) and persists learned weights
to `results/auction_bandit_weights.json`.

## Why this must not be read as a performance claim

- **Only 6-9 fixed scenario clips exist project-wide** (`scenarios/*.json`,
  backed by the small real-clip set documented in
  `data/clips_real/manifest.json`). Self-play episodes replay these same
  clips repeatedly; there is no held-out scenario to validate
  generalization against. Any convergence the bandit shows can only be
  "the learned weights come to resemble something like the existing
  heuristic on these exact clips" — not "the bandit generalizes to new
  situations" or "the bandit outperforms `mas-auction`."
- **No statistically meaningful before/after comparison is possible at this
  scale.** `docs/ai-enhancement-research.md` Section 7 explains why: the
  effective independent sample size for evaluating a new intervention is
  scenario-cluster-sized (single digits), not run-count-sized. Do not report
  an F1/precision/recall delta between `mas-auction` and `mas-auction-bandit`
  as if it were a validated result — see Card et al. (2020), cited in the
  report, on underpowered small-N comparisons.
- **`fov_overlap` and camera `busy` state are not available to the
  coordinator** (they live only inside each `CameraAgent`'s own process and
  are never published back), so the bandit's context is a strict subset of
  what `_view_score` itself uses. This is a known, deliberate simplification
  of a toy PoC, not a bug — extending the bandit to use those signals would
  require a new bus topic for camera state, out of scope for a
  days-not-weeks research pass.
- In practice, `_view_score`'s own `overlap` term is always `0.5` today
  regardless of camera (nothing in the codebase ever populates
  `task["fov_overlap"]`), so the *existing* hand-coded heuristic is itself
  effectively `base × capacity` with a constant overlap factor — worth
  knowing when comparing the bandit's learned behavior against it, since
  the "heuristic" it's being compared to is simpler in practice than its
  docstring suggests.

## Honest framing for the thesis

The correct claim, if this is included: **"AURA-MAS's coordination layer can
architecturally accommodate a learned, adaptive component in place of a
hand-coded rule, demonstrated as a toy proof-of-concept."** This is a real,
citable point against the novelty framing in
`research/aura-mas-landscape-positioning/findings/F2` (prior local-thesis
precedent had zero learned/adaptive components). It is not evidence the
learned component is *better* — that claim is not supportable with the data
this project has, and should not be made.

## Reproducing

```bash
source .venv/bin/activate
python -m aura_mas.scripts.train_auction_bandit --episodes 40
python -m aura_mas.scenarios.replay scenarios/intrusion_01.json \
    --mode mas-auction-bandit --bus local
```

Offline unit tests (no models, no video): `aura_mas/tests/test_bandit.py`.
