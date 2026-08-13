---
source_type: thesis (PFE / Master's mémoire)
credibility: 3
recency: 2022
directly_relevant: no
---

# Détection d'objet en temps réel en utilisant une approche basée sur l'apprentissage profond
("Real-time object detection using a deep-learning-based approach")

> Note on filename: the source PDF filename attributes this work to "Sahla Mahla," but that is the watermark of an Algerian student document-sharing platform ("SAHLA MAHLA — المصدر الاول للطالب الجزائري", visible on every page). The actual authors are named on the cover page.

## Metadata
- **Title**: Détection d'objet en temps réel en utilisant une approche basée sur l'apprentissage profond
- **Author(s)**: NACHEF Abd el karim, BOUMEDIENE Noureddine
- **Year**: 2021–2022 (publicly defended 27/06/2022)
- **Institution / Degree type**: Université Ibn Khaldoun – Tiaret, Algeria. Faculté des Mathématiques et de l'Informatique, Département d'Informatique. MASTER, Spécialité: Génie Logiciel (Software Engineering). This is a Master's PFE (mémoire), 77 pages.
- **Supervisor**: Mr SAFA Khaled ("Encadrant"). Jury: Mr MOSTEFAOUI Kadda (Président), Mr BEKKI Khadir (Examinateur).

## Research problem
The authors ask, in their own words, "what are the most suitable and efficient Deep Learning models for real-time object recognition?" The work is framed as a generic computer-vision engineering problem (object detection performance/speed trade-offs), not as a surveillance-system design problem, even though the abstract lists video surveillance as one of several motivating application domains for object detection generally.

## Objectives
1. Review existing deep-learning object-detection model families (two-stage: R-CNN, SPP-net, Fast R-CNN, Faster R-CNN, Mask R-CNN; one-stage: YOLO v1–v5, SSD, RetinaNet) and compare them for real-time suitability.
2. Select and implement the best candidate model.
3. Train and evaluate it on a self-collected two-class dataset (person, cat) to validate real-time object detection/recognition.

## Proposed approach (high-level)
Transfer learning on YOLOv3 (Darknet-53 backbone, TensorFlow/Keras implementation): the first 249 layers (feature extraction) are frozen, and only the last 3 layers (classification + localization) are fine-tuned for the two custom classes. Images of people and a cat were collected "from various perspectives," manually labeled (LabelImg-style tool producing XML/CSV annotations with bounding boxes), and split 80% train / 10% test / 10% validation.

## System architecture
Single-module, single-pipeline object detector — **not** multi-agent, **not** multi-camera, no cooperating decision-making units:

```
Webcam/video frame (480×640×3)
  → Darknet-53 backbone (frozen, 249 layers, feature extraction)
  → 3 detection heads at 13×13 / 26×26 / 52×52 (large/medium/small objects)
  → objectness score + bbox offsets + class probabilities
  → post-processing (thresholding)
  → bounding boxes with class label
```
It is a single trained CNN classifier/detector run frame-by-frame on a webcam feed. No tracking across frames, no video-level temporal reasoning, no multi-camera fusion, no alerting/reasoning layer.

## AI/ML techniques used
YOLOv3 (Darknet-53 backbone) via TensorFlow Object Detection / Keras; transfer learning (layer freezing + fine-tuning of the last 3 layers); trained with CUDA/cuDNN GPU acceleration.

## Computer vision techniques
Only object detection (single-shot bounding-box regression + classification, YOLOv3). No tracking, no segmentation, no anomaly detection, no re-identification.

## Agent-based / multi-agent / distributed / coordination components
**None.** This is a single-script, single-model, single-camera system with no autonomous cooperating agents, no distributed processing, and no coordination logic of any kind.

## Dataset(s) used
Custom, self-collected dataset of person and cat images/photos taken "from various perspectives" (no exact image count is given in the text reviewed). Not a public benchmark. Chapter 2's literature-review comparisons of other researchers' models reference public benchmarks (Pascal VOC, COCO) but the authors' own trained YOLOv3 model is evaluated only on their private dataset.

## Evaluation methodology and metrics
True/False Positive/Negative case definitions, Precision, Recall, Average Precision (AP, area under the Precision–Recall curve per class), and Mean Average Precision (mAP) across the two classes.

## Main quantitative results
- **cat AP = 76.16%**
- **person AP = 72.82%**
- **mAP = 74.49%**
- Qualitative webcam test screenshots show correct detections, but the screenshot in Figure 53 explicitly displays **"FPS: 1"** during live inference — i.e., the deployed system ran at ~1 frame per second, not in real time, despite "real-time" being the thesis's central claim/title.

## Stated limitations (from the document's own conclusion)
- "we were partially successful, but not totally, especially given the difficulty of training yolo network while utilizing a relatively weak device" (hardware: NVIDIA GT 630M 2GB GPU, Intel Core i7 2nd-generation CPU, 10GB RAM — a low-end, dated mobile GPU).
- "the accuracy was low in comparison to what could be achieved with certain adjustments."
- Supervised object-detection models are described as "data-hungry," and data annotation is called "a costly work which requires lots of time."
- Future work explicitly proposed: better-balanced model structure, more data, more powerful training hardware.

## Claimed contributions
- A comparative literature review of deep-learning object detectors for real-time suitability, concluding YOLO(v3) is "the best model in terms of accuracy and speed."
- A working transfer-learning pipeline that trains YOLOv3 to detect person and cat classes.
- A claim of general reusability: "by modifying the data set, this program might be used in any field where object detection is required."

## Critical assessment (own analysis)
- **Self-contradiction on the central claim**: the thesis title and abstract are built around "real-time" detection, yet the only FPS figure shown in the results is 1 FPS — this directly undercuts the paper's own framing and is not acknowledged as a limitation explicitly tied to the real-time claim.
- **Weak experimental documentation**: no explicit image count for the custom dataset, no discussion of class balance, no error analysis beyond aggregate AP/mAP, and the model's own detector is never benchmarked against a public dataset (only literature-reported numbers for other researchers' models are cited).
- **Very narrow scope relative to length**: of 77 pages, ~40 are generic deep-learning/object-detection background (largely textbook-level literature review), leaving a comparatively thin (~11-page) experimental chapter.
- **No system-level or surveillance-specific design**: despite invoking "surveillance" and "the security sector" rhetorically in the abstract and general conclusion, there is no surveillance-specific pipeline (no tracking, no alerting, no multi-camera handling, no anomaly reasoning) — it is a generic two-class object detector demo.
- Given the dated/weak GPU and small custom dataset, generalization claims should be read cautiously.

