# HANDOFF — multi-zone / multi-camera demo scenarios

**Working doc, not thesis material.** Delete or move it before any merge.
Written 2026-08-26 by the session that planned this work and got blocked
partway through implementation.

---

## 0. TL;DR for the next agent

The plan is **approved and complete**. Nothing has been written into the
repository yet. The blocker is environmental, not analytical: `git` and
`python` invocations through the Bash tool return

> `claude-opus-5 is temporarily unavailable, so auto mode cannot determine the
> safety of Bash right now.`

Read-only Bash (`cat`, `sed -n`, `grep`, `find`, `ls`) works. The `Write` and
`Edit` tools work. So **file authoring is unblocked; git and python execution
are not.**

Workaround that the user agreed to: hand them the exact shell command and they
run it themselves by prefixing `!` in the prompt. Retry the Bash tool yourself
periodically too — the outage may lift.

Order of work: §3 (branch) → §4 (probe, needs the user) → §5 (code) → §6
(scenarios, needs probe output) → §7 (verify) → §8 (report).

---

## 1. Governing constraints — do not relax these

From the user's brief, verbatim:

- "Work only on the new branch. Never commit to or modify the current
  default/working branch."
- "Reuse existing project conventions (config format, ground-truth schema,
  agent interfaces) — do not introduce a parallel or incompatible structure."
- "Cite the source (paper, dataset, or documentation) for every anomaly type or
  technique you adopt from external research. Do not fabricate citations."
- "If digital-twin/synthetic-scene generation is not practically feasible with
  the current stack and timeline, say so explicitly and propose the next-best
  alternative instead of forcing it in."
- "Only make changes directly required for the new scenarios. Do not refactor
  unrelated code or restructure the existing architecture."

**Stop and ask before:** merging into `main`/`master`; adding any new external
dependency or service; deleting or overwriting any existing scenario or
ground-truth file. None of the work below requires any of the three.

From `CLAUDE.md`: "This is thesis material: don't silently rewrite evaluation
numbers, chapter text, or research findings. Surface discrepancies to the user
instead of 'fixing' them unilaterally." Also: rerun N≥3 before citing a number;
keep the `roundrobin`/`off`/`centralized`/`mas-nocoord` ablation paths alive; no
comments explaining *what* code does (docstrings for *why*); don't make heavy
optional deps hard requirements.

**Required progress format:** after each completed step output
`✅ [what was done] — [file(s)/branch affected]`. The final reply must state the
branch name, scenarios added, techniques researched and adopted with sources,
and the digital-twin feasibility verdict.

The full approved plan is at
`/home/lokmane-zed/.claude/plans/fluffy-imagining-plum.md`. Read it — this
handoff is the delta and the operational detail, not a replacement.

---

## 2. Files already drafted (outside the repo, ready to place)

All three are finished. Copy their content to the repo paths below using the
`Write` tool once the branch exists — no `cp` needed, which avoids Bash.

| Draft (in `/home/lokmane-zed/.claude/jobs/502b5aa5/tmp/`) | Repo destination |
|---|---|
| `probe_tracks.py` (~287 lines) | `aura_mas/scripts/probe_tracks.py` |
| `test_zone_rules.py` (17 tests) | `aura_mas/tests/test_zone_rules.py` |
| `synthetic_scene_generation_feasibility.md` | `research/reports/synthetic_scene_generation_feasibility.md` |

That job tmp directory is deleted when the job is deleted — move them early.

`test_zone_rules.py` was hand-checked against the §5 implementation below and
all 17 assertions pass by construction. If you change the confidence formulas,
the tests are what breaks first; treat them as the spec.

---

## 3. Step 1 — create the branch

Branch name: **`multi-zone-demo-scenarios`**, off `main`.

The brief proposed `feature/multi-zone-demo-scenarios` and invited a rename to
match repo convention. No `feature/` prefix exists anywhere here: human-authored
branches are bare kebab-case (`code-hardening`, `harden-for-submission`), and
`devin/*` prefixed remotes are bot-generated. Hence the bare name. **State this
choice in the final report** — the brief asked which convention was used.

```
cd "/home/lokmane-zed/Workspace/PFE(Memoire)/Intelligent Surveillance System for Master's Thesis" && git checkout -b multi-zone-demo-scenarios && git branch --show-current
```

**The user has ~20 uncommitted files in the working tree** (see `git status`:
modified agents, plus untracked `aura_mas/copilot/`, `aura_mas/streaming/`,
`aura_mas/core/db.py`, frontend components, and a `data/aura_surveillance.db`).
`git checkout -b` carries all of it across untouched — that is the agreed
behaviour. **Stage only files you create or modify. Never `git add -A`.**

Two of their uncommitted changes matter downstream:

