# Anomaly types for the multi-zone demo pack — survey, adoption decisions, citation status

**Date:** 2026-08-26
**Branch:** `multi-zone-demo-scenarios`
**Purpose:** record which anomaly-detection types were considered for the new
multi-zone / multi-camera demo scenarios, which were adopted, the exact
operational definition of each adopted rule as implemented in this repo, why
each fits a multi-agent architecture, and — separately and explicitly — the
citation status of each.

Companion documents: `research/reports/synthetic_scene_generation_feasibility.md`
(why the scenes are real footage rather than simulated),
`docs/HANDOFF_multi-zone-demo-scenarios.md` + its `_ADDENDUM`.

---

## 0. Citation status

The sources in §5 were verified against their publisher, official project,
or official software pages on 2026-08-26. The implementation remains careful
not to overclaim what those sources mean:

- Techniques this repo **implements** are described as what they are:
  **geometric decision rules defined from first principles** over the
  track output of an off-the-shelf detector/tracker. They are not
  reproductions of any specific published method, so attaching a paper to
  them would misrepresent them even if the paper were real.
- Papers are cited as context for the adopted anomaly definitions and
  detection/tracking foundation, not as algorithms reproduced by AURA-MAS.
- Dataset URLs, licences, frame counts, normalized-file checksums, and the
  official XML annotations are recorded in `data/clips_real/manifest.json`.

---

## 1. The seven candidate types

The brief named: loitering, unattended object, crowd/queue anomalies,
perimeter intrusion, fall detection, wrong-direction movement, and
zone-occupancy violation. Each is assessed against what
`ZoneRuleEngine` (`aura_mas/agents/camera_agent.py`) can actually decide from
a YOLO11n + ByteTrack track stream.

### 1.1 Perimeter intrusion — **already implemented, adopted for scenario 1**

*Operational definition (existing code):* a `person` track's foot point
`((x1+x2)/2, y2)` falls inside a polygon whose `type` is `restricted`. Fires
**once per `(track_id, zone)` for the lifetime of the run**.

*Why it fits a multi-agent architecture:* a perimeter is a chain of zones
owned by different cameras, so the same physical trespass produces
independent, partial observations at successive agents. That is precisely the
condition under which a coordination protocol has something to add over a
single detector: the `CoordinatorAgent` can ask *another* camera to confirm
what one camera reported, and `FusionAgent`'s noisy-OR can accumulate
confidence across sensors. A single-camera perimeter has no such structure —
which is exactly why every existing scenario fails to exercise C2.

*Citation status:* none needed. The rule is point-in-polygon containment; the
detector and tracker are the citable components, not the rule.

### 1.2 Loitering / abnormal dwell — **implemented but never fired; adopted for scenario 2**

