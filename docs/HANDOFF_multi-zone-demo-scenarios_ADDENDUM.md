# Handoff addendum — verified corrections (2026-08-26)

Six facts in `HANDOFF_multi-zone-demo-scenarios.md` were asserted from reading
call sites but not confirmed against the actual CLI/dataclass definitions. They
have now been confirmed by direct source inspection. **Where this file and the
main handoff disagree, this file is correct.** Every claim below carries the
`file:line` it was read from, so it can be re-checked without re-deriving it.

Nothing here changes the plan's design or scope. Four of the six are
tightenings; two (#4, #5) correct claims that were wrong.

---

## 1. `--scenarios` takes manifest `name` values, not file paths

`aura_mas/scripts/run_campaign.py:145-147`:

```python
    wanted = set(args.scenarios.split(","))
    paths = [p_ for p_ in all_paths
            if json.load(open(p_))["name"] in wanted]
```

The filter compares against each manifest's **`name` field**, not its path or
filename. By repo convention `name` equals the filename stem, so the practical
effect is the same *provided each new manifest's `name` matches its filename* —
which the conventions section already requires. State it as a hard requirement:
a manifest whose `name` disagrees with its filename is silently unselectable by
`--scenarios` and will be skipped without an error.

Correct form:

```bash
python -m aura_mas.scripts.run_campaign \
  --scenarios perimeter_chain_01,loitering_multizone_01,zone_occupancy_01,wrong_direction_01 \
  --reps 0,1,2 --min-free-gb 5
```

## 2. Keep the four new scenarios camera-only — the 48-run estimate depends on it

`run_campaign.py:52`:

```python
        vo_options = [False, True] if (has_audio and include_vision_only) else [False]
```

The vision-only ablation doubles the grid **only for scenarios that declare an
audio sensor**, and `include_vision_only` is on by default (`--no-vision-only`
opts out). So:

- 4 camera-only scenarios × 4 modes × 3 reps = **48 runs**
- add one mic to each and it becomes **96 runs**, at roughly video-duration
  wall-clock each (`realtime = mode != "centralized"`, `replay.py:127`)

**Decision, stated so it is not silently reversed:** the four new scenarios
declare **no audio sensor**. This is not a cost dodge — the pack measures
cross-camera/cross-zone coordination, and cross-modal fusion is already
covered by `combined_audio_video_01`. Claim C3's corroboration path is still
exercised, via the **cross-sensor** term rather than the cross-modal one: two
CameraAgents publishing into one shared zone name yields `len(hyp.sensors) > 1`
and the `+0.05` cross-sensor bonus. Adding a mic would double the campaign to
re-demonstrate something an existing scenario already demonstrates.

`MODES = ["mas-auction", "mas-rules", "mas-nocoord", "centralized"]`
(`run_campaign.py:31`) — `mas-auction-bandit` is **not** in the campaign
default, so it only runs if invoked explicitly through `replay.py`.

## 3. `duration_seconds` is load-bearing, not decorative

`aura_mas/scenarios/replay.py:171`:

```python
            th.join(timeout=manifest.get("duration_seconds", 120) + 30)
```

It is the camera-thread join timeout. Set too low, camera threads are cut off
before the clip ends and events go missing **silently** — the same failure
shape as the `intrusion_01` zero-detection bug. Set each new manifest's
`duration_seconds` to at least the true clip length:

| Clip | Measured length | Minimum `duration_seconds` |
|---|---|---|
| `data/clips/people.mp4` | ≈ 59.6 s | 60 |
| `data/clips/street.mp4` | ≈ 64.6 s | 65 |

(Lengths from `sampled_frames / infer_fps` in existing run JSONs: 298/5 and
323/5. Confirm against the probe's own `video_seconds` field, which reads
`CAP_PROP_FRAME_COUNT` directly, before finalising.)

## 4. CORRECTION — verification step 5 is not runnable as written

The plan says to "confirm a shared `global_entity_id` appears across cameras."
**It cannot be read from a run JSON.** `Alert` (`aura_mas/core/bus.py:69-81`)
has exactly these fields:

```
alert_id, timestamp, severity, event_type, confidence, zone,
sensors, evidence, fused_events, explanation, status, contributing_types
```

There is no entity id. `global_entity_id` is a field on the in-memory
`Hypothesis` (`fusion_agent.py:33`), set at `fusion_agent.py:123`, and
`policy_agent.py:95-102` never copies it onto the `Alert`. It surfaces in only
two places, both inside `ExplanationAgent` — `explanation_agent.py:185` (LLM
prompt context) and `:229` (`" (Subject <id>)"` in the fallback template) — and
`ExplanationAgent` is only constructed behind `--llm`.

**Replacement, dependency-free and readable straight from the run JSON:**
`policy_agent.py:99` sets `sensors=sorted(hyp.sensors)`, so an alert whose
`sensors` list holds **two or more camera ids** is direct proof that two
cameras' events merged into one hypothesis — which is the cross-camera
coordination claim the scenario exists to demonstrate.

```bash
python -c "import json,glob;   [print(a['zone'], a['event_type'], a['sensors']) \
  for f in glob.glob('results/run_perimeter_chain_01_*.json') \
  for a in json.load(open(f))['alerts']]"
```

Re-ID specifically (`global_entity_id`) stays verifiable only by (a) running
with `--llm` and grepping the `explanation` string for `Subject`, or (b) an
offline unit test, which is what `aura_mas/tests/test_reid_fusion.py` already
does with hand-built vectors. Report it that way; do **not** claim the run JSON
evidences re-ID.

## 5. CORRECTION — `fov_overlap` is not a bandit feature, so saved weights stay valid

Softer than the main handoff's claim. `aura_mas/core/bandit.py:39-45`:

```python
def build_context(candidate_id: str, task: Dict) -> np.ndarray:
    bias = [1.0]
    is_origin = [1.0 if task.get("origin_sensor") == candidate_id else 0.0]
    zone = _hash_bucket(task.get("zone"))
    event = _hash_bucket(task.get("event_type"))
```

`FEATURE_DIM = 2 + 2 * 3 = 8` (`bandit.py:27`) and the module docstring
(`bandit.py:12-16`) states outright that `fov_overlap`/`busy` "are not
available to the coordinator … a known, explicitly-documented simplification."

So plumbing `fov_overlap` into the task dict **does not change the context
vector**, and `results/auction_bandit_weights.json` stays dimensionally valid.
Two real but milder consequences:

- **New arm ≠ invalidation.** `ensure_arm` (`bandit.py:62-66`) cold-starts an
  unknown arm at `A = identity(8)`, `b = zeros(8)`. `cam_03` therefore joins
  cleanly with no crash and no dimension error. But an untrained arm has the
  largest possible UCB exploration bonus, `alpha * sqrt(x @ A_inv @ x)`, so in
  `auction-bandit` mode the bandit will **preferentially pick the brand-new
  camera** early. That looks exactly like "the bandit learned to prefer cam_03"
  and is nothing but cold-start exploration. Do not report it as learning.
- **Hash collisions, not new dimensions.** `_hash_bucket` is `crc32(value) % 3`
  (`bandit.py:30-36`), so new zone names and the two new event types fold into
  the same 3 buckets as existing ones. No dimension change, but the trained
  weights' meaning shifts. `auction-bandit` is outside the campaign default
  (#2), so this only matters for an explicit `--mode mas-auction-bandit` run.

## 6. `fov_overlap` really is dead today — confirmed repo-wide

`grep -rn "fov_overlap" aura_mas/ scenarios/` returns exactly two hits:
`camera_agent.py:373` (the read, defaulting to `0.5`) and `bandit.py:13` (the
docstring above). It is written nowhere, so `_view_score`'s `overlap` term is
permanently `0.5` and the bid collapses to a 3-valued function of origin-ness
and busy-ness. This confirms the main handoff's finding and the requirement to
disclose that **all prior campaign results ran with `overlap` pinned at 0.5**,
regardless of what `chapter6.tex:120` / `chapter4.tex:104` claim.

---

## Still-verified-good

Everything else the addendum did not touch was re-confirmed in passing:
`run_campaign.py:144` is `sorted(glob.glob("scenarios/*.json"))`, so new
manifests need **zero** harness edits; `metrics.py:137` `--out` defaults to
`results/summary.csv`; and `metrics.py:170-173` is the trap the main handoff
flags — `--agg-out` defaults to `None`, whereupon `n_reps > 1` silently writes
the **cited** `results/summary_agg.csv`. Always pass it explicitly:

```bash
python -m aura_mas.eval.metrics "results/run_perimeter_chain_01_*.json" \
  ... --out results/summary_multizone.csv \
      --agg-out results/summary_multizone_agg.csv
```

`data/clips_real/abandoned_object/video3.avi` exists (4,407,330 bytes, beside
`video1.avi` at 4,441,866 bytes, same mtime), so the conditional 5th scenario
is still live pending a probe confirming YOLO holds a static non-person track
in it.

---

## 7. ⚠️ The base branch changed — the repo is no longer on `main`

The main handoff's §3 says to branch off `main`. **That is now stale.** As of
2026-08-26 the working branch is **`thesis-v3-update`**, and it carries a large
amount of the user's own uncommitted work that did not exist when the plan was
written:

```
?? aura_mas/scripts/thesis_stats.py        ?? results/thesis_stats.json
?? aura_mas/scripts/make_thesis_figures.py ?? results/figures/*.png  (6 figures)
?? 01projectsummary.md                     ?? thesis/Assets/generated/
?? 03conceptsexplained.md                  ?? thesis/Assets/tikz/
 M .gitignore                              M  aura_mas/core/taxonomy.py
```

Consequences for the next agent:

1. **Branch off the current HEAD (`thesis-v3-update`), not `main`.** The brief
   says "create branch off current branch"; when the plan was written that
   happened to be `main`. Branching off `main` now would orphan the v3 thesis
   work this pack's documentation cross-references.
2. **The tree is shared.** The user's uncommitted files sit alongside this
   pack's. `git add -A` would commit their in-progress thesis work. Stage
   **only** the explicit path list in the main handoff §2, exactly as the plan
   requires ("only files I create or modify get staged").
3. Several files are modified by **both** this pack and the user's v3 work
   (`camera_agent.py`, `coordinator_agent.py`, `policy_agent.py`,
   `taxonomy.py`, `replay.py`, `fusion_agent.py`, `bus.py` were already `M` at
   session start). Do not revert or check out any of them — inspect with
   `git diff <path>` before staging.

## 8. ⚠️ NEW FINDING — GT is scored on the wrong clock, and it hits `centralized` hardest

Full write-up: **`research/reports/gt_video_vs_wall_clock_discrepancy.md`**
(new this pass). Surfaced, deliberately **not** fixed. Summary of what the next
agent must know before authoring any GT:

**(a) Two different clocks.** Rules fire on **video** time
(`camera_agent.py:412`, `video_ts = frame_id / src_fps`), but `metrics.py:45`
matches on **wall** time (`a_t = a["t_wall"] - run["t_start"]`).

**(b) Wall time drifts ~1.2× and never recovers.** `camera_agent.py:349-352`
only ever *sleeps* — there is no catch-up branch — and measured `infer_ms` is
241.6 against the 200 ms budget implied by `infer_fps=5.0`. So
`wall ≈ video × 1.21`, accumulating, penalising late-clip events.

**(c) The end-to-end relation to author GT against:**

```
a_t  ≈  video_ts_of_event × 1.2   +   6.0   [ + ~1.5 if auctioned ]
```

The `+6.0` is `FusionAgent.window_seconds` (verified: last evidence frame at
wall +46.5, alert at +52.94). The `~1.5` is the measured
`allocation_ms: [1527.5]`.

**(d) `centralized` is penalised ~40 s on multi-camera scenarios.**
`replay.py:165-169` runs it strictly sequentially (`th.start(); th.join()`), so
camera 2's video clock starts only after camera 1's clip finishes. The *same
physical `zone_B` intrusion* in `demo_site_01` lands at **+9.4 s** under
`mas-auction` (parallel) and **+49.05 s** under `centralized` (sequential).
Only `demo_site_01` and `intrusion_01` have 2 cameras; all other seven
manifests have ≤1, so the bias is invisible elsewhere.

**(e) The zone-blind matcher hides wrong attribution.** `demo_site_01`'s GT 1
(`intrusion`/`zone_A`/3–35) and GT 2 (`loitering`/`entry`/16–46) are **both
family `security`** with **overlapping ±5 s bands**. So a `zone_A` intrusion
alert is scored as a true positive for an `entry`-zone **loitering** GT, and a
`zone_B` alert is scored for a `zone_A` GT. Both runs reach F1 0.667 through
mutually inconsistent matchings.

**Why this is load-bearing for THIS pack, not just trivia:** (e) means the
existing metrics **cannot distinguish correct cross-camera attribution from a
lucky same-family time collision** — so they cannot, even in principle,
evidence a claim that coordination improved cross-camera behaviour. That is an
independent reason to obey the main handoff §6.2 rule (same-family GT events
> 5 s apart, never two same-family windows overlapping), and it is worth stating
in the final write-up as a limitation of the comparison rather than a result.

**Concrete GT-authoring rules that follow:**

- Convert every intended video-time event through `× 1.2 + 6.0` and check the
  result lands inside `[t_start - 5, t_end + 5]` before committing a window.
- Prefer events **early** in each clip — accumulated drift is smallest there.
- Write the arithmetic into each manifest's `notes` so the window is auditable
  instead of magic.
- Do **not** "fix" this by widening `tolerance`, editing `metrics.py`, or
  rewriting existing GT. All three are out of scope and the last is forbidden.

## 9. ⚠️ This collides with work the user is doing right now

`aura_mas/scripts/thesis_stats.py:49` and
`aura_mas/scripts/make_thesis_figures.py:43-44` read `results/summary.csv` and
`results/thesis_stats.json` — the numbers §8 affects.
`results/thesis_stats.json` is already generated (`n_rows_used: 180`,
10 000 bootstrap resamples, `seed: 20260826`, Wilcoxon signed-rank paired on
`(scenario, rep)`, Holm–Bonferroni over 6 comparisons, Cliff's delta) and six
figures exist in `results/figures/`.

Two of the affected quantities are load-bearing:
`mean_time_to_alert_s` (`metrics.py:51` — a wall-clock latency against a
video-time origin, plotted directly by `fig_tta_per_scenario.png`), and
F1/precision/recall (which inherit §8's TP/FP/FN misclassifications). Because
§8(d) biases **against `centralized`** and only on the two multi-camera
scenarios, the paired mode comparisons are affected **asymmetrically** —
visible in `fig_mode_ci.png` and `fig_paired_forest.png`.

**Do not regenerate, adjust, or "correct" any of those figures or stats.** The
direction of the effect is knowable; the magnitude is not without a re-run.
This is the user's call — `CLAUDE.md`: "don't silently rewrite evaluation
numbers… surface discrepancies to the user instead."

## 10. Tooling state at handoff

The Bash safety classifier was **intermittently unavailable** for the whole of
both sessions. Read-only commands (`cat`, `sed -n`, `grep`, `find`, `wc`,
`git status`/`branch`/`rev-parse`) pass; anything that writes or executes
(`git checkout -b`, `pytest`, `python`, `bash <script>`, heredocs, `for` loops,
`grep` with brace quantifiers) is rejected. `WebSearch`/`WebFetch` were down
throughout (~14 attempts) — hence §8 of the main handoff and the
`CITATION-NEEDED` table in
`research/reports/anomaly_type_survey_multizone.md`.

**All code changes are already on disk and verified present by grep** (all four
event-type registration points, both new rules, the `ZoneRuleEngine` kwargs,
`fov_overlap` in the coordinator task dict, and the `replay.py` plumbing).
Nothing is committed. What remains blocked is only: `git checkout -b`,
`pytest`, and the probe runs.

`/home/lokmane-zed/.claude/jobs/502b5aa5/tmp/unblock.sh` does all three in one
command and is safe to hand to the user verbatim — it creates the branch, runs
the offline suite, writes `probe_{people,street,video3}.json` into that tmp
dir, and prints clip geometry. It does **not** commit, push, or touch anything
under `scenarios/` or `results/`.

---

## 11. `loitering_multizone_01` is fully derivable WITHOUT the probe — use this

Scenario 2 no longer needs to wait on the probe. Its ground truth can be
grounded in a measurement **already empirically verified and recorded in this
repo**, and its alert behaviour is **deterministic arithmetic**. The other
three scenarios still genuinely need the probe.

### 11.1 The grounding measurement

`scenarios/loitering_01.json:12` (`notes`) records a direct ByteTrack
measurement, and explicitly says it was checked against a full-frame zone:

> "the longest continuous single-track presence found anywhere is **5.5 s
> (people.mp4, track 3, t=15.3–20.8 s)**, below `ZoneRuleEngine`'s
> `loiter_seconds=8.0` threshold, **regardless of zone shape (also tried a
> full-frame zone)**"

That last clause is what makes it reusable: the dwell is not an artifact of
`loitering_01`'s particular `entry` polygon, so a full-frame-ish zone on
`people.mp4` preserves it. With `loiter_seconds: 4.0`, track 3 fires at video
≈ **19.3 s** (15.3 + 4.0).

### 11.2 The arithmetic — loitering alerts **iff** coordination is on

`loitering` confidence is **purely dwell-based** and ignores detector
confidence entirely (`camera_agent.py`):

```python
"confidence": min(1.0, (ts - first) / 30.0 + 0.5)
```

so it is deterministic given the dwell, not subject to the CPU-float
non-determinism `CLAUDE.md` warns about. At fire time the dwell is
`loiter_seconds` plus one frame interval (0.2 s at `infer_fps=5.0`), so
`d ≈ 4.2`:

| step | value |
|---|---|
| event confidence `4.2/30 + 0.5` | 0.640 |
| `FusionAgent` noisy-OR, one video sensor: `0.9 × 0.640` | **0.576** |
| `loitering` → `SEVERITY_MAP` → **INFO** → threshold | **0.70** |
| 0.576 < 0.70 → `mas-nocoord`, `centralized` | **suppressed = false negative** |
| 0.576 ∈ gray zone (0.35, 0.75) → verification requested | `mas-auction`, `mas-rules` |
| verified: `0.576 + 0.15` (`policy_agent.py:62`) | **0.726 ≥ 0.70 → ALERT** |
| failed verification: `0.576 − 0.20` (`policy_agent.py:65`) | 0.376 → still suppressed |

**The usable window for `loiter_seconds` is [3.34, 5.4] s**, from solving
`0.9 × (d/30 + 0.5) + 0.15 ≥ 0.70` → `d ≥ 3.33` (lower bound: below this even
a verified alert misses 0.70) against the measured 5.5 s ceiling (upper bound:
above this it never fires at all). **`4.0` sits comfortably inside** — do not
use 3.0, which yields 0.696 and misses the threshold by 0.004.

And the un-coordinated path can never clear it on this footage: alerting
without verification needs `0.9 × (d/30 + 0.5) ≥ 0.70` → **`d ≥ 8.33 s`**,
against a measured maximum of 5.5 s. So on every clip on disk, **loitering is
detectable if and only if coordination is enabled** — a footage-grounded,
arithmetically exact demonstration of contribution C2, and the first loitering
positive in this repo's history.

### 11.3 ⚠️ `fov_overlap` must be declared, or this scenario produces a false negative

`camera_agent.py:_verify` re-runs inference on **the winning camera's own
`_last_frame`** (`predict(imgsz=960, conf=0.25)`, `verified = score > 0.4`). So
if a camera that cannot see the loiterer wins the auction, verification
**fails**, applies **−0.20**, and kills the alert. `fov_overlap` is what
prevents that — this is exactly why it stops being cosmetic here.

Bids are `base × capacity × overlap` with `base = 0.3` for the origin sensor
and `1.0` otherwise (`camera_agent.py:444-486`), so the origin camera is
**penalised 3.3×** by default. To let the camera that actually sees the zone
win, it must be handed enough overlap to overcome that:

```json
"fov_overlap": {"entry": {"cam_01": 1.0, "cam_02": 0.2}}
```

→ `cam_01` bids `0.3 × 1.0 × 1.0 = 0.30`, `cam_02` bids `1.0 × 1.0 × 0.2 =
0.20`. `cam_01` wins and re-checks its own frame, where the loiterer is.

Note what this makes the scenario demonstrate: **self-verification** ("look
again, more carefully, at higher resolution"), not cross-camera confirmation.
That is a legitimate active-verification story and it is what the code
implements — but it must be described accurately in the write-up. A genuine
*cross-camera* loitering confirmation would need two clips that both contain a
≥4 s dwell of the same person, and whether `street.mp4` contains any dwell at
all is unknown until the probe runs.

### 11.4 Recommended manifest shape

Two cameras, **different** zone names so the hypotheses do **not** merge
(`FusionAgent` keys on `f"{family}:{zone}"` — a shared name would pool them):

- `cam_01` = `data/clips/people.mp4`, zone `entry`, `loiter_seconds: 4.0` →
  fires the loitering event.
- `cam_02` = `data/clips/street.mp4`, zone `forecourt` → supplies the second
  zone and the auction's losing bid.

GT (one event, in video seconds per convention), with the §8(c) conversion
`19.3 × 1.2 + 6.0 ≈ 29.2` s wall — so the window must reach into the low 30s:

```json
"ground_truth": [
  {"event_type": "loitering", "zone": "entry", "t_start": 18.0, "t_end": 32.0}
]
```

`duration_seconds` must be ≥ 60 for `people.mp4` (it is the `th.join()`
timeout — see §3 of this addendum). Single GT event, so the zone-blind matcher
(§8(e)) has nothing to collide with.

**Still unverified and must be probed before this is trusted:** that
`street.mp4` yields ≥1 person detection at all (otherwise `cam_02` contributes
nothing and the second "zone" is decorative), and that a full-frame `entry`
polygon on `people.mp4` reproduces the 5.5 s dwell under
`model.track(..., conf=0.35)` as `CameraAgent` calls it — `loitering_01`'s note
says a full-frame zone was tried, but does not state the exact conf used.

---

## 12. ⚠️ Why no manifest was written into `scenarios/` — read before moving files

`loitering_multizone_01.json` **is written and fully derived**, but it is staged
at

```
/home/lokmane-zed/.claude/jobs/502b5aa5/tmp/staged_scenarios/loitering_multizone_01.json
```

**not** in `scenarios/`. This is deliberate, and the reason is a live
contamination hazard rather than caution for its own sake.

`aura_mas/scripts/run_campaign.py:144` discovers scenarios by
`sorted(glob.glob("scenarios/*.json"))`, and `:132-133` defines `--scenarios`
with `default=None`, documented as "default: all in `scenarios/`". So **any
manifest sitting in `scenarios/` is picked up by every unfiltered campaign
run.** Combined with §9: the user is *right now* computing thesis-v3
statistics, `aura_mas/scripts/thesis_stats.py:49` reads
`results/summary.csv`, and `results/thesis_stats.json` pins `n_rows_used: 180`.
A new manifest in the shared working tree therefore means the user's next
`run_campaign` invocation silently adds runs to `results/`, changes
`summary.csv`, and moves `n_rows_used` — the exact outcome branch isolation
exists to prevent. Because the branch could not be created (§10), that
isolation does not exist yet.

**The asymmetry that matters, and why the code edits were left in place while
the manifests were not:**

| Change class | Safe in the shared tree? | Why |
|---|---|---|
| The six code edits | **Yes** | All default-inert. `spec.get("loiter_seconds", 8.0)` (`replay.py:141`) keeps the old value; `manifest.get("fov_overlap")` (`:106`) yields `None` → `task.get("fov_overlap", {}).get(id, 0.5)` → the same 0.5 every prior campaign ran with; both new rules are gated on `max_occupancy` / `flow_direction`, and no existing zone declares either. Hand-verified by `test_default_loiter_seconds_unchanged` and `test_legacy_zone_dict_still_yields_intrusion_only` (§13). |
| New `scenarios/*.json` | **No** | Auto-discovered by the campaign glob above. Nothing gates them. |

**What to do once the branch exists** — after `git checkout -b`, and only then:

```bash
cp /home/lokmane-zed/.claude/jobs/502b5aa5/tmp/staged_scenarios/*.json scenarios/
```

Then score to a **separate** CSV, passing `--agg-out` explicitly (it silently
defaults to the cited `results/summary_agg.csv`):

```bash
python -m aura_mas.eval.metrics "results/run_*multizone*.json" \
  --out results/summary_multizone.csv \
  --agg-out results/summary_multizone_agg.csv
```

Note the glob only catches manifests whose `name` contains `multizone`. Of the
four planned scenarios only `loitering_multizone_01` does;
`perimeter_chain_01`, `zone_occupancy_01` and `wrong_direction_01` do not, so
either widen the glob or list their run files explicitly. Do **not** fall back
to `results/run_*.json` — that re-scores the whole cited 373-run campaign into
your new CSV.

## 13. The new test suite is hand-verified — you do not need to re-derive it

`aura_mas/tests/test_zone_rules.py` could not be executed (§10), so all **17**
tests were instead checked line-by-line against the implementation. Every one
is consistent with the code as written. The arithmetic-bearing ones:

- `test_zone_occupancy_fires_above_limit` asserts `pytest.approx(0.8)`. The
  formula is `min(1.0, mean_conf + 0.1 * (n - limit - 1))`
  (`camera_agent.py:113`); with 3 occupants at `conf=0.8` and
  `max_occupancy=2` that is `0.8 + 0.1*(3-2-1)` = `0.8 + 0.0` = **0.8** ✓.
- `test_zone_occupancy_escalates_once_per_level` uses `max_occupancy=1`, so two
  occupants give `0.8 + 0.1*(2-1-1)` = 0.8 and three give
  `0.8 + 0.1*(3-1-1)` = **0.9**, satisfying the strict
  `escalated > first` ✓. The middle `repeat == []` holds because firing is
  keyed `("occupancy", zone, n)`, so a *steady* count is silent while a
  *growing* one re-reports ✓.
- `test_zone_occupancy_counts_only_persons_inside` discriminates all three
  exclusion paths in the `inside` comprehension (`:94-98`) at once — class
  (`suitcase` inside the polygon), geometry (a person at x=900, outside), and
  `track_id is not None` ✓.

Two tests are sharper than they look, and should not be "simplified":

- `test_wrong_direction_resets_on_zone_exit` places the return at x=260 with
  `min_flow_px=40`. Without the `self._entry_point.pop(key, None)` at
  `camera_agent.py:129`, `p0` would still be `(300, 200)` and the projection
  would be exactly **−40**, which fires because the comparison is `<=`. The
  reset is the *only* reason the test stays silent, so it genuinely covers
  that line.
- `test_leaving_the_zone_resets_dwell` is built the same way: with
  `loiter_seconds=3.0` and a re-entry at t=4.0, an un-popped `_dwell` would
  give `4.0 - 0.0 > 3.0` and fire.
- `test_wrong_direction_uses_the_flow_axis_not_raw_sign` moves a track 200 px
  in **x** while the flow axis is `[0, 1]`; `_project(200, 0, [0,1])` = **0**,
  so cross-axis motion is correctly ignored, and only the subsequent
  `dy = -100` fires. This is what makes it a projection test rather than a
  displacement-magnitude test.

The `_person(tid, x, y)` helper builds `bbox = [x-10, y-40, x+10, y]`
specifically so that `cx = x` and `cy = bbox[3] = y` under the foot-point
convention — i.e. the helper's `(x, y)` *is* the foot point, which is why every
polygon assertion in the file can be read at a glance.

Expected result when you finally run it: **17 passed**, plus the 6 pre-existing
tests, offline, in well under a second. If any of the three arithmetic
assertions above fails, the implementation drifted from this handoff — trust the
test and re-read `_occupancy_events`, not the other way round.
