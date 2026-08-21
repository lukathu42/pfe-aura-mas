# AURA-MAS: Modernized PFE Theme and Project Vision

**Author:** Manus AI — prepared for the final-year Master's project (PFE) in Artificial Intelligence and Data Science, ESI-SBA, academic year 2025/2026.

---

## 1. The Modernized Theme

### 1.1 Original theme

> "Intelligent surveillance system and agentic AI — agents coordinate and cooperate to manage the surveillance of a place, identify and alert."

### 1.2 Modernized theme (recommended title)

> **AURA-MAS — Agentic and Multi-Agent Intelligent Surveillance: a privacy-aware, edge-first hierarchical multi-agent system for multimodal event detection, inter-sensor coordination, and explainable alerting on semi-closed sites.**

**French version (for the ESI-SBA administrative record):**

> **AURA-MAS — Surveillance intelligente multi-agents et agentique : un système hiérarchique, edge-first et respectueux de la vie privée pour la détection multimodale d'événements, la coordination inter-capteurs et l'alerte explicable sur sites semi-fermés.**

### 1.3 Why this modernization is stronger than the original

The original theme ("agents that coordinate to surveil, identify, alert") suffers from three weaknesses that a jury will immediately probe: it is vague on what "identify" means (biometric identification is legally toxic under the EU AI Act and CNIL doctrine), it does not name a concrete site or scenario, and it does not state a measurable scientific contribution. The modernized theme fixes all three:

| Dimension | Original | Modernized |
|---|---|---|
| Scope | "such place", undefined | Semi-closed site (warehouse / campus zone) — legally safer, simulatable, concrete |
| Identification | Implied biometric ID | **Non-biometric event detection** (intrusion, fall, fight, fire/smoke proxy, abandoned object, crowding, anomalous sound) |
| Architecture | "agents coordinate" (undefined) | **Hierarchical 3-layer MAS**: edge perception agents → site coordination agents → governance/operator layer |
| Agentic AI | Buzzword | **Rule-guarded agentic layer**: LLM/VLM agents generate evidence-linked incident explanations *downstream* of deterministic alert policy |
| Modernity hooks | None | VLM-based anomaly detection (CLIP/VadCLIP-style), auction-based task allocation, MQTT/Redis event bus, edge-first privacy-by-design, EU AI Act compliance narrative |
| Evaluation | None | Component metrics (mAP, HOTA, AUC) + system metrics (time-to-alert, false alerts/hour) + coordination ablations |

### 1.4 The elevator pitch (memorize this for your supervisor)

"Most surveillance systems are camera-siloed, centralized, and opaque: they push every pixel to one server, flood operators with false alarms, and cannot explain *why* they alerted. My PFE designs and builds **AURA-MAS**, a hierarchical multi-agent system in which lightweight perception agents run at the edge (one per camera/microphone), publish compact semantic events on an MQTT bus, and cooperate through an auction-based coordination agent that fuses evidence across sensors. A rule-guarded policy agent decides escalation, and an agentic explanation layer built on a vision-language model turns raw evidence into human-readable, auditable incident reports. I evaluate it against a centralized baseline on UCF-Crime-class benchmarks and scripted scenario replays, measuring detection quality, time-to-alert, false-alert rate, and coordination overhead — under an explicit privacy-by-design constraint aligned with the EU AI Act and CNIL guidance."

---

## 2. System Architecture

### 2.1 Three-layer hierarchical design

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 3 — GOVERNANCE & OPERATOR                                │
│  Streamlit dashboard · alert acknowledgment · audit log (SQLite)│
│  evidence store (anonymized crops/clips) · retention policy    │
├────────────────────────────────────────────────────────────────┤
│ LAYER 2 — SITE COORDINATION (agents on the site server)        │
│  Fusion/World-State Agent  — spatio-temporal event fusion      │
│  Coordinator Agent         — auction-based task allocation     │
│  Policy & Alert Agent      — deterministic rules + thresholds  │
│  Explanation Agent         — VLM/LLM incident summarization    │
├────────────────────────────────────────────────────────────────┤
│ LAYER 1 — EDGE PERCEPTION (one agent per sensor)               │
│  Camera Agents  — YOLO11n + ByteTrack + zone rules + anomaly   │
│  Audio Agents   — YAMNet/AST embeddings + anomaly scoring      │
│  (streams stay local; only events + anonymized crops leave)    │
└────────────────────────────────────────────────────────────────┘
         Bus: MQTT (edge→site telemetry/events, QoS 0-1)
              Redis Streams (durable alert log, consumer groups)
