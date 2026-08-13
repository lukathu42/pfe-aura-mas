# Agentic Multi-Agent Surveillance: Landscape & Positioning Report

**Date**: 2026-08-11 · **Genre**: landscape + validation · **Scope**: research analysis only (no implementation)
**Corpus**: 7 theses in `../Documents/`, 1 thesis found outside it (BREK Bouthaina), 22 supplementary papers triaged / 11 deep-analyzed, plus a critical audit of this project's own prior AI-generated materials (AURA-MAS thesis draft, bibliography, blueprint).
**Full source files**: `sources/00`–`20` · **Atomic findings**: `findings/F1`–`F6` · **Index**: `sources.csv` · **Plan**: `plan.md`

> **Reading key**: throughout this report, **[FACT]** = directly evidenced in a read document, **[INTERPRETATION]** = my reading of what a fact means, **[INFERENCE]** = a conclusion drawn by combining multiple facts, **[SPECULATION]** = a plausible but unverified guess, **[RECOMMENDATION]** = an actionable suggestion. Unmarked prose in the analytical sections is interpretation unless it carries a source citation.

---

## 1. Executive Summary

**[FACT]** This is not a greenfield literature search. Before any external document was read, this session discovered that the working directory already contains a fully implemented prototype ("AURA-MAS"), a compiled 53-page Master's thesis PDF, a separately compiled but topically unrelated "Engineer thesis" PDF, a 94-entry bibliography, and a state-of-the-art chapter — all produced by a prior autonomous-agent session (self-labeled "Manus AI," sandbox paths `/home/ubuntu/pfe/...`, per `STATE_NOTES.md`).

**[FACT]** Of the 7 documents in `Documents/`, only **one** (Bousetouane, 2015 PhD, Annaba) implements a genuine multi-agent architecture for surveillance (autonomous "cognitive" camera agents + a formal consensus protocol, validated on a real 7-camera testbed). The other six are single-pipeline, non-agentic classical or deep-learning CV systems, one of which (Kraled Kebir Nesrine, 2016) explicitly rejects agent terminology in favor of "master-slave."

**[FACT]** A second, highly relevant local thesis was found *outside* `Documents/` (BREK Bouthaina, 2019, Univ. Tébessa): a genuine JADE multi-agent system, but for **network/cybersecurity** intrusion detection (NSL-KDD tabular data), not physical surveillance.

**[FACT]** A 2000-era paper (Monitorix, Abreu et al.) shows that "multiple agents cooperating to monitor a site" is a **25-year-old research direction** at the level of FIPA-standard, BDI-based multi-agent systems — not a novel framing in itself.

**[INFERENCE]** Combining these: the genuine research gap is narrow and specific, not broad. "Multi-agent surveillance" alone is not new (Bousetouane, Monitorix). "Modern deep-learned perception for surveillance" alone is not new (5 of the 7 local theses, plus the whole of contemporary CV literature). What appears **not yet combined**, locally or in the reviewed literature, is: modern learned perception **+** auditable/interpretable multi-agent coordination **+** a decision/generation-decoupled, evidence-grounded LLM explanation layer **+** rigorous system-level (not just per-component) evaluation. This four-way combination is the actual candidate contribution — not "agentic multi-agent surveillance" as a category.

**[FACT]** Auditing the project's own prior AI-generated materials surfaced three concrete risks that are independent of the literature question but material to both theses: (1) the compiled thesis title pages carry an unrelated name/supervisor apparently inherited un-replaced from a LaTeX template; (2) the existing "Engineer thesis" PDF in this project is about a completely different topic (a consultation-marketplace platform), meaning no Engineer-diploma-level surveillance thesis currently exists; (3) the existing bibliography and "experimental results" are real-but-imprecise and toy-scale respectively, and are not yet defense-ready. These are flagged prominently in §13 and should be addressed regardless of the research direction chosen.

**[RECOMMENDATION]** Narrow the proposed direction from "an agentic multi-agent surveillance system" (too broad, and partially already established) to two distinct, falsifiable research questions — one per thesis — built on the same underlying platform. See §12 for the proposed split and §14 for the full recommendation.

---

## 2. Research Context

**[FACT]** The user needs two related but distinct academic outputs: a State Engineer diploma thesis and a Master's degree thesis, both in AI & Data Science, intended to form a coherent research trajectory rather than duplicate work.

**[FACT]** The working directory (`Intelligent Surveillance System for Master's Thesis/`) sits alongside two sibling project directories at `PFE(Memoire)/` level:
- `pfe_surviellance_pfe/` — an earlier, simpler prototype of the same surveillance direction (warehouse intrusion/abandoned-object/fall detection via a Streamlit app), with its own scope document and an earlier `deep-research-report.md` that is textually the same blueprint as `pasted_content_2.txt` in the current directory.
- `pfe_agentic_ai/` — a topically unrelated project: an "agentic educational toy" for resource-constrained systems, driven by its own official "Sujet de Stage" PDF (*"Architectures Agentic AI pour systèmes à ressources limitées"*).