- `replay.py:186` is now `agent_metrics = {a.agent_id: a.metrics for a in agents}`
  (raw `infer_ms` lists) where committed code reduced it to a rounded scalar
  mean, and line 213 lost `default=str`. **New run JSONs will therefore not be
  structurally identical to the 373 cited campaign artifacts.** Note it in the
  report; do not "fix" it — it is their work in progress.
- `results/auction_bandit_weights.json` is modified. See §6 note on
  `perimeter_chain_01` adding a third camera.

---

## 4. Step 2 — measure the footage (blocked on the user)

**Do not guess polygons or ground-truth windows.** The plan is explicit: every
polygon and GT window is derived from probe output. This is what makes the GT a
measurement rather than an assertion, which is the pack's one genuine
methodological improvement (it addresses landscape finding F6).

`aura_mas/scripts/probe_zones.py` cannot do this — line 22 calls
`m.predict(frame, conf=0.4)`, **not** `model.track`, so it yields no `track_id`
and therefore no dwell times, no per-zone occupancy counts, and no per-track
direction. `probe_tracks.py` mirrors `CameraAgent._process_frame` exactly:
same `model.track(persist=True, tracker="bytetrack.yaml", conf=0.35)` call, same
`infer_fps` stride, same blank-frame `predict` warmup (so ByteTrack state is not
seeded and track IDs are not shifted), same `video_ts = frame_id / src_fps`
clock, same foot point `(cx, y2)`. Dwell runs break on zone exit exactly as
`ZoneRuleEngine` pops `_dwell`.

These three commands were already handed to the user. They run the script from
tmp with `PYTHONPATH=.`, so **nothing is written into the working tree** and they
are safe to run before the branch exists. Each takes roughly a minute
(~200 ms/frame × ~300 frames).

```
cd "/home/lokmane-zed/Workspace/PFE(Memoire)/Intelligent Surveillance System for Master's Thesis" && PYTHONPATH=. .venv/bin/python /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/probe_tracks.py data/clips/people.mp4 --out /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/probe_people.json
```
```
cd "/home/lokmane-zed/Workspace/PFE(Memoire)/Intelligent Surveillance System for Master's Thesis" && PYTHONPATH=. .venv/bin/python /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/probe_tracks.py data/clips/street.mp4 --out /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/probe_street.json
```
```
cd "/home/lokmane-zed/Workspace/PFE(Memoire)/Intelligent Surveillance System for Master's Thesis" && PYTHONPATH=. .venv/bin/python /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/probe_tracks.py data/clips_real/abandoned_object/video3.avi --out /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/probe_video3.json
```

Once the script is in the repo, the normal form is
`python -m aura_mas.scripts.probe_tracks data/clips/people.mp4`.

**What to read out of each probe JSON:**

- `dwell_runs[].dwell_s` — directly comparable to `loiter_seconds`. Pick
  `loiter_seconds` *below* the measured max for the zone you draw.
- `occupancy[zone][].count` and the printed `count>=k` windows — these give the
  `max_occupancy` limit and the GT window for `zone_occupancy`.
- `dwell_runs[].net_dx` / `net_dy` — these give the `flow_direction` axis and the
  GT window for `wrong_direction`. Set `flow_direction` *opposite* to the track
  you want to flag, and check `path_len` is comfortably over `min_flow_px`.
- `foot_points` — the raw `(t, cx, cy, track)` trace. Draw polygons from this.
- `static_object_runs` — longest static non-person hold, for `abandoned_seconds`.

**Already-known measurements** (from existing artifacts, no probe needed):

| Clip | Sampled frames @ infer_fps 5 | Total detections | Source |
|---|---|---|---|
| `people.mp4` | 298 (≈ 59.6 s) | 198 | `results/run_loitering_01_mas-auction-r0.json` |
| `street.mp4` | 323 (≈ 64.6 s) | 149 | `results/run_intrusion_01_mas-auction-r0.json` |

Both average well under one detection per frame, so **occupancy limits must be
low** (`max_occupancy: 1` is likely the only value that ever fires on these two
clips). Confirm against the probe's actual peak count before committing to a
limit — if peak is 1, `zone_occupancy_01` needs a different clip (the AIRTLab
violence clips have two or more people in frame by construction).

`scenarios/loitering_01.json`'s notes already record the longest continuous
single-track presence anywhere as **5.5 s** (`people.mp4`, track 3,
t=15.3–20.8 s), which is why `loiter_seconds: 4.0` is the plan's value.

`data/clips_real/abandoned_object/video3.avi` exists on disk (4,407,330 bytes)
but is **absent from `data/clips_real/manifest.json`** and referenced by no
scenario. It gates the optional 5th scenario — see §6.

---

## 5. Step 3 — code changes

