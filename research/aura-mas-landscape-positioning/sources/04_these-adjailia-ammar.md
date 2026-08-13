---
source_type: thesis (PhD / Doctorat en Sciences)
credibility: 4
recency: 2019
directly_relevant: partial
---

# Analyse et Reconnaissance des Activités Humaines à partir des Séquences Vidéo
("Analysis and Recognition of Human Activities from Video Sequences")

## Metadata
- **Title**: Analyse et Reconnaissance des Activités Humaines à partir des Séquences Vidéo
- **Author**: LADJAILIA Ammar
- **Year**: 2019
- **Institution / Degree type**: Université Badji Mokhtar – Annaba, Algeria. Faculté des Sciences de l'Ingéniorat, Département Informatique. Doctorat en Sciences (PhD), Option: Informatique. 174 pages (full doctoral thesis, not a PFE).
- **Supervisor(s)**: Directeur de thèse: Imed BOUCHRIKA (Pr., Université de Souk-Ahras). Co-Directeur de thèse: Farida Hayet MEROUANI (Pr., Université de Annaba). Jury: Président Labiba SOUICI-MESLATI (Pr., Annaba); Examinateurs Halima BAHI (Pr., Annaba), Abdelhani BOUKROUCHE (Pr., Guelma), Amara BEKHOUCH (MCA, Souk-Ahras).

## Research problem
Automated recognition and analysis of human activities from video sequences, in order to determine which human actions occur in a scene. The thesis frames this as particularly difficult because of huge variation in appearance and motion when actions are performed, plus acquisition-related challenges (viewpoint changes, background clutter, occlusion) and the sheer volume of video data requiring analysis.

## Objectives
- Propose a motion-only descriptor for human action recognition, derived purely from optical flow (deliberately avoiding reliance on appearance/silhouette or background subtraction).
- Evaluate this descriptor with both classical machine-learning classifiers (KNN, decision tree, SVM) and deep learning (autoencoder-based).
- Study the descriptor's robustness under conditions realistic for surveillance cameras: frame loss ("frame dropping") and reduced image resolution.
- Extend the elementary-action recognizer toward decomposing longer, more complex/realistic activities into sequences of elementary actions.

## Proposed approach (high-level)
Optical flow (Horn–Schunck method) is computed between consecutive frame triplets of a 15-frame elementary-action clip. Each pixel's flow vector (angle + magnitude) is discretized into one of 8 orientation sectors and combined across the triplet into a per-pixel descriptor code (base-9 → base-10). These codes are aggregated into local histograms (per-triplet, extended with mean/STD statistics — 951 features) and global histograms (spatial "bars," dividing the frame vertically/horizontally to capture where motion occurs — up to ~1035 features depending on bar count). The concatenated local+global feature vector is optionally reduced via an ASFFS (Adaptive Sequential Forward Floating Search) feature-selection procedure, then classified with KNN / Decision Tree / SVM, or alternatively fed (as a "Binary Motion Image" 2D representation) into a Deep Learning Autoencoder (and, in an extension using GMM-based silhouette extraction, a "History of Binary Motion Image" + Sparse Stacked Autoencoder variant). A separate mechanism detects elementary actions inside longer video clips by sliding a window and matching against a similarity-thresholded dictionary of Weizmann-derived elementary-action signatures.

## System architecture
Single sequential pipeline — **not multi-agent, not multi-camera**:

```
Video (single, static camera) → Optical flow estimation (Horn–Schunck)
  → Local motion-feature histograms + Global (spatial) motion-feature histograms
  → [optional] ASFFS feature selection
  → Classification: KNN / Decision Tree / SVM   — OR —   Deep Learning Autoencoder (BMI/HBMI input)
  → Action label
```
Extension for longer/complex scenes: sliding window over the video → per-window motion descriptor → similarity matching (Euclidean distance, threshold) against an elementary-action dictionary → sequence of recognized elementary actions (Precision/Recall/F1 evaluated).

The document explicitly scopes the method to a single person in front of a largely static camera; camera-motion robustness and multi-person/crowd handling are named as unsolved, left to future work (see Limitations below). There is no agent abstraction anywhere in the thesis — no autonomous cooperating units, no distributed/coordinated decision-making, no message-passing between components.

## AI/ML techniques used
KNN (k=1,3,5), Decision Tree (entropy-based, with built-in feature selection), multi-class SVM, Autoencoder (unsupervised deep learning: encoder → 3 shrinking hidden layers → Softmax classification output), Sparse Stacked Autoencoder (SSAE, used in the HBMI extension), Gaussian Mixture Model (GMM, for silhouette/background modeling in the HBMI extension), ASFFS feature-selection algorithm.

