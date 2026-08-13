---
source_type: paper
credibility: 5
recency: 2022
directly_relevant: partial
---

# Zhang et al. — "ByteTrack: Multi-Object Tracking by Associating Every Detection Box"

## Bibliographic metadata

- **Title:** ByteTrack: Multi-Object Tracking by Associating Every Detection Box
- **Author(s):** Yifu Zhang, Peize Sun, Yi Jiang, Dongdong Yu, Fucheng Weng, Zehuan Yuan, Ping Luo, Wenyu Liu, Xinggang Wang
- **Affiliations:** Huazhong University of Science and Technology; The University of Hong Kong; ByteDance Inc.
- **Year:** 2022 (v3, 7 Apr 2022)
- **Venue:** ECCV 2022 (European Conference on Computer Vision) — pre-print version read (arXiv:2110.06864v3)
- **Length:** 14 pages
- **Code:** github.com/ifzhang/ByteTrack

## Research problem

Standard tracking-by-detection MOT pipelines associate detection boxes into tracklets using a confidence-score threshold: only high-scoring detections are kept and matched; detections below the threshold (often occluded or partially-visible objects) are simply discarded. This causes non-negligible true-object misses and fragmented trajectories, because low-confidence boxes frequently correspond to real but partially-occluded objects rather than background/noise, and discarding them breaks tracks unnecessarily.

## Proposed approach

**BYTE**: a simple, general, near-parameter-free association method that tracks by associating **almost every detection box, including low-confidence ones**, rather than only high-scoring detections. The core idea: first match high-score detection boxes to existing tracklets (as in standard approaches); then, in a *second* association step, match the remaining unmatched tracklets against the **low-score** detection boxes using similarity with tracklets (motion/IoU-based, not appearance-based, to remain robust) to recover genuine occluded objects while filtering out true background/noise detections (which, lacking any spatial similarity to any existing tracklet, are naturally rejected in this second stage). **ByteTrack** is the resulting complete tracker (BYTE association + a Kalman-filter-based motion model + a strong detector, YOLOX) built to demonstrate BYTE's effectiveness as a plug-in improvement applicable to (nearly) any detector.

## Architecture/method

