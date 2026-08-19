# 01 — Project Summary and Honest Assessment

**Audit date:** 2026-08-18
**Audited tree:** `~/Workspace/PFE(Memoire)/` (read-only; no project file was modified, moved, or deleted)
**Auditor stance:** senior AI research scientist reviewing against current state-of-the-art standards for a Master's thesis in intelligent surveillance / agentic AI.

> **How to read this document.** Every technical term used here has a full entry in `03-concepts-explained.md`. If a word is unfamiliar, look it up there before drawing conclusions. Where I could not verify something from file contents, I write `[not found in repo]` or `[uncertain]` rather than guessing.

---

## 1. Inventory: what is actually on disk

`~/Workspace/PFE(Memoire)/` contains **four** code/thesis trees plus reference material. They are not one project; three of them are dead or superseded.

| Directory | Status | Evidence |
|---|---|---|
| `Intelligent Surveillance System for Master's Thesis/` | **The live project (AURA-MAS).** ~1,775 files. Contains the runnable prototype, the compiled thesis, the evaluation campaign, and the research notes. | `CLAUDE.md`, `README.md`, `aura_mas/`, `AURA-MAS_Thesis_LaTeX/` |
| `pfe_surviellance_pfe/` | **Superseded earlier prototype.** A single-process YOLO + zone-rule pipeline with a `agents.py` that is not agent-based in any meaningful sense. Last modified ~2026-05. | `src/surveillance_prototype/` (11 modules, ~20 KB total), `PFE-Scope-Document-v1.md` |
| `pfe_agentic_ai/` | **Abandoned learning sandbox.** An LLM "agentic sandbox" (curriculum, memory, workflow) unrelated to surveillance. Last modified ~2026-03. | `src/agentic_sandbox/`, `docs/project_report.tex` |
| `7eba_PFE-Master_template/`, `Documents/`, `Research_Paper/`, `ResearchPapers/` | LaTeX template, 7 prior Algerian theses (PDF), 22 reference papers (PDF). Input material, not project code. | directory listings |

Everything below concerns **AURA-MAS** unless stated otherwise. The other two prototypes are relevant only as evidence of scope drift, discussed in §5.9.

---

## 2. What the system currently is (architecture and data flow)

### 2.1 Layered architecture as implemented

The system is a **hierarchical multi-agent system** with three layers over a message bus. This is documented in `CLAUDE.md` and `README.md` and matches the code.

```
Layer 3 — Governance   : Streamlit operator console (aura_mas/dashboard/app.py)
                         audit log (JSONL or Redis Streams), evidence store
Layer 2 — Coordination : FusionAgent · CoordinatorAgent · PolicyAgent · ExplanationAgent
Layer 1 — Edge         : CameraAgent (YOLO11n + ByteTrack + zone rules + optional CLIP)
                         AudioAgent (YAMNet, or DSP z-score fallback)
Bus                    : LocalBus (in-process) | MqttBus (Mosquitto) ; AlertStore (Redis Streams | JSONL)
```

### 2.2 Component-by-component, grounded in files

**`aura_mas/core/bus.py` (258 lines)** — defines three `dataclass` message schemas serialised to JSON:

- `Detection` (`bus.py:36-45`): `sensor_id, frame_id, timestamp, objects[]` where each object is `{class, confidence, bbox, track_id}`.
- `Event` (`bus.py:48-67`): `event_id, sensor_id, timestamp, event_type, confidence, modality, zone, track_id, evidence_path, extra`.
- `Alert` (`bus.py:70-90`): `alert_id, timestamp, severity, event_type, confidence, zone, sensors[], evidence[], fused_events[], explanation, status`.

Three transports: `LocalBus` (`bus.py:127-160`, thread-safe in-process publish/subscribe with MQTT-style `+`/`#` wildcard matching), `MqttBus` (`bus.py:163-198`, paho-mqtt), and `AlertStore` (`bus.py:201-243`, Redis Streams with a JSONL fallback). `make_bus()` (`bus.py:246-258`) tries MQTT and silently degrades to `LocalBus`.

**`aura_mas/agents/base.py` (54 lines)** — the `Agent` abstraction: an `agent_id`, a `beliefs` dictionary (a nod to the BDI model), bus subscriptions dispatched by callback, and an optional periodic `tick()` on a daemon thread.