```

### 2.2 The seven agents

| # | Agent | Runs where | Input | Output | Core tech |
|---|---|---|---|---|---|
| 1 | CameraAgent | Edge (per camera) | RTSP/video file | detections, tracks, zone events, anomaly scores | YOLO11n, ByteTrack, OpenCV |
| 2 | AudioAgent | Edge (per mic) | audio stream/file | audio event class + anomaly score | YAMNet / spectrogram AE |
| 3 | FusionAgent | Site | all edge events | fused event hypotheses w/ calibrated confidence | temporal window fusion, late fusion |
| 4 | CoordinatorAgent | Site | event hypotheses, agent states | task assignments (verify, zoom, cross-check) | single-round auction (contract-net) |
| 5 | PolicyAgent | Site | fused hypotheses | alert / no-alert, severity, escalation | rule engine + thresholds + hysteresis |
| 6 | ExplanationAgent | Site | evidence bundle | human-readable incident report | VLM (Qwen2.5-VL or GPT-4o-mini via API), guardrails |
| 7 | OperatorDashboard | Site | alerts stream | acknowledgments, audit entries | Streamlit + Redis |

### 2.3 What makes it "agentic"

Agentic AI here means **stateful, specialized, cooperating agents with explicit protocols** — not a monolithic model. Concretely: (1) each agent has local state, beliefs, and a message-driven control loop; (2) coordination uses an economic protocol (auction/contract-net) that is interpretable and ablatable; (3) the explanation layer is a genuine LLM-agent workflow (perceive → retrieve evidence → reason → draft → verify against guardrails) implemented with LangGraph-style state graphs, but it is **never** the safety-critical decision-maker — the deterministic PolicyAgent is.

---

## 3. Scientific Contributions (what you defend)

1. **C1 — Architecture:** A reproducible hierarchical event-driven MAS for site surveillance, compared quantitatively against a centralized monolithic baseline (latency, throughput, bandwidth, F1).
2. **C2 — Coordination:** An auction-based task-allocation mechanism for camera cross-verification, ablated against a rule-based scheduler (task completion rate, time-to-alert, message overhead).
3. **C3 — Multimodal fusion:** Late audio-visual fusion at alert time, showing measurable false-alarm reduction vs. vision-only.
4. **C4 — Explainable agentic alerting:** A rule-guarded VLM explanation agent producing evidence-linked incident reports, evaluated for evidence completeness and hallucination rate.
5. **C5 — Privacy-by-design:** Edge-first processing, on-edge anonymization (face/body blurring in exported evidence), audit logging — mapped explicitly to EU AI Act / CNIL / GDPR requirements.

## 4. Explicit non-goals (scope guard — say these out loud)

- No biometric identification / face recognition (legal risk, jury risk).
- No real drone control (simulated verification tasks only).
- No MARL training as core contribution (optional stretch, simulation-only).
- No claim of production readiness; this is a research prototype evaluated on benchmarks + scripted scenario replays.

## 5. What you will learn (the point of a PFE)

Computer vision engineering (detection/tracking/anomaly), audio ML, distributed systems (pub/sub, event-driven design), multi-agent coordination theory (auctions, consensus), LLM-agent engineering (LangGraph, guardrails, structured output), MLOps (Hydra configs, MLflow tracking, Docker Compose), evaluation methodology, and AI governance — the exact profile of a "state engineer + master" in AI expected by industry in 2026.
