# One-Month Execution Schedule — AURA-MAS PFE

**Format:** 4 weeks × 7 days, ~6-8 h/day. Each task has an ID, an exit criterion, and a thesis artifact it produces. The plan is deliberately front-loaded: a working end-to-end skeleton exists by Day 5, so every later day only *improves* something that already runs.

**Golden rule:** never spend more than one day blocked on a single component. Every component has a listed fallback.

---

## Week 1 — Scope freeze, skeleton, and perception baseline (Days 1-7)

| Day | ID | Task | Exit criterion | Thesis artifact |
|---|---|---|---|---|
| 1 | W1.1 | Scope freeze: adopt title, architecture, non-goals; set up Git repo, Python env, folder layout; install Ultralytics, paho-mqtt, redis, streamlit; run Mosquitto + Redis via Docker Compose | `docker compose up` runs broker + Redis; repo pushed | Chapter 1 problem statement |
| 1 | W1.2 | Download test assets: 10-15 UCF-Crime clips (or Avenue), 2-3 normal CCTV clips, a handful of ESC-50/UrbanSound8K audio clips (glass break, scream, alarm) | `data/` populated with manifest.json | Section on datasets |
| 2 | W1.3 | CameraAgent v0: read video file → YOLO11n detect (person/vehicle) → ByteTrack IDs → publish JSON detections on MQTT topic `site/cam/{id}/detections` | Live MQTT messages visible with `mosquitto_sub` | Design chapter, agent spec |
| 3 | W1.4 | Zone rules in CameraAgent: polygon zones (restricted area, entry), dwell time, line-crossing, abandoned-object heuristic; publish `zone_event` messages | Scripted clip triggers intrusion + loitering events | Methodology: rule perception |
| 4 | W1.5 | AudioAgent v0: chunk audio → log-mel spectrogram → YAMNet (TF-Hub) or pretrained PANNs → publish `audio_event` with class + score. Fallback: energy + spectral-flatness anomaly score | Scream/glass-break clip produces audio events | Methodology: audio branch |
| 5 | W1.6 | FusionAgent v0 + PolicyAgent v0: subscribe all events, sliding-window fusion keyed by (zone, time), simple threshold policy → publish `alert` to Redis Stream `alerts` | End-to-end: video in → alert in Redis. **MILESTONE M1: skeleton runs end-to-end** | System integration section |
| 6 | W1.7 | Streamlit dashboard v0: live alert feed from Redis, evidence thumbnail, acknowledge button writing to audit log (SQLite) | Demo-able UI | Screenshots for thesis |
| 7 | W1.8 | Buffer + write-up: document message schemas (detection/track/event/alert JSON), draw architecture diagram, start `thesis/chapter drafts` | Schemas doc committed | Design chapter figures |

## Week 2 — Anomaly detection, multimodal fusion, coordination (Days 8-14)

| Day | ID | Task | Exit criterion | Thesis artifact |
|---|---|---|---|---|
| 8 | W2.1 | Video anomaly scoring: CLIP-based zero-shot anomaly scorer (frame embedding vs. text prompts "normal warehouse scene" / "people fighting" / "fire and smoke"…) as lightweight VadCLIP-style proxy; integrate into CameraAgent | AUC computed on a small UCF-Crime subset | SOTA + methodology |
| 9 | W2.2 | Calibrate + evaluate anomaly branch: threshold sweep, per-class scores, false-positive analysis on normal clips | Metrics table (AUC/AP) saved by script | Results chapter table |
| 10 | W2.3 | Late audio-visual fusion in FusionAgent: confidence-weighted score combination with modality reliability weights; hysteresis to suppress flicker | Fusion beats vision-only on ≥1 scripted scenario (fewer false alerts) | Results: fusion ablation |
| 11 | W2.4 | CoordinatorAgent + auction protocol: on suspicious hypothesis, announce verification task; CameraAgents bid (view score = overlap of track with FOV × idle capacity); winner performs high-res re-check (larger model or zoomed crop re-inference) | Logged auction rounds: announce → bids → award → verification result | Coordination chapter core |
| 12 | W2.5 | Rule-based scheduler baseline (round-robin/static assignment) for comparison; instrument message counts, assignment latency, task completion | Comparison script produces coordination metrics CSV | Ablation: auction vs rules |
| 13 | W2.6 | Multi-camera scenario pack: build 6 scripted scenarios (intrusion, loitering, abandoned object, fight clip, audio-only glass break, combined audio+video) with ground-truth event timestamps in JSON | `scenarios/` with GT manifests; replay tool runs them | Evaluation protocol section |
| 14 | W2.7 | **MILESTONE M2: coordinated multi-agent demo** — 3 CameraAgents + 1 AudioAgent + coordination live on scenario replay; record screen demo | Recorded video + metrics | Demo + defense material |

