---
source_type: paper
credibility: 3
recency: 2025
directly_relevant: partial
---

# Huang et al. — "Deep Research Agents: A Systematic Examination And Roadmap"

## Bibliographic metadata

- **Title:** Deep Research Agents: A Systematic Examination And Roadmap
- **Author(s):** Yuxuan Huang, Yihang Chen, Haozheng Zhang, Kang Li, Meng Fang, Linyi Yang, Xiaoguang Li, Lifeng Shang, Songcen Xu, Jianye Hao, Kun Shao, Jun Wang
- **Affiliations:** University of Liverpool, Huawei Noah's Ark Lab, University of Oxford, University College London
- **Year:** 2025 (v1, 22 Jun 2025)
- **Venue:** arXiv preprint (arXiv:2506.18096v1, cs.AI)
- **Length:** 26 pages
- **Code/resource:** curated repository at github.com/ai-agents-2030/awesome-deep-research-agent

## Research problem

LLM-powered "Deep Research (DR) agents" — systems like OpenAI Deep Research, Gemini Deep Research, Grok DeepSearch, Perplexity DR — have rapidly emerged to autonomously conduct complex, multi-turn informational research (dynamic reasoning, adaptive long-horizon planning, multi-hop retrieval, iterative tool use, structured report generation), but there is no systematic analysis of their foundational technologies, architectural components, or a principled taxonomy distinguishing approaches, leaving practitioners without a clear map of the design space, benchmark landscape, or open challenges.

## Proposed approach

A systematic survey/taxonomy of DR agents structured around: (1) information acquisition strategies (API-based/static retrieval vs. browser-based/dynamic web exploration); (2) modular tool-use frameworks (code execution, multimodal input processing, Model Context Protocol/MCP integration for extensibility); (3) a taxonomy differentiating **static vs. dynamic workflows**; (4) a taxonomy classifying agent architectures by planning strategy and **agent composition — single-agent vs. multi-agent configurations**; (5) a critical evaluation of existing benchmarks (QA-style vs. task-execution-style); (6) an enumeration of open challenges and future directions.

## Architecture/method

Defines DR agents formally as "AI agents powered by LLMs, integrating dynamic reasoning, adaptive planning, multi-iteration external data retrieval and tool use, and comprehensive analytical report generation for informational research tasks." Distinguishes DR agents from prior paradigms: unlike RAG (which enhances factual accuracy but lacks sustained reasoning) and conventional tool-use (TU) systems, DR agents integrate LLM reasoning as the cognitive core with real-time external retrieval (browsers, structured APIs) and dynamic tool invocation via customized toolkits or standardized interfaces (MCP), enabling autonomous end-to-end research workflows. The paper's key architectural axis for MAS relevance is **single-agent vs. multi-agent DR architectures**: it surveys systems that use one LLM to handle planning, retrieval, and report generation end-to-end (single-agent, e.g., most current DR agents) versus emerging systems that **distribute planning, tool invocation, and report generation across multiple specialized agents** to reduce the cognitive/computational load on any one backbone model — identified as a promising but still underdeveloped direction. It also discusses "AI-native browsers" (Browserbase, Browser Use, Dia, Fellou, Comet) that expose structured, programmatically-traversable DOM views to agents instead of brittle coordinate-based UI automation, and asynchronous/parallel task execution architectures (directed acyclic graph task modeling, learned RL-based scheduling agents) as a future direction to replace the currently-dominant linear/sequential planning paradigm.

## AI/ML techniques

LLMs as reasoning core; reinforcement learning (both for training DR agents' retrieval/reasoning policies and as a proposed mechanism for a dedicated subtask-scheduling agent); retrieval-augmented generation (RAG); tool-integrated reasoning (TIR) — extending simple tool calling to adaptive, multi-step tool invocation with fine-grained rewards (tool selection appropriateness, parameter accuracy, reasoning efficiency) reported to improve performance 15-17% across benchmarks; self-reflection/verification loops (multi-source cross-checking of claims, iterative replanning on detected conflicts, akin to a human researcher's "pause and check" behavior).

## Agent-based components

**Explicit yes, with an important nuance.** The paper explicitly frames "single-agent vs. multi-agent" as one of its core taxonomic axes for DR agent architecture, and identifies multi-agent DR architectures — where planning, tool invocation, and report generation are distributed across specialized agents rather than handled by one monolithic backbone model — as a promising direction that has shown "promising improvements in system performance" but where "achieving effective end-to-end training and efficient coordination among multiple agents remains a critical open challenge." It proposes hierarchical reinforcement learning (HRL) with layered internal reward mechanisms, or a dedicated RL-trained scheduling agent that dynamically allocates subtasks and adjusts execution order, as future directions for multi-agent DR coordination.

## Dataset(s)

