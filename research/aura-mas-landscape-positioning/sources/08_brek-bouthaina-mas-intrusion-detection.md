---
source_type: thesis
credibility: 2
recency: 2019
directly_relevant: partial
---

# BREK Bouthaina — "Système de Detection d'Intrusion basée sur Les Systémes Multi-Agents"

## Bibliographic metadata

- **Title:** Système de Detection d'Intrusion basée sur Les Systémes Multi-Agents ("Intrusion Detection System based on Multi-Agent Systems")
- **Author:** BREK Bouthaina
- **Year:** 2018/2019 academic year; defended 23/06/2019
- **Institution:** Université Larbi Tébessi, Tébessa (Algeria), Faculté des Sciences Exactes et des Sciences de la Nature et de la Vie
- **Department / Filière:** Département Mathématiques et Informatique — Domaine: Mathématiques et Informatique — Filière: Informatique — **Option: Réseau et Sécurité Informatique** (Networking & Information Security track — confirms cybersecurity framing from the title page itself)
- **Supervisor (Encadreur):** Mr. Ali Abdelatif Betouil (MCB, Université Larbi Tébessa)
- **Jury:** Mr. A. Sahraoui (MAA, Président), Mr. Y. Menassel (MAA, Examinateur)

## Research problem (in own words)

Traditional (centralized/monolithic) network Intrusion Detection Systems (IDS) do not scale well as networks grow in users, services, and attack complexity. Centralized data processing creates a single point of failure, degrades performance (scalability, configurability, fault tolerance), and a large event flux can overwhelm the central analyzer, causing slow response, network overload, and data loss that biases analysis. Centralization also hampers extensibility/reconfiguration. The thesis frames Multi-Agent Systems (MAS), and specifically **mobile agents**, as a way to distribute the detection workload — moving the analyzer to the audit data rather than moving audit data to a central analyzer — while using Machine Learning to make each agent capable of independently classifying traffic as attack/normal.

## Objectives

Stated explicitly (p.34-35):
- A **distributed approach** for detecting signature-characterized attacks.
- A model using **mobile agent technology** to distribute intrusion detection across the network.
- A model using **Machine Learning technology** so each agent can detect different attacks and determine their type, making the overall model "more reliable."

## Proposed approach (high-level)

A distributed IDS in which the network is represented as a set of JADE "containers"/nodes, each hosting one **mobile agent**. Each agent is pre-trained with a *different* Weka ML classifier (Naïve Bayes, Decision Tree, RIPPER/JRip, Neural Network) and independently analyzes the traffic/records at the node it currently occupies. When an agent's classification confidence for a record falls below a fixed threshold (s = 50%), the system "loses confidence" in that local classification and triggers **agent mobility**: the agent sends an ACL message and the system randomly selects another agent to relocate to a different node ("il choisit un agent aléatoirement pour permuter les nœuds," conclusion, p.48), so that a different classifier ends up covering that traffic. If confidence exceeds the threshold, the record is simply treated as classified (attack/normal) and no action is taken.

## System architecture — THE KEY FIELD

**This is network-level, packet/connection-record cybersecurity intrusion detection — NOT physical or video/camera-based surveillance.** There is no computer vision, no image/video processing, and no camera-based sensing anywhere in the document. The unit of analysis throughout is a network traffic/connection record from the NSL-KDD dataset (an offline CSV of network connection features), and "nodes" in the architecture are network hosts/machines, not physical spaces or cameras.

**Agent types:** There are exactly **four agent types, one per ML classifier**, each implemented as a distinct Java class extending JADE's `Agent`:
- `NBAgent` — Naïve Bayes classifier
- `DTAgent` — Decision Tree classifier
- `JRIPAgent` — RIPPER (JRip) rule-learner
- `NNAgent` — Neural Network (multilayer perceptron, via Weka)

Each agent is deployed into its own named JADE container (e.g., "DT-Noeud", "NB-Noeud", "JRIP-Noeud", "NN-Noeud"). There is **no separate coordinator/manager/collector agent** and no hierarchy — this is a flat, peer architecture of 4 homogeneous-role (heterogeneous-classifier) agents.