**[INTERPRETATION]** `pfe_surviellance_pfe/` reads as an earlier, superseded iteration of the same surveillance idea — simpler scope (single-camera warehouse, 3 event types), simpler stack (no audio, no CLIP anomaly, no auction). `pfe_agentic_ai/` reads as a genuinely separate obligation (a different assigned internship topic) rather than part of this research trajectory.

**[RECOMMENDATION]** Confirm with the user whether `pfe_surviellance_pfe/` should be treated as fully superseded (no further action needed) or whether it contains decisions/scope constraints that still apply. This report treats it as historical context only, not as a source of positioning claims. `pfe_agentic_ai/` is excluded entirely from this report's scope.

---

## 3. Overview of Existing Works

Twenty sources were read in full or systematically sampled by independent research agents (raw analyses in `sources/`). Grouped by what they actually are:

### 3a. Local Algerian theses read from `Documents/` (7)

| # | Author(s) | Year | Institution | Actual topic | Agentic/MAS? |
|---|---|---|---|---|---|
| 01 | ZOUAOUI Abderaouf | 2015 | Univ. Blida 1 | Titled "information fusion for smart video surveillance" but is actually **license-plate recognition** (ALPR) | No |
| 02 | Boateng Godfred Kyeremeh | 2024 | Univ. Tlemcen | Autoencoder + ConvLSTM video anomaly detection | No |
| 03 | NACHEF & BOUMEDIENE | 2022 | Univ. Ibn Khaldoun–Tiaret | YOLOv3 transfer-learning object detection (2 classes) | No |
| 04 | Ammar Ladjailia | 2019 (PhD) | Univ. Badji Mokhtar–Annaba | Optical-flow human action recognition | No (single-camera) |
| 05 | Fouad Bousetouane | 2015 (PhD) | Univ. Badji Mokhtar–Annaba | Decentralized multi-agent consensus for cross-camera Re-ID | **Yes — genuine MAS** |
| 06 | Kraled Kebir Nesrine & Chennouf Bahaeddine | 2016 | Univ. Saad Dahlab Blida / CDTA | HOG-based person detection/tracking, master-slave | No (explicitly rejects "agent" framing) |
| 07 | Tahar Dahmani Abdelkader | 2014 | USDB Blida | Viola-Jones face detection for VS indexing | No |

### 3b. Additional local thesis found outside `Documents/`

| # | Author | Year | Institution | Topic | Agentic/MAS? |
|---|---|---|---|---|---|
| 08 | BREK Bouthaina | 2019 | Univ. Larbi Tébessi | JADE multi-agent **network** intrusion detection (NSL-KDD) | **Yes — genuine MAS, but not video** |

### 3c. Supplementary papers deep-analyzed (11 of 22 triaged; see `sources/00` for the full triage table)

| # | Work | Year | Relevance axis |
|---|---|---|---|
| 10 | Sapkota, Roumeliotis & Karkee — *AI Agents vs. Agentic AI* | 2025 | Terminology/taxonomy anchor |
| 11 | Abreu et al. — *Monitorix* | 2000 | Historical MAS-for-surveillance precedent |
| 12 | Huang et al. — *Deep Research Agents* | 2025 | Orchestration patterns |
| 13 | Zhang et al. — *Darwin Gödel Machine* | 2025 | Self-improving agents (tangential) |
| 14 | Belcak et al. (NVIDIA) — *SLMs are the Future of Agentic AI* | 2025 | Edge/cost framing for agentic AI |
| 15 | Luiten et al. — *HOTA* | 2020 | Tracking evaluation metric (component-level) |
| 16 | Zhang et al. — *ByteTrack* | 2022 | Perception building block |
| 17 | Zhu, Dastani & Wang — *MARL communication survey* | 2024 | Coordination-mechanism vocabulary |
| 18 | Xu, Zheng & Razavi — *Edge Video Analytics survey* | 2023 | Infrastructure grounding |
| 19 | Qiu et al. — *Consensus-based multi-robot task allocation* | 2024 | Coordination mechanism |
| 20 | Gong et al. — *Cloud-Edge-Terminal video analytics survey* | 2025 | Explicitly flags LLM/multimodal integration as an open frontier |

The remaining 11 supplementary files (Attention Is All You Need, GPT-2, Illusion of Thinking, etc.) are confirmed general-ML background with no direct bearing on this topic — see `sources/00` for one-line justifications each.

### 3d. This project's own prior AI-generated materials (audited, not treated as primary evidence)

`chapter_sota.tex`, `bibliography.bib` (94 entries), `pasted_content_2.txt` / `pfe_surviellance_pfe/deep-research-report.md` (an identical blueprint document), and `AURA-MAS_Deep_Dive_Report.en/fr.md` — all produced by the prior "Manus AI" session from an external, now-inaccessible web search. See §13 for the audit findings.

---

## 4. Detailed Paper/Thesis Analysis

Full structured analyses (research problem, architecture, AI/ML techniques, datasets, evaluation, results, limitations, contributions, verbatim quotes with page numbers) exist for every source listed above in `sources/01`–`20`. Rather than reproduce ~200KB of analysis here, this section highlights the four documents that actually move the positioning argument — everything else is summarized in §3 and detailed in its own source file.