Surveys, rather than introduces, benchmarks. Covers QA benchmarks (HotpotQA, 2WikiMultihopQA, NaturalQuestions, TriviaQA, GPQA, PopQA, TELEQnA, SimpleQA, Bamboogle, Humanity's Last Exam) and task-execution benchmarks (GAIA, AssistantBench, Magentic-One, SWE-bench, HumanEvalFix, MLGym, MLE-bench, MLBench, MLAgentBench, ScienceAgentBench, RE-Bench, RESEARCHTOWN, and GUI-based OSWorld/WebArena/SpaBench for future extension). Presents comparative performance tables (Tables 4-6) of ~20 named DR agent systems (Search-o1, Grok DeepSearch, R1-Searcher, DeepResearcher, WebThinker, SimpleDeepSearch, SWIRL, H2O.ai DR, Alita, Manus, OWL, Genspark Super Agent, etc.) across these benchmarks.

## Evaluation methodology

Meta-level: a structured literature synthesis, comparative benchmark performance tables sourced from the surveyed papers' own reported numbers (not independently re-run), and a critical benchmark analysis flagging benchmark misalignment (many QA benchmarks are answerable from parametric LLM knowledge alone, inflating apparent DR-agent performance; BrowseComp and continually-refreshed leaderboards are recommended to deter this) and the absence of comprehensive benchmarks for end-to-end report-generation quality (narrative coherence, table/figure integration, cross-modal alignment).

## Main results

Not original empirical results — the paper's contribution is the taxonomy, benchmark critique, and roadmap. Reported (from surveyed systems) notable performance figures include H2O.ai DR reaching 79.73% average on GAIA dev set (Level-1/2/3), and various DR agents underperforming substantially on the hardest benchmarks (Humanity's Last Exam, BrowseComp), which the authors flag as the two most critical unresolved evaluation challenges for the field.

## Limitations

Self-identified: (1) most DR agents rely on static knowledge repositories or search-engine-only browsing, unable to access proprietary/enterprise applications, databases, or subscription services; (2) conventional human-centered browsers create latency/fragility bottlenecks for agents optimized for programmatic (not visual) interaction; (3) most existing DR agents use purely linear/sequential task planning, limiting efficiency and robustness under complex subtask interdependencies; (4) current multi-agent DR architectures lack effective end-to-end training/coordination methods; (5) benchmark misalignment — QA benchmarks increasingly measure parametric memorization rather than genuine retrieval/reasoning, and no benchmark yet evaluates end-to-end structured multi-modal report generation quality; (6) self-evolving/self-improving DR agent research remains "underdeveloped and narrowly focused" on case-based reasoning paradigms only.

## Claimed contributions

- A systematic examination of DR agent foundational technologies and architectural components (information acquisition, tool-use frameworks, MCP integration).
- A taxonomy distinguishing static vs. dynamic workflows and single-agent vs. multi-agent DR architectures.
- A critical evaluation of existing QA and task-execution benchmarks, identifying benchmark misalignment as a key unresolved issue.
- An outlined roadmap of open challenges and future directions: broadening information sources via AI-native browsers/MCP, structured fact-checking/self-reflection loops, asynchronous parallel execution (DAG-based planning, RL-based scheduling agents), tool-integrated reasoning, comprehensive end-to-end report-generation benchmarks, parametric optimization of multi-agent DR architectures (HRL, dedicated scheduling agents), and self-evolving language model agents.
- A continuously-updated public repository curating DR agent research.

## Verbatim quotes

1. "We define 'Deep Research Agents' as: AI agents powered by LLMs, integrating dynamic reasoning, adaptive planning, multi-iteration external data retrieval and tool use, and comprehensive analytical report generation for informational research tasks." (Section 1, p.1)

2. "Distributing workloads across multiple specialized agents has shown promising improvements in system performance, yet achieving effective end-to-end training and efficient coordination among multiple agents remains a critical open challenge." (Section 6, p.19)

3. "To optimize multi-agent architectures for DR tasks, we propose two promising future directions: (i) adopting hierarchical reinforcement learning (HRL)... or (ii) employing an RL-based dedicated scheduling agent designed to dynamically allocate subtasks and adjust execution order based on real-time performance metrics." (Section 6, p.19)

4. "Despite notable progress, key challenges remain, including limited generalization across diverse tasks, inflexible task workflows, difficulty integrating granular external tools, and substantial computational complexity associated with advanced planning and optimization." (Limitation, p.20)

## Relevance to the MAS-surveillance thesis

Only **partially** relevant: this survey is about LLM-driven autonomous *research* agents (web-browsing, information-retrieval, report-writing), not video surveillance, and contains zero computer-vision or physical-sensing content. Its relevance to the thesis is architectural-by-analogy rather than domain-specific: it offers a rigorously surveyed vocabulary and design-pattern catalog for "agentic" systems generally — dynamic vs. static workflow, single- vs. multi-agent composition, tool-integrated reasoning, structured fact-checking/self-reflection loops, and (most transferable) the open problem of **coordinating multiple specialized agents efficiently**, which is directly analogous to coordinating detection/tracking/reasoning/alerting agents in a surveillance MAS. Its benchmark-misalignment critique (systems appearing capable because tasks are answerable from memorized knowledge rather than genuine tool use) is a useful methodological caution transferable to surveillance-agent evaluation design (ensuring evaluation scenarios truly require multi-agent perception/reasoning rather than being solvable by a single strong end-to-end model). Overall: cite as a general "agentic AI system design" reference, not as surveillance literature.