All additive and backward-compatible. Both new rules are gated behind new
**optional** zone keys, so the nine existing scenarios are bit-for-bit
unaffected when the key is absent. Only `numpy`/`cv2` are used, both already
imported — **no new dependency, so no stop-and-ask.**

### 5.1 Why each new event type must be registered in four places

`FusionAgent` keys hypotheses `f"{family}:{ev.zone or 'site'}"`. An event type
missing from `EVENT_FAMILIES` falls through to family `"other"`, and
`eval/metrics.py` can then only ever score it a **false positive** — this exact
class of bug is documented in `aura_mas/core/taxonomy.py`'s own docstring.
Missing from `SEVERITY_MAP` defaults it to `INFO`, i.e. the *strictest* 0.70
alert threshold.

### 5.2 `aura_mas/core/taxonomy.py` — add 2 entries

Replace the closing lines of `EVENT_FAMILIES` (currently ending
`"audio_anomaly": "violence_or_hazard",`) so the dict gains:

```python
    "audio_anomaly": "violence_or_hazard",
    "zone_occupancy": "hazard", "wrong_direction": "security",
```

`zone_occupancy` → **`hazard`** deliberately, not `security`: it keeps
overcrowding separable from `intrusion` in the *same zone* (same family + same
zone merge into one hypothesis and `dominant_type()` picks a single winner), and
overcrowding genuinely is a safety hazard. `wrong_direction` → **`security`**.

### 5.3 `aura_mas/agents/policy_agent.py` — add 2 entries

In `SEVERITY_MAP`, after `"audio_anomaly": "INFO",`:

```python
    "zone_occupancy": "WARNING", "wrong_direction": "WARNING",
```

Both `WARNING` → threshold 0.55. See §5.7 for why that matters.

### 5.4 `aura_mas/copilot/copilot_agent.py:27` — add 2 entries

This line is a hardcoded duplicate of the taxonomy inside an LLM prompt, and it
has **already drifted** (it is missing `audio_glass_break`, `audio_breaking`,
`audio_anomaly`). Add only the two new types. **Do not reconcile the
pre-existing drift** — out of scope, and it is the user's uncommitted file.

Change `hazard (audio_alarm, audio_explosion)` to
`hazard (audio_alarm, audio_explosion, zone_occupancy)` and
`security (intrusion, loitering, abandoned_object)` to
`security (intrusion, loitering, abandoned_object, wrong_direction)`.

### 5.5 `aura_mas/agents/camera_agent.py`

**(a) Docstring lines 6-7** currently claim a rule that exists nowhere in the
repo:

```
  2. Zone rules: intrusion (restricted polygon), loitering (dwell time),
     line crossing, abandoned object (static non-person object).
```

`line crossing` is false. Replace with:

```
  2. Zone rules: intrusion (restricted polygon), loitering (dwell time),
     zone occupancy (person count over a declared limit), wrong direction
     (net in-zone displacement against a declared flow axis), abandoned
     object (static non-person object).
```

**(b) `_project` helper** — add next to `_iou` (after it, around line 116):

```python
def _project(vec, axis) -> float:
    """Signed length of `vec` along `axis`. Projection rather than dot-product
    sign, so motion merely lateral to the declared flow never counts as
    counter-flow."""
    ax, ay = float(axis[0]), float(axis[1])
    norm = (ax * ax + ay * ay) ** 0.5
    if norm < 1e-9:
        return 0.0
    return (vec[0] * ax + vec[1] * ay) / norm
```

**(c) `ZoneRuleEngine.__init__`** (lines 52-59) gains `min_flow_px` and the
`_entry_point` store:

```python
    def __init__(self, zones: List[Dict[str, Any]], loiter_seconds: float = 8.0,
                 abandoned_seconds: float = 10.0,
                 min_flow_px: float = 40.0) -> None:
        self.zones = zones                      # {name, type: restricted|entry, polygon}
        self.loiter_seconds = loiter_seconds
        self.abandoned_seconds = abandoned_seconds
        self.min_flow_px = min_flow_px
        self._dwell: Dict[Tuple[int, str], float] = {}      # (track_id, zone) -> first_seen
        self._entry_point: Dict[Tuple[int, str], Tuple[float, float]] = {}
        self._static_objects: Dict[int, Tuple[float, Tuple]] = {}  # track -> (t0, bbox)
        self._fired: set = set()
```

Also extend the class docstring (line 50) with the *why*:

```python
    """Stateful zone rules evaluated on tracked objects.

    `zone_occupancy` and `wrong_direction` are opt-in per zone: they stay inert
    unless the zone declares `max_occupancy` / `flow_direction`, so scenarios
    authored before those keys existed score identically.
    """
```

**(d) occupancy pre-pass** — a frame-level rule, not a per-track one, so it is
a separate method. The `if limit is None: continue` guard means existing
scenarios do **zero** extra polygon tests.