**What each agent does:** On `setup()`, the agent loads the NSL-KDD training CSV, builds its Weka classifier, loads the NSL-KDD test CSV, and for each test instance obtains a class-probability prediction. If the predicted probability is below the fixed 50% confidence threshold, the agent triggers a `Mobilité` behaviour (a JADE `OneShotBehaviour`) that: (1) picks a destination container — the actual Java code (Fig. 21-23) picks a **random** container name from a fixed list of the other node names, not necessarily a paired swap; (2) sends an `ACLMessage.INFORM` to the AIDs of the other agents; (3) calls `myAgent.doMove(destination)` to physically relocate the agent's execution (code + state) to the new container. Note: the architecture diagrams (Figures 13-15) depict this as a **pairwise "swap" between two specific agents** conditioned on the low-confidence event, while the actual pseudocode/implementation (Figures 21-23, and the final conclusion's own wording) describes a **random agent choice among the available nodes** — the diagram and the implementation are not perfectly consistent, and the thesis's own conclusion (p.48) confirms the "random agent, permute nodes" version is what was actually built.

**Coordination mechanism:** Communication is via **JADE's Agent Communication Language (ACL)** message passing (`ACLMessage.INFORM`), combined with actual **agent mobility** (`doMove()` between JADE containers) as the coordination primitive — not a blackboard, not contract-net negotiation, not an auction. Despite the literature review (Chapter 2) discussing richer MAS coordination concepts (negotiation, organization, planning, synchronization, delegation), **none of these are implemented** — the working system's only coordination logic is a single fixed threshold rule ("if confidence < 50%, relocate") plus ACL broadcast/inform.

**Is this a genuine MAS in the literature sense, or a "pipeline loosely called agents"?** It sits in between. On the positive side: it is built on a real, standard MAS platform (JADE), uses genuine agent mobility (code/state migration between containers) and genuine ACL messaging — this is architecturally a real (if simple) multi-agent system, not merely a modular pipeline with the word "agent" attached. On the negative side: each agent's "intelligence" is a single pre-trained, static Weka classifier invoked once per instance — there is no online learning, no goal-directed planning, no negotiation/bargaining between agents, and the only inter-agent decision logic is one fixed IF-THEN rule. Autonomy and reactivity are present in a minimal sense (agent decides for itself whether to relocate); proactivity and social/negotiation properties (both explicitly listed as agent properties in the thesis's own Chapter 2 taxonomy) are essentially absent from the implementation.

## AI/ML techniques used

