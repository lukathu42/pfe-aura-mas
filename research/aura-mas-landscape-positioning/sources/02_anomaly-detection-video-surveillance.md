---
source_type: thesis
credibility: 4
recency: 2024
directly_relevant: partial
---

# ANOMALY_DETECTION_IN_VIDEO_SURVEILLANCE.pdf — "Anomaly Detection in Video Surveillance"

## Metadata

- **Title:** Anomaly Detection in Video Surveillance
- **Author:** Boateng Godfred Kyeremeh
- **Year:** June 30, 2024
- **Institution / Degree type:** Abou Bekr Belkaid University of Tlemcen, Faculty of Science, Department of Computer Science, Specialty "Modèle Intelligence et Décision" — **Master's thesis** ("A thesis submitted in partial fulfilment of the requirements for the award of the Degree of Master of Science in Intelligent and Decision-Making Models")
- **Supervisor:** Dr. Berrabah Sidahmed (Lecturer, University of Tlemcen)
- **Jury:** Dr. Mourtada Benazzouz (President), Mr. Briksi-Nigassa Amine (Examiner)

## Research Problem

Manual video surveillance is labor-intensive, error-prone, and inefficient because abnormal events are extremely rare relative to normal footage — the thesis cites that "abnormal events occur only 0.01% of the time, meaning that 99.9% of surveillance time is wasted on monitoring normal activities" (p.1). The core technical challenge framed by the thesis is unsupervised video anomaly detection (VAD): building a model that can flag abnormal frames/events without needing large labeled abnormal-event datasets (which are impractical to collect), while effectively capturing both spatial (appearance) and temporal (motion) patterns of "normal" behavior so that deviations can be scored.

## Objectives

"To devise and implement an innovative anomaly detection system for surveillance videos, utilizing spatial autoencoder and convolutional LSTM architectures... to construct a robust deep learning framework capable of accurately detecting abnormal events in surveillance videos" (p.4), and to evaluate this framework across multiple public benchmark datasets to establish practical viability for real-world deployment.

## Proposed Approach (high level)

An unsupervised, reconstruction-error-based spatiotemporal autoencoder trained **only on normal video**. Input is a sequence of 10 frames (144×144, grayscale, normalized); a spatial encoder (CNN) compresses each frame individually, a temporal encoder (stacked ConvLSTM layers) models the concatenated sequence's temporal dynamics, and symmetric spatial/temporal decoders reconstruct the input sequence. At test time, frames/sequences with high reconstruction error (measured via L2/MSE) are flagged as anomalous, converted into a normalized "regularity score" per frame, and thresholded.

## System Architecture

**Single end-to-end deep learning model — a pipeline, not a multi-agent or multi-component cooperating system.** Concretely (Fig 3.2, p.27):
- Spatial Encoder: Conv(7×7,128,stride1) → AvgPool → Conv(3×3,64,stride2) → AvgPool → Conv(3×3,32,stride1) → AvgPool, applied per-frame to a 10-frame input volume.
- Temporal (ConvLSTM) Autoencoder: 3 stacked ConvLSTM layers (64→32→64 filters, 3×3) processing the concatenated spatial features across the time dimension.
- Spatial Decoder: mirrored deconvolution + nearest-neighbor upsampling back to 10×144×144×1, sigmoid output.

This is a **single trained model with no autonomous decision-making sub-units, no inter-agent communication, and no explicit reasoning/alerting layer beyond thresholding a scalar reconstruction-error signal.** It operates on one video stream at a time (single camera per inference); there is no described mechanism for cross-camera reasoning, event correlation, or multi-camera coordination.

## AI/ML Techniques Used

- Spatial autoencoder (convolutional encoder/decoder, CNN with ReLU + sigmoid activations, average pooling / nearest-neighbor upsampling)
- Convolutional LSTM (ConvLSTM) — the temporal component, replacing FC-LSTM's matrix multiplications with convolutions
- Reconstruction-error-based unsupervised anomaly scoring (regularity score derived from normalized per-sequence reconstruction cost)
- Adam optimizer (lr=1e-4, decay=1e-5, epsilon=1e-6), mini-batches of 64, up to 50 epochs with early stopping (10-epoch patience on validation loss), tanh activation (chosen over ReLU to preserve encoder/decoder symmetry)
- Literature review (Ch.2) additionally surveys, but does not implement, GANs, 3D-CNNs, two-stream models, RNNs/HMMs, and dictionary-learning/trajectory-based methods as alternative VAD approaches.

## Computer Vision Techniques

