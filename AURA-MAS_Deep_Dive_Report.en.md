# AURA-MAS — Deep-Dive Technical & Theoretical Report

**Project:** *AURA-MAS: Agentic Multi-Agent Intelligent Surveillance* — a Master's thesis (PFE) in AI & Data Science, by Zeddoun Lokmane.

---

## 1. Executive Summary & Core Purpose

### The real-world problem

Physical security surveillance on semi-closed sites (warehouses, campuses, industrial yards) today suffers from three structural failures:

1. **Alert fatigue** — naive per-camera motion/object detectors fire constantly, and human operators tune them out or disable them.
2. **Single-sensor blindness** — a lone camera or microphone has no way to corroborate what it sees; a glass-break sound and a person entering a restricted zone thirty seconds later are, to an isolated sensor, two unrelated non-events.
3. **Opaque and unaccountable automation** — black-box "AI security" systems that auto-generate incident narratives risk hallucination, and offer no audit trail for who — human or model — made a containment decision, which is untenable in a domain with legal/privacy stakes.

AURA-MAS is a research testbed built to answer, empirically, a specific thesis question: **does organizing edge sensors as a coordinating multi-agent system (with auction-based task allocation, multimodal late fusion, and a rule-guarded LLM explanation layer) measurably outperform a centralized, single-process detection pipeline** on time-to-alert, F1, false-alert rate, and coordination overhead? The codebase is not a production security product — it's an *ablatable experimental apparatus*: every architectural choice (coordination on/off, auction vs. round-robin, template vs. LLM explanation) is a command-line flag so the thesis can run controlled comparisons and report the deltas.

### Domain/product concept

A **hierarchical, privacy-first, edge-to-cloud multi-agent surveillance stack**:

- **Edge layer** — per-sensor agents (`CameraAgent`, `AudioAgent`) run perception locally and never transmit raw frames off-device.
- **Coordination layer** — a `FusionAgent` merges corroborating evidence across sensors/modalities; a `CoordinatorAgent` runs contract-net-style auctions to task idle cameras with re-verifying ambiguous events; a `PolicyAgent` is the sole, deterministic decision-maker for alerts; an `ExplanationAgent` writes a natural-language incident report *after the fact*, under hallucination guardrails.
- **Governance layer** — a Streamlit operator console, an append-only audit stream, and an anonymized evidence store (blurred crops only) close the human-in-the-loop and compliance loop.

### Tech stack overview

| Concern | Choice |
|---|---|
| Language | Python 3.11 |
| Object detection & tracking | Ultralytics YOLO11n + ByteTrack (`model.track(tracker="bytetrack.yaml")`) |
| Zero-shot visual anomaly | OpenAI CLIP (ViT-B/32), zero-shot prompt scoring |
| Audio event classification | Google YAMNet (TF-Hub) with a dependency-light DSP (FFT flatness/energy z-score) fallback |
| Messaging | MQTT (Eclipse Mosquitto) for high-frequency edge events + coordination traffic; Redis Streams for durable alert/audit logs; hand-rolled `LocalBus` in-process pub/sub for tests and single-machine demos |
| LLM explanation | OpenAI-compatible Chat Completions API (GPT-4o-mini class models, or local Ollama), JSON-mode structured output |
| Operator UI | Streamlit |
| Testing | pytest, fully offline/synthetic (no models, no video, <5s) |
| Infra | Docker Compose (Mosquitto + Redis) |
| Privacy | OpenCV Gaussian blur pipeline (HOG or YOLO-driven person localization) |

---

## 2. Theoretical Foundations & Core Abstractions

### 2.1 Multi-agent systems theory: BDI-lite agents over a shared bus

Every agent (`aura_mas/agents/base.py`) is a minimal **Belief–Desire–Intention-flavored** reactive agent:

```python
class Agent:
    def __init__(self, agent_id, bus, tick_interval=0.0):
        self.beliefs: Dict[str, Any] = {}   # local, mutable world model
        ...
    def setup(self): ...   # subscribe to topics, load models  (Desire wiring)
    def tick(self):  ...   # periodic re-evaluation           (Intention execution)
```

