# Synthetic scene generation / digital twin — feasibility investigation

**Date:** 2026-08-26
**Branch:** `multi-zone-demo-scenarios`
**Question asked:** can the multi-zone / multi-camera demo scenarios be built
from synthetic or simulated scene generation (a "digital twin" of the site),
avoiding new real-world capture?

**Verdict: NOT FEASIBLE** for *genuinely new scenes* within this project's
stack, dependency budget, and remaining timeline. The next-best alternative
was adopted instead: **real footage already on disk, with ground truth
measured from what the detector actually produces** (via the new
`aura_mas/scripts/probe_tracks.py`), plus two new deterministic zone rules
that make cross-zone coordination observable without any new data.

---

## 1. Why not feasible — the decisive evidence is already in this repo

This is not a speculative judgement. The project has already tried synthetic
pixels, and the attempt is recorded as a failure in three independent places.

**1.1 The existing synthetic generator says so in its own docstring.**
`aura_mas/scripts/make_synthetic_clips.py:4-7`:

> `intrusion.mp4` : a synthetic 'person-like' figure walks into restricted
> zone_A (YOLO detects a rendered pedestrian sprite is unreliable, so this
> clip is mainly for pipeline plumbing; for the thesis use real UCF-Crime /
> Avenue clips or phone-recorded scripted scenes).

Its `draw_person()` renders `cv2` rectangles plus a circle. That is the whole
"person" model.

**1.2 The resulting clip produces zero usable detections.**
`scenarios/intrusion_01.json`'s own notes record the direct verification:

> YOLO11n never detects a 'person' in them at any confidence down to 0.05
> (verified directly; the only class ever detected in `intrusion.mp4` across
> the whole clip is a stray 'sports ball'), so this scenario could never have
> produced a real intrusion detection.

This was a **silent** failure: `intrusion_01` ran to completion, wrote run
JSONs, and was scored — with zero intrusion alerts — for an entire evaluation
campaign before anyone checked whether the pixels contained a detectable
person. A synthetic pipeline that fails this way is worse than no pipeline,
because it produces publishable-looking numbers.

**1.3 The risk is already named as the project's central one.**
`research/reports/research-report-v1/03-concepts-explained.md:895`:

> **Trade-offs and failure modes.** The synthetic-to-real gap is the central
> risk, and this project has already been bitten by its most extreme form.

---

## 2. Options considered

### A. Game-engine / simulator digital twin — rejected
Isaac Sim + Omniverse Replicator, CARLA, or UE5-based capture would give
photorealistic frames with free pixel-perfect ground truth, multi-camera rigs
with exact extrinsics, and controllable scripted behaviour. It is the
technically correct answer to the question as posed.

It is rejected on four grounds, in order of decisiveness:

1. **It is a new external dependency and service.** The brief's own stop
   conditions require pausing for approval before adding one. Nothing else in
   this task does.
2. **Cost against remaining timeline.** Install, asset acquisition, character
   animation, camera calibration, and — critically — *validating that YOLO11n
   actually detects the rendered humans* is multi-day work. The project's own
   governing rule, quoted in `data/clips_real/manifest.json:57`, is "never
   spend more than one day blocked on a single component."
3. **It does not remove the domain-gap validation burden, it relocates it.**
   A rendered human that YOLO11n detects at conf 0.9 is not evidence about
   real footage; a rendered human it misses is not evidence about the
   detector. Either way the thesis would then owe a real-vs-synthetic
   agreement study, which is a larger piece of work than the scenarios it was
   meant to enable.
4. **The plan's own documented data fallback was never synthetic generation.**
   `research/planning/One-Month Execution Schedule — AURA-MAS PFE.md:71` lists
   the mitigation for unavailable data as "Avenue dataset (2 GB) +
   self-recorded phone clips of scripted scenarios" — real capture, not
   simulation.

### B. Generative video models (text-to-video) — rejected
Rejected more firmly than A. No frame-accurate ground truth is recoverable
from a generated clip, so every GT timestamp would be a human guess about
synthetic content — reproducing exactly the unverified-GT problem that
landscape finding F6 already flags in this project's results. Provenance and
licensing of generated surveillance-like footage are also unresolved for an
academic submission, and the domain gap is *worse* than A's because there is
no camera model at all.

### C. 2D procedural compositing of real person crops onto real backgrounds
— rejected as a scene generator
Pasting real, YOLO-detectable person crops onto a real background frame
avoids the sprite problem of §1. It was rejected because the compositing
artifacts (no shadow, no perspective consistency, no motion blur, hard alpha
edges) interact unpredictably with ByteTrack's association step, and this
project's rules are *tracking*-dependent: `loitering`, `wrong_direction`, and
`abandoned_object` all key off `track_id` continuity, and
`scenarios/abandoned_object_01.json` already documents track IDs breaking on
nothing more than a class-label flicker. A synthetic track that fragments
differently from a real one invalidates the rule being demonstrated.

### D. Adopted — real footage, measured ground truth, new zone geometry
Multi-zone and multi-camera structure is expressed in **zone geometry and
scenario topology**, not in pixels. The existing real clips can therefore be
carved into several zones per camera, given shared zone names across cameras
so the FusionAgent merges their events, and assigned per-sensor rule
thresholds — producing genuinely new *coordination* behaviour from unchanged
footage.

