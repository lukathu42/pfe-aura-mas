---
source_type: paper
credibility: 3
recency: 2025
directly_relevant: yes
---

# Sapkota, Roumeliotis & Karkee — "AI Agents vs. Agentic AI: A Conceptual Taxonomy, Applications and Challenges"

## Bibliographic metadata

- **Title:** AI Agents vs. Agentic AI: A Conceptual Taxonomy, Applications and Challenges
- **Author(s):** Ranjan Sapkota, Konstantinos I. Roumeliotis, Manoj Karkee
- **Affiliations:** Cornell University, Dept. of Biological and Environmental Engineering (USA); University of the Peloponnese, Dept. of Informatics and Telecommunications (Greece)
- **Year:** 2025 (v4, 28 May 2025)
- **Venue:** arXiv preprint (arXiv:2505.10468v4, cs.AI) — not a peer-reviewed venue as of the version read; framed as a "review" article
- **Length:** 36 pages, ~237 references

## Research problem

The paper addresses definitional and architectural confusion in the literature between two terms used almost interchangeably in practice: "AI Agents" and "Agentic AI." It argues these denote genuinely different system classes (single, modular, task-specific automators vs. orchestrated, multi-agent, goal-directed collectives) and that this conflation obscures real differences in design philosophy, capability, and failure modes, making it hard to compare systems, choose architectures, or reason about limitations.

## Proposed approach

A structured, literature-based conceptual taxonomy rather than an empirical study or new system. The paper: (1) defines AI Agents as LLM/LIM-powered, modular, task-specific systems with constrained autonomy and reactivity, largely built for narrow automation (customer support, scheduling, email triage); (2) defines Agentic AI as a paradigm shift characterized by multi-agent collaboration, dynamic task decomposition, persistent memory across interactions, and orchestrated (centralized or decentralized) autonomy across a team of specialized agents; (3) chronologically traces architectural evolution from classical rule-based/symbolic agents (MYCIN, DENDRAL, SOAR, subsumption architecture, ELIZA) through LLM-driven agents to today's orchestrated multi-agent systems; (4) maps application domains for each paradigm; (5) catalogs failure modes and limitations specific to each; (6) proposes ten "potential solution" architectural mechanisms (RAG, tool-augmented reasoning/function calling, the ReAct reasoning-action-observation loop, episodic/semantic/vector memory architectures, multi-agent orchestration with role specialization, reflexive self-critique, programmatic prompt pipelines, causal modeling/simulation-based planning, monitoring/auditing/explainability pipelines, and governance-aware role-isolated architectures).

## Architecture/method

Not an implemented system — a comparative conceptual/architectural framework. Key architectural claims relevant to a MAS-surveillance thesis:
- **AI Agents:** single LLM/LIM core + tool access + limited memory; operate within a bounded, task-specific scope; largely reactive, single-pass or shallow-loop execution.
- **Agentic AI:** a **meta-agent/orchestrator** (a supervisory agent, e.g., as in MetaGPT/ChatDev-style systems) dynamically allocates tasks, manages dependencies, and maintains global context across a team of role-specialized agents (e.g., planner, retriever, verifier, summarizer). Each agent maintains local memory while accessing shared global memory. Coordination is described as occurring via structured, multi-step orchestrated pipelines with defined behavioral boundaries between agents (reducing overlapping/conflicting decisions), rather than ad hoc prompt chaining.
- Figure 13 in the paper diagrams ten architectural/algorithmic mechanisms (RAG, tool-augmented reasoning, agentic ReAct loop, memory architectures, multi-agent orchestration with role specialization, reflexive/self-critique mechanisms, programmatic prompt pipelines, causal modeling/simulation-based planning, monitoring/auditing/explainability pipelines, governance-aware architectures with accountability + role isolation) as the proposed toolkit for building robust Agentic AI.

## AI/ML techniques

LLMs and LIMs (Large Image/Vision-Language Models) as the reasoning core; retrieval-augmented generation (RAG); function calling/tool use; ReAct-style iterative reasoning-action-observation loops; reflection/self-critique (Reflexion-style verbal reinforcement); causal modeling and simulation-based planning (STRIPS/PDDL mentioned as classical planning formalisms agents could be governed by). No original model training or benchmark results are presented — this is a synthesis/survey, not an empirical ML paper.

## Agent-based components

**Explicit yes — this is the paper's entire subject.** It explicitly distinguishes single-agent ("AI Agent") systems from true multi-agent ("Agentic AI") systems, and characterizes Agentic AI by: distributed cognition across specialized agents, centralized or decentralized orchestration/control, role-based task delegation, inter-agent communication protocols, and coordinated/collective decision-making. It references concrete multi-agent orchestration frameworks (MetaGPT, ChatDev) as exemplars of role-specialized, predefined-role (CEO, software engineer, reviewer) agent teams communicating via structured messaging protocols.