There's no shared global state — each agent only knows what it perceives directly (a video/audio stream) or what arrives over the bus. This is a textbook **weak-agency** model (autonomy + social ability via message passing + reactivity via `tick`/callbacks), deliberately *not* a strong-agency BDI implementation (no explicit plan library or goal-directed planner) — appropriate for a systems/architecture thesis rather than an agent-theory one.

### 2.2 Contract-Net Protocol (CNP) for task allocation

The `CoordinatorAgent` implements a textbook **single-round Contract Net** (Smith, 1980) for the "which camera should re-verify this ambiguous hypothesis?" problem:

```
Manager (Coordinator)          Contractors (CameraAgents)
      |--- task announcement -------->|  (TOPIC_TASKS)
      |<-- bid (view utility score) --|  (TOPIC_BIDS)
      |--- award (best bid wins) ---->|  (TOPIC_AWARDS)
      |<-- verification result -------|  (TOPIC_VERIFICATIONS)
```

The bid function (`CameraAgent._view_score`) is a hand-crafted utility combining three factors — whether the camera is a *different* sensor than the one that originally raised the event (avoids asking the same biased witness), current business (`_busy` flag as a capacity constraint), and estimated field-of-view overlap with the event's zone. This is a simple **multi-attribute utility function**, not a learned or game-theoretic optimum — the auction guarantees an *efficient allocation given self-reported bids*, but bidding is not adversarial/strategic (no VCG-style incentive compatibility is needed since all agents are cooperative, owned by the same system).

The **round-robin scheduler** (`mas-rules` mode) is the deliberate control condition for the ablation — it isolates the *value of an auction* from the *value of having any* coordination.

### 2.3 Multimodal sensor fusion: noisy-OR with reliability weighting

The theoretical core of the "multimodal claim" (thesis contribution C3) is in `FusionAgent._fuse_confidence`:

```
P(incident) = 1 − ∏ᵢ (1 − wₘ(i) · conf(eᵢ))
```

This is the classical **Noisy-OR Bayesian causal model**: each event `eᵢ` is treated as an independent, imperfect (noisy) "cause" of the same underlying incident, and the model computes the probability that *at least one* of them correctly indicates it. `wₘ` is a fixed reliability prior per modality (video 0.9, audio 0.7) — a simplification of full Bayesian sensor fusion, but it has the right mathematical property the thesis needs: **confidence is monotonically non-decreasing in corroborating evidence**, and a flat +0.05 bonus is added for cross-modality and cross-sensor corroboration, capped at 1.0. This directly operationalizes the intuition "two independent witnesses are more convincing than one" without requiring learned joint likelihoods or labeled multimodal training data — appropriate given the system runs zero-shot/rule-based per-modality detectors, not a trained fusion classifier.

Events are grouped into **hypotheses** via a sliding-window temporal clustering keyed by `(incident_family, zone)` — a simple online windowed clustering algorithm, not a general point-process/change-detection model, chosen for its O(1) update cost and interpretability (auditable by a human).

### 2.4 Zone-based spatial reasoning