The enabling piece is `aura_mas/scripts/probe_tracks.py`, which mirrors
`CameraAgent._process_frame` exactly (same `model.track(persist=True,
tracker="bytetrack.yaml", conf=0.35)` call, same `infer_fps` stride, same
blank-frame warmup, same `(cx, y2)` foot-point convention) and reports
per-track in-zone dwell runs, per-frame in-zone person counts, and per-run net
displacement vectors. Every polygon and every ground-truth window in the new
scenarios is **derived from that output**, not asserted.

That is a methodological improvement independent of the scenario count: it
directly addresses landscape finding **F6** (ground truth defined by the same
session that ran the experiment) by making GT a measurement with a
reproducible command behind it.

---

## 3. What this does *not* fix — stated plainly

The newest in-repo audit already judged exactly this move.
`docs/ai-enhancement-research.md:190`:

> Procedural re-mixing of existing AIRTLab/ABODA/ESC-50 clips … **Does not
> close the real gap — the underlying event count stays at 7 unique recorded
> events regardless of re-cutting/re-timing** … Legitimate for
> ablation/stress-testing the fusion logic; **must not be reported as
> expanding real evaluation diversity** … Synthetic audio-video pairings that
> never co-occurred in reality could be mistaken for additional real evidence
> if not clearly labeled as synthetic in any results table.

`data/clips_real/manifest.json` catalogues exactly 7 assets, which is where
that count comes from. Accordingly:

1. The new scenarios are a **coordination stress-test pack**. They add zero
   new *recorded* events.
2. Their metrics are written to `results/summary_multizone.csv` /
   `results/summary_multizone_agg.csv`, **not** pooled into the cited
   `results/summary.csv` / `results/summary_agg.csv`.
3. Effective independent sample size for any new intervention stays
   scenario-cluster-sized (`docs/ai-enhancement-research.md:210`), and does not
   grow because the run count grew.
4. Each new manifest's `notes` field carries this caveat inline, so it travels
   with the artifact rather than living only in this report.

Two prior audits look like they disagree here. They do not:
`research/reports/research-report-v1/02-gaps-and-recommendations.md:323-326`
recommends scenario generation as "a defensible methodological contribution"
and means generating *genuinely new scenes*; `ai-enhancement-research.md:190`
judges *re-cutting the existing 7 recordings*. This work does the latter and
labels it as such.

What *is* new and defensible independently of footage novelty: the two new
zone rules (`zone_occupancy`, `wrong_direction`) produce detections no code
path in this repository has ever produced, and `loitering` becomes capable of
firing on real footage for the first time in the project's history — the
open item recorded at
`research/reports/research-report-v1/01-project-summary.md:343`.

---

## 4. Recommendation if real evaluation diversity is wanted later

Not simulation. **Self-recorded phone clips**, which is the execution plan's
own documented fallback (`One-Month Execution Schedule — AURA-MAS PFE.md:71`).
Three short scripted takes would close the specific gaps this investigation
surfaced, at roughly an hour of capture:

| Take | Content | Gap it closes |
|---|---|---|
| 1 | One person stands still in view for ≥ 20 s | The corpus's longest single-track dwell is 5.5 s (`scenarios/loitering_01.json`), so no clip on disk can fire `loitering` at the default 8.0 s threshold |
| 2 | Four people converge into one marked area | No real clip has a verified simultaneous 3+ person count inside a single polygon |
| 3 | One person walks against a marked flow while two walk with it | No real clip has a labelled counter-flow event |

Recording them with two phones side by side, unsynchronised but with a shared
clap for alignment, would additionally give the first genuinely multi-camera
recorded incident in the corpus — the gap this whole task set out to address
at the data level rather than the topology level.

---

## 5. Citations

Only sources verified in this repository are listed. External literature for
the two new zone rules is deliberately **not** cited: they are geometric
definitions implemented from first principles (a per-frame point-in-polygon
count against a declared limit; a sign test of net in-zone displacement
against a declared flow axis), not reproductions of a specific published
method. Attaching a paper to them would be decoration, and
`research/aura-mas-landscape-positioning/findings/F5_prior_bibliography_needs_verification.md`
records that this project already carries 94 bibliography entries of which a
6-entry spot check found corrupted author fields, a paraphrased title, and a
wrong year — so an unverified citation here would compound a known problem.

Datasets used by the new scenarios, as catalogued in
`data/clips_real/manifest.json`:

- M. Bianculli, N. Falcionelli, P. Sernani, S. Tomassini, P. Contardo,
  M. Lombardi, A.F. Dragoni, *A dataset for automatic violence detection in
  videos*, Data in Brief 33 (2020). doi:10.1016/j.dib.2020.106587.
  (AIRTLab; free for research and educational purposes.)
- ABODA — Abandoned Object Dataset (Lin et al.),
  https://github.com/kevinlin311tw/ABODA (public research dataset, used for
  non-commercial academic evaluation).
- K. J. Piczak, *ESC: Dataset for Environmental Sound Classification*,
  Proceedings of the 23rd ACM International Conference on Multimedia, 2015
  (CC BY-NC 3.0).

`data/clips/people.mp4` and `data/clips/street.mp4` predate
`data/clips_real/manifest.json` and are **not** catalogued there; their
provenance is unrecorded in this repository. They are used here because the
existing scenarios already use them and this pack deliberately introduces no
new footage, but their provenance should be established before any figure
derived from them appears in the thesis.
