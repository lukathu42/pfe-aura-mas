---
source_type: paper
credibility: 5
recency: 2020
directly_relevant: partial
---

# Luiten et al. — "HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking"

## Bibliographic metadata

- **Title:** HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking
- **Author(s):** Jonathon Luiten, Aljoša Ošep, Patrick Dendorfer, Philip Torr, Andreas Geiger, Laura Leal-Taixé, Bastian Leibe
- **Affiliations:** RWTH Aachen University; Technical University Munich; University of Oxford; Max Planck Institute for Intelligent Systems / University of Tübingen
- **Year:** 2020 (v2, 29 Sep 2020)
- **Venue:** International Journal of Computer Vision (IJCV) — accepted for publication, 19 August 2020 (pre-print version read; also arXiv:2009.07736)
- **Length:** 28 pages
- **Code:** github.com/JonathonLuiten/HOTA-metrics

## Research problem

Multi-Object Tracking (MOT) — detecting and identity-associating multiple objects across video frames — has been notoriously difficult to *evaluate* fairly. The two previously dominant metrics, MOTA and IDF1, each overemphasize one aspect of tracking quality at the expense of the other: MOTA overemphasizes detection accuracy while underweighting association/identity-assignment errors; IDF1 overemphasizes association accuracy while underweighting detection errors. Neither decomposes cleanly into interpretable sub-components, and neither explicitly measures localization (bounding-box) accuracy at all. This makes it hard to diagnose *why* a tracker under- or over-performs, or to compare trackers fairly across different error profiles.

## Proposed approach

**HOTA (Higher Order Tracking Accuracy)**: a single unified metric that explicitly balances detection accuracy, association accuracy, and localization accuracy by construction, and decomposes into a family of interpretable sub-metrics that separately quantify each of five basic error types. HOTA is computed as HOTA = sqrt(DetA × AssA), the geometric mean of a **Detection Accuracy (DetA)** score and an **Association Accuracy (AssA)** score, each itself an IoU-based (Jaccard-index-style) score computed over correctly-matched detections at a given localization threshold α, then integrated/averaged over a range of α thresholds (analogous to how mAP integrates over IoU thresholds in object detection) to also capture localization quality.

## Architecture/method

Not a system/model paper — a **measurement-theory / evaluation-metric paper**. Method: (1) define ground-truth-to-prediction matching per frame via bipartite (Hungarian) matching at a given localization IoU threshold α; (2) decompose the standard trajectory-matching confusion counts into True Positives (TP), False Negatives (FN), False Positives (FP) for detection, and separately into True Positive Associations (TPA), False Negative Associations (FNA), False Positive Associations (FPA) for the *association* of each TP across the full ground-truth/predicted trajectories it belongs to; (3) define DetA = TP / (TP+FN+FP) and AssA = (1/TP) Σ_{c∈TP} TPA(c) / (TPA(c)+FNA(c)+FPA(c)); (4) HOTA_α = sqrt(DetA_α × AssA_α); (5) integrate HOTA_α over α∈(0,1) to obtain the final HOTA score. Sub-metrics (DetRe, DetPr, AssRe, AssPr, LocA, plus classification variants) allow decomposing *why* a tracker scores well or poorly — e.g., distinguishing a tracker with many short broken tracks (association failure) from one that misses/hallucinates objects outright (detection failure).

## AI/ML techniques

None — this is a pure evaluation-metric/measurement paper, not a learned model. It is applied to evaluate MOT algorithms (which may themselves use deep learning, e.g., detection+ReID-based trackers) but does not itself involve model training.

## Agent-based components

**None.** No agents, no multi-agent coordination, no LLMs. Included in the deep-dive set because MOT evaluation methodology is directly relevant to any surveillance system component that performs object tracking (e.g., a "tracking agent" in a MAS surveillance architecture) and the thesis will need a principled, current evaluation metric for such a component.

## Dataset(s)

Evaluated on the **MOTChallenge** benchmark (standard pedestrian MOT benchmark suite: MOT16/MOT17/MOT20-style sequences), used as the testbed to demonstrate HOTA captures tracking-performance aspects MOTA/IDF1 miss, and to show HOTA scores align better with human visual judgment of tracking quality (via a human-perception alignment study).

## Evaluation methodology