Two-stage association per frame:
1. **First association:** match tracklets (predicted via Kalman filter motion model) against high-confidence detection boxes (above a first threshold) using IoU or a combination of IoU + optional appearance similarity, via Hungarian matching.
2. **Second association:** for tracklets that remain unmatched after stage 1 (i.e., their expected object wasn't found among high-confidence detections — likely due to occlusion or motion blur lowering detector confidence), attempt a second Hungarian match against the **low-confidence** detection boxes (below the first threshold but above a lower floor) using IoU similarity only (appearance similarity is deliberately avoided at this stage since low-score boxes often have unreliable appearance features due to occlusion/blur).
3. Unmatched high-score detections initialize new tracklets; unmatched tracklets are kept for a short buffer period (in case the object reappears) before being terminated.
Applied generically on top of YOLOX as the detector, but the paper explicitly demonstrates BYTE's benefit is detector-agnostic by testing it plugged into 9 different existing SOTA trackers.

## AI/ML techniques

YOLOX (anchor-free CNN object detector) for detection; Kalman filtering for motion-based state prediction/tracklet propagation; Hungarian algorithm for optimal bipartite assignment/matching; IoU-based (not deep-feature/ReID-based) similarity for the low-score association stage specifically (to avoid unreliable appearance embeddings under occlusion). No transformer-based tracking, no LLMs, no reinforcement learning.

## Agent-based components

**None.** ByteTrack is a single-pipeline, non-agentic computer vision tracker — no multi-agent coordination, negotiation, or distributed decision-making is involved. Included in the deep-dive set purely as a state-of-the-art, widely-adopted MOT technique directly relevant to the perception layer any surveillance MAS's tracking agent(s) would likely need to implement or build upon.

## Dataset(s)

MOT17, MOT20 (standard pedestrian MOT benchmarks), HiEve (crowd/complex-event tracking benchmark), and BDD100K (autonomous-driving multi-class multi-object tracking benchmark) — demonstrating generality across pedestrian-only and multi-class (vehicles, etc.) tracking settings.

## Evaluation methodology

Standard MOT benchmark protocol: MOTA, IDF1, and HOTA (see source 15) as headline metrics, plus FPS (frames-per-second) for runtime/speed comparison, reported on each benchmark's official test set leaderboard. Ablation studies isolate BYTE's contribution by plugging it into 9 different existing SOTA trackers and measuring IDF1 improvement, holding the rest of each tracker's pipeline fixed.

## Main results

- ByteTrack achieves **80.3 MOTA, 77.3 IDF1, 63.1 HOTA** on the MOT17 test set at **30 FPS** on a single V100 GPU — reported as state-of-the-art at time of publication, outperforming all previous trackers on the MOTA-IDF1-FPS trade-off (Figure 1 shows ByteTrack dominating the accuracy/speed Pareto frontier against ReMOT, TransMOT, CorrTracker, CSTrack, TransTrack, FairMOT, SOTMOT, TraDes, QuasiDense, Chained-Tracker, CenterTrack, Tube_TK, TransCenter).
- When BYTE (the association method alone) is applied to 9 different existing SOTA trackers as a drop-in replacement for their original association logic, it achieves consistent IDF1 improvements ranging from **1 to 10 points**, demonstrating BYTE's contribution is general/detector-agnostic rather than tied to YOLOX or ByteTrack's specific pipeline.
- Also achieves state-of-the-art performance on MOT20, HiEve, and BDD100K tracking benchmarks.

## Limitations

Not extensively self-critiqued in the reviewed pages, but implicit limitations typical of this tracking paradigm: relies on a strong underlying detector (YOLOX) — tracking quality is bounded by detection quality; motion-based (Kalman filter) association assumes relatively smooth/predictable motion and may degrade under highly erratic motion or very long occlusions; the low-score second-stage association uses IoU only (no appearance/ReID cues), which is a deliberate robustness trade-off but means BYTE cannot recover identity through long-term occlusion or across non-overlapping camera views (unlike appearance/ReID-based cross-camera trackers) — i.e., ByteTrack is a single-camera, short-term-occlusion-robust tracker, not a cross-camera re-identification system.

## Claimed contributions

- BYTE: a simple, effective, and (near) parameter-free two-stage detection-box association method that recovers true objects from low-confidence detections (typically occluded/blurred objects) while still filtering background, rather than discarding all low-confidence boxes as prior methods do.
- Demonstration that BYTE is a general, detector- and tracker-agnostic improvement, validated by plugging it into 9 different SOTA trackers with consistent IDF1 gains.
- ByteTrack: a complete, simple, and strong tracker (YOLOX + BYTE + Kalman filter) achieving new state-of-the-art results on MOT17, MOT20, HiEve, and BDD100K at real-time speed (30 FPS on a single V100 GPU).

## Verbatim quotes

1. "Multi-object tracking (MOT) aims at estimating bounding boxes and identities of objects in videos. Most methods obtain identities by associating detection boxes whose scores are higher than a threshold. The objects with low detection scores, e.g. occluded objects, are simply thrown away, which brings non-negligible true object missing and fragmented trajectories." (Abstract)

2. "To solve this problem, we present a simple, effective and generic association method, tracking by associating almost every detection box instead of only the high score ones. For the low score detection boxes, we utilize their similarities with tracklets to recover true objects and filter out the background detections." (Abstract)

3. "When applied to 9 different state-of-the-art trackers, our method achieves consistent improvement on IDF1 score ranging from 1 to 10 points." (Abstract)

4. "We achieve 80.3 MOTA, 77.3 IDF1 and 63.1 HOTA on the test set of MOT17 with 30 FPS running speed on a single V100 GPU. ByteTrack also achieves state-of-the-art performance on MOT20, HiEve and BDD100K tracking benchmarks." (Abstract)

## Relevance to the MAS-surveillance thesis

**Partially relevant** — ByteTrack is a pure computer-vision tracking pipeline with zero agentic or multi-agent content, so it is not architecture literature for the "agentic multi-agent" part of the thesis. Its relevance is as a **strong, current, real-time-capable perception backbone**: if the thesis's proposed surveillance MAS includes a tracking agent (or a detection-plus-tracking agent), ByteTrack (or its association principle) is a directly usable, well-validated, real-time-suitable technique that the thesis could adopt, cite as its tracking baseline, or explicitly build an "agentification" layer around (i.e., wrapping a ByteTrack-style tracker as one specialized agent within the larger MAS, analogous to how VOK was wrapped by the Proxy agent in Monitorix — source 11). It is also methodologically useful as the source of the HOTA/MOTA/IDF1 reporting convention the thesis should follow when presenting any tracking results, and its real-time performance figures (30 FPS on a single V100) provide a concrete throughput benchmark relevant to discussing the real-time feasibility of a multi-agent surveillance pipeline.