## Verbatim quotes
1. Abstract: "Moving object detection is a key step in many computer vision algorithms such as video surveillance, human motion analysis, robotics, sports footage analysis and others."
2. p. 51: "A Convolutional Neural Network derived from the TensorFlow deep learning framework was utilized as the classifier. The model utilized is yolov3 [88], which was chosen after studying the characteristics of various algorithms."
3. p. 52: "We retrain the yolo models to detect a person or cat by fine tuning the parameters of only the last three layers... and by freezing all the parameters of the first 249 layers."
4. General Conclusion, p. 58: "we were partially successful, but not totally, especially given the difficulty of training yolo network while utilizing a relatively weak device. After the model was trained, the process of detecting a person or other object from webcam video capture was fine. However, the accuracy was low in comparison to what could be achieved with certain adjustments."
5. General Conclusion, p. 58: "Though this project has an impact on the security sector, by modifying the data set, this program might be used in any field where object detection is required."

## Relevance to an "agentic multi-agent surveillance system" research direction
Minimal. This is a single-module, single-camera, offline-trained object detector with no tracking, no multi-agent or multi-camera coordination, no autonomous reasoning, no anomaly detection, and no explainable alerting. "Surveillance" appears only as rhetorical motivation in the abstract and conclusion, never as a system requirement shaping the architecture. At best, its chapter-2 literature review of real-time object-detector trade-offs (YOLO family vs. R-CNN family vs. SSD/RetinaNet) could inform the choice of a low-level perception component for one agent in a future multi-agent pipeline — it offers nothing on multi-agent architecture, coordination, reasoning, or explainability, and its own "real-time" claim is empirically undermined by the 1 FPS result it reports.
