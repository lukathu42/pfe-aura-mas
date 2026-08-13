---
source_type: paper
credibility: 3
recency: 2025
directly_relevant: partial
---

# Belcak et al. (NVIDIA Research) — "Small Language Models are the Future of Agentic AI"

## Bibliographic metadata

- **Title:** Small Language Models are the Future of Agentic AI
- **Author(s):** Peter Belcak, Greg Heinrich, Shizhe Diao, Yonggan Fu, Xin Dong, Saurav Muralidharan, Yingyan Celine Lin, Pavlo Molchanov
- **Affiliations:** NVIDIA Research; Georgia Institute of Technology
- **Year:** 2025 (v1, 2 Jun 2025)
- **Venue:** arXiv preprint (arXiv:2506.02153v1, cs.AI) — marked "Preprint. Under review."
- **Length:** 17 pages
- **Correspondence:** research.nvidia.com/labs/lpr/slm-agents

## Research problem

Modern agentic AI systems overwhelmingly use large, general-purpose LLMs (accessed via centralized cloud API endpoints) as the reasoning core for every agent invocation, even though agentic systems typically call the LM repeatedly to perform a **small, repetitive set of specialized, narrow subtasks** (tool calls, formatting, routing, simple reasoning steps) rather than requiring broad open-ended conversational ability at every step. The paper poses the position/value question: given current small language model (SLM) capabilities and the structure/economics of real agentic systems, should SLMs — not LLMs — be the default building block for most agent invocations?

## Proposed approach

An argumentative **position paper** (not a new system or benchmark), structured around three pillars of evidence: (1) SLMs (models suitable for consumer/edge-class hardware) are already sufficiently capable for many of the narrow, repetitive subtasks agents actually perform, citing recent SLMs (e.g., Phi, Hymba/Nemotron-family, DeepSeek-R1-Distill, Qwen small variants) that match or approach LLM performance on tool-calling, instruction-following, and code-generation subtasks; (2) the common architecture of agentic systems (modular, tool-augmented, repeatedly invoking the LM for narrow formulaic operations) is inherently more suitable for specialized SLMs than for general-purpose LLMs; (3) SLMs are economically necessary — 10-30x cheaper/faster to serve (lower latency, memory footprint, energy) than LLMs, and this cost differential compounds because agentic systems make very high call volumes. The paper further argues that **heterogeneous agentic systems** — where different agents in the same system invoke different models (SLMs for narrow/repetitive subtasks, LLMs reserved only for genuinely open-ended, general-conversational sub-tasks) — are the natural architecture once the shift begins, and proposes a general **LLM-to-SLM agent conversion algorithm** (a migration recipe) plus a discussion of adoption barriers.

## Architecture/method

Not an implemented system; the "architecture" contribution is the proposed **LLM-to-SLM conversion algorithm** for migrating an existing agentic system: (1) collect representative logs of the agent's actual LLM invocations in production/use; (2) curate/secure the data (removing sensitive info) and cluster invocations by task type; (3) select suitable pre-existing SLMs per task cluster, or fine-tune/distill an SLM specifically for each cluster (using LLM outputs as supervision, or task-specific data curation) — effectively decomposing the single monolithic LLM-agent into a set of specialized SLM-agents-per-subtask, orchestrated by whatever control logic the original agentic system already uses; (4) iteratively refine by measuring per-task performance and falling back to an LLM only where an SLM proves insufficient. This describes a **heterogeneous multi-model agentic architecture** where model choice is itself a per-agent/per-subtask design decision rather than a system-wide constant.

## AI/ML techniques

Small language models (model compression via distillation/fine-tuning implied, not detailed as novel technique); references to instruction-tuning and tool-calling fine-tuning as means of specializing SLMs for narrow agent subtasks; no reinforcement learning or novel training method is introduced — the paper is a position/synthesis paper citing existing SLM capability results (Phi, Nemotron/Hymba, DeepSeek-R1-Distill, Qwen) rather than reporting new experiments.

## Agent-based components

**Describes, not implements.** The paper is fundamentally about agentic AI system *composition* — it explicitly discusses heterogeneous agentic systems (multiple agents in one system, each potentially backed by a different model), tool-augmented agent invocation patterns, and the general architecture of "modern agentic systems" (planner/executor/tool-caller roles) as the backdrop for its cost/capability argument, but it does not design, build, or evaluate a specific multi-agent coordination protocol — no new orchestration mechanism, negotiation protocol, or MAS architecture is proposed. Its contribution is orthogonal to *how* agents coordinate and instead addresses *what model should power each agent*.