```python
    def _occupancy_events(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for zone in self.zones:
            limit = zone.get("max_occupancy")
            if limit is None:
                continue
            inside = [o for o in tracks
                      if o.get("track_id") is not None and o["class"] == "person"
                      and point_in_polygon(((o["bbox"][0] + o["bbox"][2]) / 2,
                                            o["bbox"][3]), zone["polygon"])]
            n = len(inside)
            key = ("zone_occupancy", zone["name"], n)
            if n <= limit or key in self._fired:
                continue
            self._fired.add(key)
            lead = max(inside, key=lambda o: o["confidence"])
            mean_conf = sum(o["confidence"] for o in inside) / n
            events.append({"event_type": "zone_occupancy", "zone": zone["name"],
                           "track_id": lead["track_id"],
                           "confidence": min(1.0, mean_conf + 0.1 * (n - limit - 1))})
        return events
```

Keyed on the *count* `n`, so 3→4 people re-fires (an escalation) but the total
event count stays bounded by peak occupancy.

⚠️ **`track_id` must be a real occupant, never `None`.** `camera_agent.py:340`
does `next((o for o in objects if o.get("track_id") == tid and "reid_feat" in o), None)`
— with `tid=None` that matches a stray untracked person object and pollutes the
cross-camera re-ID gallery with the wrong appearance vector.

**(e) `evaluate`** — call the pre-pass first, pop `_entry_point` alongside
`_dwell` on zone exit, and add the `wrong_direction` block. The changed and new
lines only:

```python
    def evaluate(self, tracks: List[Dict[str, Any]], ts: float) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = self._occupancy_events(tracks)
        for obj in tracks:
            ...
                if not inside:
                    self._dwell.pop(key, None)
                    self._entry_point.pop(key, None)
                    continue
```

and, inside the `for zone in self.zones:` body after the existing `loitering`
block:

```python
                # --- wrong direction: net in-zone displacement opposes flow ---
                entry = self._entry_point.setdefault(key, (cx, cy))
                flow = zone.get("flow_direction")
                if (flow is not None and obj["class"] == "person"
                        and ("wrong_direction", key) not in self._fired):
                    proj = _project((cx - entry[0], cy - entry[1]), flow)
                    if proj <= -self.min_flow_px:
                        self._fired.add(("wrong_direction", key))
                        events.append({"event_type": "wrong_direction",
                                       "zone": zone["name"], "track_id": tid,
                                       "confidence": obj["confidence"]})
```

**(f) `CameraAgent.__init__`** — append the three kwargs **at the end** of the
signature, after `realtime: bool = True`. Appending (not inserting) keeps every
positional caller valid; `replay.py:135` is the only construction site in the
repo and it already passes everything by keyword.

```python
                 realtime: bool = True,
                 loiter_seconds: float = 8.0,
                 abandoned_seconds: float = 10.0,
                 min_flow_px: float = 40.0) -> None:
```

**(g) line 212** is the actual blocker that made loitering unreachable from
scenario JSON — `ZoneRuleEngine(self.zones)` passes no thresholds at all:

```python
        self.rule_engine = ZoneRuleEngine(self.zones,
                                          loiter_seconds=loiter_seconds,
                                          abandoned_seconds=abandoned_seconds,
                                          min_flow_px=min_flow_px)
```

### 5.6 `fov_overlap` — a dead parameter the thesis already claims works

`camera_agent.py:369-374`:

```python
    def _view_score(self, task: Dict) -> float:
        """Bid utility: can this camera verify the event? Higher = better."""
        base = 1.0 if task.get("origin_sensor") != self.agent_id else 0.3
        capacity = 0.2 if self._busy else 1.0
        overlap = task.get("fov_overlap", {}).get(self.agent_id, 0.5)
        return round(base * capacity * overlap, 3)
```

`fov_overlap` is **never written anywhere in the repo**. The task dict is built
at `coordinator_agent.py:76-82` with only `task_id, type, hypothesis_id,
event_type, zone, origin_sensor, timestamp`. So `overlap` is permanently `0.5`
and the bid collapses to a 3-valued function of origin-ness and busy-ness.

Meanwhile `thesis/Chapters/chapter6.tex:120` claims "field-of-view overlap and
origin-independence … dominate the bid" and `chapter4.tex:104` describes
`o ∈ [0,1]` as "its field-of-view overlap with the event zone."

**Per `CLAUDE.md` this gets surfaced, not silently patched.** The fix makes the
existing formula *reachable*; it does not retroactively validate the thesis
sentence. **The final report must state that all prior campaign results ran with
`overlap` pinned at 0.5.** Do not edit the thesis chapters.