`CameraAgent.ZoneRuleEngine` implements classic **computational geometry / CV surveillance primitives**:
- **Point-in-polygon test** via ray casting (the standard even-odd crossing-number algorithm) to test whether a tracked object's foot-point is inside a restricted zone.
- **Dwell-time state machine** per `(track_id, zone)` for loitering detection (a `first_seen` timestamp reset whenever the track exits the zone).
- **Static-object detection via IoU-tracked persistence**: an object is "abandoned" if its bounding box has high IoU (>0.6, i.e., hasn't moved) across a sustained period.

### 2.5 Zero-shot anomaly detection (CLIP)

`ClipAnomalyScorer` is a lightweight instantiation of the **VadCLIP** family of ideas (CLIP-based zero-shot video anomaly detection): rather than training a supervised anomaly classifier, it embeds the frame and a fixed bank of natural-language "normal" vs. "anomalous" prompts into CLIP's joint embedding space, and takes the softmax mass over the anomalous prompts as an anomaly score. This is a **zero-shot, open-vocabulary generalization strategy** — new anomaly types can be added by writing new prompts, no retraining or labeled anomaly data required. The audio side has a symmetric, even-cheaper fallback: **z-score novelty detection** over a rolling baseline of short-time energy and spectral flatness — no model weights at all, useful when TensorFlow/YAMNet isn't installed.

### 2.6 Agentic AI with guardrails (LangGraph-style state machine, rule-guarded)

`ExplanationAgent` is architecturally the most theoretically interesting piece (thesis contribution C4). It models the well-known tension in "agentic AI for safety-critical domains": LLMs are useful for natural-language synthesis but unreliable for *decisions* and prone to hallucination. The design resolves this with two structural guarantees, not prompting alone:

1. **Strict causal ordering** — the explanation pipeline runs only *after* `PolicyAgent.on_hypothesis` has already decided ALERT/SUPPRESS. The LLM can describe a decision; it can never make or veto one. This is enforced by *control flow* (the explainer is invoked inside `PolicyAgent`, downstream of the threshold check), not by a prompt instruction — an important distinction, since prompt instructions are the class of guardrail this design explicitly distrusts.
2. **Grounding/guardrail verification** — `_guardrail_check` treats the LLM's JSON output as untrusted and mechanically verifies that every cited evidence ID (`ev_[hex]` regex-scanned from the free text *and* the structured `cited_evidence` field) is a subset of the IDs actually supplied in the prompt. Any fabricated reference → reject → fall back to a deterministic template. This is a practical instance of **retrieval-grounded generation with programmatic hallucination detection**, cheaper and more auditable than a second LLM-as-judge call.

The pipeline itself is a small explicit state machine (the module docstring literally draws it as a LangGraph-style graph: `collect_evidence → describe → draft_report → guardrail_check`, with a `fail → fallback_template` edge from every node), even though it's hand-rolled with plain Python rather than the actual LangGraph library (present only as a commented-out optional dependency).

---

## 3. High-Level System Architecture

### 3.1 Component map

```
                         ┌───────────────────────────────────────────┐
                         │        Layer 3 — Governance/Operator       │
                         │  Streamlit console · Audit log (Redis)     │
                         │  Anonymized evidence store (JPEG, blurred) │
                         └───────────────▲─────────────────────────┬─┘
                                          │ read alerts             │ ack/dismiss
                                          │                         ▼
                         ┌────────────────┴───────────────────────────┐
                         │            Redis Streams (durable)          │
                         │      aura:alerts       aura:audit           │
                         └────────────────▲───────────────────────────┘
                                          │ append
        ┌─────────────────────────────────┴──────────────────────────────┐
        │                     Layer 2 — Site Coordination                 │
        │                                                                  │
        │   FusionAgent ──hypothesis──▶ PolicyAgent ──alert──▶ Explanation │
        │        ▲                          │  ▲                Agent     │
        │        │                          │  └── verify(gray-zone) ──┐  │
        │        │                          ▼                         │  │
        │        │                    CoordinatorAgent ◀───────────────┘  │
        └────────┼──────────────────────────┬───────────────────────────┘
                  │ events (QoS1)            │ tasks/bids/awards/verifs
        ┌─────────┴──────────────────────────┴───────────────────────────┐
        │                        MQTT Bus (or LocalBus)                   │
        └──────▲───────────────────────▲───────────────────────▲─────────┘
               │                       │                        │
       ┌───────┴──────┐       ┌────────┴──────┐         ┌───────┴───────┐
       │ CameraAgent   │       │ CameraAgent   │         │  AudioAgent   │
       │ cam_01        │       │ cam_02        │         │  mic_01       │
       │ YOLO+ByteTrack│       │ ...           │         │ YAMNet/DSP    │
       │ Zones+CLIP    │       │               │         │               │
       └───────────────┘       └───────────────┘         └───────────────┘
              Layer 1 — Edge Perception (privacy boundary: raw frames stop here)
```

### 3.2 Directory layout and logic separation

```
aura_mas/
  core/         transport-agnostic infrastructure
    bus.py        message schemas (Detection/Event/Alert), topic constants,
                   BaseBus interface + 3 implementations (Local/MQTT), AlertStore
    privacy.py     anonymize_and_save() — the one mandatory choke point for
                   any frame that leaves an edge agent
  agents/       one file per agent role, each importing only core/ and base.py
    base.py                generic Agent lifecycle (setup/tick/start/stop)
    camera_agent.py         edge perception + zone rules + CLIP + bidding
    audio_agent.py           edge perception (audio) + YAMNet/DSP
    fusion_agent.py           multimodal hypothesis clustering (noisy-OR)
    coordinator_agent.py     contract-net auction / round-robin
    policy_agent.py          the sole alert-authoring authority
    explanation_agent.py     rule-guarded LLM incident narration
  scenarios/    replay.py = orchestration/wiring root (the "main()" of the MAS);
                *.json manifests describe sensors/zones/ground truth
  eval/         metrics.py — offline scoring of replay runs against ground truth
  dashboard/    app.py — Streamlit read/ack UI, entirely decoupled (reads only
                from AlertStore, never talks to agents directly)
  tests/        test_pipeline.py — synthetic, model-free integration tests
```

This is a clean **layered/hexagonal separation**: `core/` is the stable interior (message contracts + transport), `agents/` is the domain logic, and `scenarios/`, `eval/`, `dashboard/` are three independent *drivers* of the same core — none of them import each other, only `core` and `agents`. Note: identically-named `.py` files exist flattened at the repository root (`bus.py`, `camera_agent.py`, etc.) alongside the `aura_mas/` package — these are point-in-time export copies (likely from the thesis-writing/figure-generation process, `AURA-MAS_Code.zip`), not a second implementation; `aura_mas/` under `scenarios/replay.py`'s imports is the authoritative, tested source of truth.

### 3.3 Canonical execution path — trace of one intrusion event

Using `scenarios/intrusion_01.json` and `--mode mas-auction` as the concrete walk-through:

1. **`replay.run_scenario`** parses the manifest, builds a `bus` (MQTT or `LocalBus`), an `AlertStore`, and wires the four Layer-2 agents: `coordinator`, `explainer` (if `--llm`), `policy` (holds refs to `store`, `coordinator`, `explainer`), `fusion` (its `on_hypothesis` callback *is* `policy.on_hypothesis` — direct Python callback, not a bus round-trip, for low latency on the hot decision path).
2. Two `CameraAgent`s and one `AudioAgent` are started, each on its own thread, reading `data/clips/*.mp4|wav` and pacing itself to real time (`realtime=True` unless `mode == "centralized"`).
3. `cam_01._process_frame` runs `YOLO.track(...)`, gets a `person` track inside `zone_A`'s polygon → `ZoneRuleEngine.evaluate` fires `intrusion` → `_emit_event` calls `anonymize_and_save` (blurs the person, never persists the raw frame) and publishes an `Event(event_type="intrusion", modality="video", confidence=0.8...)` to `TOPIC_EVENTS`.
4. `mic_01` independently detects `audio_glass_break` around the same timestamp and publishes its own `Event` to the same topic.
5. `FusionAgent._on_event` receives both. `intrusion` and `audio_glass_break` are both mapped by `EVENT_FAMILIES` to `"security"`, and both share `zone_A`, so they land in the **same `Hypothesis`** bucket (key `"security:zone_A"`). `_fuse_confidence` computes the noisy-OR across both events plus the cross-modality/cross-sensor bonuses — confidence rises above what either sensor alone would produce.
6. On its 1-second `tick()`, once `now - hyp.last_ts > window_seconds` (6s), `FusionAgent` flushes the hypothesis and calls `policy.on_hypothesis(hyp)` directly.
7. **`PolicyAgent.on_hypothesis`** — the single authority: if confidence falls in the coordinator's gray zone (0.35–0.75) it triggers `coordinator.request_verification(hyp)` (a blocking contract-net round against `cam_02`, since it wasn't the origin sensor), adjusting confidence ±0.15/0.20 based on the verification outcome; then applies `ALERT_THRESHOLDS` per severity, then a per-`(zone, event_type)` cooldown to suppress repeats; every branch — alert or suppress — is written to `store.audit(...)`.
8. If an alert fires, `PolicyAgent` calls `explainer.explain(alert, hyp)` (or, without `--llm`, `_template_explanation`) to attach a human-readable narrative, then `store.append(alert)` — durable write to Redis Streams (or JSONL fallback).
9. `replay.run_scenario`'s monkey-patched `timed_append` also records the alert with wall-clock time into an in-memory `alerts_log`, which becomes part of the `results/run_*.json` used by `eval/metrics.evaluate_run` to score precision/recall/F1/time-to-alert against the manifest's `ground_truth`.
10. Independently, the **Streamlit dashboard** polls `AlertStore.read_alerts()` and renders the alert, its blurred evidence images, and its explanation; operator Acknowledge/Dismiss clicks are appended to the audit stream — closing the human-in-the-loop.