Spatiotemporal (appearance + motion) reconstruction-based anomaly detection via autoencoding; frame extraction via OpenCV; bilinear-interpolation resizing to 144×144; sliding-window (10-frame) sequence construction with stride-1/2/3 temporal data augmentation; pixel-wise reconstruction error (L2 norm) aggregated to frame-level and sequence-level anomaly scores; thresholding via ROC/AUROC and Equal Error Rate (EER) analysis. No explicit object detection, tracking, or segmentation network is used — anomalies are detected implicitly via reconstruction failure, not via detecting/classifying specific objects (e.g., the model does not explicitly detect "bicycle" — it flags the frame region because it reconstructs poorly).

## Agent-based / Multi-agent / Distributed / Coordination Components

**None.** This is explicitly a single monolithic spatiotemporal autoencoder. There is no discussion anywhere in the thesis (introduction, literature review, methodology, results, or conclusion/future-work) of multiple cooperating agents, multi-camera fusion, distributed reasoning, or autonomous decision-making units. The conclusion's "Potential Research Directions" section (6.2) explicitly lists open future directions that are absent from this work, including "Explainable AI: Developing models that not only detect anomalies but also provide explanations for their decisions" (p.48) and "Integration with IoT Devices" (p.48) — i.e., the author himself frames explainability and distributed/IoT integration as future work, not present capabilities.

## Dataset(s)

**Public benchmark datasets**, standard in the VAD literature — no custom data collection:
- **UCSD Ped1**: 6,800 train / 7,200 test frames, 238×158, grayscale, 34 train / 36 test clips.
- **UCSD Ped2**: 2,550 train / 2,010 test frames, 360×240, grayscale, 16 train / 12 test clips.
- **CUHK Avenue**: 15,328 train / 15,324 test frames, 640×360, 16 train / 21 test clips.
All are single fixed-camera, pedestrian-walkway scenes; anomalies are non-pedestrian objects (bikes, carts, skateboards) or atypical pedestrian motion (running, walking on grass).

## Evaluation Methodology and Metrics

Frame-level evaluation using **AUROC** (area under ROC curve, from TPR/FPR sweep across reconstruction-error thresholds) and **EER** (equal error rate, where TPR = 1-FPR). A sliding-window technique with sequence length 10 was used at test time; per-sequence reconstruction cost was normalized into an abnormality/regularity score per frame, visualized as a time-series plot per test video. Results were benchmarked against five prior published methods per dataset (Adam et al., HOFME/Wang et al., Mehran et al., Chong et al., ConvAE/Hasan et al., Nawarante et al., Liu et al.).

## Main Quantitative Results

| Dataset | Method | AUROC (%) | EER |
|---|---|---|---|
| Ped1 | Mehran et al. | 96.0 | – |
| Ped1 | Chong et al. | 89.9 | 12.5 |
| Ped1 | ConvAE (Hasan et al.) | 81.0 | 27.9 |
| Ped1 | **Ours (proposed)** | **84.5** | **19.5** |
| Ped1 | Adam et al. | 77.1 | 38.0 |
| Ped2 | Nawarante et al. | 91.1 | 8.9 |
| Ped2 | ConvAE (Hasan et al.) | 90.0 | 21.7 |
| Ped2 | HOFME (Wang et al.) | 87.5 | 20.0 |
| Ped2 | Chong et al. | 87.4 | 12.0 |
| Ped2 | **Ours (proposed)** | **74.9** | **27.2** |
| CUHK Avenue | Liu et al. | 85.1 | – |
| CUHK Avenue | Chong et al. | 80.3 | 20.7 |
| CUHK Avenue | ConvAE (Hasan et al.) | 70.2 | 25.1 |
| CUHK Avenue | **Ours (proposed)** | **72.4** | **29.2** |

The proposed model ranks mid-pack on Ped1 (better than ConvAE and Adam et al., worse than Mehran et al. and Chong et al.) and is the **weakest of the compared methods on both Ped2 and CUHK Avenue** — notably underperforming the ConvAE baseline it is directly built on/compared against on 2 of 3 datasets.

## Stated Limitations (from the document's own conclusion/scope sections)

- Scope section (p.4-5): "the scope of this study is limited by several factors. The model is trained exclusively on normal scenes, which may limit its ability to detect a diverse range of anomalies not present in the training data. Additionally, the model's performance is dependent on the quality and variety of the training dataset, and may be affected by changes in lighting, occlusions, and camera angles."
- Computational-resource challenges (Ch.5.6, p.45-46): consumer hardware (16GB RAM, Windows 12, Intel Evo CPU) could not handle the workload and crashed; had to move to Google Colab's T4 GPU, which itself "often reached full capacity" (12.7GB RAM / 15GB GPU memory), forcing downsampled resolution, smaller batches, and frame skipping — i.e., the method as implemented is not shown to be practical at higher resolution or in real time without significant additional compute.
- Author's own future-research list (Ch.6.1-6.3) implicitly concedes the current model lacks: attention mechanisms, multi-scale feature extraction, adversarial (GAN) training, hybrid architectures, cross-dataset generalization, real-time deployment validation, explainability, adversarial robustness, and edge/IoT integration — none of which are present in the delivered system.