`coordinator_agent.py` — add the parameter (append to the signature, after
`bandit_alpha`):

```python
                 bandit_alpha: float = 1.0,
                 fov_overlap: Optional[Dict[str, Dict[str, float]]] = None) -> None:
```

and in the body, near `self.camera_ids = camera_ids or []`:

```python
        self.fov_overlap = fov_overlap or {}
```

then in `request_verification`, extend the task dict at lines 77-82:

```python
        task = {"task_id": task_id, "type": "verify",
                "hypothesis_id": hypothesis.hypothesis_id,
                "event_type": hypothesis.dominant_type(),
                "zone": hypothesis.zone,
                "origin_sensor": next(iter(hypothesis.sensors)),
                "fov_overlap": self.fov_overlap.get(hypothesis.zone or "site", {}),
                "timestamp": now_ts()}
```

The `or "site"` mirrors `FusionAgent`'s own hypothesis-key fallback, and the
shape `{"<zone>": {"cam_id": 0.9, ...}}` matches the existing consumer
`task.get("fov_overlap", {}).get(self.agent_id, 0.5)` exactly.

Note `coordinator_agent.py` annotates `Dict[str, Any]` at line 53 while
importing only `Dict, List, Optional` — `Any` is never imported, masked by
`from __future__ import annotations`. `fusion_agent.py:64` has the identical
latent bug. **Both out of scope. Do not fix.** (If you add a `Dict[str, Dict[str, float]]`
annotation as above you introduce no new dependency on `Any`.)

### 5.7 `aura_mas/scenarios/replay.py`

Coordinator, lines 104-105:

```python
    coordinator = CoordinatorAgent("coordinator", bus, mode=coord_mode,
                                   camera_ids=cam_ids, bandit_path=bandit_path,
                                   fov_overlap=manifest.get("fov_overlap"))
```

Camera, lines 135-139 — the manifest-tunable knobs today are only `zones`,
`enable_clip`, `anomaly_threshold`, so add the three thresholds:

```python
        cam = CameraAgent(spec["id"], bus, spec["source"],
                          zones=spec.get("zones", []),
                          enable_clip=spec.get("enable_clip", False),
                          anomaly_threshold=spec.get("anomaly_threshold", 0.55),
                          realtime=realtime,
                          loiter_seconds=spec.get("loiter_seconds", 8.0),
                          abandoned_seconds=spec.get("abandoned_seconds", 10.0),
                          min_flow_px=spec.get("min_flow_px", 40.0))
```

Both are pure `.get()` reads, so all nine existing manifests keep today's
defaults exactly.

### 5.8 The confidence arithmetic — read before choosing any threshold

This was derived by tracing Event → FusionAgent → PolicyAgent and it changes
scenario design. `FusionAgent._fuse_confidence` is noisy-OR:
`conf = 1 - Π(1 - w·min(1, c))` with `MODALITY_RELIABILITY = {"video": 0.9,
"audio": 0.7}`, `+0.05` if `len(modalities) > 1`, `+0.05` if `len(sensors) > 1`,
capped at 1.0, rounded to 3 dp. `PolicyAgent` takes severity from
`hyp.dominant_type()` (the **max-confidence** event) and applies
`ALERT_THRESHOLDS = {"CRITICAL": 0.45, "WARNING": 0.55, "INFO": 0.70}`.

**Loitering is suppressed even after lowering `loiter_seconds`.** It maps to
`INFO`, the *strictest* threshold at 0.70. Its confidence is
`min(1.0, (ts - first)/30.0 + 0.5)`, so a 4.1 s dwell yields 0.637, and a single
video event fuses to `0.9 × 0.637 = 0.573` — **below 0.70, suppressed.**
Clearing 0.70 from one sensor needs an 8.3 s dwell; the longest real dwell on
disk is 5.5 s.

Two cameras both reporting loitering: `1 - (1 - 0.573)² = 0.818`, `+0.05`
cross-sensor = **0.868 ≥ 0.70 ✓**. Because hypotheses are keyed
`f"{family}:{zone}"`, this requires both cameras to declare a zone with the
**same name** so their events merge into one `security:<zone>` hypothesis
within the 6 s window.

That is a genuine C2/C3 demonstration — at current thresholds a loitering alert
is only actionable under cross-camera corroboration — and it belongs in
`loitering_multizone_01`'s `notes`.

Budget for the new rules:

| Rule | Family → severity → threshold | Confidence | 1 video sensor fuses to | Alerts? |
|---|---|---|---|---|
| `zone_occupancy` | `hazard` → WARNING → 0.55 | `mean_conf + 0.1·(n−limit−1)`; 0.8 at `n = limit+1` | 0.72 | ✓ |
| `wrong_direction` | `security` → WARNING → 0.55 | track detection conf, 0.7–0.9 | 0.63–0.81 | ✓ |
| `intrusion` | `security` → CRITICAL → 0.45 | ~0.85 | 0.765 | ✓ |
| `loitering` | `security` → INFO → 0.70 | 0.637 @ 4.1 s | 0.573 | ✗ — needs 2 sensors |