---

## 4. Design Patterns & Architectural Paradigms

### Architectural paradigm

**Event-driven, hierarchical multi-agent system** — three explicit governance layers (Edge → Coordination → Governance), communicating exclusively through an asynchronous publish/subscribe bus at Layers 1↔2, with a direct in-process callback used only for the latency-sensitive Fusion→Policy hop. It is *not* microservices (everything can run in one process via `LocalBus`) and *not* a monolith (each agent is independently instantiable, testable, and swappable — see `mode` ablation flags). It's closer to **Actor-model-lite**: each `Agent` owns private mutable state (`self.beliefs`) and communicates only via messages, though threads share the Python GIL rather than being isolated actors, and locking (`threading.Lock`) is used explicitly wherever shared dict state (`_hypotheses`, `_bids`) is mutated from multiple callback threads.

### Design patterns in use

| Pattern | Where | Why |
|---|---|---|
| **Strategy** | `make_bus(kind=...)` returns `MqttBus`/`LocalBus`; `CoordinatorAgent.mode ∈ {auction, roundrobin, off}` | Swap transport or allocation policy without touching callers — this *is* the ablation mechanism |
| **Template Method** | `Agent.start()` calls `self.setup()` then optionally spins `_tick_loop()`; subclasses override `setup()`/`tick()` | Uniform lifecycle across 5 very different agents |
| **Observer / Pub-Sub** | `BaseBus.subscribe/publish`, `LocalBus._match` (MQTT wildcard emulation) | Decouples producers (cameras) from consumers (fusion) — N:M without direct references |
| **Pipeline / Chain of Responsibility** | `ExplanationAgent.explain`: `_collect_evidence → _describe → _draft_report → _guardrail_check → (_fallback)` | Each stage can fail closed into the next safer stage |
| **Repository** | `AlertStore` abstracts Redis Streams vs. JSONL file behind `append/audit/read_alerts` | Callers (`PolicyAgent`, dashboard) never know which backend is live |
| **Factory** | `make_bus()`, lazy model loading (`YOLO(...)`, `ClipAnomalyScorer()` only in `setup()`) | Defers expensive/optional dependencies (torch, tensorflow) to first real use, keeping the core testable without them |
| **Null Object / graceful degradation** | YAMNet → DSP fallback, CLIP unavailable → disabled, LLM guardrail failure → template explanation, Redis down → JSONL | Recurring idiom across the whole codebase: every ML/infra dependency has a deterministic, dependency-light fallback so the *system never blocks on missing infrastructure* |
| **Command / message DTO** | `Detection`, `Event`, `Alert` dataclasses with `to_json`/`from_json` | Transport-agnostic wire format; same schema works over MQTT, Redis, or in-memory `LocalBus` |
| **Auction / Contract-Net** (behavioral, not GoF) | `CoordinatorAgent` | See §2.2 |

