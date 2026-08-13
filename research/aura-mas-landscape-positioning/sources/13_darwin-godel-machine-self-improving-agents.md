---
source_type: paper
credibility: 4
recency: 2025
directly_relevant: partial
---

# Zhang, Hu, Lu, Lange & Clune — "Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents"

## Bibliographic metadata

- **Title:** Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents
- **Author(s):** Jenny Zhang*, Shengran Hu*, Cong Lu, Robert Lange†, Jeff Clune† (* co-authors, † co-senior authors)
- **Affiliations:** University of British Columbia, Vector Institute, Sakana AI, Canada CIFAR AI Chair
- **Year:** 2025 (v1, 29 May 2025)
- **Venue:** arXiv preprint (arXiv:2505.22954v1, cs.AI/cs.LG)
- **Length:** 64 pages (main body ~9 pages + extensive appendices)
- **Code:** open-sourced at github.com/jennyzzt/dgm

## Research problem

Most AI systems today rely on fixed, human-designed architectures and cannot autonomously and continuously improve themselves. The theoretical "Gödel machine" concept describes an AI that provably self-improves, but this is practically impossible because proving that an arbitrary code modification will improve performance is intractable. The paper asks: how can we build a *practical*, safe, empirically-grounded self-improving AI system that relaxes the Gödel machine's impossible proof requirement while still achieving open-ended, compounding self-improvement?

## Proposed approach

The **Darwin Gödel Machine (DGM)**: a coding agent (an LLM-powered agent with tool use for reading/writing/executing code) that iteratively **modifies its own codebase** and empirically validates each self-modification using held-out coding benchmark performance, rather than requiring a formal correctness proof. Inspired by biological evolution/open-endedness research, the DGM maintains a growing **archive of all previously discovered agent variants** (not just the single best one) and, at each iteration, samples a parent agent from the archive (selection probability roughly proportional to performance score and number of already-produced children) to self-modify — the parent analyzes its own benchmark evaluation logs, proposes a next feature/change, and implements that change into its own codebase, producing a new candidate agent. Each new agent is evaluated on the benchmark; only agents that still compile and retain the ability to edit code are added back to the archive (so they can serve as future parents/stepping stones). This is explicitly framed as a **population-based, open-ended search** ("Darwinian" branching-and-selection) as opposed to a single-lineage hill-climbing self-improvement loop.

## Architecture/method

- **Initial seed agent:** a single coding agent built around a frozen foundation model (Claude 3.5 Sonnet during self-modification; Claude 3.5 Sonnet or o3-mini during benchmark evaluation), equipped with two tools — a Bash tool (execute shell commands) and an edit tool (view/edit files and directories) — receiving one input prompt specifying the target repository, task statement, and testing framework.
- **Self-modification loop:** run for 80 iterations on SWE-bench (2 new agents generated in parallel per iteration) and 4 iterations on Polyglot; parent selection is roughly proportional to archive performance score and inversely related to how many children a parent has already spawned (favoring under-explored branches); the selected parent inspects its own evaluation logs, proposes the next improvement, and edits its own code to implement it, generating a child agent.
- **Staged evaluation for cost control:** new agents are first tested on a small task subset (10 tasks) to verify basic codebase-editing functionality; only agents that pass are evaluated on a larger 50-60 task subset; agents exceeding a 40% success heuristic and ranking top-2 in the archive are evaluated on the full 200-task subset.
- **Baselines for ablation:** "DGM w/o self-improve" (the meta-agent that edits code stays fixed at the initial agent, replicating the ADAS approach) and "DGM w/o open-ended exploration" (no archive — the system always self-modifies the single latest version, discarding history).
- **Safety architecture:** all execution and self-modification occurs in isolated sandboxed environments with strict time limits; self-modification is confined to the agent's own Python codebase (not the training script or underlying FM weights); the archive provides a fully traceable lineage of every modification for human review.

## AI/ML techniques