### Bousetouane (2015 PhD) — the strongest local precedent [source 05]

**[FACT]** Each camera is modeled as an autonomous "cognitive agent" running detection (GMM background subtraction), inter-camera color adaptation (MBTF), Haralick-texture representation, and an adaptive particle filter, collaborating via a **formal consensus protocol**: a camera detecting a new object broadcasts a feature vector to neighbor agents, adopts a matching identity if any neighbor confirms it, or mints a new global ID otherwise. Validated on a real 7-camera ad-hoc wireless testbed (E-CAM-1..7), 4 scenarios, 6 subjects, mean re-identification rate 90.11% (ROC-based).

**[FACT]** No deep learning anywhere (consistent with 2015); no anomaly detection; no explainable/natural-language output; self-collected, small-scale evaluation only; author's own named limitations include camera-motion fragility and inability to disambiguate visually-identical objects (e.g., uniformed workers).

**[INTERPRETATION]** This is real multi-agent-systems theory (autonomy, message-passing, explicit coordination protocol, situated in distributed-AI literature: Soto 2009, Olfati-Saber 2007) — not loose terminology. It sets a genuine, non-trivial bar: any new thesis claiming "multi-agent surveillance" as a contribution must clearly explain what it does that this 2015 thesis does not.

### BREK Bouthaina (2019) — MAS-for-detection, but not vision [source 08]

**[FACT]** Four JADE agents (NBAgent, DTAgent, JRIPAgent, NNAgent), each wrapping a different pre-trained Weka classifier (Naïve Bayes, Decision Tree, RIPPER, Neural Net) over NSL-KDD network-traffic records. Coordination: a fixed 50% confidence threshold triggers ACL broadcast and JADE agent **mobility** (code/state migration) when a local classifier is unsure. Results strong on NSL-KDD (~99% detection for DT/JRip agents), but the mobile-agent architecture's own marginal contribution over the classifiers' raw accuracy is never isolated.

**[INTERPRETATION]** Zero computer vision, zero overlap with physical surveillance content — but it establishes "wrap a classifier per agent + threshold-based coordination" as a known, examinable local thesis pattern. A jury may implicitly compare a new MAS design's coordination sophistication against this baseline.

### Monitorix (Abreu et al., 2000) [source 11]

**[FACT]** A fully decentralized, FIPA-standard multi-agent traffic-surveillance system: real ACL messaging with SL content, BDI-like production-system reasoning per agent, a four-tier role-specialized agent taxonomy, a "Proxy" middle-agent bridging a classical CV module (VOK) into the agent society, and a Tracker agent doing cross-camera vehicle re-identification via an online-adapted traffic model.

**[INTERPRETATION]** Establishes that "agents cooperate to monitor a site and generate alerts" — close to the user's original, pre-modernization theme wording — is a **25-year-old idea**, executed with 2000-era symbolic AI. This is the single strongest piece of evidence that novelty cannot rest on the MAS framing itself.

### Sapkota, Roumeliotis & Karkee (2025) — terminology anchor [source 10]

**[FACT]** Proposes a structured distinction: **AI Agents** = single LLM/tool-augmented system, narrow scope, reactive; **Agentic AI** = orchestrated, multi-agent, role-specialized collaboration with dynamic task decomposition and persistent shared memory. Also catalogs known failure modes of Agentic AI systems: unpredictable emergent behavior, poor explainability/verifiability ("no formal verification tools exist for multi-agent LLM systems"), expanded attack surface via shared memory, accountability gaps.

**[INTERPRETATION]** This is the field's own current vocabulary for exactly the distinction the user asked about in Q6 — used extensively in §7 below.

---

## 5. Comparison of Existing Approaches

| Approach family | Representative source(s) | Capability | Key limitation |
|---|---|---|---|
| **Traditional/centralized VMS analytics** | ALPR (01), face-detect (07) | Single-camera, single-task detection; simple, cheap, well-understood | No cross-camera reasoning, no coordination, no explanation, siloed |
| **Modern deep-learning single-pipeline CV** | YOLOv3 (03), AE+ConvLSTM anomaly (02), optical-flow action recognition (04) | State-of-the-art per-task accuracy on public benchmarks; well-documented, reproducible | Still single-module; no fusion across sensors; several local examples show real rigor gaps (1 FPS "real-time" claim in 03; underperforms own cited baselines in 02) |
| **Distributed but non-agentic** | Master-slave HOG tracking (06) | Splits processing load across nodes | Authors *themselves* reject "agent" framing; no autonomy, no negotiation — pure task distribution |
| **Classical multi-agent systems (rule/consensus-based)** | Bousetouane (05), Monitorix (11), BREK (08) | Genuine autonomy, explicit inter-agent protocols (consensus, ACL/BDI, mobility); decentralization without central point of failure | No learning-based reasoning, no natural-language output, coordination sophistication capped at rules/consensus/threshold; two of three predate deep learning entirely |
| **MARL-based coordination (research)** | Cited in chapter_sota.tex (QMIX, MADDPG) and supplementary survey (17) | Can learn coordination policies beyond hand-crafted rules | Sample-inefficient, opaque/non-auditable policies, scarce real (non-simulated) surveillance deployments — a gap independently corroborated across sources |
| **LLM/VLM video agents (general AI literature)** | chapter_sota.tex citations (Hawk, VideoAgent); Sapkota (10) | Rich, human-readable scene/incident understanding; flexible reasoning | Either used as the detector itself or as an unchecked narrator — no surveyed system decouples generation from the safety-critical decision, per chapter_sota's own synthesis; Sapkota independently confirms explainability/verifiability is an open, acknowledged weakness of this class generally |
| **Proposed direction (AURA-MAS-style)** | This project's own draft | Combines hierarchical MAS + modern perception + auction coordination + rule-guarded LLM explanation | Not yet validated at scale (§13); "agentic" label applied unevenly across components that are not all actually agent-like (§7) |