The fallback idiom deserves its own callout: it is the single most consistent architectural decision in the codebase, and it's what makes the **offline test suite** possible — `aura_mas/tests/test_pipeline.py` exercises bus wildcards, noisy-OR fusion, auction bidding, policy thresholds/cooldown, metrics scoring, and the explanation guardrail, entirely with synthetic `Event`/`Hypothesis` objects, in under 5 seconds, with zero GPU/model/network dependency.

---

## 5. Deep-Dive Code Walkthrough: Critical Files

### 1. `aura_mas/core/bus.py` — the system's nervous system & contract
The only file every other module transitively depends on. Defines the three wire-format dataclasses (`Detection`, `Event`, `Alert`) that constitute the *entire* inter-agent contract — any agent can be replaced as long as it speaks these JSON shapes. `BaseBus` is a 4-method interface; `LocalBus` reimplements MQTT topic-wildcard semantics (`+`/`#`) in pure Python so tests and single-process demos behave identically to the real broker. `AlertStore` decouples durability (Redis Streams with consumer-group-ready `xadd`, or JSONL) from every writer/reader. **Watch:** `make_bus("auto", ...)` — the try/except MQTT→LocalBus fallback is the reason the whole system degrades gracefully when Mosquitto isn't running.

### 2. `aura_mas/agents/policy_agent.py` — the accountability chokepoint
Explicitly documented as "the ONLY component allowed to create alerts." Six-step deterministic pipeline: coordination-triggered re-verification → severity-based threshold → cooldown/hysteresis → mandatory audit write (even for suppressions) → alert construction → downstream (non-authoritative) explanation. **Watch:** `on_hypothesis` — this single method is the decision boundary the whole thesis's "rule-guarded agentic AI" claim rests on; the explainer's exception is caught locally so an LLM outage can never prevent an alert from being logged (`except Exception: ... alert.explanation = self._template_explanation(...)`).

