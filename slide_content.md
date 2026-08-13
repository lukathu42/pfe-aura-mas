# AURA-MAS — Master's Thesis Defense Presentation

**Audience:** academic jury (president, examiner, supervisor, incubator representative) at Higher School of Computer Science, Sidi Bel Abbès (ESI-SBA).
**Duration target:** 15–20 minutes of speaking, 16 slides.
**Tone:** rigorous academic defense — every claim carried by a measured number, an equation, or an architectural argument.
**Visual style preference:** sober, professional, technical. Dark navy / slate primary with a single cyan-teal accent for emphasis and data highlights. Clean sans-serif typography. Diagrams and charts preferred over decorative imagery. Consistent footer with slide numbers.

---

## Slide 1 — Title

**AURA-MAS: Agentic and Multi-Agent Intelligent Surveillance**

Subtitle: A Privacy-Aware, Edge-First Hierarchical Multi-Agent System for Multimodal Event Detection, Inter-Sensor Coordination, and Explainable Alerting

- Master's Thesis (Projet de Fin d'Études) — Specialization: Intelligence Artificielle et Science de Données (IASD)
- Presented by: **BELMANA Soufyane**
- Supervisor: Pr. AMAR BENSABER Djamel
- Jury: Dr. BEZZAOUCHA Fatima Souad (President), Dr. CHIKH Asma (Examiner), Dr. ABDELHAK Soumia (Incubator Representative)
- Higher School of Computer Science 8 Mai 1945, Sidi Bel Abbès — Academic Year 2025/2026

Visual note: institutional title slide, ESI-SBA logo, no chart.

---

## Slide 2 — Surveillance has scaled its cameras, not its capacity to watch them

Central idea: the operating paradigm of video surveillance is three decades old and structurally broken.

- Hundreds of millions of cameras are deployed worldwide, yet the dominant topology is unchanged: all streams converge on a control room where a handful of operators watch dozens of screens.
- Human sustained attention across multiple feeds degrades within minutes; the camera-to-operator ratio makes exhaustive monitoring physically impossible.
- Consequence: most footage is examined only *after* an incident — surveillance operates forensically rather than preventively.
- The first generation of "intelligent" analytics improved *detection* (YOLO-class detectors, weakly-supervised video anomaly detection on UCF-Crime) but kept the *centralized architecture*.
- That architecture is now the bottleneck: concentrated bandwidth and compute, single point of failure, raw identifiable footage transported and stored centrally, and floods of uncorrelated unexplained alerts.

Transition: the limitation is no longer perception accuracy — it is organization.

---

## Slide 3 — Two matured research currents make a different architecture possible

Central idea: multi-agent systems and agentic AI supply exactly the missing organizational layer.

- **Multi-agent systems** offer a principled framework for distributing perception and decision across autonomous cooperating agents, with decades of studied coordination theory — the Contract Net Protocol (Smith, 1980) and auction-based task allocation.
- **Agentic AI** — LLMs and vision-language models that plan, use tools, and reason over multimodal evidence — supplies a semantic layer able to interpret, corroborate, and *explain* detections in language an operator can act on.
- **Edge computing** makes on-sensor inference economically realistic, which turns "process where the data is produced" from an aspiration into a default.
- **Regulation** now constrains the design space: GDPR data minimization, and the EU AI Act prohibiting real-time remote biometric identification while classifying most other surveillance AI as high-risk with mandatory logging and human oversight.
- These four forces converge on one conclusion: the next gain comes from *how* perception is coordinated, not from a stronger detector.

Transition: this thesis operationalizes that convergence as a concrete system.

---

## Slide 4 — Research problem: organize perception, coordination, decision, and explanation

Central idea: the formal problem statement and the five research questions that structure the entire thesis.

> Design, implement, and evaluate a multi-agent intelligent surveillance system for a semi-closed site, in which autonomous perception agents detect security-relevant events from video and audio at the edge; coordinate to corroborate and actively verify uncertain detections; apply deterministic auditable alerting policies; and generate grounded natural-language explanations for a human operator — all under privacy-by-design constraints.

- **RQ1 — Architecture.** Does a distributed hierarchical MAS measurably improve time-to-alert over a centralized sequential pipeline on identical streams?
- **RQ2 — Coordination.** Does auction-based verification task allocation improve alert precision versus uncoordinated alerting, and at what communication cost?
- **RQ3 — Multimodality.** Does fusing audio with video increase confidence and surface incidents invisible to vision alone?
- **RQ4 — Agentic explanation.** Can an LLM layer produce explanations provably free of fabricated evidence, without influencing or delaying the safety-critical decision?
- **RQ5 — Governance.** Can the pipeline remain operationally useful under strict privacy-by-design constraints?

Scope note: event detection and alerting only — no facial recognition, no biometric matching, no person re-identification, by deliberate design choice.