Four classical (non-deep, non-CV) Weka classifiers, one per agent, each described briefly in the text:
- **Naïve Bayes** (Bayes' theorem-based classifier)
- **Decision Tree** (generic Weka decision-tree classifier; specific Weka class not named beyond "Decision Tree")
- **RIPPER / JRip** — "Repeated Incremental Pruning to Produce Error Reduction," a rule-learner (William W. Cohen), described as an optimized version of IREP
- **Neural Network** — described generically as a "series of algorithms" mimicking brain function; specific Weka class (e.g., MultilayerPerceptron) not explicitly named in the text

No deep learning, no CNNs/RNNs, no reinforcement learning, no LLMs.

## Computer vision techniques

**None.** The document contains zero mention of images, video, cameras, frames, object detection, or visual features. Confirmed net-level/tabular-data only.

## Dataset(s) used

**NSL-KDD Dataset** — a well-known **public benchmark** (improved version of the KDD Cup '99 dataset, addressing its redundant-record problems). The thesis explicitly acknowledges (citing its own reference [64]) that NSL-KDD "n'est pas un représentant idéal des réseaux réels actuels" (is not an ideal representative of today's real networks) but is still useful as a reference dataset for comparing detection methods.
- Training file: `normal_training20.csv` — 40,000 instances
- Testing file: `normal_testing.csv` — 199,996 instances (note: this is unusually large relative to the standard NSL-KDD test partitions — e.g., the canonical KDDTest+ file has ~22,544 records — suggesting a nonstandard preprocessing, duplication, or a different NSL-KDD file variant than usually cited; not explained in the text)
- Only two class labels used: **"Attack" vs "Normal"** (binary), not the finer DARPA-style categories (DoS, Probing, R2L, U2R) — explicitly flagged as future work.

## Evaluation methodology and metrics

Standard binary-classification confusion-matrix metrics computed per agent/classifier:
- **DR (Detection Rate)** = TP / (TP + FN) × 100
- **FAR (False Alarm Rate)** = FP / (FP + TN) × 100
- **Accuracy** = (TP + TN) / (TP + TN + FP + FN) × 100

No cross-validation, ROC/AUC, precision/recall/F1, or latency/scalability benchmarking is reported. No comparison against a non-agent (single-machine, non-mobile) baseline running the same four classifiers is performed, so the specific contribution of the mobile-agent architecture to detection quality (as opposed to the classifiers' own inherent quality on NSL-KDD) is not empirically isolated.

## Main quantitative results (as reported, p.44-46)

Per-agent results (Figure 24):
| Agent (classifier) | TP | FP | TN | FN | DR | FAR | Accuracy |
|---|---|---|---|---|---|---|---|
| NB (Naïve Bayes) | 6068 | 1734 | 31374 | 823 | 88.06% | 5.24% | 93.61% |
| DT (Decision Tree) | 34280 | 671 | 164869 | 175 | 99.49% | 0.41% | 99.58% |
| JRIP (RIPPER) | 34177 | 437 | 165103 | 278 | 99.19% | 0.26% | 99.64% |
| NN (Neural Network) | 30313 | 660 | 164880 | 4142 | 87.98% | 0.40% | 97.60% |

The Decision Tree agent is presented as "le meilleur agent" (the best agent). A pairwise-averaging example is shown for the "JRIP-Nœud" (averaging jripagent + nnagent results): DR = 93.585%, FAR = 0.33%, Accuracy = 98.62%.

The general conclusion (p.48) reports an overall system-level result: **DR = 93.68%, FAR = 1.5775%, Accuracy = 97.6075%**.

Note: there are visible **labeling inconsistencies** across Figure 24's result boxes (e.g., a box showing what appear to be Neural-Network-style numbers labeled "DT-Noeud," and "affich NN-Noeud" appearing under the JRip results box) — these look like copy/paste or annotation errors in the results section, and reduce confidence in the precise agent-to-node attribution of the headline numbers, though the numbers themselves are internally plausible and roughly consistent with typical published NSL-KDD results for these algorithm families.

## Stated limitations (from the document's own conclusion/perspectives)

- Only binary "Attack"/"Normal" classification — no distinction between the four standard DARPA attack categories (DoS, Probing, R2L, U2R); listed as future work ("Amélioré ce travail en utilisant une nouvelle dataset d'actualité et qui contient les quatre catégories d'attaque...").
- The work is explicitly framed as needing further completion to become "une application fiable et commerciale" (a reliable, commercial-grade application) — i.e., the author herself frames the current system as a prototype/proof of concept, not production-ready.
- NSL-KDD itself is acknowledged (via cited source) as not fully representative of current real-world network traffic.

## Claimed contributions

- A distributed intrusion detection model based on mobile agents that avoids the weaknesses (scalability, single point of failure, network overload) of centralized IDS architectures reviewed in Chapter 1/2.
- The core mobile-agent idea: "transporting the analyzer to the audit flow rather than the audit flow to the analyzer" — moving computation to data rather than data to computation.
- Integration of four different ML classifiers, each embedded in its own mobile JADE agent, achieving detection rates approaching 99% for some agents (DT, JRip) on NSL-KDD.

## MAS platform/framework used

**JADE (Java Agent DEvelopment Framework)** — a standard, real Java-based multi-agent platform providing ACL messaging and agent mobility (`doMove()`), used together with **Weka** (3.8.3) for the ML classifiers and **Eclipse Indigo** as the IDE. Language: Java 8 (JRE 8).

## Critical assessment (own analysis)

- **Real but shallow MAS.** The system is a legitimate, working implementation on a genuine MAS platform (JADE) with real agent mobility and ACL messaging — a meaningfully stronger claim to "multi-agent-ness" than a system that merely renames pipeline modules "agents." However, the actual coordination intelligence is limited to a single fixed confidence threshold plus a broadcast/random-relocation rule; none of the richer MAS coordination mechanisms discussed in the thesis's own literature chapter (negotiation, contract-net-like delegation, blackboard, hierarchy) are actually implemented. The architecture reviewed for related work (AAFID, IDA/Japan, JAM) is *more* hierarchically sophisticated (monitor/transceiver/collector roles) than what this thesis itself builds, which is flatter (four peer agents + one relocation rule).
- **Diagram/implementation mismatch.** Figures 13-15 depict a specific two-agent "swap on low confidence" interaction, but the actual pseudocode and code (Figures 21-23) and the general conclusion describe random selection of a destination/agent among a fixed list — a discrepancy between the described architecture and what was actually built, worth flagging if this thesis is cited as a comparator.
- **Unvalidated scalability/robustness claims.** The motivating argument for mobile agents (reduced network delay, reduced traffic, persistence/fault tolerance, scalability) is never empirically tested — there is no real multi-host network deployment, latency measurement, or failure-injection experiment; everything runs via JADE's Remote Agent Management GUI on what appears to be a single machine (IP 192.168.1.33) with multiple logical containers. The performance numbers reported are purely classifier accuracy metrics on a static offline dataset, not systems-level (distributed, mobile-agent) benefits.
- **No ablation against non-agent baseline.** Because the same four Weka classifiers would likely produce very similar DR/FAR/Accuracy numbers if simply run centrally (without any agent/mobility apparatus) on the same NSL-KDD split, the reported ~99% detection rates should be attributed mainly to the classifiers (Decision Tree/JRip are well known to perform strongly on NSL-KDD in many non-agent papers), not to the multi-agent architecture itself. The thesis does not isolate or demonstrate any performance benefit specifically attributable to "being multi-agent."
- **Dataset/reporting inconsistencies.** The reported test-set size (199,996 instances) is far larger than the standard NSL-KDD test partitions, and per-agent result labels in Figure 24 appear internally inconsistent (mismatched node labels), both of which reduce confidence in the precision of the reported numbers, though they do not invalidate the overall approach.
- **Overclaiming is modest.** The thesis is fairly measured — it explicitly frames the work as incomplete/non-commercial and proposes concrete future work (multi-class attack categorization, a more current dataset). It does not overclaim generalizability beyond the tested scenario.

## Verbatim quotes (with page numbers)

1. Abstract (p. II): "we assert that multi-agent technology and precisely a mobile agent greatly contributes to achieving the desired ideal behavior in an intrusion detection system (IDS), and to improve the performance of mobile agents, we make them intelligent in using machine-learning techniques."

2. Motivations (p.34): "Les agents mobiles nous permettent de faire le calcul distribué. L'idée est de faire transporter l'analyseur vers les flux d'audit et non les flux d'audit vers l'analyseur."

3. Architecture description (p.35): "Notre architecture se compose de plusieurs conteneurs, qui contiennent à leur tour un agent, doté de la fonctionnalité de la mobilité, ce qui signifie qu'il est possible de passer d'une machine à une autre, et qu'il s'agit d'une machine learning de sorte que chacun d'entre eux est différent et il se base sur des différent classifieur pour permettre l'analyse d'un nœud réseau dans lequel il se trouve et selon les résultats de l'analyse ils vont déterminer s'il y a une attaque ou non."

4. Coordination/communication mechanism (p.36): "La communication entre les agents se fait à partir de l'expédition et la réception des message ACL (Agent Communication Langage)... Afin d'envoyer le résultat de la probabilité et selon la condition les deux agents se déplacent vers leurs nœuds en échangeant les conteneurs."

5. Best individual result (p.44): "si on prend les résultats de l'agent DTAgent (Decision Tree) on voit qu'il est le meilleur agent; 34280 attaques (True Positive) et 164869 normale (True Négative)... il a les meilleurs résultats de performance par une DR égale à 99.49 % et FAR égale à 0.41 %, Accuracy égale à 99.58 %."

6. General conclusion, exact coordination rule as implemented (p.48): "On a fixé un seuil s=50% comme un minimum de confiance, si la valeur du test dépasse s alors l'agent traite l'enregistrement comme « normal » sinon il choisit un agent aléatoirement pour permuter les nœuds."

## Relevance note

This thesis is **network/cybersecurity intrusion detection**, not physical or video-based surveillance, and contains no computer vision component whatsoever — so it does not overlap with an "agentic multi-agent video surveillance" research direction on the sensing/perception side at all. However, it remains a directly relevant **local precedent** for the user's thesis jury context: it is a Master's thesis from an Algerian university (Larbi Tébessi, Tébessa) explicitly combining "Systèmes Multi-Agents" with a detection/security task, built on a real MAS platform (JADE) with genuine agent mobility and ACL communication, integrated with classical ML (not deep learning, not CV). A jury evaluating a proposed "agentic multi-agent surveillance system" thesis may well be aware of or compare against this kind of local prior work, so it is useful to explicitly position the new work against it: e.g., contrasting network-traffic/tabular multi-agent detection (this thesis) against physical/video-based multi-agent detection (the proposed thesis), and contrasting this thesis's flat, single-threshold, mobility-based coordination against a more sophisticated agentic architecture (richer autonomy, planning, negotiation, and/or LLM-based reasoning) that a modern "agentic" MAS surveillance system would be expected to demonstrate.