### 3. `aura_mas/agents/fusion_agent.py` — the multimodal claim, in code
Implements the noisy-OR combiner (§2.3) and the sliding-window `Hypothesis` clustering. **Watch:** `_fuse_confidence` (static method, easily unit-testable in isolation — see `test_fusion_noisy_or_increases_with_corroboration`) and the `tick()`/`flush_all()` pair — `tick()` is time-driven for live operation, `flush_all()` is the deterministic end-of-replay drain so batch scenario runs don't lose the last open hypothesis to a race against thread shutdown.

### 4. `aura_mas/agents/camera_agent.py` — heaviest, most feature-dense module
Combines four distinct capabilities: (a) YOLO11n+ByteTrack inference (`_process_frame`), (b) the geometric `ZoneRuleEngine` (intrusion/loitering/abandoned-object), (c) optional CLIP zero-shot anomaly scoring, and (d) the contract-net *contractor* side (`_on_task_announce` bids, `_on_award` runs `_verify` — a deliberately higher-precision re-detection pass at `imgsz=960` vs. the streaming pass's default resolution). **Watch:** `_view_score` (the bid function) and `_verify` (what "winning the auction" actually causes to happen — a second, more expensive inference pass, which is the real cost/benefit tradeoff the auction is supposed to justify).

### 5. `aura_mas/agents/coordinator_agent.py` — the allocation mechanism
`request_verification` is a **blocking** call from the caller's (Policy's) perspective, internally driven by pub/sub: publish task → sleep `bid_window` seconds collecting bids on a lock-protected dict → pick `max(bids, key=bid)` → publish award → poll (`_await_verification`, 50ms interval, 3s timeout) until a matching verification arrives or times out. **Watch:** the `mode` branch in `request_verification` (`auction` vs `roundrobin`) is exactly the toggle the thesis ablation table (`mas-rules` vs `mas-auction`) measures — same call signature, different allocation algorithm, letting `eval/metrics.py` produce an apples-to-apples comparison.