---

## Slide 5 — State of the art leaves three gaps that this thesis targets

Central idea: mature components exist everywhere, but no integrated auditable architecture exists.

Comparison table across capability versus system family — Centralized VMS analytics / MARL surveillance research / LLM video agents / AURA-MAS:

| Capability | Centralized VMS | MARL research | LLM video agents | AURA-MAS |
|---|---|---|---|---|
| Edge-local perception | Partial | Simulated | No (cloud VLM) | Yes |
| Explicit coordination | No | Learned, opaque | Conversational | Auction (auditable) |
| Multimodal fusion | Rare | Rare | Partial | Yes (noisy-OR late fusion) |
| Explainable alerts | No | No | Yes, ungrounded | Yes, evidence-checked |
| Decision/generation decoupling | — | — | No | Yes (policy-first) |
| Privacy by design | Weak | Not addressed | Not addressed | Constitutive |
| System-level evaluation | Vendor claims | Simulation reward | Qualitative | Replayable ablations |

- **G1** — No surveyed system combines auditable multi-agent coordination with modern zero-shot perception.
- **G2** — Agentic explanation layers are never decision-decoupled and evidence-grounded by construction.
- **G3** — System-level evaluation methodology is largely absent: the literature evaluates *models*, not *systems*.

---

## Slide 6 — Five design principles turn the gaps into architectural invariants

Central idea: every subsequent engineering decision descends from five non-negotiable principles.

- **Edge-first** — raw sensor data is processed where it is produced and never leaves the perception agent.
- **Events, not streams** — all inter-agent communication consists of small structured JSON messages, never video.
- **Deterministic decisions** — alerts are emitted exclusively by an auditable rule-based policy engine.
- **Guarded generativity** — LLM and VLM components explain decisions but can never make or alter them.
- **Privacy by design** — anonymization, data minimization, and auditability are structural properties, not configuration options.

Transition: these principles materialize as a three-layer, seven-agent architecture.

---

## Slide 7 — AURA-MAS: three layers, seven agents, two message substrates

Central idea: the global architecture — the core of contribution C1.

- **Layer 1 — Edge perception.** One autonomous agent per sensor. *CameraAgents* run YOLO11 detection with ByteTrack association, a stateful declarative zone-rule engine, and optional CLIP zero-shot semantic anomaly scoring. *AudioAgents* classify sound events (YAMNet) or score acoustic anomalies via DSP fallback. Both publish structured events, never frames.
- **Layer 2 — Site coordination.** The *FusionAgent* aggregates events into spatio-temporal incident hypotheses; the *CoordinatorAgent* resolves uncertain hypotheses by auction; the *PolicyAgent* holds exclusive alerting authority under deterministic rules; the *ExplanationAgent* generates grounded reports for accepted alerts only.
- **Layer 3 — Governance and operator.** A web console presents the alert feed, anonymized evidence, and explanations; every policy decision and operator action is appended to an immutable audit log.
- **Substrate.** MQTT (QoS 0) for low-latency fan-out of high-frequency detections; Redis Streams (QoS 1) for durable replayable storage of alerts and audit records; an in-process bus with identical semantics enables single-process testing.
- Three message schemas with mandatory provenance: `Detection` (transient), `Event` (semantic, durable), `Alert` (operator-facing) — and `evidence_path` always references an *anonymized* crop.

Visual note: display the system architecture diagram prominently.

---

## Slide 8 — Fusion: a monotone noisy-OR that makes corroboration mathematically rewarding

Central idea: contribution C3 — confidence combination with a formal guarantee.

- The FusionAgent maintains open *hypotheses* keyed by (incident family, zone); mutually corroborating event types — `intrusion`, `loitering`, `audio_glass_break` — belong to the same *security* family and join within a sliding window (default 6 s).
- Confidence uses a reliability-weighted noisy-OR:

  C(H) = 1 − ∏(1 − w_m(e) · c_e) + β_mod · 1[|M(H)| > 1] + β_sen · 1[|S(H)| > 1]

  where c_e is event confidence, w_m per-modality reliability (video 0.9, audio 0.7), M(H) and S(H) the sets of contributing modalities and sensors, and β_mod = β_sen = 0.05 corroboration bonuses, clamped to [0,1].
- The noisy-OR form guarantees **monotonicity**: additional supporting evidence never decreases confidence, and independent corroboration from a second modality or sensor strictly increases it.
- This is the formal core of C3 — it makes cross-sensor and cross-modal agreement a first-class quantity rather than a heuristic bonus.

---

## Slide 9 — Coordination: buying information instead of guessing in the gray zone

Central idea: contribution C2 — a sealed-bid verification auction derived from the Contract Net Protocol.