**[INTERPRETATION]** The progression traditional → modern-CV → distributed → classical-MAS → MARL → LLM-agent is not a strict capability ladder; each family solves a different sub-problem (perception quality vs. coordination vs. reasoning/explanation) and none of the reviewed sources combines all three well.

---

## 6. Research Landscape

**[INFERENCE]**, synthesizing §3–§5: the landscape splits cleanly into three largely non-overlapping clusters, and the local corpus sits almost entirely in Cluster 1.

- **Cluster 1 — Perception quality** (5 of 7 local theses + most supplementary component papers: ByteTrack, HOTA): mature, well-trodden, individually low-novelty for a thesis contribution today.
- **Cluster 2 — Classical multi-agent coordination** (Bousetouane, Monitorix, BREK): established since 2000, rule/consensus/threshold-based, non-learning, non-explanatory. Real but dated.
- **Cluster 3 — Agentic AI / LLM orchestration** (Sapkota, Huang, Belcak, Darwin Gödel Machine): active, fast-moving, general-purpose CS research (2024–2026), **not surveillance-specific in any of the reviewed sources**, and explicitly flagged (by the Cloud-Edge-Terminal survey, source 20, and independently by Sapkota) as an *open integration frontier* rather than a solved problem.

**[INFERENCE]** The user's proposed direction sits at the **intersection** of Clusters 1, 2, and 3 — an intersection that, across 20 independently read sources spanning three decades and two countries' worth of institutions, was not found populated by any single work. This is a genuine landscape gap, but it is a narrow, specific intersection, not a wide-open field — see §9 for the honest strength assessment.

---

## 7. Multi-Agent / Agentic AI Analysis

This directly answers the user's Q5 and Q6.

### 7a. Terminology, precisely (Q6)

Using Sapkota et al.'s (source 10) now-current field vocabulary, cross-checked against the classical MAS literature evidenced by Bousetouane/Monitorix/BREK:

| Term | Defining property | Exemplar in this corpus |
|---|---|---|
| **Multi-Agent System (MAS, classical)** | Autonomous, communicating, often rule/protocol-governed entities; decades-old formalism (BDI, ACL, contract-net, consensus) | Bousetouane (05), Monitorix (11), BREK (08) |
| **Distributed AI** | Broader parent field; MAS is one instantiation | — |
| **Autonomous agents (general)** | Individual entities with local decision authority; not necessarily organized as a "society" | Any single perception module with local thresholding logic |
| **AI Agent (LLM-based, per Sapkota)** | Single LLM/tool-augmented system, narrow/reactive scope | AURA-MAS's `ExplanationAgent` in isolation |
| **Agentic AI (per Sapkota)** | Orchestrated **multi**-agent collaboration, dynamic task decomposition, persistent shared memory, coordinated autonomy — specifically among LLM-driven agents | Not demonstrated by any source in this corpus for surveillance |
| **Multi-Agent LLM systems** | Agentic AI where the agents are specifically LLM-driven (e.g., AutoGen, MetaGPT) | Cited in chapter_sota.tex, not surveillance-specific |
| **AI orchestration pipelines** | Sequential/DAG tool-calling without genuine autonomy or negotiation | Risk category — see 7b |
| **Conventional modular software architecture** | Components with fixed responsibilities, no autonomy/negotiation | Risk category — see 7b |