## Claimed Contributions (from the document itself)

Section 6.5 (p.49) states three contributions: (1) "Novel Methodology: The study presents a novel spatiotemporal autoencoder methodology for detecting anomalies in video sequences"; (2) "Comprehensive Evaluation: The methodology was evaluated on multiple benchmark datasets, demonstrating its efficacy and robustness across different scenarios and types of anomalies"; (3) "Practical Insights: The study provides practical insights into the challenges and solutions related to computational resource constraints."

## Critical Assessment (own analysis)

- **Overclaiming relative to the numbers reported.** The conclusion and contributions section describe the approach as demonstrating "significant efficacy," "robustness," and "a significant advancement in ... video anomaly detection" (p.49), but the thesis's own comparison tables show the proposed model is outperformed by multiple prior methods on 2 of the 3 benchmark datasets (notably underperforming even its own direct architectural predecessor, ConvAE/Hasan et al., on Ped2 by 15 points AUROC and on Avenue by only +2 points despite being a more complex model). The "novel methodology" claim is also modest: spatial-AE + ConvLSTM for VAD is a well-established combination in the cited prior literature ([9], [19], [20]), so the genuine novelty appears to be more in implementation/engineering (clip-based/stride data augmentation, specific hyperparameter tuning) than in architecture.
- **No object-level or semantic anomaly explanation** — the system outputs only a scalar regularity score per frame/sequence with a heatmap-style "difference" visualization; it cannot explain *what* the anomaly is (a bike vs. a person running) or produce a human-readable alert, which the author's own future-work section acknowledges as a gap ("Explainable AI").
- **Single fixed-camera assumption throughout** — none of the three benchmark datasets, nor the proposed architecture, addresses multi-camera scenes, camera handoff, or scene-level (as opposed to frame-level) reasoning.
- **Small-scale/dated benchmarks.** Ped1/Ped2 (2010) and CUHK Avenue (2013) are long-standing but now relatively easy/saturated VAD benchmarks; the thesis's own literature review (Fig 2.5, p.20) lists newer, larger, more complex datasets (ShanghaiTech 2017, UCF-Crime 2018, XD-Violence 2020) that were not used, which limits how far the reported results generalize to more realistic, crowded, or multi-scene surveillance settings.
- **Computational fragility** is honestly reported (a strength of the writeup) but also undermines the practical-deployment claim — the author needed cloud GPU resources and still hit memory ceilings on 144×144 grayscale, 10-frame clips, which is far below the resolution/frame-rate needed for real production surveillance.

## Verbatim Quotes

1. Abstract, p.i: "This thesis introduces an innovative deep learning method aimed at enhancing video anomaly detection through the use of a spatial autoencoder combined with convolutional Long Short-Term Memory (ConvLSTM) networks."
2. p.1: "abnormal events occur only 0.01% of the time, meaning that 99.9% of surveillance time is wasted on monitoring normal activities."
3. p.4-5 (Scope and Limitations): "The model is trained exclusively on normal scenes, which may limit its ability to detect a diverse range of anomalies not present in the training data."
4. p.44-45, Tables 3-5: Ped1 AUROC 84.5%/EER 19.5; Ped2 AUROC 74.9%/EER 27.2; CUHK Avenue AUROC 72.4%/EER 29.2, each compared against 4-5 prior published methods.
5. p.48 (Potential Research Directions): "Explainable AI: Developing models that not only detect anomalies but also provide explanations for their decisions is essential for gaining user trust and improving the interpretability of the models."

## Relevance to "Agentic Multi-Agent Surveillance System" Direction

Partial. The thesis is squarely within the **anomaly detection** pillar of a future agentic-MAS surveillance system — it demonstrates a working (if benchmark-mid-tier) unsupervised, reconstruction-based anomaly scorer that could plausibly serve as one perception/detection component feeding into a larger reasoning layer. However, it has **zero multi-agent, multi-camera, coordination, or reasoning-agent content**: it is a single deep model producing a single numeric score per video, with no explanation generation, no alerting logic beyond thresholding, and no LLM-based or symbolic reasoning layer. Its explicit "future work" section (explainability, IoT/edge integration, cross-dataset generalization) maps directly onto gaps a genuinely agentic multi-camera surveillance thesis would need to fill — making it useful primarily as a baseline/component-level reference and as evidence that even the most recent (2024) local prior work in this department has not yet touched agentic or multi-agent architectures.