Weak detections honestly fail to alert. That is intended; do not tune the
formulas to force alerts.

**Severity/dominance interaction:** where `intrusion` (conf ~0.85) and
`loitering` (0.637) merge in one `security:<zone>` hypothesis, the alert emits
as `intrusion` at CRITICAL/0.45 — and since the matcher is family-only, a
`loitering` GT row still scores a true positive.

---

## 6. Step 4 — the four scenarios

### 6.1 Manifest conventions (observed across all nine existing files)

Key order is consistently `name, duration_seconds, sensors, ground_truth,
notes`; 2-space indent; compact one/two-line sensor objects. `name` matches the
filename stem. GT is **inline**, timed in **video seconds**; zone-independent
events use `"zone": null`. `notes` is never read by any code but is load-bearing
socially — every scenario uses it to record how GT was empirically verified and
what is known not to work.

```json
{
  "name": "<matches filename stem>",
  "duration_seconds": 55,
  "fov_overlap": {"perimeter": {"cam_02": 0.9, "cam_03": 0.4, "cam_01": 0.1}},
  "sensors": [
    {"type": "camera", "id": "cam_01", "source": "data/clips/people.mp4",
     "loiter_seconds": 4.0,
     "zones": [{"name": "entry", "type": "entry", "polygon": [[0,300],[380,300],[380,432],[0,432]],
                "max_occupancy": 1, "flow_direction": [1, 0]}]},
    {"type": "audio", "id": "mic_01", "source": "...wav", "zone": "entry"}
  ],
  "ground_truth": [
    {"event_type": "intrusion", "zone": "zone_A", "t_start": 15.0, "t_end": 34.0}
  ],
  "notes": "provenance, verification method, known limitations"
}
```

⚠️ An audio sensor with **no** `zone` key can never corroborate video —
`combined_audio_video_01.json`'s notes state that without a matching `zone` the
events "land in separate hypotheses and can NEVER corroborate regardless of
family match." `demo_site_01.json`'s `mic_01` has no `zone` key.

⚠️ **`replay.py:96` silently drops sensors whose `type` is not
`camera`/`audio`.** A typo produces no error, just a missing agent.

### 6.2 ⚠️ The matcher is zone-blind — this constrains GT design

`eval/metrics.py:40-52` matches on **family and time only** —
`if a_fam == g_fam and (g["t_start"] - tol) <= a_t <= (g["t_end"] + tol)` — with
no zone comparison, greedy 1:1, `tolerance` default 5.0 s. So two same-family GT
events in overlapping windows in *different* zones can be satisfied by the wrong
camera's alert and still score a true positive.

Rules for authoring the new GT, so greedy matching stays unambiguous **without
touching shared scoring code**:

- Same-family GT events must be **> 5 s apart** (matcher tolerance), ideally
  **> 6 s** (the fusion window) so they form separate hypotheses.
- Different-family events may overlap freely.

### 6.3 The scenarios

All reuse footage already on disk. Polygons and GT windows come from §4's probe
output — **placeholders below, derive every number.**

**1. `perimeter_chain_01`** — cross-camera perimeter intrusion / zone-to-zone
escalation. **Three CameraAgents** — the first scenario ever to run three,
closing the `research/planning/` W2.7/M2 gap. Chain: `approach`
(non-restricted, dwell + re-ID only) → `perimeter` (restricted) → `inner_yard`
(restricted). Declares `fov_overlap` so the auction picks the camera that can
actually see the zone. GT: two `intrusion` events ≥ 10 s apart in different
zones. Exercises C2 on real geometry and the cross-camera re-ID code on real
footage for the first time.

