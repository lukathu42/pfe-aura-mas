---
source_type: paper
credibility: 3
recency: 2000
directly_relevant: yes
---

# Abreu et al. — "Video-Based Multi-Agent Traffic Surveillance System" (Monitorix)

## Bibliographic metadata

- **Title:** Video-Based Multi-Agent Traffic Surveillance System
- **Author(s):** Bruno Abreu, Luís Botelho, Andrea Cavallaro, Damien Douxchamps, Touradj Ebrahimi, Pedro Figueiredo, Benoit Macq, Benoit Mory, Luís Nunes, Javier Orri, Maria José Trigueiros, Ana Violante
- **Affiliation/Consortium:** MODEST Consortium — ADETTI (Lisbon, Portugal), EPFL (Lausanne, Switzerland), LEP (Paris, France), UCL (Louvain, Belgium)
- **Year:** 2000
- **Venue:** Proceedings of the 2000 IEEE Intelligent Vehicles Conference, Ritz-Carlton Hotel, Dearborn, MI, USA, October 4-5, 2000
- **Length:** 6 pages
- **File:** iv2k.pdf

## Research problem

How to build a traffic surveillance system (multiple non-overlapping cameras along a highway) that automatically detects abnormal or relevant traffic situations by combining video analysis with a distributed agent-based software architecture — specifically addressing: what video processing approach to use, how to integrate video algorithms with agent technology, what agent architecture is suitable, and how to track vehicles across cameras whose fields of view do not overlap.

## Proposed approach

Monitorix: a fully decentralized multi-agent system, implemented on a standard **FIPA-compliant agent platform** using **FIPA ACL** (Agent Communication Language) messaging with **SL (Semantic Language)** content, where video-derived object descriptions are progressively abstracted and fused by a hierarchy of cooperating agents across four functional tiers, ultimately generating alarms for abnormal situations and supporting vehicle re-identification/tracking across non-overlapping camera fields via a traffic/prediction model.

## Architecture/method

**Four-tier agent architecture**, organized by the kind of information processing performed:
1. **Sensors and effectors tier** — cameras + processing units running VOK (Video Object Kernel), a data-driven, application-independent image-processing module that segments the scene and generates a sequence of object descriptions per camera (adaptive background subtraction, adaptive statistical change detection, competitive-learning-based mobile-object classification, statistically-adapted trajectory computation).
2. **Objective description tier** — agents that receive VOK's per-camera descriptions and perform higher-level analyses to detect/describe abnormal or relevant situations.
3. **Application assistant tier**
4. **User assistant tier**

**Middle agent — "Proxy":** VOK (the non-agent, low-level vision module) is integrated into the agent society via a special middle agent called Proxy. VOK runs as a server co-located with the camera's processing unit; Proxy runs as a client on a separate computer and mediates between the raw vision output and the agent society — an explicit **agentification bridge pattern** between a classical CV pipeline and a MAS.

**Agent internal architecture:** Each agent's control/decision logic is implemented via a **BDI (Belief-Desire-Intention)-like architecture**, realized concretely as a **production (rule) system**. Agents communicate exclusively by requesting information from other agents that provide it ("pull"/request-based interaction is emphasized as the control/communication paradigm), using FIPA ACL messages whose content is expressed in SL, a modal-logic-based content language with belief, goal, intention, uncertainty, and action operators. Each agent defines its own set of predicates, functions, and actions referenceable in messages it receives.

**Cross-camera tracking:** The **Tracker agent** re-identifies/tracks vehicles across non-overlapping camera views using an improved version of a pre-existing traffic model, whose parameters are continuously updated online by learning algorithms as vehicles move from one camera's scope into the next (i.e., a prediction model of inter-camera transit that adapts itself).

## AI/ML techniques

- Adaptive, data-driven background subtraction and statistical change detection for foreground/vehicle segmentation.
- Competitive learning algorithms for mobile-object classification.
- Statistical adaptation for typical-trajectory computation.
- An online-updated traffic/prediction model (parameters tuned by learning algorithms) for cross-camera vehicle re-identification/tracking.
- BDI-style symbolic reasoning (production/rule system) for agent decision-making — not statistical/ML-based agent cognition; the "intelligence" of the coordination layer is classical symbolic AI (rules + logic-based ACL content), while the "intelligence" of the low-level perception (VOK) is adaptive/statistical.
- No deep learning (predates the deep learning era); no LLMs.

## Agent-based components

