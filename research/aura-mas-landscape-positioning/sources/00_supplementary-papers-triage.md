---
source_type: index
credibility: n/a
recency: 2026
directly_relevant: n/a
---

# Triage of supplementary paper corpus (Research_Paper/ + ResearchPapers/)

Two folders of general arXiv-style reading material (not curated specifically for this thesis) were triaged for relevance to "agentic multi-agent surveillance systems." Every file's title/abstract (first 1-2 pages) was read to determine topic and relevance; the 11 files rated **high** or **medium** were then fully deep-read and given dedicated structured source files (`10_...` through `20_...` in this directory).

## Folder: `/home/lokmane-zed/Workspace/PFE(Memoire)/Research_Paper/` (11 files)

| Filename | Apparent title | One-line topic | Relevance | Justification |
|---|---|---|---|---|
| `2501.12948v1.pdf` | DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning | Reasoning-focused LLM trained via large-scale RL (no SFT-first) | **Low** | General foundational LLM/reasoning-training paper; background/classic. No agent, MAS, or surveillance content. |
| `2505.10468v4.pdf` | AI Agents vs. Agentic AI: A Conceptual Taxonomy, Applications and Challenges (Sapkota, Roumeliotis, Karkee) | Conceptual taxonomy distinguishing single AI Agents from orchestrated multi-agent "Agentic AI" | **High** | Directly defines and taxonomizes agentic multi-agent AI architecture, orchestration, memory, and failure modes — core conceptual scaffolding for the thesis. See `10_ai-agents-vs-agentic-ai-taxonomy.md`. |
| `2505.17117v2.pdf` | "From Tokens to Thoughts" (LLM concept formation / representation study) | How LLMs form internal conceptual representations from token sequences | **Low** | Interpretability/representation-learning study of LLM internals; no agent, MAS, or surveillance relevance. |
| `2505.22954v1.pdf` | Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents (Zhang, Hu, Lu, Lange, Clune) | Self-improving coding agent that edits its own codebase, validated empirically via coding benchmarks | **Medium** | Rigorous empirical study of agentic self-improvement (a named "Agentic AI" frontier mechanism); not multi-agent coordination or surveillance, but directly relevant to agent architecture/self-improvement framing. See `13_darwin-godel-machine-self-improving-agents.md`. |
| `2506.18096v1.pdf` | Deep Research Agents: A Systematic Examination And Roadmap (Huang et al.) | Survey/taxonomy of LLM-based autonomous research agents, incl. single- vs. multi-agent architectures | **High** | Explicitly surveys single-agent vs. multi-agent orchestration, tool use, planning — directly transferable agentic-architecture vocabulary and open-problem catalog. See `12_deep-research-agents-roadmap.md`. |
| `2507.05566v1.pdf` | SingLoRA (or similar low-rank adaptation variant) | Parameter-efficient fine-tuning (LoRA-family) technique | **Low** | General PEFT/model-training technique paper; no agent, MAS, or surveillance content. |
| `iv2k.pdf` | Video-Based Multi-Agent Traffic Surveillance System (Monitorix) — Abreu et al., IEEE Intelligent Vehicles Conference 2000 | FIPA-standard, BDI-based multi-agent system for video traffic surveillance across non-overlapping cameras | **High** | Exact-match precedent: genuine MAS (FIPA ACL, BDI agents) applied specifically to video surveillance with cross-camera vehicle tracking. Historically important but pre-deep-learning. See `11_monitorix-multi-agent-traffic-surveillance.md`. |
| `language_models_are_unsupervised_multitask_learners.pdf` | Language Models are Unsupervised Multitask Learners (GPT-2, Radford et al., OpenAI) | Foundational autoregressive LLM paper | **Low** | Background/classic — confirmed by title. No agent, MAS, or surveillance content. |
| `NIPS-2017-attention-is-all-you-need-Paper.pdf` | Attention Is All You Need (Vaswani et al., NeurIPS 2017) | Introduces the Transformer architecture | **Low** | Background/classic — confirmed by title. Foundational to all LLMs used by agentic systems, but not itself agent/MAS/surveillance content. |
| `Small Language Models are the Future of Agentic AI.pdf` | Small Language Models are the Future of Agentic AI (Belcak et al., NVIDIA Research) | Position paper arguing SLMs should power most agentic-system subtasks; heterogeneous multi-model agent architectures | **Medium** | Directly informs practical model-selection architecture for a multi-agent surveillance system's agents (cost/latency/edge-deployment relevance); not surveillance-specific. See `14_small-language-models-agentic-ai.md`. |
| `the-illusion-of-thinking.pdf` | The Illusion of Thinking (Apple ML research, reasoning-model limitations study) | Empirical study of large reasoning models' failure modes on controlled puzzle tasks | **Low** | General LLM-reasoning-limits study; tangential to agentic reasoning but not agent/MAS/surveillance-specific; not deep-read. |

## Folder: `/home/lokmane-zed/Workspace/PFE(Memoire)/ResearchPapers/` (11 files)