⚠️ `aura_mas/scripts/train_auction_bandit.py:47` derives the bandit's arm set
from each manifest's camera IDs. Adding a `cam_03` **changes the arm space and
invalidates `results/auction_bandit_weights.json`** (already modified in the
user's tree). `run_campaign.py` deliberately excludes `mas-auction-bandit` from
`MODES`, so the campaign is unaffected — but say so in the report and do not
retrain over their file.

**2. `loitering_multizone_01`** — loitering / abnormal dwell. Two cameras,
`loiter_seconds: 4.0` per sensor (below the measured 5.5 s max dwell), **sharing
one zone name** so the two events merge and clear the 0.70 INFO threshold per
§5.8. The first loitering positive on real footage in this repo's history;
directly answers `research/reports/research-report-v1/01-project-summary.md:343`.

**3. `zone_occupancy_01`** — zone-occupancy / crowding violation. New rule. Two
cameras with different `max_occupancy` limits, derived from the probe's per-frame
in-zone counts. **If the probe's peak count on `people.mp4`/`street.mp4` is 1,
switch to an AIRTLab violence clip**, which has ≥ 2 people by construction.

**4. `wrong_direction_01`** — wrong-direction / counter-flow movement. New rule.
Two cameras with opposing `flow_direction` axes, derived from the probe's
per-track net displacement.

**Conditional 5th.** `data/clips_real/abandoned_object/video3.avi` is on disk
but absent from `manifest.json` and unreferenced. If the §4 probe shows genuine,
usable ABODA footage distinct from `video1.avi`, a two-camera
`abandoned_object_multizone_01` is the **only** addition here that would
contribute a genuinely new *recorded* event — and it needs a
`data/clips_real/manifest.json` entry for citation integrity (adding an entry is
not a stop-condition: the manifest is neither a scenario nor a GT file). If it
fails, drop it and say so — four scenarios already meet the acceptance criteria.

### 6.4 Honesty constraint on how this pack may be reported

`docs/ai-enhancement-research.md:190` (2026-08-21, the newest audit) judges
exactly this kind of work:

> Procedural re-mixing of existing AIRTLab/ABODA/ESC-50 clips … **Does not close
> the real gap — the underlying event count stays at 7 unique recorded events
> regardless of re-cutting/re-timing** … Legitimate for ablation/stress-testing
> the fusion logic; **must not be reported as expanding real evaluation
> diversity** … Synthetic audio-video pairings that never co-occurred in reality
> could be mistaken for additional real evidence if not clearly labeled as
> synthetic in any results table.

`data/clips_real/manifest.json` catalogues exactly 7 assets, which is where that
count comes from. Therefore:

1. Each new manifest's `notes` records that footage is reused and states the
   underlying-event-count caveat.
2. The written summary labels the pack a **coordination stress-test pack**, not
   expanded real evaluation diversity.
3. New metrics go to **separate** CSVs, never pooled into the cited
   `results/summary.csv` / `results/summary_agg.csv`.
4. Effective independent sample size stays scenario-cluster-sized
   (`docs/ai-enhancement-research.md:210`) and does not grow with the run count.

Two prior audits look contradictory here but are not:
`research/reports/research-report-v1/02-gaps-and-recommendations.md:323-326`
recommends scenario generation as "a defensible methodological contribution" and
means *genuinely new scenes*; `:190` judges *re-cutting the existing 7
recordings*. This work does the latter and labels it so.

---

## 7. Step 5 — verification

Harness wiring needs **zero code changes**: `run_campaign.py:144` is
`all_paths = sorted(glob.glob("scenarios/*.json"))` and `replay.py` takes an
arbitrary manifest path. That acceptance criterion is verified, not coded.
(`--scenarios` matches `manifest["name"]`, not filenames. `--bus local` is
hardcoded at line 100. `MODES = ["mas-auction", "mas-rules", "mas-nocoord",
"centralized"]`. Output paths are `results/run_{scenario}_{tag}.json`, and the
campaign resumes by skipping existing ones.)

Cost note: `realtime = mode != "centralized"` (`replay.py:127`), so a run takes
roughly its video duration. Keep clips ~30–45 s: 4 scenarios × 4 modes × 3 reps
≈ 48 runs.

```
python -m pytest aura_mas/tests -q
```
Existing suite plus the new zone-rule tests, offline, < 1 s. Confirms no
regression in the nine existing scenarios' code paths.

```
python -m aura_mas.scenarios.replay scenarios/<new>.json --mode mas-auction --bus local
```
Per scenario. **Check counts, not exit code** — the `intrusion_01`
zero-detection failure was completely silent. Confirm the intended events fire
and `agent_metrics` shows *every* camera producing detections.

Then: `coord_tasks > 0` and bid values **varying per camera** instead of
constant (evidence `fov_overlap` is live); and a shared `global_entity_id`
across cameras in `perimeter_chain_01` (first real-footage exercise of the
re-ID code).

```
python -m aura_mas.scripts.run_campaign --dry-run
```
Confirms the new scenarios appear × 4 modes with no harness edits.

Scored campaign, new scenarios only, N ≥ 3 reps (per `CLAUDE.md`'s
non-determinism warning — the ±0.447 stds in existing data are 1-of-5 binary
outcomes, not distributions):

```
python -m aura_mas.scripts.run_campaign --scenarios perimeter_chain_01 loitering_multizone_01 zone_occupancy_01 wrong_direction_01 --reps 0,1,2 --min-free-gb 5
```

⚠️ **Two scoring traps.** `metrics.py`'s `runs` is `nargs="+"`, and only one of
the four new names contains "multizone" — a single `results/run_*multizone*.json`
glob would silently miss three of four. And `--agg-out` **defaults to
`results/summary_agg.csv` whenever > 1 rep exists**, which would overwrite the
cited campaign aggregate. Pass both explicitly:

```
python -m aura_mas.eval.metrics "results/run_perimeter_chain_01_*.json" "results/run_loitering_multizone_01_*.json" "results/run_zone_occupancy_01_*.json" "results/run_wrong_direction_01_*.json" --out results/summary_multizone.csv --agg-out results/summary_multizone_agg.csv
```

Finally, `git status` must show **no modification to any pre-existing scenario,
GT, or results file**, and `main` untouched.

---

## 8. Citations — open blocker, and the rule

`WebSearch`/`WebFetch` returned `claude-opus-5 is temporarily unavailable` on
every attempt across the whole session (~12 tries). The brief requires a
verified, non-fabricated citation for every technique adopted from external
research.

In-repo `.bib` entries are **not** self-certifying either:
`research/aura-mas-landscape-positioning/findings/F5_prior_bibliography_needs_verification.md`
records 94 AI-generated entries, 6 spot-checked, with corrupted author fields, a
paraphrased title and a wrong year — verdict "starting draft / citation-discovery
list, not submission-ready material." And
`grep -in -E "loiter|abandon|crowd|occupan|direction|counter-flow|trajector|ABODA|AIRTLab|ESC-50|Piczak|Bianculli" thesis/Bibliography/bibliography.bib`
returns **zero** matches — there is no in-repo citation for any anomaly type
being implemented.

**Rule: no citation gets written into any repo file unless verified against a
live source.** If the tool stays down:

- Cite only the three dataset sources already verified in
  `data/clips_real/manifest.json` (AIRTLab / Data in Brief 2020 with DOI, ABODA /
  Lin et al., ESC-50 / Piczak 2015 CC BY-NC 3.0) — full strings are in §5 of the
  drafted feasibility report.
- Describe the two new rules as **geometric definitions implemented from first
  principles rather than reproductions of a specific paper** — which is what
  they are.
- Leave explicit `CITATION-NEEDED` markers rather than plausible-looking
  references.

Honest and costs nothing later. Fabricating is unrecoverable.

Also note: `data/clips/people.mp4` and `street.mp4` predate
`data/clips_real/manifest.json`, are not catalogued there, and their provenance
is unrecorded anywhere in the repo. Flag this — it should be established before
any figure derived from them enters the thesis.

---

## 9. Synthetic-scene / digital-twin verdict: NOT FEASIBLE

Already written up in full in the drafted
`research/reports/synthetic_scene_generation_feasibility.md` (§2). Summary of the
reasoning, all four quotes verified at the exact line numbers given:

- `aura_mas/scripts/make_synthetic_clips.py:4-7` says so in its own docstring;
  `draw_person()` renders `cv2` rectangles plus a circle.
- `scenarios/intrusion_01.json`'s notes: YOLO11n never detects a person in the
  resulting clip "at any confidence down to 0.05 … the only class ever detected
  in `intrusion.mp4` across the whole clip is a stray 'sports ball'." It was
  scored for a whole campaign before anyone noticed.
- `research/reports/research-report-v1/03-concepts-explained.md:895`: "The
  synthetic-to-real gap is the central risk, and this project has already been
  bitten by its most extreme form."
- `research/planning/One-Month Execution Schedule — AURA-MAS PFE.md:71`: the
  documented data fallback is "Avenue dataset (2 GB) + self-recorded phone clips
  of scripted scenarios" — real capture, not simulation.

A real generator (Isaac Sim / Omniverse, CARLA, UE5) is a new external
dependency **and service** — a stop-condition needing approval — with multi-day
install/asset/calibration cost against a project whose own rule
(`data/clips_real/manifest.json:57`) is "never spend more than one day blocked on
a single component," and it relocates rather than removes the domain-gap
validation burden.

Adopted alternative: real footage on disk + GT measured from what the detector
actually produces (§4). Recommended next step if real diversity is wanted later:
self-recorded phone clips, three takes, ~1 hour — table in §4 of the report.

---

## 10. Task-list state to carry over

| # | Status | Task |
|---|---|---|
| 1 | completed | Inventory existing scenario/ground-truth/replay conventions |
| 2 | pending | Research anomaly types with citable sources — **blocked on WebSearch**, see §8 |
| 3 | completed | Investigate synthetic/digital-twin feasibility — report drafted |
| 4 | pending | Design 3–4 multi-zone/multi-camera scenarios — **blocked on §4 probe output** |
| 5 | completed | Write final plan and get approval |
| 6 | in_progress | Create branch and enabling fixes — **blocked on git via Bash** |