**`aura_mas/agents/camera_agent.py` (353 lines)** — per-frame pipeline at `infer_fps=5.0`:
1. `model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.35)` — YOLO11n detection with ByteTrack association (`camera_agent.py:254`).
2. `ZoneRuleEngine.evaluate()` (`camera_agent.py:48-105`) — three stateful rules: **intrusion** (a `person` track's foot point inside a `restricted` polygon, fired once per `(track_id, zone)`), **loitering** (dwell > `loiter_seconds=8.0`), **abandoned object** (a non-person track with IoU > 0.6 against its first box for > `abandoned_seconds=10.0`). Polygon membership is a ray-casting test (`point_in_polygon`, `camera_agent.py:34-45`).
3. `ClipAnomalyScorer` (`camera_agent.py:118-161`), optional — CLIP ViT-B/32 zero-shot scoring: 3 "normal" prompts vs 5 "anomalous" prompts, anomaly score = softmax mass on the anomalous set.
4. `_emit_event()` (`camera_agent.py:298-312`) — writes an anonymised evidence JPEG via `core/privacy.py`, then publishes an `Event`.
5. Coordination: `_on_task_announce` bids, `_on_award` runs `_verify()` (`camera_agent.py:339-352`) which re-runs detection at `imgsz=960, conf=0.25` on `self._last_frame`.

**`aura_mas/agents/audio_agent.py` (223 lines)** — two backends selected by `backend={auto|yamnet|dsp}`:
- **YAMNet** (`audio_agent.py:121-135`): a local TensorFlow SavedModel fetched by `aura_mas/scripts/fetch_yamnet.py` (the `tensorflow_hub` URL is dead — HTTP 404, per `results/yamnet_integration_notes.md`). 521 AudioSet classes; `SURVEILLANCE_CLASSES` (`audio_agent.py:28-40`) maps 10 of them to 6 event types with per-class thresholds.
- **DSP fallback** (`DspAnomalyScorer`, `audio_agent.py:43-62`): rolling z-score of short-time energy and spectral flatness, normalised by `min(1.0, z/6.0)`, emitting a generic `audio_anomaly`.
- Scoring detail (`audio_agent.py:175-215`): YAMNet is fed a **lookback-extended window** (chunk + trailing half of the previous chunk) and **max-pooled** across internal frames, after mean-pooling on bare 1 s chunks was found to dilute short transients below threshold.

**`aura_mas/agents/fusion_agent.py` (121 lines)** — late fusion. Events are grouped into `Hypothesis` objects keyed by `f"{family}:{zone or 'site'}"` where `family` comes from `aura_mas/core/taxonomy.py`. Confidence is a reliability-weighted **noisy-OR**: `1 - Π(1 - w_m · c_e)` with `w_video=0.9, w_audio=0.7`, plus `+0.05` if more than one modality contributes and `+0.05` if more than one sensor contributes, clamped to 1.0 (`fusion_agent.py:77-93`). A 1 Hz `tick()` flushes hypotheses whose 6 s window has closed.

**`aura_mas/agents/coordinator_agent.py` (130 lines)** — single-round sealed-bid auction derived from the Contract Net Protocol. `needs_verification()` fires when fused confidence is in the gray zone `[0.35, 0.75)`. `_run_auction()` publishes a task, sleeps `bid_window=1.0` s, takes the max bid, publishes the award, then blocks up to 3 s on the verification topic. `mode` ∈ `{auction, roundrobin, off}`; `roundrobin` is the non-market ablation baseline.

**`aura_mas/agents/policy_agent.py` (127 lines)** — the only component allowed to create an `Alert`. `SEVERITY_MAP` assigns CRITICAL/WARNING/INFO per event type; `ALERT_THRESHOLDS = {CRITICAL: 0.45, WARNING: 0.55, INFO: 0.70}`. Verification adjusts confidence by `+0.15` (verified) or `−0.20` (refuted). A per-`(zone, event_type)` cooldown of 20 s implements hysteresis. **Every** decision, alert or suppression, is written to the audit stream.

**`aura_mas/agents/explanation_agent.py` (161 lines)** — a four-node state machine (`collect_evidence → describe → draft_report → guardrail_check`) over an OpenAI-compatible chat API. The **guardrail** (`explanation_agent.py:130-145`) rejects any draft whose `cited_evidence` set, or whose free-text `ev_[0-9a-f]{6,}` matches, are not a subset of the hypothesis's real event IDs. On any failure it falls back to a deterministic template.

**`aura_mas/eval/metrics.py` (183 lines)** — scores run JSONs. An alert matches a ground-truth entry if the **incident families match** and the alert's wall time falls in `[t_start − 5 s, t_end + 5 s]`. Reports precision/recall/F1, mean time-to-alert, false alerts per hour, coordination message count, mean allocation latency, wall seconds. `aggregate()` groups by `(scenario, mode, audio_backend)` and emits mean/standard deviation/n.

**`aura_mas/scenarios/replay.py` (205 lines)** — the experiment driver. Instantiates the whole stack from a JSON manifest and runs one of four modes: `mas-auction`, `mas-rules` (round-robin), `mas-nocoord` (coordination off), `centralized`. Key line: `realtime = mode != "centralized"` (`replay.py:108`).

**`aura_mas/scripts/run_campaign.py` (177 lines)** — the campaign grid driver. Runs each `(scenario, mode, vision_only, audio_backend, rep)` combination as a **fresh subprocess** with `--bus local`, resumes by skipping existing outputs, and aborts below a free-disk floor.

### 2.3 End-to-end data flow

```
video file ──► CameraAgent ──► Detection (site/{id}/detections, QoS 0)
                    │
                    └────────► Event (site/events, QoS 1) ──┐
audio file ──► AudioAgent ────► Event (site/events, QoS 1) ──┤
                                                             ▼
                                                       FusionAgent
                                            (noisy-OR, 6 s window, keyed by family:zone)
                                                             │ hypothesis flushed on tick
                                                             ▼
                                                        PolicyAgent
                                        ┌── gray zone? ──► CoordinatorAgent ──► auction
                                        │                        │ award
                                        │                CameraAgent._verify() (imgsz=960)
                                        │                        │ ±0.15 / −0.20
                                        ▼
                                 threshold + cooldown ──► Alert ──► AlertStore (JSONL)
                                        │                            │
                                        └──► audit record            └──► ExplanationAgent
                                                                          (guardrail → template)
                                                                              │
                                                                     Streamlit console
```

### 2.4 Models, data, and dependencies

| Layer | Model / asset | Provenance | Trained here? |
|---|---|---|---|
| Detection | YOLO11n (`yolo11n.pt`, 5.6 MB) | Ultralytics pretrained on COCO | No |
| Tracking | ByteTrack (`bytetrack.yaml`) | Ultralytics built-in | No |
| Semantic anomaly | CLIP ViT-B/32 | OpenAI pretrained | No |
| Audio | YAMNet SavedModel (`models/yamnet/`, gitignored) | fetched by `scripts/fetch_yamnet.py` | No |
| Explanation | OpenAI-compatible chat endpoint | external API | No |
| Video clips | AIRTLab violence, ABODA, plus 2 public pedestrian clips | `data/clips_real/manifest.json` `[not read — not staged]` | — |
| Audio clips | ESC-50 excerpts | same manifest | — |

**Zero model training happens anywhere in this project.** That is a defensible engineering choice for a one-month scope, and it is stated as such in `chapter3.tex:44`. It is also the single largest reason the work reads as systems engineering rather than machine-learning research.

Core dependencies (`requirements.txt`): numpy, opencv-python-headless, paho-mqtt, redis, streamlit, pytest, ultralytics, librosa, openai. Optional and **commented out**: `tensorflow-cpu`, CLIP, torch/torchvision, langgraph.

### 2.5 Evaluation infrastructure as built

- **9 scenario manifests** in `scenarios/`: `abandoned_object_01`, `audio_alarm_clock_01`, `audio_alarm_siren_01`, `audio_glass_break_01`, `combined_audio_video_01`, `demo_site_01`, `fight_01`, `intrusion_01`, `loitering_01`.
- **v2 campaign**: 373 runs, 0 failures (`results/evaluation_campaign_v2_notes.md`). 9 scenarios × 4 modes × {audio-visual, vision-only} × 5 repetitions = 300 runs; plus 6 audio-capable scenarios × 4 modes × 3 repetitions with the DSP backend = 72 runs.
- **Artefacts**: `results/summary.csv` (416 rows, one per run), `results/summary_agg.csv` (84 groups with mean/standard deviation), `results/campaign_log.csv`, `results/figures/*.png` (5 figures), and one `results/run_*.json` + `data/alerts_*.jsonl` + `data/audit_*.jsonl` per run.
- **Tests**: `aura_mas/tests/test_pipeline.py` — 6 offline unit tests (bus wildcards, noisy-OR monotonicity, auction best-bidder selection, policy threshold + cooldown, metric computation, guardrail hallucination probe). Runs in under a second with no models.

**This evaluation harness is the strongest asset in the repository.** It is more disciplined than most Master's-level work I review: fresh-subprocess isolation, resume-on-restart, repetition indices, a preserved v1 baseline CSV, and a written `results/methodology_changes.md` mapping every scoring-affecting change old→new. Credit where it is due.

---

## 3. What the thesis currently argues

Source: `AURA-MAS_Thesis_LaTeX/main.tex` + `Chapters/chapter{1..7,_sota}.tex`, compiled to a 53-page `main.pdf`.

### 3.1 Problem statement

From `chapter1.tex:19`: design, implement, and evaluate a multi-agent intelligent surveillance system for a **semi-closed site** in which autonomous perception agents detect events from video and audio at the edge, coordinate to corroborate and actively verify uncertain detections, apply deterministic auditable alerting policies, and generate grounded natural-language explanations for a human operator, all under privacy-by-design constraints.

### 3.2 Research questions (`chapter1.tex:24-30`)

- **RQ1 (Architecture)** — does a distributed hierarchical MAS improve time-to-alert and scalability over a centralized sequential pipeline?
- **RQ2 (Coordination)** — does auction-based verification task allocation improve alert precision versus uncoordinated alerting, and at what communication cost?
- **RQ3 (Multimodality)** — does fusing audio with video increase detection confidence and reduce false alerts versus vision-only?
- **RQ4 (Agentic explanation)** — can an LLM layer generate explanations provably free of fabricated references without influencing or delaying the alert decision?
- **RQ5 (Governance)** — can the pipeline run under privacy-by-design constraints while remaining useful?

### 3.3 Claimed contributions (`chapter1.tex:36-42`)

- **C1** — three-layer architecture, seven agent roles, formal message schema, MQTT/Redis substrate.
- **C2** — single-round auction active-verification protocol derived from the Contract Net Protocol.
- **C3** — reliability-weighted noisy-OR multimodal late fusion with a monotonicity guarantee.
- **C4** — decision-decoupled, evidence-grounded agentic explanation layer with a mechanical guardrail.
- **C5** — reproducible system-level evaluation methodology and a four-way architectural ablation.

### 3.4 Methodology and evaluation strategy as written

`chapter6.tex:12` argues that model-centric metrics (mAP, HOTA) characterise components rather than systems, and that architectures should be compared by **scenario replay**: recorded sources replayed at real-time pacing through the full stack, with alerts scored against a ground-truth manifest. Four variants "differing only in architecture — identical models, rules, thresholds, and inputs" (`chapter6.tex:20`).

### 3.5 Results as currently written in the manuscript

`chapter6.tex:41-55`, Table `tab:ablation`, single scenario `demo_site_01`:

| Mode | F1 | Precision | Recall | Mean TTA (s) | FA/h | Coord. msgs |
|---|---|---|---|---|---|---|
| Centralized | 0.667 | 0.667 | 0.667 | 21.6 | 67.9 | 0 |
| MAS-nocoord | 0.571 | 0.500 | 0.667 | 13.3 | 107.5 | 0 |
| MAS-rules | 0.571 | 0.500 | 0.667 | 13.3 | 106.9 | 4 |
| MAS-auction | **0.667** | **0.667** | 0.667 | 13.8 | **53.6** | 10 |

The narrative built on this (`chapter6.tex:73-88`, repeated in `chapter7.tex:8`): MAS is ≈36–38 % faster to alert; auction coordination halves false alerts and restores precision; audio fusion adds an otherwise-invisible incident; the guardrail yields zero uncaught hallucinated citations; the privacy pipeline holds.

---

## 4. The central problem: the manuscript and the data no longer agree

This is the finding that dominates everything else, so it goes first.

The numbers in `chapter6.tex` come from **one run of one scenario** executed by a prior automated session (documented in `STATE_NOTES.md:19-25` and acknowledged in `EXECUTION_PLAN.md §1` and `research/.../findings/F6`). The project has since run a 373-run campaign that **contradicts the manuscript's conclusions**. The team knows this — `THESIS_REPATCH.md` is an unapplied worklist that says so — but the thesis PDF a jury would read still contains the old story.

Computed directly from `results/summary_agg.csv` (audio-visual runs, `audio_backend=auto`, mean F1 over 5 repetitions per cell):

| Scenario | centralized | mas-nocoord | mas-rules | mas-auction |
|---|---|---|---|---|
| abandoned_object_01 | **0.667** | 0.534 | 0.200 | 0.200 |
| audio_alarm_clock_01 | **1.000** | **1.000** | **1.000** | **1.000** |
| audio_alarm_siren_01 | 0.200 | 0.600 | **0.800** | **0.800** |
| audio_glass_break_01 | 0.000 | **0.800** | **0.800** | **0.800** |
| combined_audio_video_01 | **0.467** | 0.400 | 0.200 | 0.100 |
| demo_site_01 | 0.773 | **0.781** | 0.629 | 0.667 |
| fight_01 | **1.000** | 0.800 | 0.400 | 0.200 |
| intrusion_01 | **0.567** | 0.280 | 0.380 | 0.300 |
| loitering_01 (true-negative probe) | 0.000 | 0.000 | 0.000 | 0.000 |
| **Mean over all 9** | 0.519 | **0.577** | 0.490 | **0.452** |

**The auction — contribution C2, the thesis's flagship mechanism — has the lowest mean F1 of the four modes.** The centralized baseline wins outright on 6 of 9 scenarios. `mas-nocoord` (coordination disabled) beats both coordinated modes on average. Excluding the deliberately-empty `loitering_01` probe, the ordering is unchanged: nocoord 0.649 > centralized 0.584 > rules 0.551 > auction 0.508 (these are the numbers in `results/evaluation_campaign_v2_notes.md`, and I reproduced them independently from the CSV).

`THESIS_REPATCH.md` handles this honestly but partially: it tells the writer that "the v2 numbers do not support this narrative and it needs rethinking, not renumbering", and proposes a **stability** story instead (auction has precision 0.667 ± 0.0 while nocoord is 0.767 ± 0.224). That reframing is defensible but it is not yet in the thesis, and on its own it is a weak contribution claim — "our mechanism is worse on average but has lower variance" needs a much stronger argument about why variance matters operationally, backed by a proper statistical test.

**Bottom line for §4:** the thesis as compiled today asserts conclusions its own experiments refute. This is the single highest-severity finding in the audit. It is fixable — the data to write a better, more honest chapter 6 already exists — but it must be fixed before any defence.

---

## 5. Honest assessment: negative findings

Ordered roughly by severity. Each is grounded in a file.

### 5.1 The centralized baseline is confounded — RQ1 does not measure what it claims

`replay.py:108`: `realtime = mode != "centralized"`.

- In MAS modes, `CameraAgent.run()` sleeps to pace playback to source frame rate (`camera_agent.py:242-247`), so wall-clock time ≈ video time.
- In `centralized` mode, agents run **unpaced** (as fast as the CPU allows) and **sequentially** (`replay.py:139-141`: `th.start(); th.join()` per sensor).

Time-to-alert is then measured as `alert_wall_time − t_scenario_start` and compared against ground-truth timestamps expressed in **video** time (`metrics.py:46-51`). The two modes therefore use incompatible time bases. Worse:

- `FusionAgent.window_seconds = 6.0` is a **wall-clock** window (`fusion_agent.py:68`, `tick()` uses `now_ts()`). Under unpaced centralized replay, 6 wall-seconds cover far more scene content than under paced MAS replay, so hypothesis grouping differs between modes.
- `PolicyAgent.cooldown_seconds = 20.0` is likewise wall-clock (`policy_agent.py:73`). In a compressed centralized run, a 20 s cooldown can swallow most of the scenario, changing the false-positive count for reasons unrelated to architecture.

The thesis states the variants differ "only in architecture — identical models, rules, thresholds, and inputs" (`chapter6.tex:20`). That is **false as implemented**: they also differ in pacing policy, in stream sequencing, and consequently in the effective temporal width of the fusion window and cooldown. RQ1's headline result is therefore not attributable to architecture.

Additionally, a real centralized video-management-system baseline does not process streams one-after-another to completion; it ingests them concurrently at real time. The "sequential" baseline is a strawman that guarantees the MAS wins on latency by construction.

### 5.2 The evaluation metric cannot distinguish event types — and on the flagship scenario it is nearly degenerate

`metrics.py:41-45` matches an alert to ground truth when their **incident families** are equal. From `core/taxonomy.py:14-21`, the family map assigns `intrusion → security`, `loitering → security`, `abandoned_object → security`, `audio_glass_break → security`.

On `demo_site_01` — the scenario the entire chapter 6 is built on — **all three ground-truth entries are in the `security` family**. So an `intrusion` alert can satisfy the `loitering` ground truth, and vice versa. The metric measures "did some security-ish alert occur near this time", not "did the system detect the right thing".

The tolerance compounds this. Matching accepts `[t_start − 5, t_end + 5]`. For `demo_site_01`'s intrusion ground truth `[3, 35]`, that is an acceptance window of `[−2, 40]` on a 55-second scenario — **73 % of the run**. Precision, recall, F1 and mean time-to-alert computed over such a window carry very little information.

The greedy, ground-truth-order-dependent matching is separately documented by the team in `results/evaluation_campaign_v2_notes.md` as under-crediting successful fusion on `combined_audio_video_01`. That is a real observation, but it is a symptom of the same root cause: the matcher is a first-fit loop (`metrics.py:40-52`), not an optimal assignment.

### 5.3 `demo_site_01` still contains a ground-truth event the project has proven is undetectable

`scenarios/loitering_01.json`'s `notes` field records an empirical check: across all available clips, the longest continuous single-track presence is **5.5 s**, below `ZoneRuleEngine.loiter_seconds = 8.0`. The note concludes that `demo_site_01`'s loitering ground-truth claim at `t = 16–46 s` "was never actually empirically verified" and is almost certainly why every mode shows exactly one false negative.

`scenarios/demo_site_01.json` **still declares that loitering ground-truth entry.** I confirmed the consequence in `results/summary.csv`: of 60 `demo_site_01` rows, 48 have `fn = 1`, 1 has `fn = 2`, 11 have `fn = 0`, with `gt_events = 3` throughout.

So the flagship scenario carries a known-false annotation that mechanically caps recall at 2/3, and the resulting F1 numbers are printed in the thesis. Either the annotation must be removed (and every number regenerated) or its falsity must be stated explicitly in the manuscript.

### 5.4 The auction's bid function does not do what the thesis says it does

`chapter4.tex:104` describes the bid as `u = b · κ · o` where `o ∈ [0,1]` is "field-of-view overlap with the event zone".

`camera_agent.py:315-320`:

```python
overlap = task.get("fov_overlap", {}).get(self.agent_id, 0.5)
```

`CoordinatorAgent.request_verification()` (`coordinator_agent.py:54-59`) builds the task dictionary with keys `task_id, type, hypothesis_id, event_type, zone, origin_sensor, timestamp`. **It never sets `fov_overlap`.** Therefore `o` is the constant `0.5` for every camera in every run in the entire campaign.

The bid reduces to `base × capacity`, i.e. `0.3` for the originating sensor and `1.0` for any other idle camera. With two cameras, the auction deterministically picks "the other camera" — which is exactly what round-robin does. The thesis's central claim for C2, that "*who* verifies matters more than *that* verification happens" (`chapter6.tex:101`), is therefore **untestable with the current code**: the mechanism that would make it true was never wired up.

This also explains, mechanistically, why `mas-auction` and `mas-rules` produce nearly identical results in the v2 data.

### 5.5 Verification verifies the wrong frame

`camera_agent.py:339-352`: `_verify()` operates on `self._last_frame`, the most recently read frame. The hypothesis being verified was formed from events up to 6 s earlier, plus a 1 s bid window and fusion tick latency. Under real-time pacing the verified frame is typically several seconds after the incident, and the target may have left the scene.

Compounding this, `self._last_frame` is written by the camera thread (`camera_agent.py:240`) and read by the coordinator's callback thread with **no synchronisation** — a data race. In CPython this will not corrupt memory, but it means the verification can read a frame from an arbitrary point relative to the event.

`_verify()` also only counts `person` detections and returns `max(conf) > 0.4` regardless of the hypothesis's event type — so verifying an `abandoned_object` or `audio_alarm` hypothesis asks "is there a person in the current frame", which is not evidence about that hypothesis at all.

### 5.6 On `LocalBus`, the measured "coordination overhead" is an artefact, not a cost

Every campaign run used `--bus local` (`run_campaign.py:100-101`). `LocalBus.publish()` (`bus.py:147-156`) invokes subscriber callbacks **synchronously in the publisher's thread**. Consequences:

- Bids are collected during `self.bus.publish(TOPIC_TASKS, ...)` and are already in `self._bids` *before* `time.sleep(self.bid_window)` executes (`coordinator_agent.py:88-90`). The 1-second bid window is therefore **pure dead latency with no function**.
- The award publish runs `CameraAgent._on_award` → `_verify()` → YOLO inference synchronously inside the coordinator's call, so `_await_verification`'s 3 s timeout can never fire.
- The reported `coord_messages` count is a count of in-process Python function calls. It says nothing about network bandwidth, MQTT quality-of-service overhead, or broker load.

So the thesis's quantified "communication cost" for RQ2 is not a communication cost. And since the MQTT and Redis paths were never exercised in any reported result, **contribution C1's substrate claim is entirely unevaluated**.

### 5.7 Statistics: N = 5 with standard deviations of 0.45 is not a result

In `results/summary_agg.csv`, many cells read `f1_mean = 0.8, f1_std = 0.447` or `0.2 ± 0.447`. With 5 repetitions those values arise from a per-run F1 that is either 1.0 or 0.0 — a **binary flip**, not a distribution. Reporting a mean and standard deviation over a Bernoulli outcome with n = 5 is not informative, and no confidence interval, significance test, or effect size appears anywhere in `results/` or in the chapters.

Specific gaps:
- No random seed control anywhere. `run_campaign.py:6-8` mentions `PYTHONHASHSEED` in a docstring but never sets it. No `torch.manual_seed`, no `torch.set_num_threads(1)`, no `numpy.random.seed`. `CLAUDE.md` acknowledges "real run-to-run non-determinism" and prescribes N ≥ 3 as a workaround rather than fixing the cause.
- No paired test across modes on the same scenario/repetition, which is the natural design here (a Wilcoxon signed-rank test or a bootstrap confidence interval on the paired difference).
- The DSP ablation uses N = 3 while the headline uses N = 5, so the two are not directly comparable.

### 5.8 `false_alerts_per_hour` is degenerate at these run lengths

`metrics.py:60,76`: `hours = wall_seconds / 3600`; `false_alerts_per_hour = fp / hours`. Several scenarios have `wall_seconds ≈ 10`. One false positive in a 10-second run extrapolates to **360 false alerts per hour**. `results/summary_agg.csv` duly contains values like `377.3` and `358.8`. These are arithmetic artefacts of dividing a count of 0, 1 or 2 by a very small denominator; they are not operational false-alarm rates, and they are plotted in `results/figures/fig_system_metrics.png`.

### 5.9 The evidence base for RQ4 is a unit test, not an experiment

`ExplanationAgent` is instantiated only when `use_llm=True` (`replay.py:90`). `run_campaign.py` never passes `--llm`. `results/explanation_eval_notes.md` states there was no LLM key in the environment and evaluates the **template fallback**.

So across all 373 runs, the LLM path never executed. The claim in `chapter6.tex:86` — "in replay runs, all accepted reports cited only identifiers present in the event log, i.e. zero uncaught hallucinated citations" — is vacuously true: no report was ever generated by a model. The only real evidence for C4 is `test_pipeline.py:149-173`, a single unit test with one hand-written fabricated identifier.

A guardrail that has never been attacked by an actual generative model has not been evaluated. This is the weakest empirical link in the thesis, and it supports one of the five headline contributions.

### 5.10 Fusion model: the "guarantee" is a limitation, and the parameters are unjustified

The noisy-OR (`fusion_agent.py:77-93`) assumes **conditional independence** of evidence. In this system, repeated events from the same camera watching the same incident are strongly dependent, yet each multiplies into the product. `combined_audio_video_01` produces 9 video events from one camera; the fused confidence saturates near 1.0 regardless of whether the incident is real.

The thesis presents monotonicity as a formal virtue (`chapter4.tex:95`, "additional supporting evidence never decreases confidence"). Mechanically, monotonicity means the fusion layer **cannot represent disconfirming evidence at all**. The only downward adjustment in the whole pipeline is the coordinator's `−0.20`.

The `+0.05` corroboration bonuses (`fusion_agent.py:89-92`) break the probabilistic interpretation of the noisy-OR — the output is no longer a probability under any model — and every constant in the decision path is a magic number with no derivation, no calibration, and no sensitivity analysis:

`w_video=0.9, w_audio=0.7, β_mod=β_sen=0.05, window=6.0 s, gray zone=[0.35,0.75), thresholds 0.45/0.55/0.70, cooldown=20 s, verification ±0.15/−0.20, tolerance=±5 s, loiter=8 s, abandoned=10 s, IoU=0.6, infer_fps=5, YOLO conf=0.35, verify conf=0.25/imgsz=960, YAMNet per-class thresholds 0.2–0.3.`

That is more than twenty free parameters governing every reported number, none of them tuned on a held-out split, none subjected to a sweep except the CLIP anomaly threshold (`results/clip_anomaly_threshold_sweep.csv`).

### 5.11 CLIP is worse than random and the thesis does not say so

`results/clip_anomaly_calibration_notes.md` reports **AUC = 0.308** for the zero-shot CLIP anomaly scorer, root-caused to a prompt/scene domain mismatch (the `NORMAL_PROMPTS` in `camera_agent.py:125-128` describe indoor warehouse scenes; the test clips are outdoor street footage). An AUC below 0.5 means the scorer is anti-correlated with the label.

`THESIS_REPATCH.md` confirms no chapter mentions this: no `AUC` or `calibrat` hit exists in `AURA-MAS_Thesis_LaTeX/Chapters/*.tex`. `chapter5.tex:67` and `chapter7.tex:6` describe `ClipAnomalyScorer` as a working system component. Presenting a component measured worse than chance without disclosing the measurement is the kind of omission that a jury treats as an integrity problem rather than a technical one.

### 5.12 Reproducibility problems

- **No dependency lock.** `requirements.txt` uses `>=` bounds only; the heavy dependencies that actually determine results (`tensorflow-cpu`, CLIP, torch) are commented out. There is no `requirements-full.txt` despite `README.md` referencing one — `[not found in repo]`.
- **No packaging.** No `pyproject.toml` or `setup.py` for `aura_mas`; the package only imports from the repository root.
- **No environment capture in results.** `results/env/pip-freeze-{pre,post}-tf.txt` exist but are not linked to individual runs; run JSONs record no library versions, no hardware, no seed.
- **`configs/` does not exist**, although `README.md`'s repository layout, `chapter5.tex:50`, and `CLAUDE.md` all describe it. Zone geometry and thresholds live inline in `scenarios/*.json`. `aura_mas/configs/` exists but is empty.
- **Stale duplicates at the repository root.** `camera_agent.py`, `audio_agent.py`, `fusion_agent.py`, `bus.py`, `metrics.py`, `replay.py`, `app.py`, `base.py`, `privacy.py`, `policy_agent.py`, `coordinator_agent.py`, `explanation_agent.py`, `test_pipeline.py`, `make_figures.py` all exist twice. `results/methodology_changes.md` confirms the root copies now hold **pre-fix** logic. A reader who clones this repository and runs `python camera_agent.py` gets the old, buggy version.
- **Two LaTeX trees.** Root-level `main.tex` + `chapter*.tex` are a failed build (`main.pdf` there is a 15-byte stub); the real manuscript is `AURA-MAS_Thesis_LaTeX/`. Both are on disk.

### 5.13 Bibliography integrity

94 entries in `Bibliography/bibliography.bib`. `research/.../findings/F5` documents that the bibliography and `chapter_sota.tex` were generated by a prior automated session, that 6 of 94 entries were spot-checked, and that concrete errors were found in that sample: author fields with affiliation text merged into names (`"Abbeel, OpenAI Pieter"`, `"Moritz, Philipp reinforcement learning"`), truncated author lists, a paraphrased title (Hawk), and at least one wrong year (Murakkab listed as 2024; the arXiv identifier 2508.18298 is August 2025).

**88 entries remain unverified.** I additionally found 16 entries carrying neither a DOI nor a URL: `rashid2018qmix, lowe2017multiagent, terry2021pettingzoo, liang2018rllib, light2017mosquitto, smith1980contract, wooldridge2009introduction, rao1995bdi, zhang2022bytetrack, radford2021clip, sultani2018ucfcrime, parker2002alliance, euaiact2024, gdpr2016, hershey2017cnn, yao2023react`. Several of those are the load-bearing citations for the thesis's core claims (Contract Net, ByteTrack, CLIP, the EU AI Act).

### 5.14 Authorship

`EXECUTION_PLAN.md §0`: the compiled `main.pdf` carries the name **"BELMANA Soufyane"** and supervisor **"Pr. AMAR BENSABER Djamel"**, inherited from the template. `AURA-MAS_Thesis_LaTeX/Master_BELMANA_Soufyane.pdf` (3.5 MB) is the source template thesis, still in the tree. This is flagged as open in `EXECUTION_PLAN.md §4` as of the latest edit. It is a five-minute fix and a zero-tolerance one.

### 5.15 Smaller but real

- `chapter5.tex:6` and `chapter7.tex:8` claim "approximately 2,500 lines" of Python. Summing `aura_mas/**/*.py` file sizes gives roughly 130 KB of source across ~25 modules; a line count was not computed, so treat the 2,500 figure as `[uncertain]` until verified with `cloc`.
- `chapter1.tex:37` and `chapter4.tex` Table `tab:agents` claim **seven agent roles**. Six are implemented as agents; the seventh row is "Operator console", a Streamlit page, not an agent.
- `docker-compose.yml` runs Mosquitto with `mosquitto-no-auth.conf` and Redis with no password, both on host ports. For a system whose thesis argues about governance and the EU AI Act, an unauthenticated broker carrying event and alert traffic is a contradiction worth naming.
- `AlertStore.audit()` (`bus.py:230`) derives the audit path by `self._jsonl_path.replace("alerts", "audit")` — a substring replacement that silently misbehaves for any path containing "alerts" elsewhere.
- `ZoneRuleEngine._fired`, `_dwell` and `_static_objects` (`camera_agent.py:57-59`) grow without bound; there is no track eviction. Harmless for 60-second clips, a leak for continuous operation — which is the deployment mode the thesis argues for.
- `replay.py:96-101` monkey-patches `store.append` to capture timing. Functional, but it means the measured path differs from the production path.
- `Event.from_json` (`bus.py:65-67`) is `Event(**json.loads(s))`, which raises on any unknown field — the schema cannot evolve without breaking the 400+ archived run artefacts.
- The **loitering** rule has never fired on any real clip in the corpus, and **abandoned object** is exercised by exactly one scenario. Two of the three zone rules are effectively unvalidated.
- `AudioAgent` DSP mode scores `f1 = 0.000 ± 0.000` on every audio-only scenario by construction (its generic `audio_anomaly` label maps to family `violence_or_hazard`, never matching a `security`/`hazard` ground truth). This is presented as "the most quantitatively dramatic result in the v2 campaign" (`results/evaluation_campaign_v2_notes.md`). It is not an empirical finding about DSP versus deep audio classification — it is a **label-space mismatch**. A DSP detector that fires perfectly on the transient still scores zero. The comparison is not measuring detection quality.

---

## 6. What went right

An audit that lists only defects is a bad audit. Genuinely strong elements:

1. **The bug-hunting discipline is exceptional.** `results/evaluation_campaign_notes.md`, `results/yamnet_integration_notes.md`, and `results/methodology_changes.md` document real, subtle, pre-existing defects found and fixed with before/after evidence: wall-clock versus video-time rule evaluation; synthetic placeholder clips YOLO could never detect a person in; a dead `tensorflow_hub` URL masked by a silent `except Exception`; mean-pooling diluting short audio transients (0.069 versus 0.75 confidence on the same clip); a missing `zone` field structurally blocking cross-modal corroboration. Most theses at this level never find a single bug of that class.
2. **Refusal to tune away inconvenient results.** `results/methodology_changes.md` has an explicit "Explicitly NOT changed" section listing parameters left alone precisely because adjusting them would have improved the target scenarios while silently moving everything else. That is correct scientific practice and rare.
3. **The v1 baseline is preserved, not overwritten** (`results/summary_v1_dsp_baseline.csv`), and `rep=None` rows are excluded from aggregation with a written justification (`metrics.py:84-100`).
4. **The prior-work positioning study** (`research/aura-mas-landscape-positioning/`, 6 findings, 20 source summaries) is better than the related-work sections of most submitted theses, and it correctly concludes that "agents cooperate to surveil a place" is not novel (finding F4: Monitorix, 2000) and that novelty must rest on a specific named mechanism.
5. **The architecture itself is sound and well-motivated.** Decision/generation decoupling — a deterministic policy engine holding exclusive alerting authority with the LLM strictly downstream — is a genuinely good pattern and is, as far as the survey material shows, not standard in the LLM-video-agent literature.
6. **Graceful degradation is designed in throughout**, and the fallback paths are real, not aspirational.

---

## 7. Positioning against the current state of the art

I searched the current literature (August 2026) to place this work. Summary of what comparable systems do that AURA-MAS does not.

### 7.1 Video anomaly detection

The field is now dominated by three lines the thesis names but does not compete with:

- **Weakly-supervised VAD** on UCF-Crime and XD-Violence, reported as frame-level AUC and Average Precision. This is the standard currency of the field. AURA-MAS reports **no number on any public benchmark**.
- **CLIP-based zero-shot / weakly-supervised VAD** (VadCLIP, AVadCLIP). AURA-MAS's `ClipAnomalyScorer` is a hand-written prompt-comparison proxy of this family that measures AUC = 0.308 — that is, worse than chance — on the project's own clips.
- **Explainable MLLM-based VAD.** Holmes-VAD and Holmes-VAU (CVPR 2025 Highlight) do instruction-tuned, multi-granularity anomaly *understanding* with generated explanations, evaluated on purpose-built instruction datasets. This is contribution C4's territory, done at scale with real evaluation. AURA-MAS's explanation layer has never been run with a model.
- **Agentic VAD** is now an explicit research topic ("Glance, Scrutinize, and Think: Advancing Video Anomaly Detection from Training-Free to Agentic Reasoning", 2026), and a 2026 survey catalogues agentic/LLM multimodal anomaly-detection architectures into detection-only, reasoning, tool-using, and planner agents, naming systems such as ARGOS, AD-AGENT, SentinelAgent, AnomalyRuler and Audit-LLM. **AURA-MAS's related-work chapter predates and does not cite this taxonomy**, which means the thesis cannot currently say where it sits in it.

### 7.2 Evaluation methodology

`chapter3.tex:40` claims that "for system-level evaluation, no standard benchmark exists that combines multi-sensor streams with ground-truth incident annotations". That claim is now weak:

- **"Rethinking Metrics and Benchmarks of Video Anomaly Detection" (2025)** identifies exactly the problems this thesis has — annotation bias (measured by Fleiss' kappa, 0.51–0.68 across datasets), latency insensitivity, and scene overfitting — and proposes concrete instruments: annotation-averaged AUC/AP, **Latency-aware Average Precision (LaAP)** with time-decaying recall weights, and hard-normal benchmarks (UCF-HN, MSAD-HN). AURA-MAS's "mean time-to-alert" is a naive ancestor of LaAP; adopting LaAP would give the latency claim a citable, comparable metric.
- **Multi-camera benchmarks exist**: MTMMC (large-scale real-world multi-modal multi-camera tracking), the AI City Challenge 2026 Track 1 (multi-camera 3D perception), and the collaborative-perception line (V2X-Sim and successors) which reports **communication cost in bytes against accuracy** — precisely the trade-off RQ2 claims to study but measures in in-process function calls.
- **Audio-visual violence detection** on XD-Violence is an established benchmark with Average Precision leaderboards, including lightweight frameworks (AVAR-Net, 2025). RQ3 could be evaluated there against published numbers instead of on three self-authored audio clips.

### 7.3 Coordination

Contract-Net-style auctions are a 1980 mechanism. The modern comparison set is: consensus-based bundle algorithms for multi-robot task allocation, submodular sensor selection, task-oriented communication under bandwidth constraints, and MARL (QMIX, MADDPG) with standardised environments. The thesis correctly argues MARL is unsuitable for a certifiable system — but the argument would be far stronger if the auction were compared against **at least one non-trivial alternative allocator** (greedy-by-utility, Hungarian assignment, or a consensus scheme) rather than only against round-robin and no coordination. As implemented (§5.4), the auction is not even distinguishable from round-robin.

### 7.4 Where the work genuinely is competitive

Two things in this project are not standard in the surveyed literature and are worth defending as the actual contribution:

1. **Architectural decoupling of the generative layer from the safety-critical decision**, with a mechanical evidence-citation guardrail and a deterministic fallback. The 2026 agentic-anomaly-detection survey lists reliability and trustworthiness as open challenges; most surveyed systems use the LLM either as the detector or as an unchecked narrator. This is a real, transferable pattern — it just needs to actually be evaluated against a real model.
2. **A reproducible, subprocess-isolated, multi-repetition system-level ablation harness with a documented methodology-change log.** The evaluation *infrastructure* is better than the evaluation *results*. That infrastructure, generalised and released, is a legitimate contribution in a field the same literature says suffers from evaluation-standardisation problems.

Everything else in the contribution list — hierarchical MAS for surveillance (Monitorix, 2000), auction task allocation (Smith, 1980), noisy-OR late fusion, YOLO + ByteTrack + zone rules — is well-trodden ground and cannot carry novelty on its own.

---

## 8. Verdict

**As an engineering artefact:** solid, honest, better-instrumented than typical Master's work, with a genuinely good architectural idea at its centre.

**As a thesis in its current state:** not defensible. The manuscript asserts conclusions that its own most recent experiments refute (§4); the primary architectural comparison is confounded (§5.1); the metric on the flagship scenario is close to degenerate (§5.2); the flagship scenario contains a ground-truth entry the team has proven is wrong (§5.3); the mechanism behind the flagship contribution was never wired up (§5.4); one of five contributions has no empirical evidence at all (§5.9); a component measured worse than chance is described as working (§5.11); and 88 of 94 citations are unverified (§5.13).

None of these are fatal. All are fixable, several in hours. `02-gaps-and-recommendations.md` lists them as ranked, costed work.