## Dataset(s)

None — this is a conceptual/literature review paper, not an empirical study. No benchmarks, datasets, or quantitative evaluation are used.

## Evaluation methodology

None in the empirical sense. The "evaluation" is a structured literature synthesis and comparative framework (taxonomy tables, architecture diagrams, application-domain mapping, and a challenges/limitations enumeration for each paradigm).

## Main results

Not applicable (no experiments). The paper's "results" are conceptual: (1) a clear definitional/taxonomic separation between AI Agents and Agentic AI; (2) an application-domain map showing AI Agents dominate narrow automation while Agentic AI is emerging in collaborative research, swarm robotics, medical decision support, and adaptive workflow automation; (3) a roadmap of ten solution mechanisms and a five-pronged future trajectory for each paradigm (AI Agents: proactive intelligence, tool integration, causal reasoning, continuous learning, trust & safety; Agentic AI: multi-agent scaling, unified orchestration, persistent memory, simulation planning, ethical governance, domain-specific systems).

## Limitations

The paper itself is a preprint, non-peer-reviewed synthesis with no original experiments — its claims are argumentative/taxonomic rather than empirically validated, and it explicitly acknowledges (Section V) that Agentic AI systems currently suffer from: unpredictable/uncontrollable emergent behavior; scalability and debugging complexity from opaque, non-compositional multi-agent chains; poor trust/explainability/verifiability (no formal verification tools exist for multi-agent LLM systems); a significantly expanded attack surface and single-point-of-compromise risk from shared memory/messaging (prompt injection, model poisoning propagating across agents); accountability gaps and bias amplification/propagation across interacting agents; value misalignment/drift in long-horizon multi-agent settings; and an overall "immature foundations" problem — no standard architectures, no causal-discovery tooling, fragile ad hoc implementations that resist comparison or generalization.

## Claimed contributions

- A structured conceptual taxonomy distinguishing AI Agents from Agentic AI along dimensions of autonomy, orchestration, memory, and collaboration.
- A chronological architectural-evolution narrative from symbolic/rule-based agents to LLM-driven agents to orchestrated multi-agent Agentic AI.
- An application-domain comparison contrasting where each paradigm is deployed today.
- A unified challenges/limitations analysis specific to each paradigm (hallucination/brittleness for AI Agents; coordination bottlenecks/emergent behavior/governance gaps for Agentic AI).
- A "potential solutions and future roadmap" proposing ten architectural/algorithmic mechanisms to advance both paradigms toward reliability and scalability.

## Verbatim quotes

1. "This review critically distinguishes between AI Agents and Agentic AI, offering a structured, conceptual taxonomy, application mapping, and analysis of opportunities and challenges to clarify their divergent design philosophies and capabilities." (Abstract)

2. "In contrast to AI Agents, Agentic AI systems, which represent a paradigm shift marked by multi-agent collaboration, dynamic task decomposition, persistent memory, and coordinated autonomy." (Abstract)

3. "Agentic AI architectures introduce a significantly expanded attack surface compared to single-agent systems, exposing them to complex adversarial threats. One of the most critical vulnerabilities lies in the presence of a single point of compromise. Since Agentic AI systems are composed of interdependent agents communicating over shared memory or messaging protocols, the compromise of even one agent... can propagate malicious outputs or corrupted state across the entire system." (Section V.6, p.25)

4. "There is currently no widely accepted blueprint for how to design, monitor, or evaluate multi-agent systems built on LLMs. This architectural fragmentation makes it difficult to compare implementations, replicate experiments, or generalize findings across domains." (Section V.8, p.26)

## Relevance to the MAS-surveillance thesis

This paper is highly relevant as a **conceptual/vocabulary anchor** for a thesis on "agentic multi-agent surveillance systems": it directly supplies the definitional distinction (AI Agent vs. Agentic AI) that the thesis needs to justify why its system is "agentic" and not just a modular pipeline, and its ten architectural mechanisms (role-specialized orchestration, persistent/shared memory, reflexive self-critique, governance-aware role isolation, causal/simulation-based planning) map closely onto design choices a surveillance MAS would need to make (e.g., a detector agent, a tracker agent, an anomaly-reasoning agent, and an orchestrator/alerting agent coordinating via structured messaging). It is not surveillance-specific and contains no computer-vision, tracking, or camera content — its value is entirely as an architecture/taxonomy reference and as a source of the field's own catalog of known failure modes (single point of compromise via shared agent memory, accountability gaps, emergent uncontrolled behavior) that the thesis should proactively address or at least acknowledge as open problems. As a non-peer-reviewed preprint with a broad, somewhat promotional "roadmap" tone, it should be cited as a framing/positioning source rather than as evidence of any validated technique.