## Dataset(s)

None original — the paper cites third-party benchmark results for SLM capability claims (tool-calling benchmarks, instruction-following benchmarks referenced from prior SLM papers) rather than running new evaluations.

## Evaluation methodology

None original; argumentative/position-paper methodology backed by literature citation of existing SLM vs. LLM capability and cost comparisons, plus an economic cost-modeling argument (per-token/per-invocation serving cost multiplied by typical agentic call volume).

## Main results

Not empirical results in the traditional sense — the paper's "results" are its position claims: (1) SLMs are already capable enough for a large fraction of real agentic subtasks; (2) SLM inference is reported as roughly an order of magnitude (10-30x) cheaper/faster to serve than comparable LLMs; (3) heterogeneous (mixed SLM/LLM) agentic architectures are argued to be the natural and economically rational end state as the agentic AI industry matures; the agentic AI sector itself is cited as valued at USD 5.2bn in late 2024 and projected to approach USD 200bn by 2034, framing the economic stakes of the model-choice argument.

## Limitations

Self-identified: the paper explicitly discusses "potential barriers for the adoption of SLMs in agentic systems" (implying real adoption friction — e.g., tooling/ecosystem maturity, developer inertia toward familiar large-model APIs, cases genuinely requiring broad general-purpose conversational ability). As a position paper it presents an argument rather than a validated system; it does not itself empirically demonstrate the LLM-to-SLM conversion algorithm on a concrete agentic benchmark, and it is explicitly "under review" (non-peer-reviewed at time of reading), so its central claims should be treated as an industry-research position rather than settled empirical fact.

## Claimed contributions

- A formal position/value statement that SLMs are "sufficiently powerful, inherently more suitable, and necessarily more economical" for many agentic-system invocations, and are therefore the future of agentic AI.
- An argument for heterogeneous agentic architectures (mixed SLM/LLM agents) as the natural design once cost/capability trade-offs are taken seriously.
- A general LLM-to-SLM agent conversion algorithm intended as a practical migration recipe for existing agentic systems.
- A discussion of adoption barriers, framed as an invitation for community contribution and critique (the authors explicitly solicit responses/critiques to their position).

## Verbatim quotes

1. "Here we lay out the position that small language models (SLMs) are sufficiently powerful, inherently more suitable, and necessarily more economical for many invocations in agentic systems, and are therefore the future of agentic AI." (Abstract)

2. "We further argue that in situations where general-purpose conversational abilities are essential, heterogeneous agentic systems (i.e., agents invoking multiple different models) are the natural choice." (Abstract)

3. "A typical AI agent then simply communicates with a chosen LLM API endpoint by making requests to centralized cloud infrastructure that hosts these models." (Section 1, p.1)

4. "As of late 2024, the agentic AI sector had seen more than USD 2bn in startup funding, was valued at USD 5.2bn, and was expected to grow to nearly USD 200bn by 2034." (Section 1, p.1)

## Relevance to the MAS-surveillance thesis

**Partially relevant** — this paper contains no computer vision, video, or surveillance content at all, and its contribution is an infrastructure/economics position rather than a coordination architecture or perception technique. Its relevance to the thesis is as a **practical design consideration for the thesis's own system**: if the proposed surveillance MAS uses multiple LLM-backed agents (e.g., a detection-triage agent, a tracking-reasoning agent, an alert-summarization agent, an orchestrator), this paper offers a directly applicable argument for making that a *heterogeneous* architecture — using small/specialized models for narrow, repetitive, well-defined agent subtasks (e.g., classifying an event as anomalous given structured detector output) and reserving larger LLMs only for genuinely open-ended reasoning (e.g., natural-language incident summarization for a human operator) — which is relevant to real-time/edge deployment constraints that a video surveillance system would face (latency, on-premise/edge inference cost, privacy of not sending video-derived data to cloud LLM APIs). It should be cited as a systems-engineering/cost-architecture reference for justifying model-selection choices in the thesis's proposed architecture, not as MAS-coordination or surveillance-technique literature.
