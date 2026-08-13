---
source_type: paper
credibility: 3
recency: 2025
directly_relevant: yes
---

# Gong et al. — "A Survey on Video Analytics in Cloud-Edge-Terminal Collaborative Systems"

## Bibliographic metadata

- **Title:** A Survey on Video Analytics in Cloud-Edge-Terminal Collaborative Systems
- **Author(s):** Linxiao Gong, Hao Yang, Gaoyun Fang, Bobo Ju, Juncen Guo, Xiaoguang Zhu, Xiping Hu, Yan Wang, Peng Sun, Azzedine Boukerche
- **Affiliations:** Fudan University; University of Toronto; Imperial College London; University of California, Davis; SMBU; Duke Kunshan University; University of Ottawa
- **Year:** 2025 (v4, 5 Apr 2025)
- **Venue:** arXiv preprint (arXiv:2502.06581v4, cs.NI)
- **Length:** 9 pages

## Research problem

The explosive growth of video data (surveillance cameras, smartphones, IoT devices) demands distributed video analytics that is real-time, efficient, and privacy-preserving. Cloud-only video analytics faces bandwidth bottlenecks and latency that critically impact response-sensitive applications (e.g., traffic monitoring, autonomous driving); dependence on constant, reliable cloud connectivity is itself a reliability risk in areas with unstable networks. Cloud-Edge-Terminal Collaborative (CETC) systems — jointly leveraging cloud servers, edge devices, and terminal/end devices — have emerged as a promising architecture, but prior surveys addressed only isolated pieces of this space (edge computing alone, video streaming alone, or generative-AI integration alone) without a systematic treatment of video analytics specifically across the full cloud-edge-terminal collaborative continuum, including how large language models and multimodal integration create new opportunities/challenges in this setting.

## Proposed approach

A survey structured around: (1) fundamental CETC architectural components — hierarchical, distributed, and hybrid frameworks; edge computing platforms; resource management mechanisms; (2) **edge-centric approaches** (on-device processing, edge-assisted offloading, edge intelligence); (3) **cloud-centric approaches** (leveraging cloud compute for complex video understanding and model training); (4) **hybrid video analytics** incorporating adaptive task offloading and resource-aware scheduling to optimize performance across the full cloud-edge-terminal system; (5) recent advances integrating **large language models and multimodal models** into video analytics, examining both opportunities and challenges for platform scalability, data protection, and system reliability that this integration raises; (6) future directions: explainable systems, efficient processing mechanisms, advanced video analytics.

## Architecture/method

Note: this survey's architectural taxonomy (hierarchical/distributed/hybrid frameworks; edge-centric/cloud-centric/hybrid approaches) closely parallels the companion Edge Video Analytics survey (source 18) — both surveys, published within roughly the same period by overlapping thematic focus, organize the field along the same core axis of *where computation is placed across the cloud-edge-terminal hierarchy*. This paper's specific added emphasis, distinguishing it from source 18, is: (a) explicit framing around the three-tier "cloud-edge-terminal" (rather than just "edge") continuum, treating terminal/end devices as a distinct architectural tier alongside edge and cloud; (b) a dedicated treatment of **LLM and multimodal-model integration** into video analytics pipelines as a specific, recent architectural trend — examining how LLMs/multimodal models are being incorporated into video-understanding workflows and what new system-level challenges (scalability, data protection/privacy, reliability) this integration introduces, beyond the classical CNN-based analytics pipelines covered by earlier edge-video-analytics literature.

## AI/ML techniques

CNN-based video analytics as the traditional workload baseline; edge intelligence and adaptive task-offloading/resource-scheduling algorithms (similar techniques to source 18: model compression, adaptive streaming configuration, workload-aware scheduling); and, distinctively, coverage of **large language models and multimodal models** as an emerging component of video-analytics pipelines (e.g., using LLMs/VLMs for higher-level video understanding, semantic querying, or reasoning over video-derived data, layered on top of the cloud-edge-terminal infrastructure) — directly relevant to a thesis proposing LLM/VLM-based agentic reasoning over surveillance video streams.

## Agent-based components

**No explicit multi-agent framing** — like source 18, this is a systems/networking survey, not MAS-theoretic literature. Its relevance to the thesis is the same infrastructure-substrate argument as source 18, but sharpened by its explicit LLM/multimodal-integration angle: a surveillance MAS whose agents include LLM/VLM-based reasoning components (e.g., an "incident description" or "anomaly explanation" agent) would need to be deployed across exactly the cloud-edge-terminal architecture this survey describes, and would face exactly the scalability/privacy/reliability challenges the survey flags for LLM-integrated video analytics specifically.