**[RECOMMENDATION]** Do not describe the system uniformly as "Agentic AI." **[INTERPRETATION]** Precisely: the AURA-MAS-style design as currently drafted is a **classical/software hierarchical multi-agent system** (in the Bousetouane/Monitorix sense — autonomous nodes, explicit coordination protocol) **with one embedded AI Agent subsystem** (the LLM-based `ExplanationAgent`, in Sapkota's narrower sense). It does not yet meet Sapkota's definition of "Agentic AI" as a whole, because that requires **multiple** LLM-driven agents dynamically decomposing tasks and sharing persistent memory — only one component (explanation) is LLM-driven; the rest (camera, fusion, policy) are deterministic. This is a more defensible, more precise claim than "agentic multi-agent surveillance system," and it is *also* a stronger claim in one respect: it correctly signals that the safety-critical path is deliberately **not** LLM-driven, which directly answers Sapkota's own flagged concern about unverifiable multi-agent LLM decision-making.

### 7b. Why use agents at all? (Q5) — component-by-component

| Proposed component | Does it genuinely need agent framing? | Reasoning |
|---|---|---|
| CameraAgent / AudioAgent | **Weak case**, unless given real local autonomy (e.g., deciding *whether* to request PTZ handoff based on its own belief state) | As a "run YOLO, publish detections" module, this is a conventional ML/CV service; calling it an "agent" does not add architectural or scientific content over calling it a "detection module" |
| FusionAgent | **Weak-to-moderate** | Becomes agent-like only if it maintains persistent world-state and makes autonomous fusion decisions under uncertainty rather than executing a fixed fusion formula (e.g., noisy-OR) — currently closer to the latter |
| CoordinatorAgent (auction/contract-net) | **Strong case** | Auction/contract-net protocols are themselves multi-agent-systems formalism (bidding, negotiation, winner determination) — this is the one component where "multi-agent" is not just a label but the actual mechanism |
| PolicyAgent (rule engine) | **Weak case** | A deterministic rule engine with thresholds and hysteresis; framing it as an "agent" is largely nominal — it has no autonomy to negotiate, only to apply fixed rules |
| ExplanationAgent (LLM-based) | **Strong case** | A genuine perceive→retrieve-evidence→reason→draft→verify loop is the actual definition of an "AI Agent" per Sapkota — this is the one place "agentic AI" terminology is fully earned |

**[INFERENCE]** Of 5 proposed components, only 2 (Coordinator, Explanation) genuinely need agent-theoretic framing to be accurately described; the other 3 could be honestly called ML/CV modules or a rule engine without loss of technical content. **[INTERPRETATION]** This is not a fatal flaw — a hierarchical system with two genuinely agentic components and three well-engineered conventional modules is still a coherent, defensible architecture — but the thesis should not claim uniform "agentic" status for all seven agents, since a jury member familiar with MAS theory (plausible, given Bousetouane and BREK exist locally) would likely probe exactly this distinction.

---

## 8. Positioning of My Proposed Direction

**What has already been done** (facts, §3–§6): classical multi-agent surveillance coordination (2000–2015, rule/consensus-based); modern single-pipeline deep-learning perception for surveillance (2019–2024, locally); general-purpose agentic-AI/LLM-orchestration research (2024–2026, not surveillance-specific).

**What appears to be missing** (inference, triangulated across ≥3 independent, differently-typed sources — a local PhD thesis, a 2000 conference paper, and a 2025 survey — satisfying the deep-research triangulation bar): the specific combination of (a) modern learned perception, (b) auditable multi-agent coordination, (c) decision/generation-decoupled grounded LLM explanation, (d) system-level evaluation methodology.

**What is genuinely different about the proposed direction**: not "using multiple agents for surveillance" (established since 2000) and not "using AI for surveillance" (established, well-trodden locally) — but specifically the **architectural decision to keep the safety-critical decision deterministic while adding a decision-decoupled, evidence-grounded LLM explanation layer on top of an auditable (not opaque-learned) coordination mechanism**. This is a real, narrow, and currently plausible gap.

**What is already well established (do not oversell as novel)**: individual detection/tracking/anomaly components (Cluster 1, §6); auction/consensus/contract-net coordination as a mechanism family (Cluster 2, §6 — Bousetouane and the supplementary consensus/task-allocation papers, sources 05/11/19); "agentic AI" as a general paradigm (Cluster 3 — not invented by this project, and not surveillance-specific in any reviewed source, so applying it here is legitimate but not itself the novelty).

**What might be rebranding, not research** (per §7b): calling deterministic modules (camera perception, policy rules) "agents" uniformly. **[RECOMMENDATION]** Reserve "agent" terminology for components that are actually autonomous/negotiating (Coordinator) or actually LLM-driven (Explanation); describe the rest plainly.

**[INTERPRETATION — critical assessment requested by the user]**: The proposed direction, as originally worded ("agents coordinate and cooperate to manage the surveillance of a place, identify and alert"), is **too broad and not well-defined enough to defend on its own** — it does not name what kind of agents, what coordination mechanism, or what specifically is novel, and as shown in §6/§7, "multi-agent surveillance" by itself is not new. The already-drafted "modernized" framing (hierarchical MAS + auction coordination + rule-guarded LLM explanation + privacy-by-design) is considerably stronger and more specific, and is now independently corroborated (not just by the prior AI session's own literature synthesis, but by this session's separate reading of the local corpus) as occupying a real, narrow gap — **provided** the terminology is corrected per §7 and the evaluation is expanded per §13/F6.

---

## 9. Research Gaps (ranked)

**G1 — Auditable multi-agent coordination combined with modern (deep-learned/zero-shot) perception for surveillance. [STRONGEST]**
- Evidence: Bousetouane (05) has coordination but 2015-era classical perception; all 5 modern local theses (01–04, 06 minus consensus) have modern perception but no coordination; Monitorix (11) has coordination but pre-deep-learning perception; none of the 11 supplementary papers combine both for surveillance.
- Why it matters: this is the load-bearing claim of the existing draft's own SOTA chapter (its "G1"), and it is now independently triangulated against real, read primary documents rather than resting solely on the prior session's unverifiable web search.
- What would need to be demonstrated: a working system with both properties, evaluated against a centralized baseline **and** against a rule-based (non-auction) coordination baseline, on more than one scenario.

**G2 — Decision/generation-decoupled, evidence-grounded LLM explanation for surveillance alerts specifically. [MEDIUM-STRONG]**
- Evidence: chapter_sota.tex's own literature synthesis (Hawk, VideoAgent — unverified primary sources, treat with caution per §13) claims no surveyed system decouples generation from decision; independently, Sapkota (10) confirms "no widely accepted blueprint," "poor trust/explainability/verifiability" as an open, field-wide acknowledged gap for LLM multi-agent systems generally (not surveillance-specific, but consistent).
- Caveat: this gap's evidentiary base is weaker than G1's because the surveillance-specific half of the claim (Hawk, VideoAgent) comes from the audited, not-independently-reverified bibliography (§13). Treat as **plausible, not yet independently confirmed** until those specific citations are verified.

**G3 — System-level (not component-level) evaluation methodology for MAS surveillance under controlled ablation. [MODERATE, mainly methodological]**
- Evidence: none of the 7 local theses use system-level metrics (time-to-alert, false-alerts/hour, coordination overhead); they universally use component metrics (mAP, CCR, detection rate, TPR). HOTA (15) and ByteTrack (16) are themselves component-level tracking metrics/methods, not system-level.
- Caveat: this is more of a methodological contribution opportunity than a "gap" that requires new theory — but per §13/F6, it is also the axis where the project's own existing execution is currently weakest (single toy scenario).

**Ranking rationale**: G1 > G2 > G3 by strength of independent evidence — G1 is triangulated across a real local PhD thesis, a real historical paper, and consistent absence across all modern local work; G2 rests partly on unverified prior-session citations; G3 is a real, evidenced, but more methodological-than-theoretical gap.

---

## 10. Potential Research Questions

Derived from G1–G3, phrased narrowly and falsifiably (not "is agentic MAS surveillance good" — see §8's critique of the original broad framing):

1. **(G1)** Does combining an auditable (auction/contract-net) multi-agent coordination layer with modern deep-learned perception reduce time-to-alert and/or improve precision relative to (a) a centralized pipeline and (b) a rule-based-only coordination scheme, under controlled ablation?
2. **(G1/local-comparison)** Does a learned/zero-shot perception layer (e.g., CLIP-based anomaly scoring) combined with the classical consensus-style coordination pattern established locally by Bousetouane (05) outperform Bousetouane's own 2015 classical-feature approach on a comparable cross-camera re-identification/coordination task?
3. **(G2)** Does decoupling alert *generation* (LLM explanation) from alert *decision* (deterministic policy) reduce hallucinated or unsupported claims in generated incident reports, relative to an LLM-as-narrator baseline that is not decoupled?
4. **(G2)** What is the evidence-completeness and contradiction rate of a rule-guarded, evidence-grounded explanation agent, measured against human-rated usefulness, across a range of scenario difficulty?
5. **(G3)** Under identical perception quality, how do false-alerts-per-hour and coordination-message overhead trade off across rule-based, auction-based, and (optionally, stretch) learned coordination schemes?

**[RECOMMENDATION]** Questions 1 and 5 (or a merged version) are the natural Engineer-thesis research questions (systems/architecture-level, "does the design work"). Questions 3 and 4 are the natural Master's-thesis research questions (focused mechanism-level, "does this specific technique work, and why").

---

## 11. Potential Contributions

| Candidate contribution | Type | Novel relative to | Hypothesis | Evaluation | Baseline |
|---|---|---|---|---|---|
| Working integrated hierarchical MAS surveillance pipeline (edge perception + coordination + governance) | **Engineering** | The 5 modern local theses (single-pipeline only) and Bousetouane (no modern perception) | — (feasibility demonstration, not itself a testable hypothesis) | Working demo, code quality, reproducibility | None needed — engineering contributions are evaluated on completeness/soundness, not comparatively |
| Auction/contract-net coordination integrated with modern perception, evaluated system-level | **Architectural + Multi-agent** | Bousetouane (05, classical consensus/no modern perception); rule-based-only local systems | Auction coordination improves precision and reduces false-alerts/hour vs. no-coordination and vs. rule-based coordination, at bounded message overhead | Time-to-alert, F1, false-alerts/hour, message count, across ≥3 scenarios (not 1, per F6) | Centralized baseline; rule-based coordination baseline |
| Decision/generation-decoupled, evidence-grounded LLM explanation agent | **AI/ML + Methodological** | LLM-as-detector or LLM-as-unchecked-narrator systems (per chapter_sota's citations, unverified — flag pending verification) | Decoupled, evidence-grounded generation reduces hallucination/unsupported-claim rate vs. an undecoupled narrator baseline | Evidence completeness, contradiction rate, hallucination rate (LLM-as-judge + human-rated), operator-usefulness rating | Ungrounded/undecoupled LLM narrator baseline; template-based (non-LLM) explanation baseline |
| System-level evaluation methodology for MAS surveillance (time-to-alert, false-alerts/hour, coordination overhead under ablation) | **Evaluation** | Component-level evaluation universal in local corpus (mAP/CCR/detection-rate); HOTA/ByteTrack (component-level tracking metrics) | — (methodological contribution, not a single hypothesis) | Applied consistently across ≥3 scenarios with varied conditions | Component-only evaluation (status quo) |
| Privacy-by-design (edge-local processing, on-edge anonymization, audit logging) mapped to EU AI Act/GDPR/CNIL requirements | **Engineering + light Methodological** | None of the 7 local theses address privacy/legal compliance at all | — | Compliance checklist / design-requirement mapping, not an empirical hypothesis | — |

**[INTERPRETATION]** The **AI/ML contribution axis is weak** — none of YOLO11n, ByteTrack, or CLIP are novel ML research, and this should not be oversold. The **strongest, most defensible axes are Architectural+Multi-agent (for the Engineer thesis) and AI/ML+Methodological via the explanation-agent question (for the Master's thesis)** — this directly motivates the split in §12.

---

## 12. Possible Two-Thesis Structure

**[RECOMMENDATION]**, built on what already exists (§3d) rather than starting over:

### Thesis 1 — State Engineer Diploma (systems/engineering-oriented)

- **Research question**: Questions 1 and 5 from §10 (does hierarchical, auditable multi-agent coordination combined with modern perception improve system-level surveillance metrics vs. centralized and vs. rule-only baselines?).
- **Scope**: the full AURA-MAS pipeline — CameraAgent/AudioAgent perception, MQTT/Redis bus, FusionAgent, CoordinatorAgent (rule vs. auction ablation), PolicyAgent, dashboard, privacy-by-design (anonymization, audit log). This matches what is already ~80% built (per `README.md`, `STATE_NOTES.md`).
- **Contribution type**: Engineering + Architectural (+ light Multi-agent, per §11).
- **Methodology**: expand the existing single-scenario evaluation (§13/F6) to ≥3 scenarios before treating any comparative numbers as defensible.
- **Explicitly excludes**: deep evaluation of the LLM explanation agent's output quality — treat `ExplanationAgent` as a working component but not the object of study here.

### Thesis 2 — Master's degree (research-oriented)

- **Research question**: Questions 3 and 4 from §10 (does decision/generation decoupling reduce hallucination/unsupported claims in LLM-generated incident explanations, and how good is the resulting explanation quality?).
- **Scope**: takes the Thesis-1 system as a **given platform** (built, not re-litigated) and focuses narrowly on the `ExplanationAgent` — this is the one component in the whole architecture that is genuinely and fully "agentic AI" in the Sapkota sense (§7).
- **Contribution type**: AI/ML + Methodological (the strongest, most novel axis per §11).
- **Methodology**: ablation against an undecoupled LLM-narrator baseline and a template-based non-LLM baseline; evidence-completeness, contradiction-rate, hallucination-rate (LLM-as-judge, cross-checked with human rating), and operator-usefulness metrics — none of which appear in any of the 20 reviewed sources for this specific domain, making this genuinely the most defensible novelty claim in the whole project.

**Avoiding duplication**: Thesis 1's evaluation stays at the system/architecture level (does distributing + coordinating help at all); Thesis 2's evaluation stays at the single-component/mechanism level (is this specific explanation technique good, and why) — different research questions, different metrics, different baselines, clearly separable at a defense. **[RECOMMENDATION]** State this division explicitly in both theses' introductions so neither committee perceives overlap.

**[FACT]** A prior AI session already attempted a two-thesis split in this project (`engineerthesis/` vs. the main Master's thesis), but per §2/§13, the existing `engineerthesis/` content is topically unrelated (a consultation-marketplace platform) — so this split needs to be built fresh along the lines above, not adapted from what exists.

---

## 13. Risks and Weaknesses

**[FACT — high priority, unrelated to the literature question, but must be fixed regardless of research direction]**
1. **Title-page authorship mismatch**: the compiled Master's and (unrelated) Engineer thesis PDFs carry the name "BELMANA Soufyane" and supervisor "Pr. AMAR BENSABER Djamel" — apparently inherited from the LaTeX template and never replaced, per `STATE_NOTES.md`'s own change-log, which lists many adaptations but not this one. **[RECOMMENDATION]** Fix before any submission or sharing of these PDFs; treat as a template artifact, not a content issue.
2. **No Engineer-diploma-level surveillance thesis currently exists**: `engineerthesis/` compiles to a document about an unrelated "Consultation Marketplace" platform. **[RECOMMENDATION]** Clarify with the institution/program whether this reflects a genuinely separate, already-assigned Engineer-diploma requirement, or whether it's stray content to be discarded — this materially affects whether §12's Thesis-1 plan is starting fresh or needs to be reconciled with an existing obligation.
3. **Bibliography accuracy** (finding F5): spot-checked entries are real papers but with corrupted author fields, truncated author lists, at least one paraphrased title, and at least one likely-wrong year. **[RECOMMENDATION]** Full verification pass before defense; treat the existing `bibliography.bib` as a discovery list, not submission-ready.
4. **Toy-scale existing results** (finding F6): current comparative numbers come from one scenario, 2 real clips + 1 synthetic audio event, self-defined ground truth. **[RECOMMENDATION]** Expand to ≥3 scenarios before presenting any comparative claim (directly required by §12's Thesis-1 methodology).
5. **Terminology overclaim risk** (§7b): calling all seven planned components "agents" uniformly is not fully accurate; a jury familiar with MAS theory (plausible given Bousetouane/BREK exist locally) may probe this specifically.
6. **Ambition/capacity mismatch**: the original blueprint (`pasted_content_2.txt`) recommends ROS2/DDS, Kafka, Isaac Sim/Omniverse digital twins, MAPPO/QMIX, and UCF-Crime/XD-Violence benchmark evaluation — considerably more ambitious than what is actually implemented (MQTT/Redis, single-round auction, toy scenario). **[RECOMMENDATION]** Keep scope anchored to what §12 actually proposes; treat the blueprint as aspirational background, not a literal requirements list.
7. **G2's evidentiary base is partly unverified** (§9): the specific claim that no LLM video-agent system decouples generation from decision rests on citations (Hawk, VideoAgent) from the audited, not-yet-independently-verified bibliography. **[RECOMMENDATION]** Independently verify these two specific citations before relying on G2 as a defended gap.
8. **Unresolved status of `pfe_surviellance_pfe/`**: possibly superseded, possibly still relevant — not resolved by this report (§2).

---

## 14. Recommended Research Direction

**[RECOMMENDATION]**, synthesizing §7–§13:

1. **Reframe the proposed direction** away from "an agentic multi-agent surveillance system" (too broad, partially pre-existing since 2000) toward the precise, evidence-backed intersection identified in G1/G2: *auditable multi-agent coordination + modern perception* (Engineer thesis) and *decision-decoupled, evidence-grounded LLM explanation* (Master's thesis).
2. **Adopt precise terminology** per §7: describe the overall system as a hierarchical multi-agent (classical/software-agent-theoretic) architecture with one embedded LLM-based AI Agent subsystem — not uniformly "Agentic AI."
3. **Split into two theses** as detailed in §12, sharing the same underlying platform but with cleanly separated research questions, evaluation methodologies, and baselines.
4. **Before either thesis is finalized**, resolve the five risk items in §13 that are independent of the research direction: title-page identity, Engineer-diploma administrative status, bibliography verification, evaluation-scale expansion, and G2's citation verification.
5. **Position novelty honestly**: this project's own SOTA chapter's three gaps (G1–G3) are now independently corroborated against 8 real local theses and 11 supplementary papers this session actually read — a materially stronger evidentiary basis than existed before this research pass, but still narrower than the original broad framing implied.

---

## 15. Open Questions Requiring Further Investigation

1. Is `engineerthesis/`'s current content (consultation marketplace) a real, separate, already-assigned Engineer-diploma obligation, or stray/mistaken content? — **only the user/institution can answer this.**
2. Who is "BELMANA Soufyane," and is the ESI-SBA/jury information in the templates genuinely applicable, or purely a template artifact? — **only the user can answer this.**
3. Is `pfe_surviellance_pfe/` formally superseded, or does it need to be reconciled/merged?
4. Does `pfe_agentic_ai/` represent a live, parallel obligation that needs independent tracking, or is it fully closed/irrelevant to this trajectory?
5. What are the actual institutional regulations governing the Engineer-diploma + Master's split (are two fully independent theses required, or is a shared-platform/differentiated-scope structure like §12's acceptable)? — outside document scope; requires checking with the program directly.
6. Do the two specific citations underlying G2 (Hawk, VideoAgent, in the audited `bibliography.bib`) actually say what `chapter_sota.tex` claims they say? — not yet independently verified in this session; recommended before relying on G2.
7. Has any very recent (2026, post-dating this session's supplementary corpus) paper already closed the G1 gap? The Cloud-Edge-Terminal survey (source 20, 2025) explicitly still calls LLM/multimodal integration an "open frontier" as of its writing — worth a final targeted check close to submission time.

---

## Methodology Note

This investigation triangulated claims across three independent, differently-typed source categories per the deep-research triangulation standard: (a) primary local academic documents (8 theses, read directly), (b) supplementary peer-reviewed/preprint literature (11 papers, read directly), and (c) this project's own prior AI-generated materials (audited critically, not treated as primary evidence — see finding F5). Where a claim (e.g., G1) is supported by all three categories, it is reported with higher confidence than where a claim (e.g., G2) rests partly on category (c) pending independent verification. All source files, verbatim quotes with page numbers, and the full triage table are preserved in `sources/` for audit.