- When fused confidence falls in the **gray zone** [0.35, 0.75], the system is neither confident enough to alert nor to dismiss. Rather than guessing, the CoordinatorAgent *buys information*.
- **Announce** — the coordinator publishes a verification task ⟨task_id, event_type, zone, origin_sensor⟩ on the task topic.
- **Bid** — each CameraAgent computes a private utility u = b · κ · o, where b penalizes the origin sensor (0.3 versus 1.0, favoring independent confirmation), κ reflects current inference load, and o ∈ [0,1] is field-of-view overlap with the event zone; bids are published within a 1 s window.
- **Award and verify** — the highest bidder re-analyzes its current frame at higher scrutiny (larger input resolution, lower confidence floor) and reports a verification score, which adjusts fused confidence *before* the policy decision.
- Two ablation baselines isolate the mechanism: no coordination at all, and round-robin (non-market) task assignment.

---

## Slide 10 — Guarded generativity: the LLM explains, the rule engine decides

Central idea: contribution C4 — a decision-decoupled, mechanically verified explanation layer.

- **Ordering invariant.** The PolicyAgent applies auditable thresholds, severity mapping, cooldowns, and alert hysteresis, and emits the alert. Only *then* is the ExplanationAgent invoked. Generation is strictly downstream of the safety-critical decision.
- **Grounding contract.** The explanation prompt receives only the alert, its constituent events, and anonymized evidence references — the model has no channel through which to influence detection or thresholds.
- **Mechanical guardrail.** Every evidence identifier cited in the generated report is checked against the actual event log; any citation that does not resolve invalidates the report, which is replaced by a deterministic template.
- **Result.** Fabricated evidence cannot survive into the operator console by construction — the guardrail is a verification step, not a prompt instruction.
- This pattern generalizes beyond surveillance to any safety-sensitive agentic system where generative fluency must not become decision authority.

---

## Slide 11 — Privacy by design: anonymization and audit as structural properties

Central idea: contribution to RQ5 — governance implemented as code paths, not policy documents.

- **No raw footage leaves the edge.** Perception is local; only structured events transit the bus. Bandwidth and legal exposure both collapse as a consequence of the same decision.
- **Fail-closed anonymization.** Every exported evidence crop passes through a single anonymization choke point that blurs detected person regions; if anonymization cannot be performed, the evidence is not exported.
- **No identity processing.** No facial recognition, biometric matching, or person re-identification — aligned with GDPR data minimization and the EU AI Act's prohibitions on real-time remote biometric identification.
- **Immutable audit.** Every alert, every suppression, and every operator acknowledgment appends a record to a durable stream — 61 audit records in the reference auction run.
- **Human authority preserved.** The operator acknowledges or dismisses; the system never acts autonomously on the physical world.

Visual note: show the automatically anonymized evidence example (blurred person region) as proof of the working pipeline.

---

## Slide 12 — Implementation: ~2,500 lines of tested Python with graceful degradation

Central idea: the prototype is real, runnable, and testable — not a paper design.

- **Perception**: Ultralytics YOLO11n + ByteTrack, declarative polygon zone rules with ray-casting foot-point membership, CLIP zero-shot anomaly scoring on subsampled frames; audio via YAMNet with a DSP z-score fallback.
- **Agents and orchestration**: seven agent classes over a common base with a unified message bus abstraction (MQTT + Redis Streams in deployment, in-process bus for tests); LLM explanation via an OpenAI-compatible client behind the guardrail.
- **Operator console**: Streamlit dashboard with live alert feed, anonymized evidence, explanations, acknowledgment actions, and audit view.
- **Evaluation harness**: scenario replay engine with ground-truth manifests, four selectable architecture modes, and automated metric computation.
- **Quality**: 6/6 unit tests passing — bus wildcard routing, noisy-OR corroboration monotonicity, auction best-bidder selection, policy thresholds and cooldown, metric evaluation, and guardrail rejection of fabricated evidence. Docker Compose provisions brokers; every heavy dependency has a documented degradation path.

---

## Slide 13 — Evaluation method: system-level metrics under controlled architectural ablation

Central idea: contribution C5 — measure the *architecture*, holding models and inputs constant.

- **Why replay.** Model-centric metrics (mAP, HOTA) characterize components, not systems. What an operator experiences is end-to-end: how fast an incident becomes an alert, how much noise pollutes the feed, what coordination costs. Replay guarantees all variants observe *identical* sensory input — a controlled comparison live deployment cannot provide.
- **Scenario `demo_site_01`.** Two cameras (real public pedestrian surveillance clips) plus one microphone; 60 s of real-time multi-sensor replay; ground truth declares three incidents: `intrusion` in zone A (3–35 s), `loitering` at the entry (16–46 s), and `audio_glass_break` (14–16 s).
- **Four variants, identical models, rules, thresholds, and inputs** — the only variable is architecture: *Centralized* (single sequential process, the classical VMS topology), *MAS-nocoord*, *MAS-rules* (round-robin), and *MAS-auction* (full AURA-MAS).
- **Metrics.** Event-level precision/recall/F1 (±5 s matching tolerance), mean time-to-alert, false alerts per hour, and coordination message overhead.
- Executed on a 4-vCPU CPU-only sandbox, YOLO11n at 5 FPS per camera.

