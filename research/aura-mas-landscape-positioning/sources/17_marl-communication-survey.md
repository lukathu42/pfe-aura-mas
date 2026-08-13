---
source_type: paper
credibility: 4
recency: 2024
directly_relevant: yes
---

# Zhu, Dastani & Wang — "A Survey of Multi-Agent Deep Reinforcement Learning with Communication"

## Bibliographic metadata

- **Title:** A Survey of Multi-Agent Deep Reinforcement Learning with Communication
- **Author(s):** Changxi Zhu, Mehdi Dastani, Shihan Wang
- **Affiliation:** Department of Information and Computing Sciences, Utrecht University
- **Year:** 2024 (v2, 18 Oct 2024)
- **Venue:** arXiv preprint (arXiv:2203.08975v2, cs.MA)
- **Length:** 34 pages

## Research problem

In multi-agent deep reinforcement learning (MADRL), agents typically face partial observability (no access to global state) and non-stationarity (the environment appears to change because other agents' policies are simultaneously changing/learning). Communication among agents — sharing observations, intentions, experiences, or derived features — is a well-known mechanism to mitigate both problems and improve coordination, but the growing body of "Comm-MADRL" research lacks a systematic, structural way to classify, compare, and analyze existing communication-based MADRL approaches, making it hard to identify trends, gaps, and promising future combinations of design choices.

## Proposed approach

A systematic survey proposing **9 analytical dimensions** along which Comm-MADRL approaches can be classified, compared, and combinatorially explored: these span *what* is communicated, *how* communication is structured, and *how* communication is learned/optimized. The survey projects a large body of existing Comm-MADRL work onto this multi-dimensional space to identify empirical trends (which dimension-combinations are common vs. unexplored) and proposes novel directions by considering under-explored combinations of the 9 dimensions.

## Architecture/method

The 9 proposed dimensions (as reconstructed from the survey's tables and discussion) characterize Comm-MADRL systems along axes including: **what is communicated** (raw observations vs. learned/compressed messages/embeddings vs. intentions/plans vs. value estimates); **communication scope/topology** (broadcast to all agents vs. targeted/selective communication to specific agents or subgroups, vs. learned attention-based addressing); **communication timing/scheduling** (every timestep vs. gated/conditional communication triggered by learned importance signals, to reduce bandwidth); **centralized vs. decentralized training and execution** paradigms (CTDE — centralized training, decentralized execution — being a dominant pattern); **differentiable vs. non-differentiable communication channels** (whether gradients can flow through the communication channel during training, enabling end-to-end learned communication protocols, e.g., CommNet/TarMAC-style architectures, vs. discrete/non-differentiable message passing requiring other training tricks); **communication architecture** (graph neural network-based message passing among agents modeled as nodes, attention mechanisms for selective message aggregation, recurrent memory for message history); **cooperative vs. competitive vs. mixed reward structures** and how communication is used differently across these settings; **robustness considerations** (communication noise, delay, bandwidth/latency constraints, and their tolerance); and **scalability** (how communication-based approaches perform/degrade as the number of communicating agents grows). Later sections (per the pages reviewed) present detailed comparison tables of specific published Comm-MADRL algorithms across these dimensions, discuss learning methods and training schemes for communication protocols, and synthesize "findings" and "research directions" from cross-referencing the dimension space.

## AI/ML techniques

Deep reinforcement learning (value-based, e.g., DQN-family; policy-gradient/actor-critic methods); graph neural networks for structured multi-agent message passing; attention mechanisms for learned, selective inter-agent communication; centralized critic / decentralized actor (CTDE) training paradigms; differentiable communication channel learning (backpropagation through discrete or continuous communication signals). No LLM-based agent communication is covered (the survey's timeframe/scope predates the LLM-agent wave — it is a MARL-communication survey in the classical RL sense, not an LLM-agent-orchestration survey).

## Agent-based components

**Explicit yes — this is a survey entirely about multi-agent systems and inter-agent communication as a first-class design object.** It is squarely MAS/MARL literature: agents, partial observability, non-stationarity, and communication protocols among agents are the paper's core subject matter throughout. This is one of the most directly MAS-theoretic papers in the entire supplementary corpus (alongside source 19, the consensus-based task allocation paper), even though it is not surveillance-specific.

## Dataset(s)

Not applicable in a single-dataset sense — as a survey, it references the standard MARL benchmark environments used across the surveyed papers (implied: cooperative navigation / predator-prey / StarCraft Multi-Agent Challenge (SMAC)-style environments and similar are the conventional Comm-MADRL testbeds in this literature, consistent with citations visible in the paper's reference list, though specific benchmark names were not exhaustively captured in the reviewed pages).

## Evaluation methodology

Meta-level: systematic literature classification along the proposed 9-dimensional taxonomy, comparative tables mapping surveyed papers to their choices along each dimension, and a synthesis of empirical/qualitative "findings" (patterns in what combinations of dimensions tend to be used together, and why) drawn from the surveyed literature rather than new experiments.

## Main results

The survey's "results" are structural/synthetic: (1) a 9-dimensional classification framework for Comm-MADRL, presented via detailed comparison tables (the reviewed pages show Tables 8, 9, 10 cataloging specific algorithms and their dimension values); (2) identification of dominant design patterns (e.g., CTDE as the prevailing training paradigm, differentiable/learned communication as increasingly favored over hand-designed protocols); (3) identification of gaps/under-explored combinations in the 9-D space, used to motivate proposed future research directions (e.g., combining scalable, bandwidth-constrained, robustness-aware, and cooperative-competitive-mixed settings in ways not yet jointly studied in the literature).

## Limitations

The survey itself does not report new empirical benchmarks — its conclusions are drawn from synthesizing prior work, so its "findings" are only as reliable as the surveyed papers' original reported results, and the field's rapid pace (MARL communication research evolving quickly, plus the more recent rise of LLM-based agent communication not covered here) means later work may already exceed this survey's classification's descriptive power for the newest architectures.

## Claimed contributions

- Nine analytical dimensions for systematically classifying and comparing Comm-MADRL approaches — filling a gap in structural/comparative frameworks for this subfield.
- A projection of a substantial body of existing Comm-MADRL research onto this multi-dimensional space, revealing trends in which dimension combinations are common.
- Identification of interesting/promising directions for designing future Comm-MADRL systems by exploring currently under-combined dimension pairs/tuples.

## Verbatim quotes

1. "Communication is an effective mechanism for coordinating the behaviors of multiple agents, broadening their views of the environment, and to support their collaborations. In the field of multi-agent deep reinforcement learning (MADRL), agents can improve the overall learning performance and achieve their objectives by communication." (Abstract)

2. "As agents are often distributed in the environment where they only have access to their local observations rather than the complete state, partial observability becomes an essential assumption in MARL. Moreover, MARL suffers from the non-stationary issue, since each agent faces a dynamic environment that can be influenced by the changing and adapting policies of other agents. Communication has been viewed as a vital means to tackle the problems of partial observability and non-stationary in MARL." (Introduction, p.1)

3. "With the growing body of research work in MADRL with communication (Comm-MADRL), there is a lack of a systematic and structural approach to distinguish and classify existing Comm-MADRL approaches. In this paper, we survey recent works in the Comm-MADRL field and consider various aspects of communication that can play a role in designing and developing multi-agent reinforcement learning systems." (Abstract)

4. "We propose 9 dimensions along which Comm-MADRL approaches can be analyzed, developed, and compared. By projecting existing works into the multi-dimensional space, we discover interesting trends. We also propose some novel directions for designing future Comm-MADRL systems through exploring possible combinations of the dimensions." (Abstract)

## Relevance to the MAS-surveillance thesis

**Highly relevant** as a coordination-mechanisms reference: this survey is explicitly named in the task brief's list of relevant topics ("coordination/task-allocation mechanisms... MARL"), and it directly addresses the theoretical/architectural question of *how agents in a MAS should communicate to coordinate effectively* — a core design decision for any multi-agent surveillance system where, e.g., multiple camera/detection agents need to share observations or alerts, or a tracking agent needs to coordinate hand-offs with neighboring-camera agents (echoing the cross-camera coordination problem also seen in Monitorix, source 11). Its 9-dimensional taxonomy (what to communicate, when, to whom, how learned, CTDE vs. fully decentralized, robustness to noise/bandwidth) gives the thesis a principled vocabulary for justifying its own agent-communication design choices, and its discussion of scalability and bandwidth/robustness constraints is directly applicable to a real-time, potentially many-camera, resource-constrained surveillance deployment. Its main limitation for direct reuse is that it is classical MARL-communication (learned numeric/vector messages, not natural-language LLM-agent communication), so the thesis will likely need to bridge this MARL-communication framing with the more recent LLM-agent-orchestration framing found in sources 10 and 12.