*Operational definition (existing code):* continuous presence of one
`track_id` inside **any** zone (the zone's `type` is ignored by this rule)
for longer than `loiter_seconds`. The dwell timer resets when the track
leaves the zone.

*Why it fits a multi-agent architecture:* dwell is the one rule here whose
evidence is *duration*, not appearance, so it degrades badly under occlusion
and track fragmentation — a track that breaks and re-IDs restarts the timer
and the event is lost. A second camera covering the same named zone gives an
independent dwell measurement over a different occlusion pattern, and
`FusionAgent` treats the two as corroborating rather than duplicate. This is
the clearest case in the pack where multi-camera coverage recovers a
detection a single camera structurally cannot make.

*Repo-specific finding that governs its use:* the longest continuous
single-track presence measured anywhere in this corpus is **5.5 s**
(`people.mp4`, track 3, t=15.3–20.8 s), recorded in
`scenarios/loitering_01.json:12`. The hardcoded `loiter_seconds=8.0` is
therefore unreachable on every clip on disk, which is why
`scenarios/loitering_01.json` ships deliberately empty ground truth as a
true-negative probe and why `research/reports/research-report-v1/01-project-summary.md:343`
reports the rule has never fired. Making the threshold per-sensor
configurable (this pass) turns it from impossible into achievable on the
existing footage — a real capability gain that required no new data.

*Citation status:* the *rule* needs none. The *literature* on what dwell
threshold is defensible is genuinely worth citing → §5.

### 1.3 Unattended / abandoned object — **already implemented; conditional scenario 5 only**

*Operational definition (existing code):* a non-`person` track whose bbox
keeps IoU ≥ 0.6 with its first-seen bbox for longer than
`abandoned_seconds`. Zone-independent — it emits `"zone": None`.

*Why it fits a multi-agent architecture:* weakly. The rule is a
single-view temporal-persistence test and gains little from a second
viewpoint beyond redundancy. Its known failure mode is also not a
coordination problem: `scenarios/abandoned_object_01.json` documents that the
detector's class label flickers between `handbag` and `suitcase` at a fixed
bbox until t≈58 s, and each flip can reset `track_id` and so reset the timer.

*Decision:* **not adopted as one of the four required scenarios.** It is
already covered single-camera by `abandoned_object_01`, and duplicating it
multi-camera would add a scenario without adding a coordination question.
Retained only as the conditional fifth (`data/clips_real/abandoned_object/video3.avi`,
on disk but absent from `manifest.json` and referenced by no scenario) —
because that clip, if usable, is the **only** candidate in this whole pass
that would contribute a genuinely new *recorded* event rather than a re-cut
of the existing 7 assets.

*Citation status:* ABODA is verified (§4). The rule needs none.

### 1.4 Zone-occupancy violation — **new rule, adopted for scenario 3**

*Operational definition (implemented this pass,
`ZoneRuleEngine._occupancy_events`):* in a single inference frame, count
`person` tracks whose foot point lies inside a zone declaring
`max_occupancy`; emit `zone_occupancy` when the count exceeds it. Firing is
keyed on `("occupancy", zone, count)`, so a crowd that keeps *growing* keeps
reporting while a steady one goes quiet after its first report. Confidence is
the mean occupant confidence plus `0.1` per occupant beyond the first
excess one, capped at 1.0.

*Why it fits a multi-agent architecture:* occupancy is the only rule in the
engine that is a property of the **frame**, not of a track — which makes it
the only one whose single-camera answer is *systematically wrong* rather than
merely noisy. One camera sees the occupants its viewpoint doesn't occlude,
so a per-camera headcount is a lower bound on true occupancy. Two cameras
with different sightlines into the same named zone therefore disagree by
construction, and reconciling that disagreement is a genuine coordination
task rather than redundant confirmation. This is the strongest architectural
argument in the pack, and it is the reason occupancy was chosen over the
brief's more generic "crowd/queue anomalies".

*Design note (why `hazard`, not `security`):* `FusionAgent` keys hypotheses
on `f"{family}:{zone or 'site'}"` and `dominant_type()` keeps only the
highest-confidence event in a merged hypothesis. Filing overcrowding under
`security` would merge it with an `intrusion` in the same zone and silently
discard whichever scored lower. It is mapped to `hazard` in
`aura_mas/core/taxonomy.py` to stay separable — and overcrowding is
genuinely a safety hazard, so the family is not a workaround.

*Citation status:* the counting rule is first-principles. The *thresholds*
that make an occupancy limit meaningful are a codes/standards question, not
an ML one → §5.

### 1.5 Wrong-direction / counter-flow movement — **new rule, adopted for scenario 4**

*Operational definition (implemented this pass):* a zone may declare
`flow_direction: [dx, dy]`, an arbitrary vector in image coordinates. For a
`person` track inside that zone, the displacement from its **zone entry
point** to its current foot point is projected onto the normalised flow axis
(`_project`); the track fires `wrong_direction` once per `(track_id, zone)`
when that signed projection reaches `-min_flow_px` or below.

Two non-obvious choices, both deliberate:
- The axis is **normalised**, so `[10, 0]` and `[1, 0]` express the same
  direction instead of scaling the `min_flow_px` threshold by 10×.
- Displacement is measured **from the zone entry point, not the previous
  frame**. At `infer_fps = 5.0` a per-frame delta is dominated by bbox
  jitter, whose sign flips constantly; cumulative displacement from a fixed
  origin is the only form of this test that is stable at this frame rate.

*Why it fits a multi-agent architecture:* direction is viewpoint-relative.
The same physical motion projects onto opposite image axes for two cameras
facing each other, so the *site-level* claim "this person is moving against
the flow" cannot be made by any single agent from its own image coordinates —
it requires per-camera axes declared in a shared site frame and an agent that
reasons over more than one camera's report. Counter-flow is thus the type in
this pack that most directly motivates a coordination layer rather than a
better per-camera detector.

*Citation status:* the projection test is elementary vector geometry. The
*framing* of counter-flow as a surveillance anomaly class is literature → §5.

### 1.6 Crowd / queue anomalies — **considered, not adopted**

Crowd-density and queue-dynamics anomalies (density estimation, flow
turbulence, queue-length or wait-time outliers) all require either a
density-regression model or sustained multi-object trajectory statistics that
this stack does not produce, and the available footage contains no crowd:
`people.mp4` shows at most a small number of people in an indoor room. The
brief's crowd/queue slot is served instead by §1.4's occupancy rule, which is
the tractable, honestly-measurable subset of the same concern on this data.

### 1.7 Fall detection — **considered, rejected**

Falls need either pose estimation (a new model → a **stop-and-ask**
dependency under the brief) or an aspect-ratio/vertical-velocity heuristic
over bboxes, which is notoriously false-positive-prone on people bending,
sitting, or being partially occluded. There is also **no fall in any clip on
disk**, so any ground truth would be unmeasurable and any scenario would be
an empty true-negative probe. Rejected on both counts.

**Also absent and worth recording:** *line crossing* / tripwire. Until this
pass, `camera_agent.py`'s own module docstring claimed the engine implemented
it; it never did. The docstring was corrected this pass rather than the
feature added, and the correction is dated in place so the discrepancy is
auditable rather than silently erased.

---

## 2. Adopted set

| # | Scenario | Anomaly type | Rule status |
|---|---|---|---|
| 1 | `perimeter_chain_01` | perimeter intrusion, zone-to-zone escalation | existing rule, first 3-camera use |
| 2 | `loitering_multizone_01` | loitering / abnormal dwell | existing rule, first time it can fire |
| 3 | `zone_occupancy_01` | zone-occupancy violation | **new rule** |
| 4 | `wrong_direction_01` | wrong-direction / counter-flow | **new rule** |
| 5 | `abandoned_object_multizone_01` | unattended object | conditional on `video3.avi` |

Four distinct types, each spanning multiple zones and ≥2 cameras.

**What is genuinely novel here, stated precisely:** the two new rules produce
event types no code path in this repository has ever produced, and loitering
becomes detectable on real footage for the first time. What is **not** novel:
the underlying footage. Per `docs/ai-enhancement-research.md:190`, re-mixing
the existing 7 recorded assets adds **zero new underlying events** and "must
not be reported as expanding real evaluation diversity." This pack is a
**coordination stress-test pack**, and its metrics are written to a separate
CSV so nothing pools into the cited 373-run campaign.

---

## 3. Why "multi-zone" is the axis that matters

Reading all 9 existing manifests, **no scenario has a ground-truth incident
requiring more than one camera or spanning more than one zone**:
`demo_site_01`'s `cam_02` has zero ground truth in `zone_B`, `intrusion_01`'s
`cam_02` has `"zones": []`, and the other seven are single-sensor. So the
auction protocol — the flagship contribution C2 — has never been measured on
an incident that actually needs it.

An incidental finding while grounding the new polygons, recorded here because
it is the mechanism behind that gap and **not** something to fix silently:
`demo_site_01`'s `zone_B` polygon is `[[0,400],[960,400],[960,540],[0,540]]`,
but `street.mp4` is natively **768×432** (confirmed from the evidence JPEGs,
which `privacy.anonymize_frame` writes at native frame size — it copies the
frame and blurs regions, and its only `resize` is an internal 640-px
downscale for HOG detection that never touches the output). The zone's
effective area is therefore the bottom **32-pixel sliver** y∈[400,432]; the
rest is off-frame. That is consistent with the measured `cam_02` metrics in
`results/run_demo_site_01_mas-auction-r0.json` — **149 detections but exactly
1 zone event**. Existing scenarios are left untouched per the brief; new
scenarios use 768×432 coordinates.

---

## 4. External sources actually asserted in this pack (all verified in-repo)

From `data/clips_real/manifest.json`, which records source URL, license and
citation per asset:

- **AIRTLab violence dataset** — M. Bianculli, N. Falcionelli, P. Sernani,
  S. Tomassini, P. Contardo, M. Lombardi, A. F. Dragoni, "A dataset for
  automatic violence detection in videos," *Data in Brief* 33 (2020),
  doi:10.1016/j.dib.2020.106587. Free for research/educational use.
  (Used by the pre-existing `fight_01`, not by the new scenarios.)
- **ABODA — Abandoned Object Dataset** (Lin et al.),
  https://github.com/kevinlin311tw/ABODA. Public research dataset, no
  explicit per-file license; used for non-commercial academic evaluation.
  (Used by `abandoned_object_01` and the conditional scenario 5.)
- **ESC-50** — K. J. Piczak, "ESC: Dataset for Environmental Sound
  Classification," *Proc. 23rd ACM International Conference on Multimedia*,
  2015. CC BY-NC 3.0. (Audio scenarios; the new scenarios are camera-only.)

**Provenance gap, flagged not papered over:** `data/clips/people.mp4` and
`data/clips/street.mp4` — the footage the new scenarios actually run on —
are **not** in `manifest.json` and their origin is recorded nowhere in this
repository. They predate the 2026-08-13 real-footage pass. Before either
appears in a thesis figure or results table, their provenance and licence
must be established; that is a question for the repo owner, not something
this pass can resolve or should guess at.

The detector and tracker (`YOLO11n` via `ultralytics`, ByteTrack via
`tracker="bytetrack.yaml"`) are pinned in `requirements.txt`; their canonical
software/paper citations are included in §5.

---

## 5. Verified external sources

- G. Jocher and J. Qiu, *Ultralytics YOLO11*, software version 11.0.0
  (2024), official citation and AGPL-3.0 licence:
  https://docs.ultralytics.com/models/yolo11/.
- Y. Zhang et al., *ByteTrack: Multi-Object Tracking by Associating Every
  Detection Box*, ECCV 2022, arXiv:2110.06864.
- J. Núñez, Z. Li, S. Escalera and K. Nasrollahi, *Identifying Loitering
  Behavior With Trajectory Analysis*, WACV Workshops 2024, pp. 251–259.
  This motivates trajectory/dwell analysis; AURA-MAS implements its own
  explicit dwell threshold rather than reproducing that method.
- S. H. Kim, S. C. Lim and D. Y. Kim, *Intelligent intrusion detection system
  featuring a virtual fence, active intruder detection, classification,
  tracking, and action recognition*, Annals of Nuclear Energy 112 (2018),
  845–855, doi:10.1016/j.anucene.2017.11.026.
- *Real-Time Deep Learning Method for Abandoned Luggage Detection in Video*,
  arXiv:1803.01160. AURA-MAS uses a simpler tracked static-object rule and
  does not claim to reproduce its two-stage method.
- CAVIAR Test Case Scenarios, EC-funded project IST 2001 37540, official
  synchronized videos, manual XML annotations, and CC BY-SA terms:
  https://groups.inf.ed.ac.uk/vision/DATASETS/CAVIAR/CAVIARDATA1/.

---

## 6. What a reviewer should take from this document

1. Four distinct anomaly types are covered, two of them by rules that did not
   exist in this repo before this pass.
2. Every rule is stated as an exact operational definition that can be read
   against the code, so nothing here depends on trusting a paraphrase.
3. The multi-agent justification for each type is argued from this system's
   own architecture (hypothesis keying, noisy-OR, the auction gray zone), not
   borrowed from a citation.
4. External citations are verified and separated explicitly from the two
   deterministic rules designed in this repository (`zone_occupancy` and
   `wrong_direction`).