### 6. `aura_mas/agents/explanation_agent.py` — the safety-critical LLM boundary
See §2.6 for the theory. **Watch:** `_guardrail_check`'s regex hallucination scan (`re.findall(r"ev_[0-9a-f]{6,}", ...)`) — this is the concrete mechanism, not a prompt instruction, that prevents the LLM from inventing evidence; `test_explanation_guardrail_rejects_fabricated_evidence` is the executable spec for this guarantee.

### 7. `aura_mas/scenarios/replay.py` — composition root
Not a "core logic" file, but the one place all agents are actually wired together, so it's the fastest way to understand runtime data flow without reading five files. **Watch:** the `mode` dict (`{"mas-auction": "auction", "mas-rules": "roundrobin", "mas-nocoord": "off", "centralized": "off"}`) and the `if mode == "centralized": ... th.start(); th.join()` sequential-vs-parallel branch — this single `if` is literally the "centralized vs. hierarchical MAS" architectural comparison the thesis measures wall-clock time against.

---

## 6. Data & State Management

### State locality
There is **no shared global state and no central database** for live operation — each agent's `self.beliefs`/instance attributes are the only mutable state, and all cross-agent state is either (a) transient messages on the bus, or (b) durable records in `AlertStore`. This is a deliberate consequence of the MAS design: state is distributed by construction, which is exactly what the "centralized" baseline mode removes (it runs sources sequentially in one process/thread-join chain instead of independently threaded agents) to isolate the architectural effect being measured.

### Persistence
- **Detections** (`site/{sensor}/detections`, QoS 0): ephemeral, never persisted — pure streaming telemetry.
- **Events** (`site/events`, QoS 1): ephemeral on the bus, but each carries an `evidence_path` pointing to a JPEG already anonymized and written to `data/evidence/` at emission time — the frame itself is what's durable, not the message.
- **Alerts**: the only durable, queryable record — Redis Streams (`aura:alerts`) if reachable, else append-only JSONL (`data/alerts_<scenario>_<mode>.jsonl`). Redis Streams was chosen specifically for its consumer-group/replay semantics (durable log, not a queue that loses messages once consumed) — appropriate for an audit-grade record.
- **Audit** (`aura:audit` / `data/audit.jsonl`): every `PolicyAgent` decision (alert *and* suppression) and every operator UI action (`acknowledge`/`dismiss`) is appended — an immutable, chronological accountability trail, intentionally separate from the alert stream so it can't be edited by re-processing alerts.
- **Scenario run results** (`results/run_<scenario>_<mode>.json`): the full experimental record (ground truth, timestamped alerts, per-agent metrics) that `eval/metrics.py` consumes — this is effectively the thesis's raw dataset for its ablation tables.