## Computer vision techniques
Optical flow estimation (Horn–Schunck differential method) as the sole low-level motion cue; a custom motion descriptor built from flow orientation/magnitude histograms (local + global/spatial); GMM-based background subtraction for silhouette extraction (only in the "HBMI" deep-learning extension); Binary Motion Image / History of Binary Motion Image 2D representations. No object-detection network, no tracking algorithm, no semantic segmentation, and no implemented anomaly-detection module (anomaly detection in crowds is discussed only as a proposed future perspective, citing others' work).

## Agent-based / multi-agent / distributed / coordination components
**None implemented.** The thesis explicitly frames multi-person/crowd activity recognition and multi-camera scenarios as open future work, not as delivered capabilities — see Perspectives quote below (citing OpenPose crowd-pose-estimation work by Cao et al. as a possible future enabler, not something built here).

## Dataset(s) used
All public benchmarks, re-annotated/relabeled by the author for the thesis's specific elementary-action taxonomy:
- **Weizmann** (public): 90 original videos, re-annotated into 241 sequences covering 19 elementary actions (15-frame clips).
- **UCF101** (public): subset of 72 videos across 23 classes, filtered to exclude camera motion.
- **KTH** (public): used together with UCF101 for the complex-activity decomposition experiment — 1400 manually annotated sequences.
- **Ixmas** (public): mentioned as used in the HBMI/SSAE journal-article extension alongside Weizmann and KTH.
No custom-collected video dataset; all sources are established public action-recognition benchmarks, though the fine-grained elementary-action annotation on top of them is original work.

## Evaluation methodology and metrics
Correct Classification Rate (CCR) via KNN with Leave-One-Out cross-validation; Cumulative Match Score (CMS) / Rank-N accuracy curves; comparative CCR across classifier types (KNN, Decision Tree, SVM, Deep Autoencoder) and across spatial "bar" granularities (5/10/20); verification analysis via ROC (False Accept Rate vs. False Reject Rate), Equal Error Rate, and Daugman's decidability index; confusion matrices; for the complex-activity decomposition task: Precision, Recall, F1-score against manually annotated ground truth; robustness studies: CCR vs. number of dropped frames, and CCR vs. reduced image resolution (100% down to 50%, explicitly motivated by real surveillance-camera image quality); a feature-contribution study quantifying local vs. global-temporal vs. global-spatial feature share and their individual CCR.

## Main quantitative results
- **Weizmann (19 elementary actions)**: CCR = **98.76%** at Rank-1 (KNN, k=3, with ASFFS feature selection, 5 spatial bars); 100% at Rank-2. Without feature selection, KNN peaks around 85%. SVM: 89.67–90.08%. Decision Tree: 82.64–94.21%.
- **UCF101 (23 classes, 72 videos)**: CCR = **70.00%** — the thesis's own comparison table places this above simple Bag-of-Words (44.5%) but clearly below then-recent deep methods (Two-stream SVM fusion 88.0%, TS-LSTM+Temporal-Inception 94.1%, Temporal Segment Networks 94.2%).
- **Deep learning (Autoencoder) on Weizmann**: 87.60% (19 classes), 97.11% (10 classes); HBMI + SSAE extension: 97.66% (10 classes).
- **Complex-activity decomposition** (UCF101+KTH, 1400 annotated sequences): TP=682, TN=184, FP=356, FN=178 → Precision=65.70%, Recall=79.30%, F1=71.87%.
- **Verification/similarity**: Equal Error Rate = 1.89%.
- **Robustness — frame dropping**: CCR (KNN, k=1) collapses from 97.93% (0 frames dropped) to 59.72% with just 2 of 15 frames dropped, and continues to fall (~50% by 6–7 dropped frames).
- **Robustness — resolution**: much less severe degradation, especially with feature selection (97.93% at full resolution → 77.27% at 50% resolution with feature selection, vs. 85.12% → 71.07% without).
- **Feature contribution**: global-temporal features dominate (90.58% of the selected-feature distribution, 93.39% CCR alone); local features contribute a marginal 0.08% of the distribution but still 88.42% CCR alone; global-spatial features: 9.34% distribution, 65.29% CCR alone.

## Stated limitations (from the document's own conclusion/perspectives)
- Performance is highly sensitive to missing/dropped frames because "la classification est purement basée sur la détection du mouvement à partir de la nature consécutive des trames" — the recognition mechanism directly depends on consecutive frames.
- The method's main structural advantage (no background subtraction needed) "n'est pas toujours le cas, en particulier quand la caméra est en mouvement" — it does not robustly handle camera motion.
- Optical flow estimation and ASFFS feature selection are computationally expensive and scale poorly (complexity depends on dataset size), which the author flags as a barrier to real-time applications.
- The number of orientation sectors (fixed at 8) was never varied/optimized.
- Complex-activity decomposition results are called only "raisonnables" (reasonable), with explicit room for improvement.
- Deep-learning experiments used only 2D feature representations (BMI/HBMI images), not 3D or hybrid architectures.
- The system recognizes actions for a single person at a time; multi-person/crowd recognition and anomaly detection are explicitly named as unaddressed, proposed only as future perspectives.

## Claimed contributions
- A purely motion-based (optical-flow-derived) descriptor combining local and global kinematic histograms, requiring no background-subtraction step for the main method.
- Empirical validation on two public benchmarks (Weizmann 98.76%, UCF101 70%), reported by the author as exceeding several previously published methods on Weizmann.
- A comparative study spanning classical classifiers (KNN, Decision Tree, SVM) and deep learning (Autoencoder / SSAE).
- A novel mechanism for decomposing longer, more realistic video scenes into sequences of elementary actions.
- A dedicated robustness analysis under simulated surveillance-camera degradations (frame loss, low resolution), explicitly tied to real surveillance-camera quality.
- Two referenced published articles underlying the deep-learning contributions (BMI+Autoencoder, and HBMI+SSAE).

## Critical assessment (own analysis)
- This is a methodologically solid, empirically thorough PhD thesis — public-benchmark evaluation, multiple classifiers compared, explicit robustness/ablation studies, and prior publications backing the deep-learning chapters. It is considerably more rigorous than the Sahla/Mahla Master's PFE reviewed alongside it.
- However, relative to an "agentic multi-agent surveillance" direction, it is a classical (pre-modern-deep-learning-era for this problem), single-camera, single-person action-recognition pipeline: optical flow + handcrafted histograms + shallow classifiers/autoencoder. There is no agent abstraction, no reasoning/LLM component, no alerting/explainability layer, and no multi-camera fusion anywhere.
- The author is candid and precise about scope: multi-person/crowd handling and anomaly detection are explicitly named as *future perspectives*, not contributions — this is a clean, honest positioning that a new thesis can build on without duplicating.
- Mild overclaiming risk: the abstract states results "confirmed the potential of the proposed approach" without foregrounding that on UCF101 (70%) the method trails most contemporary competing methods by a wide margin (up to 24 points behind Temporal Segment Networks) — the comparison table itself is transparent about this, but the abstract framing is more upbeat than the numbers fully support.
- The frame-drop fragility (CCR collapsing from ~98% to ~60% after losing just 2 of 15 frames) is a serious practical weakness for any real deployment on lossy/degraded surveillance video streams, though the author does report and discuss it candidly rather than hiding it.

## Verbatim quotes
1. Abstract, p. iv: "In this thesis, we propose a motion descriptor based on optical flux estimation for human action recognition, taking into account only the characteristics derived from motion. ... Experimental results from the Weizmann and UCF101 datasets confirmed the potential of the proposed approach with classification rates of 98.76% and 70% respectively."
2. p. 118: "En ce qui concerne la faible résolution des images, elle reflète la vraie qualité de la vidéo enregistrée par des caméras de surveillance intégrées dans des lieux publics et dans certains lieux sensibles." ("As for the low resolution of images, it reflects the true quality of video recorded by surveillance cameras integrated in public places and certain sensitive locations.")
3. p. 119: "En effet, la classification est purement basée sur la détection du mouvement à partir de la nature consécutive des trames où le saut ou l'absence des trames peut masquer ses caractéristiques vitales." ("Classification is purely based on motion detection derived from the consecutive nature of frames, where skipping or missing frames can mask its vital characteristics.") — accompanying Table 6.1 shows CCR dropping from 97.93% (0 dropped frames) to 59.72% (2 dropped frames), k=1.
4. p. 126 (Perspectives 7.2.2): "il existe des études qui montrent la possibilité de la détection des poses d'une foule des personnes [32, 33], cela nous donne une plus grande chance de la reconnaissance des activités de plusieurs personnes en même temps." ("there exist studies showing the possibility of pose detection for a crowd of people, giving us a greater chance of recognizing the activities of several people at the same time.") — confirming multi-person recognition is future work, not a delivered capability.
5. p. 126: "Nous proposons notre descripteur ... comme une solution pour la détection des activités anormales d'une foule dans une séquence vidéo." ("We propose our descriptor ... as a solution for detecting abnormal crowd activities in a video sequence.") — anomaly detection is proposed only as a future perspective, not implemented or evaluated in the thesis.

## Relevance to an "agentic multi-agent surveillance system" research direction
Partial/indirect. This is a rigorous, single-camera, single-person, non-agentic human-activity-recognition pipeline (optical flow + classical ML / shallow autoencoder) validated on public benchmarks, which explicitly and candidly scopes out multi-person/crowd handling, anomaly detection, and camera-motion robustness as unsolved future work rather than claiming them as contributions. It confirms that even fairly recent (2019) local doctoral work in this exact application space — one that explicitly discusses surveillance-camera image quality and frame-loss robustness — stopped at a single-modality, single-agent perception level with no coordination, reasoning, or explainability layer. This strengthens the case that a genuinely multi-agent, autonomous-reasoning, multi-camera-coordinating system would be a non-duplicative extension of the local research landscape. At the same time, its robustness findings (severe frame-drop sensitivity, motion-descriptor design trade-offs) are directly useful lessons for designing a perception agent within a future multi-agent surveillance architecture.