Analytical decomposition arguments (illustrated with constructed toy examples, e.g., Fig. 1's three synthetic trackers A/B/C showing MOTA and IDF1 disagreeing about which tracker is "better" depending on whether they weight detection or association more), applied to real tracker outputs on MOTChallenge, plus a **human-evaluation alignment study** comparing metric rankings of trackers against human visual assessments of tracking quality — used to argue HOTA correlates better with human judgment than MOTA or IDF1.

## Main results

- HOTA is shown to decompose cleanly into detection (DetA), association (AssA), and localization (LocA) components, each independently interpretable, unlike MOTA (detection-dominated) and IDF1 (association-dominated).
- HOTA scores are shown to align better with human visual evaluation of tracking performance than MOTA or IDF1 in the paper's human-study comparison.
- The paper demonstrates concrete cases (constructed and from real trackers) where MOTA and IDF1 disagree about tracker ranking, while HOTA's balanced decomposition resolves the ambiguity by making explicit which axis (detection vs. association) drives the difference.
- HOTA has since become a standard, widely-adopted MOT evaluation metric in the field (reflected by its adoption as a primary leaderboard metric on MOTChallenge and other tracking benchmarks in subsequent years, including being reported as a headline metric by later trackers such as ByteTrack — see source 16).

## Limitations

Self-scoped as an evaluation-methodology contribution rather than a tracking-algorithm contribution — the paper does not propose a new tracker. Limitations are primarily about the generality of the metric: it is designed for the standard MOT task formulation (bounding-box-level, single-camera, closed-set object tracking with ground-truth trajectory annotations) and its extension to more complex settings (e.g., cross-camera re-identification, open-set/novel-object tracking, or panoptic/segmentation-based tracking) is not the focus of this paper (subsequent work has extended HOTA-style metrics to such settings).

## Claimed contributions

- A novel MOT evaluation metric, HOTA, that explicitly and jointly balances detection, association, and localization accuracy in a single, principled, mathematically well-motivated score.
- A decomposition of HOTA into interpretable sub-metrics enabling fine-grained diagnostic analysis of *why* a tracker succeeds or fails (detection-limited vs. association-limited vs. localization-limited).
- Empirical demonstration, via the MOTChallenge benchmark and a human-perception alignment study, that HOTA captures important aspects of tracking performance not previously captured by MOTA or IDF1, and aligns better with human visual judgment.

## Verbatim quotes

1. "Multi-Object Tracking (MOT) has been notoriously difficult to evaluate. Previous metrics overemphasize the importance of either detection or association. To address this, we present a novel MOT evaluation metric, HOTA (Higher Order Tracking Accuracy), which explicitly balances the effect of performing accurate detection, association and localization into a single unified metric for comparing trackers." (Abstract)

2. "HOTA decomposes into a family of sub-metrics which are able to evaluate each of five basic error types separately, which enables clear analysis of tracking performance." (Abstract)

3. "We evaluate the effectiveness of HOTA on the MOTChallenge benchmark, and show that it is able to capture important aspects of MOT performance not previously taken into account by established metrics. Furthermore, we show HOTA scores better align with human visual evaluation of tracking performance." (Abstract)

4. "As can be seen in Fig. 1, currently used metrics MOTA and IDF1 overemphasize detection and association respectively. HOTA explicitly measures both types of errors and combines these in a balanced way. HOTA also incorporates measuring the localisation accuracy of tracking results which isn't present in either MOTA or IDF1." (Introduction, p.1)

## Relevance to the MAS-surveillance thesis

**Partially relevant, but practically important**: HOTA is not a MAS or surveillance-architecture paper — it contributes no agent coordination content — but it is directly relevant on the *perception/evaluation* side of any video surveillance system: if the thesis's proposed MAS includes a tracking agent (which is highly likely, given "surveillance" typically implies tracking people/objects/vehicles across frames or cameras), HOTA is the current standard, methodologically rigorous metric the thesis should use to report and justify that agent's tracking performance, rather than the older, individually-biased MOTA or IDF1 metrics. It should be cited in the thesis's evaluation-methodology section as the justification for metric choice when assessing any tracking component, and its decomposition (DetA/AssA/LocA) gives the thesis a principled way to diagnose whether tracking failures in the proposed system stem from the detector, the association/re-identification logic, or localization precision — a diagnostic capability valuable when comparing single-agent vs. multi-agent tracking coordination strategies.