**Explicit yes — the paper's central architectural claim.** This is a genuine, fully decentralized multi-agent system built on a standards-compliant agent platform (FIPA) with real inter-agent negotiation/request protocols (FIPA ACL + SL), a BDI-like reasoning architecture per agent, a specialized middle "Proxy" agent bridging raw CV output into the agent society, and a dedicated "Tracker" agent performing the cross-camera identity-linking task. Multiple agent tiers exist (sensor/effector, objective-description, application-assistant, user-assistant), representing role specialization comparable to a modern orchestrator + specialized-worker-agents pattern, but here implemented with 2000-era symbolic/BDI agent technology rather than LLM-based agents.

## Dataset(s)

Not specified in the extracted content (paper is a system/architecture description rather than a benchmark evaluation); highway camera footage from the deployed Monitorix testbed cameras is implied but no named public dataset or quantitative accuracy tables are presented in the pages reviewed.

## Evaluation methodology

The paper is architecture/system-description-oriented rather than benchmark-evaluation-oriented; no formal quantitative evaluation protocol (e.g., detection/tracking accuracy metrics) is presented in the reviewed content — it documents design decisions and rationale ("During the development of Monitorix we faced the following questions...") more than measured performance.

## Main results

A working, fully decentralized multi-agent video surveillance prototype (Monitorix) integrating adaptive vision algorithms with FIPA-standard agent technology; demonstrated capability to detect abnormal/relevant traffic situations and to track vehicles across non-overlapping camera views via the Tracker agent's continuously-adapted traffic model.

## Limitations

As a 6-page conference paper from 2000, the description is architectural/positional rather than deeply empirical — no benchmark accuracy numbers, scalability analysis, or failure-mode discussion are present in the excerpted content. The system predates deep learning entirely: its "adaptive learning" is classical statistical/competitive learning, not CNNs or modern trackers, so its perception layer is far weaker than 2020s computer vision by construction. Communication/coordination is a fixed request-response protocol (agents request info from providers) rather than negotiation, auction, or contract-net task allocation — coordination sophistication is limited relative to later MARL/negotiation-based MAS literature.

## Claimed contributions

- A fully decentralized, FIPA-standard multi-agent architecture for real-time video-based traffic surveillance, explicitly integrating video analysis algorithms and agent technology via a middle "Proxy" agent.
- A four-tier agent taxonomy (sensors/effectors, objective description, application assistant, user assistant) organizing the system by information-processing role.
- A BDI-like, production-system-based agent control architecture communicating via FIPA ACL/SL.
- A Tracker agent performing cross-camera (non-overlapping FOV) vehicle re-identification using an online-adapted traffic/prediction model.
- An explicit, reusable answer to the practical integration question "how do you connect a non-agent computer-vision pipeline to a multi-agent system" (the Proxy middle-agent pattern).

## Verbatim quotes

1. "This paper describes Monitorix, a video-based traffic surveillance multi-agent system. Monitorix agents are grouped in four tiers, according to the kind of information processing they perform: the sensors and effectors tier, the objective description tier, the application assistant tier, and the user assistant tier." (Abstract)

2. "The integration of video analysis algorithms and agent technology is made via a special middle agent called Proxy. VOK runs as a server in the processing unit of the camera; Proxy runs as a client in a different computer." (Abstract)

3. "Monitorix is a fully decentralised multi-agent system living in a FIPA Platform and using FIPA Agent Communication Language. The Tracking of vehicles across non-overlapping cameras is performed by the Tracker agent, using a traffic model and learning algorithms that tune the model parameters." (Abstract)

4. "The interaction of an agent with the others is controlled by a BDI-like architecture implemented by a production system. Agents communicate using FIPA ACL messages with SL contents. SL is a content language based on a modal logic with belief, goal, intention, uncertainty and action operators." (Introduction, p.1)

## Relevance to the MAS-surveillance thesis

This is arguably the single most directly on-topic paper in the supplementary corpus: it is a genuine multi-agent system (FIPA-standard platform, real ACL messaging, BDI-based agent reasoning, role-specialized agent tiers) applied specifically to **video surveillance** (traffic monitoring across multiple non-overlapping cameras), addressing exactly the sensing-plus-coordination problem a MAS surveillance thesis needs to engage with — including the practical "how do you bridge a CV pipeline into an agent society" problem via its Proxy middle-agent pattern, and a concrete cross-camera re-identification/tracking agent. Its main limitation as a modern reference is age (2000): it predates deep learning, LLM-based agentic reasoning, and modern MOT/Re-ID techniques entirely, so it is best used as a **historical architectural precedent** — evidence that "agentic MAS for video surveillance" is not a new idea but a two-decades-old research direction — while the thesis's own contribution should be framed as modernizing this architecture with contemporary perception (deep detectors/trackers) and contemporary agent reasoning (LLM-based/agentic planning) in place of Monitorix's classical statistical vision and symbolic BDI production rules.