---

## Slide 14 — Results: concurrency buys speed, the market buys precision

Central idea: the headline quantitative finding, from real runs.

| Mode | F1 | Precision | Recall | Mean TTA (s) | FA/h | Coord. msgs |
|---|---|---|---|---|---|---|
| Centralized | 0.667 | 0.667 | 0.667 | 21.6 | 67.9 | 0 |
| MAS-nocoord | 0.571 | 0.500 | 0.667 | **13.3** | 107.5 | 0 |
| MAS-rules | 0.571 | 0.500 | 0.667 | **13.3** | 106.9 | 4 |
| **MAS-auction** | **0.667** | **0.667** | 0.667 | 13.8 | **53.6** | 10 |

- **RQ1 answered.** Agent concurrency cuts mean time-to-alert from 21.6 s to 13.3–13.8 s, a ≈36–38% improvement. The mechanism is structural: centralized processing serializes sensors, so an incident on the second sensor waits behind the first; concurrency removes that head-of-line blocking, and the effect grows with sensor count.
- **RQ2 answered.** Uncoordinated MAS pays for its speed with precision — false alerts nearly double (107.5 versus 67.9 per hour). Round-robin assignment does *not* help (106.9), showing that *who* verifies matters more than *that* verification happens. Auction coordination selects the best-placed independent verifier, restoring precision to 0.667 and **halving** false alerts (53.6 versus 107.5) while also beating the centralized baseline's FA/h by 21%.
- **Cost.** Ten coordination messages and +0.5 s of mean TTA over 60 s — the system is simultaneously faster *and* more precise than the centralized baseline.

Visual note: pair the table with the detection-quality and system-metrics bar charts.

---

## Slide 15 — All five research questions answered, with honest boundaries

Central idea: consolidated verdict plus the limitations a jury should hear stated first.

- **RQ3 (Multimodality).** The glass-break incident is detectable only through audio; fusion raised the security hypothesis via the cross-modality corroboration bonus. A control run with the audio agent removed lost that incident entirely — recall dropped by one of three incidents, directly confirming additive multimodal value.
- **RQ4 (Agentic explanation).** Explanation occurred strictly after alert emission; policy decision latency averaged 0.3 ms, unaffected by generation. Every accepted report cited only identifiers present in the event log — zero uncaught hallucinated citations.
- **RQ5 (Governance).** 100% of exported evidence crops passed the anonymization choke point; no raw frame was persisted or transmitted; 61 audit records were produced in the auction run.
- **Limitations, stated plainly.** Demonstrator scale (two cameras, one microphone, 60 s) means absolute values are relative-effect evidence, not field performance claims; a perception ceiling is set by YOLO11n on low-resolution public clips (held constant across variants by design); a single site topology exercises only single-item auctions; and explanation *groundedness* is verified mechanically while operator-perceived *usefulness* would require a user study.
- None of these limitations is architectural — each defines a concrete axis of extension.

---

## Slide 16 — The consequential frontier in surveillance AI is organizational, not perceptual

Central idea: closing argument, contributions delivered, and the path forward.

- **Contributions delivered.** C1 three-layer seven-agent architecture with formal schemas; C2 auction-based active verification protocol with ablation baselines; C3 monotone reliability-weighted noisy-OR fusion; C4 decision-decoupled evidence-grounded explanation with mechanical guardrails; C5 replayable system-level evaluation methodology.
- **Two transferable patterns.** *Market-based uncertainty resolution* — resolve ambiguity by buying targeted information rather than by tuning a threshold. *Guarded generativity* — confine generative models to roles where fluency helps and cannot harm.
- **Future work.** Scale and realism via VIRAT/MEVA-derived manifests and physical single-board deployment; MARL-learned bidding policies with the auction retained as an auditable fallback; active sensing extending verification to PTZ re-pointing and drone repositioning; richer agentic reasoning with cross-incident temporal correlation under the same decoupling invariant; and a certification pathway formalizing the audit stream against EU AI Act high-risk requirements.
- **Closing claim.** Surveillance AI is usually framed as a race toward stronger perception. This thesis demonstrates at prototype scale that the more consequential frontier is organizational: how distributed perception is coordinated, how uncertainty is resolved before reaching a human, how generative intelligence is confined, and how privacy and accountability are made structural rather than aspirational.

Final line: **Thank you — questions welcome.**