## Dataset(s)

Not applicable — survey paper; no original datasets used. References publication/citation statistics (Figure 1: publication and citation trends for "video analytics" and "cloud-edge-terminal" research over the last decade) to motivate the field's growth rather than to benchmark a system.

## Evaluation methodology

Meta-level survey methodology: systematic literature synthesis and taxonomy construction, contrasted explicitly against prior surveys' narrower scopes (the paper explicitly names and differentiates itself from surveys that focus only on edge computing, only on video streaming, or only on generative AI, arguing none of them jointly address video analytics across cloud-edge-terminal tiers with LLM/multimodal integration).

## Main results

Not original empirical results — contribution is the synthesized taxonomy and the explicit identification of LLM/multimodal integration as a distinguishing, under-surveyed architectural trend in CETC video analytics, alongside the standard edge/cloud/hybrid processing taxonomy. Documents strong growth in both video-analytics and cloud-edge-terminal research publication/citation volume over the past decade (Figure 1), evidencing the topic's increasing research relevance.

## Limitations

Very short for a survey (9 pages vs. source 18's 31 pages), suggesting narrower depth per subtopic despite covering a similar breadth of architectural ground — likely more of a focused/positioning survey (or workshop/short-paper format) than an exhaustive one; as with any survey, conclusions are bounded by the literature available at time of writing and are not independently re-validated by the authors.

## Claimed contributions

- A systematic analysis of CETC video-analytics fundamental architectural components (hierarchical, distributed, hybrid frameworks) and edge computing platforms/resource management.
- Coverage of edge-centric, cloud-centric, and hybrid (adaptive offloading + resource-aware scheduling) video-analytics approaches.
- A specific investigation of recent advances integrating large language models and multimodal models into video analytics, including both opportunities and system-level challenges (platform scalability, data protection, system reliability) this raises.
- Identification of future directions: explainable systems, efficient processing mechanisms, advanced video analytics.

## Verbatim quotes

1. "The explosive growth of video data has driven the development of distributed video analytics in cloud-edge-terminal collaborative (CETC) systems, enabling efficient video processing, real-time inference, and privacy-preserving analysis. Among multiple advantages, CETC systems can distribute video processing tasks and enable adaptive analytics across cloud, edge, and terminal devices, leading to breakthroughs in video surveillance, autonomous driving, and smart cities." (Abstract)

2. "Beyond conventional approaches, recent advances in large language models and multimodal integration reveal both opportunities and challenges in platform scalability, data protection, and system reliability." (Abstract)

3. "Although existing surveys have studied video analytics and edge-cloud computing, there is still a lack of systematic analysis of video analytics in CETC systems. Previous surveys either focus on specific aspects like edge computing, video streaming, or generative AI, without systematically examining the integration of video analytics across cloud, edge, and terminal tiers." (Introduction, p.1)

4. "Large-scale video data transmission to centralized servers creates significant network bottlenecks, especially evident in deployments with multiple high-resolution camera streams. Such network congestion directly impacts real-time applications, where processing delays can critically affect decision-making capabilities." (Introduction, p.1)

## Relevance to the MAS-surveillance thesis

**Highly relevant**, and complementary to source 18 rather than redundant with it: this survey's explicit focus on **LLM/multimodal-model integration into video analytics** — flagged as a recent trend with its own scalability, privacy, and reliability challenges — speaks directly to the core premise of an "agentic multi-agent surveillance system" thesis (i.e., adding LLM/VLM-based agentic reasoning on top of a video-analytics pipeline). It gives the thesis: (a) an up-to-date (2025) framing of exactly where the field currently sees LLM-integrated video analytics heading and what open problems remain, useful for positioning the thesis's novelty; (b) the same cloud-edge-terminal architectural vocabulary as source 18 (hierarchical/distributed/hybrid, edge/cloud/hybrid processing) for describing the deployment substrate of a proposed surveillance MAS; (c) explicit named risks (data protection/privacy, system reliability, platform scalability) that a thesis proposing LLM-based agents processing surveillance video should proactively address, since these are exactly the concerns a jury would likely raise about deploying LLMs on sensitive video/camera data. Recommended to cite alongside source 18 in the related-work section on distributed video-analytics infrastructure, using this paper specifically for the LLM/multimodal-integration angle.