| Filename | Apparent title | One-line topic | Relevance | Justification |
|---|---|---|---|---|
| `1512.06808v1.pdf` | Game theory textbook/notes (Bonanno-style, "AGT" — general game theory) | General/introductory game theory reference text | **Low** | General textbook covering game theory foundations (relevant background for auction/negotiation theory) but not agent-system, MAS-architecture, or surveillance-specific; not deep-read given generic textbook nature. |
| `2009.07736v2.pdf` | HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking (Luiten et al., IJCV 2020) | Principled MOT evaluation metric balancing detection, association, localization accuracy | **High** | Standard, rigorous evaluation methodology directly applicable to any tracking-agent component of a surveillance MAS. See `15_hota-multi-object-tracking-metric.md`. |
| `2110.06864v3.pdf` | ByteTrack: Multi-Object Tracking by Associating Every Detection Box (Zhang et al., ECCV 2022) | SOTA real-time multi-object tracker using low-confidence detection recovery | **High** | Core, real-time-capable MOT technique directly usable/adaptable as the perception backbone of a surveillance MAS's tracking agent. See `16_bytetrack-multi-object-tracking.md`. |
| `2203.08975v2.pdf` | A Survey of Multi-Agent Deep Reinforcement Learning with Communication (Zhu, Dastani, Wang, Utrecht University) | 9-dimensional taxonomy of communication mechanisms in MARL | **High** | Core MAS/MARL coordination-mechanisms literature — communication design is central to any multi-agent surveillance architecture. See `17_marl-communication-survey.md`. |
| `2205.11916v4.pdf` | Large Language Models are Zero-Shot Reasoners (Kojima et al.) | Chain-of-thought / zero-shot prompting technique for LLM reasoning | **Low** | General LLM-prompting technique paper; not agent, MAS, or surveillance-specific. |
| `2211.15751v3.pdf` | Edge Video Analytics: A Survey on Applications, Systems and Enabling Techniques (Xu, Zheng, Razavi, McMaster University, IEEE COMST 2023) | Comprehensive survey of edge/cloud video-analytics system architectures | **High** | Directly addresses distributed video surveillance infrastructure (edge/cloud placement, scalability, latency) — the deployment substrate for an agentic surveillance MAS. See `18_edge-video-analytics-survey.md`. |
| `2307.03172v3.pdf` | Lost in the Middle: How Language Models Use Long Contexts (Liu et al.) | Empirical study of LLM long-context positional-bias limitations | **Low** | General LLM-context-usage limitation study; not agent, MAS, or surveillance-specific. |
| `2307.11760v7.pdf` | Large Language Models Understand and Can Be Enhanced by Emotional Stimuli (EmotionPrompt) | Prompting technique using emotional framing to improve LLM output quality | **Low** | General prompting-technique paper; not agent, MAS, or surveillance-specific. |
| `2412.10087v1.pdf` | Consensus-Based Dynamic Task Allocation for Multi-Robot System Considering Payloads Consumption (Qiu, Zhu, Hu, Zeng, Lu, NUDT) | Auction/consensus-based (CBBA-family) multi-robot task-allocation algorithm | **High** | Core, modern (2024) auction-based MAS coordination mechanism — directly the "auctions/task-allocation" theme named as relevant. See `19_consensus-based-task-allocation-multi-robot.md`. |
| `2502.06581v4.pdf` | A Survey on Video Analytics in Cloud-Edge-Terminal Collaborative Systems (Gong et al.) | Survey of CETC video-analytics architectures incl. LLM/multimodal integration | **High** | Directly addresses distributed video-surveillance infrastructure plus explicit LLM/multimodal-integration trend — strong novelty-positioning source. See `20_video-analytics-cloud-edge-terminal-survey.md`. |
| `8.pdf` | Speech and Language Processing, Ch. on Transformers/attention (Jurafsky & Martin textbook excerpt) | Textbook chapter on Transformer architecture fundamentals | **Low** | Background/classic educational material; no agent, MAS, or surveillance content. |

## Summary

- **Total files triaged:** 22 (11 + 11)
- **Rated high or medium (deep-analyzed, dedicated source files written):** 11 — `10_` through `20_`
- **Rated low (background/classic or off-topic, logged only):** 11

### Deep-dive source files produced

| File | Paper |
|---|---|
| `10_ai-agents-vs-agentic-ai-taxonomy.md` | AI Agents vs. Agentic AI: A Conceptual Taxonomy (Sapkota et al. 2025) |
| `11_monitorix-multi-agent-traffic-surveillance.md` | Video-Based Multi-Agent Traffic Surveillance System / Monitorix (Abreu et al. 2000) |
| `12_deep-research-agents-roadmap.md` | Deep Research Agents: A Systematic Examination And Roadmap (Huang et al. 2025) |
| `13_darwin-godel-machine-self-improving-agents.md` | Darwin Gödel Machine (Zhang, Hu, Lu, Lange, Clune 2025) |
| `14_small-language-models-agentic-ai.md` | Small Language Models are the Future of Agentic AI (Belcak et al., NVIDIA 2025) |
| `15_hota-multi-object-tracking-metric.md` | HOTA: A Higher Order Metric for Evaluating MOT (Luiten et al. 2020) |
| `16_bytetrack-multi-object-tracking.md` | ByteTrack (Zhang et al. 2022) |
| `17_marl-communication-survey.md` | A Survey of Multi-Agent Deep RL with Communication (Zhu, Dastani, Wang 2024) |
| `18_edge-video-analytics-survey.md` | Edge Video Analytics Survey (Xu, Zheng, Razavi, IEEE COMST 2023) |
| `19_consensus-based-task-allocation-multi-robot.md` | Consensus-Based Dynamic Task Allocation / CBPA (Qiu et al. 2024) |
| `20_video-analytics-cloud-edge-terminal-survey.md` | A Survey on Video Analytics in CETC Systems (Gong et al. 2025) |
