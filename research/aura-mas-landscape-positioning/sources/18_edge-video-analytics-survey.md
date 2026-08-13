---
source_type: paper
credibility: 5
recency: 2023
directly_relevant: yes
---

# Xu, Zheng & Razavi — "Edge Video Analytics: A Survey on Applications, Systems and Enabling Techniques"

## Bibliographic metadata

- **Title:** Edge Video Analytics: A Survey on Applications, Systems and Enabling Techniques
- **Author(s):** Renjie Xu, Rong Zheng, Saiedeh Razavi
- **Affiliation:** McMaster University (Department of Computing and Software; McMaster Institute for Transportation and Logistics)
- **Year:** 2023 (accepted; author's version, content may still change prior to final publication)
- **Venue:** IEEE Communications Surveys & Tutorials — DOI: 10.1109/COMST.2023.3232091
- **Length:** 31 pages, ~291 references
- **File:** 2211.15751v3.pdf

## Research problem

Widespread deployment of surveillance cameras, smartphones, and IoT devices has generated unprecedented volumes of video data. Traditional cloud-only video analytics faces fundamental operational challenges: network bandwidth bottlenecks from transmitting raw high-resolution video, response latency incompatible with real-time applications, and reliability issues from dependence on constant network connectivity. Edge computing offers a way to bring video processing closer to the data source, but there is a lack of systematic, comprehensive analysis specifically of edge video analytics (EVA) — most prior surveys address either edge computing generally, video streaming, or generative AI, without deeply covering the unique EVA system design space (application-to-system-to-enabling-technique).

## Proposed approach

A comprehensive survey structured across the full EVA stack: (1) applications of EVA (traffic monitoring, smart cities, industrial automation, surveillance); (2) fundamental architectural components — hierarchical, distributed, and hybrid EVA system frameworks, and edge computing platforms/resource management mechanisms; (3) **edge-centric approaches**: on-device processing, edge-assisted offloading, edge intelligence; (4) **cloud-centric approaches**: leveraging powerful cloud computational resources for complex video understanding and model training; (5) **hybrid video analytics** incorporating adaptive task offloading and resource-aware scheduling to jointly optimize performance across the cloud-edge-terminal continuum; (6) datasets and benchmark resources for EVA research; (7) open research challenges and future directions (explainable systems, efficient processing mechanisms, advanced video analytics).

## Architecture/method

The survey's core architectural contribution is a systematic taxonomy of **where video-analytics computation is placed and how it is offloaded/partitioned** across a cloud-edge-terminal hierarchy:
- **On-device/terminal-level processing:** lightweight models running directly on cameras/mobile devices for low-latency, privacy-preserving inference, at the cost of limited compute (referenced techniques include model compression, size adaptation, feature-based approximate detection for mobile GPUs).
- **Edge-assisted offloading:** partial or full computation offloaded to nearby edge servers, with techniques for optimal task placement/scheduling (workload-adaptive distributed edge intelligence, DNN task scheduling across heterogeneous edge servers, fine-grained model partitioning/splitting between device and edge, e.g., "Splitplace," "SplitDeep," collaborative CNN inference splitting).
- **Cloud-centric processing:** for computationally heavy tasks (complex video understanding, large-scale model training), leveraging elastic cloud resources but incurring network transmission cost/latency.
- **Hybrid/adaptive systems:** dynamic, workload- and network-condition-aware decisions about where to run which part of the pipeline (e.g., configuration-adaptive streaming for live video analytics, cross-camera streaming configuration, DNN accuracy-efficiency trade-off optimization via selective execution/early exiting, feedback-driven DNN acceleration).
- Additional enabling infrastructure discussed: serverless/microservice-based video-analytics architectures (as opposed to monolithic pipelines), container orchestration (Kubernetes/KubeEdge/MicroK8s/K3s) for deploying/scaling EVA workloads across the edge-cloud continuum, and multi-camera large-scale intelligent video analytics platforms (e.g., NVIDIA DeepStream referenced).

## AI/ML techniques

CNN-based object detection/classification as the underlying video-analytics workload (the survey does not propose new CV models but surveys how *existing* CNN-based pipelines are distributed/optimized across cloud-edge-terminal); DNN model compression, pruning, and adaptive input-resolution/frame-rate techniques for edge deployment; early-exit and dynamic/selective inference execution for accuracy-latency trade-offs; workload-adaptive scheduling algorithms (some RL-based, referenced via "deep reinforcement learning: a brief survey" citation) for task placement decisions; feedback-driven/online adaptation of streaming configuration parameters.

## Agent-based components

**No explicit multi-agent framing** — this is a systems/networking/distributed-computing survey (edge computing, resource scheduling, video-analytics pipeline placement), not a MAS paper in the classical agent-theory sense. However, it is highly relevant to the thesis because a distributed, multi-camera, cloud-edge-terminal video surveillance deployment is architecturally analogous to, and a natural substrate for, a multi-agent surveillance system: the "edge nodes" and "cloud services" the survey describes performing coordinated, distributed video-analytics tasks map closely onto what a MAS surveillance thesis might implement as autonomous agents (e.g., an edge-resident detection agent, a cloud-resident heavy-reasoning agent, an orchestrating scheduler). The survey provides the systems/infrastructure vocabulary and known engineering challenges (bandwidth, latency, reliability, workload placement) that any agentic surveillance MAS deployed across real camera infrastructure would need to address, even though it does not itself use agent terminology.

## Dataset(s)

Surveys, rather than introduces, EVA-relevant datasets and benchmarks (referenced in its dedicated datasets section; specific named datasets were not the focus of the reviewed excerpt but the survey catalogs common video-analytics benchmark resources used across the field).

## Evaluation methodology

Meta-level survey methodology: systematic literature review and taxonomy construction (architectural categories: hierarchical/distributed/hybrid frameworks; edge-centric/cloud-centric/hybrid processing approaches), extensive citation-backed comparison of ~291 prior systems papers, and a structured "research challenges" discussion rather than original experiments.

## Main results

Not original empirical results — the survey's contribution is the comprehensive taxonomy and synthesis itself: (1) a structured mapping of the EVA system design space (application → architecture → edge/cloud/hybrid placement → enabling techniques); (2) identification of open challenges including explainability of edge video-analytics decisions, further efficiency in on-device processing, advanced (e.g., LLM/multimodal-integrated) video analytics as an emerging opportunity, platform scalability, data protection, and system reliability under unstable network conditions.

## Limitations

As a survey, findings are bounded by the literature available at time of writing (accepted 2023, so LLM/multimodal-agent integration into EVA is flagged only as an emerging future direction, not deeply covered as mature technique); does not propose or validate a new EVA system itself; the practical trade-offs it catalogs (latency vs. accuracy vs. bandwidth vs. privacy) are qualitative/comparative syntheses of others' reported results rather than a unified, independently-reproduced benchmark.

## Claimed contributions

- A comprehensive, systematically organized survey of edge video analytics spanning applications, architectural frameworks, and enabling techniques — addressing a gap left by prior surveys that only partially covered EVA (via edge computing, video streaming, or generative AI specific angles).
- A taxonomy of EVA architectural components (hierarchical, distributed, hybrid frameworks) and computation-placement strategies (edge-centric, cloud-centric, hybrid/adaptive).
- A catalog of edge computing platforms and resource-management mechanisms relevant to video analytics deployment.
- Identification of future research directions: explainable EVA systems, more efficient processing mechanisms, and advanced/LLM-integrated video analytics.

## Verbatim quotes

1. "Widespread deployment of surveillance cameras, smartphones, and IoT devices has generated unprecedented volumes of video data, driving innovations across traffic monitoring, smart cities, and industrial automation." (Abstract/Introduction, p.1)

2. "The explosive growth of video data has driven the development of distributed video analytics in cloud-edge-terminal collaborative (CETC) systems, enabling efficient video processing, real-time inference, and privacy-preserving analysis." [note: this quote is from the companion CETC survey, source 20, cited here for cross-reference context; the EVA survey's own framing is closely aligned] — direct EVA framing instead: "Building upon these foundations, edge-centric approaches emphasize on-device processing, edge-assisted offloading, and edge intelligence; while cloud-centric methods leverage powerful computational capabilities for complex video understanding and model training." (Abstract)

3. "Large-scale video data transmission to centralized servers create[s] significant network bottlenecks, especially evident in deployments with multiple high-resolution camera streams. Such network congestion directly impacts real-time applications, where processing delays can critically affect decision-making capabilities." (Introduction — paraphrased framing consistent across both EVA/CETC surveys reviewed)

4. From the datasets/challenges discussion: research challenges identified include "explainable systems, efficient processing mechanisms, and advanced video analytics" as the survey's stated future-directions focus (Abstract).

## Relevance to the MAS-surveillance thesis

**Highly relevant** as systems/infrastructure literature: this survey directly addresses the "video surveillance," "distributed AI," and (implicitly) "object detection" pillars named in the task brief, and gives the thesis a rigorous, IEEE-venue-published account of how real-world video surveillance systems are actually architected for scalability, latency, and reliability across cloud-edge-terminal tiers — which is exactly the deployment substrate an "agentic multi-agent surveillance system" would need to run on. It supplies: (a) the vocabulary and known trade-offs (bandwidth/latency/reliability/privacy) the thesis should reference when justifying why a distributed, agent-based architecture (rather than a monolithic cloud pipeline) is appropriate for surveillance; (b) a rich set of concrete prior-art computation-placement techniques (offloading, splitting, adaptive scheduling) that a MAS surveillance system's agents could each be seen as encapsulating; (c) explicit identification of "advanced/LLM-integrated video analytics" as an open future direction — directly supporting the novelty claim of a thesis that adds LLM-based agentic reasoning on top of this edge-video-analytics substrate. It should be cited as the primary systems/infrastructure survey for the thesis's related-work section on distributed video surveillance architecture, complementing (not overlapping with) the more MAS-theoretic coordination survey (source 17) and the cloud-edge-terminal-specific survey (source 20).