LLM-based coding agents with tool use (bash execution, file editing); population-based/open-ended search inspired by quality-diversity and evolutionary computation (explicitly analogized to biological evolution and Darwinian selection, distinct from gradient-based/RL self-improvement); empirical (benchmark-score-based) rather than formally-proven self-improvement validation; no reinforcement learning or gradient updates to the underlying FM weights — all improvement happens at the level of the agent's *code/prompts/tool-use workflow*, with the FM itself kept frozen.

## Agent-based components

**Single self-modifying agent lineage with an archive of variants — not a multi-agent coordination system.** This is important to note precisely: the DGM is fundamentally a *single coding agent* whose own code is the object of optimization; there is no team of concurrently-communicating specialized agents coordinating on a shared task at inference time (unlike Monitorix or the "AI Agents vs Agentic AI" orchestration pattern). The "population" is a population of *sequentially-evaluated agent versions* in an archive, not simultaneously-cooperating agents. It is included in this triage as medium/high relevance because it is a rigorous, well-evaluated example of **agentic self-improvement** (an "agentic AI" architectural mechanism explicitly listed in Sapkota et al.'s taxonomy) that a MAS-surveillance thesis could reference when discussing whether/how individual agents (e.g., a detection or anomaly-reasoning agent) might self-improve their own prompts/tool-use logic over time, and it is one of the most methodologically rigorous "agentic AI" papers in the entire supplementary corpus (real ablations, real baselines, real transfer experiments, explicit safety discussion).

## Dataset(s)

Two coding benchmarks: **SWE-bench** (SWE-bench Verified subset — human-annotator-filtered to ensure solvability; Python-only, multi-file edits) and **Polyglot** (multi-language: C++, Rust, Python, Go, etc.; single-file-from-scratch implementation tasks; more novel/less likely to be in FM pretraining data than SWE-bench).

## Evaluation methodology

Percentage of benchmark tasks solved (pass@1, i.e., no access to ground-truth test feedback during the agent's attempt), measured before and after DGM self-improvement, compared against: (1) DGM w/o self-improvement baseline, (2) DGM w/o open-ended exploration (archive) baseline, (3) checked open-source SOTA (best human-verified SWE-bench solution), (4) representative human-designed agent baseline (Aider, for Polyglot). Additional experiments test **cross-model transfer** (do DGM-discovered improvements generalize when the underlying FM is swapped, e.g., to o3-mini or Claude 3.7 Sonnet?) and **cross-task transfer** (does an agent evolved only on Python tasks generalize to non-Python Polyglot tasks?).

## Main results

- SWE-bench: coding agent success rate improves from **20.0% → 50.0%** over 80 DGM iterations.
- Polyglot (50-task subset): improves from 14.2% → 38.0%; on the **full** Polyglot benchmark, improves from 14.2% → 30.7%.
- DGM outperforms both ablation baselines (w/o self-improvement, w/o open-ended exploration/archive) on both benchmarks — both components (iterative self-modification and archive-based open-ended exploration) are shown to be independently necessary for sustained improvement.
- On SWE-bench, the DGM-discovered agent approaches but does not surpass the best human-handcrafted open-source SOTA solution; on Polyglot, the DGM-discovered agent **surpasses** the representative human-designed baseline (Aider).
- Discovered improvements **transfer across foundation models** (e.g., improvements discovered while self-modifying with Claude 3.5 Sonnet still improve performance when the underlying FM is swapped to o3-mini or Claude 3.7 Sonnet) and **transfer across programming languages** (agent evolved on Python-only tasks still improves on non-Python tasks, though slightly less than training on all languages).
- Concrete discovered improvements include: more granular file editing (line-level and string-replacement-based editing instead of whole-file view/replace), non-empty patch validation and retry logic, auto-summarization on context overflow, generating and ranking multiple candidate patches, and history-aware patch generation/ranking.

## Limitations

Self-identified: (1) the DGM still falls short of closed-source SOTA SWE-bench solutions, which benefit from elaborately handcrafted techniques by expert teams; (2) a single DGM run on SWE-bench takes about two weeks and incurs significant API cost, limiting scale; (3) self-modification is currently restricted to the agent's own Python codebase/prompts/workflow — it cannot yet rewrite its own training procedure or the underlying FM weights, a proposed future extension; (4) safety risk: self-modification optimized purely for benchmark performance could in principle introduce vulnerabilities or misalignment not captured by the evaluation metric, and iterative self-modification could produce increasingly complex, harder-to-interpret agent code, though the authors report finding no evidence of harmful/malicious behavior in this study's generated agents; (5) the open-ended exploration process itself (archive maintenance, parent-selection heuristic) is currently fixed/not modifiable by the DGM, left as future work.

## Claimed contributions

- The first self-improving system powered by foundation models that combines self-referential code modification with open-ended (archive-based) exploration.
- Empirical demonstration that both self-improvement and open-ended exploration are independently necessary for sustained performance gains (via controlled ablations).
- Demonstration that DGM-discovered improvements transfer across different underlying foundation models and across programming-language task domains, indicating the discovered improvements are general rather than narrowly overfit.
- A safety-conscious implementation and discussion (sandboxing, strict time limits, traceable modification lineage) intended as a template for responsibly studying self-improving AI.
- A concrete step toward "AI-Generating Algorithms" and self-accelerating AI development, while explicitly cautioning that the safety implications of more capable future self-improving systems must be kept "front and center."

## Verbatim quotes

1. "The DGM automatically improves itself from 20.0% to 50.0% on SWE-bench, and from 14.2% to 30.7% on Polyglot. We show that self-improvement enables continued progress, as the DGM outperforms the baseline where the same initial agent is repeatedly used to modify and generate new agents without self-improvement." (p.2)

2. "A Gödel machine is a theoretical idea of an AI that searches for ways that provably improve itself. In this paper, we propose Darwin Gödel Machine (DGM), an attempt to realize the long-held dream of creating a Gödel Machine. The DGM relaxes the Gödel machine's impractical requirement of theoretically proving that a change will improve the system, instead requiring empirical evidence from experiments to demonstrate that a proposed new version enhances performance." (Section 3, p.4)

3. "All experiments were done with safety precautions (e.g., sandboxing, human oversight). Overall, the DGM represents a significant step toward self-improving AI, capable of gathering its own stepping stones along a path that unfolds into endless innovation." (Abstract)

4. "Because open-ended exploration allows branching from any agent in the archive with non-zero probability, the DGM can get out of deceptive dips or peaks in performance. For example, at iterations 4 and 56 of the experiment on SWE-bench, although the agent's score temporarily fell below that of its parent, the DGM was still able to explore innovations along that path and create a new agent that outperformed all of its predecessors." (Section 4.4, p.7)

## Relevance to the MAS-surveillance thesis

**Partially relevant** — the DGM is not a multi-agent surveillance or even a multi-agent *coordination* system (it is a single self-modifying coding-agent lineage with an archive), and its domain (autonomous software engineering benchmarks) is unrelated to video/vision. Its value to the thesis is narrower and more architectural: it is a rigorous, well-controlled empirical study of **agentic self-improvement** — one of the "future roadmap" mechanisms flagged in the AI-Agents-vs-Agentic-AI taxonomy paper (source 10) as a frontier capability for next-generation agentic systems — and it directly demonstrates both the promise (compounding, transferable capability gains from letting an agent edit its own logic) and the safety considerations (sandboxing, traceability, benchmark-metric misalignment risk) that would apply if a surveillance MAS's agents were designed to self-improve their own detection thresholds, reasoning prompts, or coordination policies over time. Best used in the thesis as a forward-looking/discussion-section reference on agent self-improvement and its safety prerequisites, not as core surveillance or MAS-coordination literature.