### Concurrency & side effects
- Each perception agent (`CameraAgent`, `AudioAgent`) runs its `run()` loop on its own **daemon thread** started from `replay.run_scenario`; the tick-based agents (`FusionAgent`) run their periodic logic on an internal thread spawned by `Agent.start()`.
- Shared mutable dicts accessed from multiple threads (`FusionAgent._hypotheses`, `CoordinatorAgent._bids`/`_verifications`) are guarded by a plain `threading.Lock` around each read-modify-write — coarse-grained but correct, appropriate given message volumes are modest (event-level, not frame-level).
- `CoordinatorAgent.request_verification` is a **synchronous-over-async** pattern: it blocks the calling thread (Policy's) on a timed poll loop waiting for an async pub/sub reply — a pragmatic simplification (no futures/asyncio) that keeps `PolicyAgent.on_hypothesis` a straight-line, easy-to-audit synchronous function, at the cost of tying up a thread for up to 3s per gray-zone hypothesis.
- Failure isolation is bus-level: `LocalBus.publish` and `MqttBus._on_message` both wrap each subscriber callback in `try/except Exception: log.exception(...)` so one misbehaving agent can't crash the publisher or other subscribers — an important robustness property for a system meant to survive optional/flaky ML dependencies.

---

## 7. Developer Takeaways & Mental Model Summary

### Mental model

Think of AURA-MAS as **a newsroom, not a machine**:
- **Camera/AudioAgents are field reporters** — each files independent, unverified reports (`Event`) the moment they see something.
- **FusionAgent is the wire desk** — it doesn't investigate, it just notices when multiple reporters are describing the same story within a time/place window and bumps up its credibility.
- **CoordinatorAgent is an assignment editor** — for a story that's plausible but unconfirmed, it puts out a call ("who's near zone_A?") and dispatches whichever reporter is best positioned to double-check.
- **PolicyAgent is the sole editor-in-chief who can approve publication** — deterministic style rules (thresholds, a "don't republish the same story within 20s" rule), and every accept/reject decision goes in the masthead's permanent log.
- **ExplanationAgent is a copy-editor, hired *after* the story is approved**, who is only allowed to write using facts already in the approved story — never allowed to add a new fact, and fact-checked against the source list before print.

If you remember only one line: **perception is distributed and best-effort; the alert decision is centralized, deterministic, and audited; the narrative is generated last and can never overrule the decision.**

### Trade-offs, bottlenecks, technical debt

- **Coarse-grained polling in the auction path** (`time.sleep(bid_window)`, 50ms verification poll) — simple and testable, but adds fixed latency (`bid_window` + up to 3s) to every gray-zone verification; an event-driven `Condition`/future-based rendezvous would cut this but adds complexity the thesis doesn't need to prove its point.
- **Fixed reliability weights** (`MODALITY_RELIABILITY = {"video": 0.9, "audio": 0.7}`) and **hand-tuned thresholds** (`ALERT_THRESHOLDS`, `gray_zone=(0.35, 0.75)`) are not learned from data — reasonable for a controlled experimental system, but would need calibration against a real deployment's false-positive cost before production use.
- **`_verify`'s re-detection cost is unmeasured against its benefit inside the code itself** — the auction's ROI (does re-verification actually reduce false alerts more than it costs in latency/compute?) is the kind of question `eval/metrics.py`'s `mean_allocation_ms` and `false_alerts_per_hour` columns are built to answer, but only once real ablation runs are executed — currently `results/` and `data/` are present but scenario clips (`data/clips/*.mp4|wav`) referenced by manifests don't ship in this snapshot, so `replay.py` needs real media before it can run end-to-end.
- **Root-directory file duplication** (loose `bus.py`, `camera_agent.py`, etc. alongside `aura_mas/`) is dead weight for anyone editing the code — always edit under `aura_mas/`, since that's what `scenarios/replay.py` and the test suite import.
- **README references a `configs/` directory** ("site zones, thresholds") that doesn't currently exist in the repo — zone/threshold config is inline in scenario JSON and the `SEVERITY_MAP`/`ALERT_THRESHOLDS` module constants instead; minor doc drift, not a functional gap.
- **`ExplanationAgent`'s guardrail is regex/set-based, not semantic** — it stops literal ID fabrication but wouldn't catch a subtler hallucination (e.g., misattributing a real cited event's contents). Sufficient for the thesis's specific "no invented evidence IDs" claim, but a known scope limit worth stating explicitly if the thesis defense gets probed on it.

### Suggested starting points for modification

- **Adding a new event type** (e.g., "fence climbing"): add detection logic to `ZoneRuleEngine` or `CLIP.ANOMALY_PROMPTS`, then register it in `EVENT_FAMILIES` (fusion_agent.py) and `SEVERITY_MAP`/`ALERT_THRESHOLDS` (policy_agent.py) — three small, well-isolated edits, no other files touch event-type strings.
- **Changing the fusion math**: everything lives in the single static method `FusionAgent._fuse_confidence` — it's pure (dataclass in, float out), so it's trivially unit-testable in isolation exactly as `test_fusion_noisy_or_increases_with_corroboration` already demonstrates.
- **Running the ablation suite yourself**: `README.md`'s §"Thesis ablations produced by this code" is literally a runnable recipe — start there, and put real clips at the paths scenario JSONs expect (`data/clips/...`) before invoking `replay.py`.
- **Understanding the guardrail contract before touching `explanation_agent.py`**: read `test_explanation_guardrail_rejects_fabricated_evidence` first — it's the executable specification of what "safe" means for that module.