## Week 3 — Agentic explanation layer, privacy, evaluation campaign (Days 15-21)

| Day | ID | Task | Exit criterion | Thesis artifact |
|---|---|---|---|---|
| 15 | W3.1 | ExplanationAgent v1: LangGraph-style state graph (collect evidence → describe frames with VLM → draft report → guardrail check → emit). Use GPT-4o-mini/Qwen2.5-VL API on evidence keyframes; strict JSON schema output | Alert in dashboard shows structured incident report w/ evidence links | Agentic AI chapter |
| 16 | W3.2 | Guardrails + hallucination control: report must cite only supplied evidence IDs; contradiction check vs. PolicyAgent decision; fallback template if LLM unavailable | Guardrail test suite passes (fabricated-evidence probe rejected) | Ethics/safety section |
| 17 | W3.3 | Privacy layer: face/person blurring (YOLO person boxes → Gaussian blur) on all exported evidence; retention config; role note in audit log; document EU AI Act / CNIL mapping table | Evidence images anonymized by default | Governance chapter |
| 18 | W3.4 | Centralized baseline: single monolithic process consuming all streams sequentially (same models); measure end-to-end latency, throughput, dropped frames vs. MAS at 1/2/4 cameras | Baseline metrics CSV | Core comparison (C1) |
| 19 | W3.5 | Full evaluation campaign: run all scenarios × {centralized, MAS-rules, MAS-auction} × {vision-only, audio-visual}; compute detection F1, time-to-alert, false alerts/hour, message overhead | `results/` with all CSVs + plots (matplotlib) | Results chapter complete data |
| 20 | W3.6 | Explanation quality eval: evidence-completeness checklist, hallucination rate on 20 alerts, small rubric-based usefulness rating | Explanation metrics table | Results (C4) |
| 21 | W3.7 | **MILESTONE M3: evaluation freeze.** Generate all final figures (architecture, sequence diagram, Gantt, results plots) | All figures in `thesis/Assets/` | Figures done |

## Week 4 — Thesis writing, polish, defense (Days 22-30)

| Day | ID | Task | Exit criterion |
|---|---|---|---|
| 22 | W4.1 | Chapters 1-2: General introduction + background (MAS, agentic AI, surveillance CV) — adapt from research reports | Drafts compiled in LaTeX |
| 23 | W4.2 | Chapter 3: State of the art (VAD, tracking, coordination, agentic frameworks, privacy) with the wide-research bibliography | SOTA chapter compiled |
| 24 | W4.3 | Chapter 4: System design and architecture (agents, protocols, schemas, privacy-by-design) | Design chapter compiled |
| 25 | W4.4 | Chapter 5: Implementation (stack, code structure, key algorithms, MLOps) | Implementation chapter compiled |
| 26 | W4.5 | Chapter 6: Evaluation and results (tables, ablations, error analysis, limitations) | Results chapter compiled |
| 27 | W4.6 | Chapter 7: Conclusion + future work; abstracts EN/FR/AR; acronyms; final bibliography pass | Full PDF compiles clean |
| 28 | W4.7 | **MILESTONE M4: thesis draft to supervisor.** Buffer for corrections | PDF sent |
| 29 | W4.8 | Defense slides (15-20) + live demo rehearsal + demo video backup | Slides + rehearsed demo |
| 30 | W4.9 | Final corrections, repo cleanup, README, reproducibility check (`docker compose up` + `make demo`) | Tagged release v1.0 |

---

## Risk fallback table

| Risk | Fallback (decide within 1 day) |
|---|---|
| YAMNet/TF install pain | Pure-librosa anomaly score (spectral flatness + energy z-score) — 2 h of work |
| CLIP anomaly AUC weak | Keep it as "semantic tagger", lean thesis contribution on zone rules + fusion + coordination |
| No GPU | YOLO11n CPU ≈ 10-20 FPS at 640px is fine for 3 simulated cameras from files |
| LLM API unavailable/cost | Template-based explanation generator + local Qwen2.5-VL-2B via Ollama, or rule-based NLG |
| Time crunch in Week 3 | Drop W3.6 (explanation eval) to a qualitative discussion; never drop W3.4/W3.5 |
| UCF-Crime download slow | Avenue dataset (2 GB) + self-recorded phone clips of scripted scenarios |

## Milestones summary

- **M1 (Day 5):** end-to-end skeleton (video → detection → fusion → alert → dashboard).
- **M2 (Day 14):** coordinated multi-agent demo with auction protocol on scenario replays.
- **M3 (Day 21):** evaluation frozen — all numbers and figures final.
- **M4 (Day 28):** complete thesis PDF to supervisor.
