# 03 — Concepts Explained

Every technical term, model, framework, metric, dataset, and research concept used in `01-project-summary.md` and `02-gaps-and-recommendations.md` has an entry here. Nothing is assumed. Entries are written for a competent programmer who is new to AI research vocabulary.

Each entry covers: a plain-language definition; why the thing exists; how it works mechanically; how it applies to **this** project; trade-offs and failure modes; and a pointer to a canonical source.

**Index**
1. [Computer vision and detection](#1-computer-vision-and-detection)
2. [Tracking](#2-tracking)
3. [Video anomaly detection and vision-language models](#3-video-anomaly-detection-and-vision-language-models)
4. [Audio](#4-audio)
5. [Agents, multi-agent systems, and coordination](#5-agents-multi-agent-systems-and-coordination)
6. [Agentic AI and large language models](#6-agentic-ai-and-large-language-models)
7. [Fusion, probability, and decision logic](#7-fusion-probability-and-decision-logic)
8. [Evaluation metrics](#8-evaluation-metrics)
9. [Experimental design and statistics](#9-experimental-design-and-statistics)
10. [Datasets and benchmarks](#10-datasets-and-benchmarks)
11. [Named systems in the literature](#11-named-systems-in-the-literature)
12. [Distributed systems and messaging](#12-distributed-systems-and-messaging)
13. [Privacy, law, and governance](#13-privacy-law-and-governance)
14. [Software engineering, tooling, and reproducibility](#14-software-engineering-tooling-and-reproducibility)

---

## 1. Computer vision and detection

### Object detection
**Plain definition.** Given an image, find every object of interest, draw a box around each one, and say what class it belongs to.
**Why it exists.** Image *classification* answers "what is in this picture?" with one label. Surveillance needs "how many people, and where, and since when?" — that requires localisation, not just labelling.
**How it works.** A convolutional or transformer network produces, for many candidate image regions, a class score and four box coordinates. Candidates below a confidence threshold are discarded; overlapping survivors are merged.
**In this project.** `aura_mas/agents/camera_agent.py:254` calls YOLO11n on every sampled frame with `conf=0.35`. Every downstream event — intrusion, loitering, abandoned object — is derived from these boxes, so detection quality is a hard ceiling on the whole system (`chapter6.tex:107` calls this the "perception ceiling").
**Trade-offs and failure modes.** The confidence threshold trades recall for precision. Small, distant, occluded, or low-light objects are missed. Detectors trained on web-scale photos degrade on surveillance footage (odd angles, low resolution, compression artefacts). A missed person is a missed intrusion — the error propagates silently.
**Canonical reference.** Zou et al., *Object Detection in 20 Years: A Survey*, arXiv:1905.05055.

### Bounding box
**Plain definition.** A rectangle described by four numbers — here `[x1, y1, x2, y2]`, the top-left and bottom-right pixel coordinates.
**Why it exists.** It is the cheapest useful description of "where" an object is: four numbers instead of a per-pixel mask.
**How it works.** The detector regresses the four coordinates directly; consumers treat the box as the object's spatial extent.
**In this project.** Stored in `Detection.objects[].bbox` (`bus.py:42`). The **foot point** — bottom-centre of the box, `cx = (x1+x2)/2, cy = y2` (`camera_agent.py:67-68`) — is used as the person's ground position for zone membership, because a standing person's feet are where they actually are on the floor plane.
**Trade-offs and failure modes.** A box is a poor fit for non-rectangular or overlapping objects. The foot-point heuristic breaks when a person is occluded from the waist down, sitting, or when the camera looks straight down.
**Canonical reference.** Any detection dataset specification; the COCO format is the de facto standard (cocodataset.org/#format-data).

### Intersection over Union (IoU)
**Plain definition.** A number from 0 to 1 measuring how much two boxes overlap: the area of their intersection divided by the area of their union.
**Why it exists.** You need a single scalar to answer "are these two boxes the same object?" — for matching predictions to ground truth, for suppressing duplicates, and for tracking.
**How it works.** `IoU = area(A ∩ B) / area(A ∪ B)`. Identical boxes give 1.0; disjoint boxes give 0.0. Implemented at `camera_agent.py:107-115`.
**In this project.** The abandoned-object rule fires when a non-person track's current box still has `IoU > 0.6` with its first observed box after `abandoned_seconds = 10.0` — i.e. the object has not moved (`camera_agent.py:96-103`).
**Trade-offs and failure modes.** IoU is scale-sensitive: a few pixels of jitter drops IoU a lot for small boxes and barely at all for large ones. So the 0.6 threshold means "static" differently for a backpack than for a truck.
**Canonical reference.** Rezatofighi et al., *Generalized Intersection over Union*, CVPR 2019.

### YOLO / YOLO11n
**Plain definition.** YOLO ("You Only Look Once") is a family of real-time object detectors. YOLO11n is the "nano" (smallest) member of the 2024 generation, about 2.6 million parameters.
**Why it exists.** Earlier detectors ran a classifier over thousands of image regions, which was far too slow for video. YOLO reframed detection as a single forward pass over the whole image.
**How it works.** One network pass produces a dense grid of predictions; each cell predicts boxes, objectness, and class scores. Post-processing removes duplicates.
**In this project.** `yolo11n.pt` (5.6 MB) is the sole visual detector, loaded via the Ultralytics library (`camera_agent.py:196`). It is used **pretrained on COCO with no fine-tuning**, which is the project's deliberate zero-training stance.
**Trade-offs and failure modes.** The nano variant trades accuracy for speed — roughly 39.5 % mAP on COCO versus ~54 % for the largest variant. On CPU at 5 frames per second it is viable on edge hardware, but it will miss small or partially-occluded people, which is exactly the surveillance failure case that matters.
**Canonical reference.** Ultralytics YOLO11 documentation, docs.ultralytics.com; original: Redmon et al., *You Only Look Once*, CVPR 2016.

### RT-DETR
**Plain definition.** A real-time object detector built on the transformer architecture rather than the convolutional YOLO design.
**Why it exists.** Transformer detectors (DETR family) removed hand-designed post-processing by treating detection as set prediction, but were slow; RT-DETR made the family real-time.
**How it works.** An encoder-decoder transformer attends over image features and directly emits a fixed set of object queries, each resolving to a box and class — no duplicate-suppression step needed.
**In this project.** Cited in `chapter3.tex:10` as a "drop-in upgrade path". It is not used. Recommendation D "Perception" suggests actually swapping it in, because doing so would validate the thesis's claim that agents encapsulate their detector behind a common event interface.
**Trade-offs and failure modes.** Higher memory and compute than YOLO11n; less mature edge tooling; the accuracy gain may not survive on low-resolution surveillance footage.
**Canonical reference.** Zhao et al., *DETRs Beat YOLOs on Real-time Object Detection*, CVPR 2024.

### Open-vocabulary detection (YOLO-World, Grounding DINO)
**Plain definition.** Detectors that can find objects described by arbitrary text ("a ladder", "an orange safety cone") rather than only a fixed class list.
**Why it exists.** Fixed class lists like COCO's 80 classes cannot cover the long tail of things a specific site cares about, and retraining for each new class is expensive.
**How it works.** The detector is trained to align image regions with text embeddings, so at inference you supply class names as text and it localises them.
**In this project.** Not used. Proposed in `02` §E as a capability extension: zone rules could then reference site-specific objects without any training, which is consistent with the project's zero-training constraint.
**Trade-offs and failure modes.** Accuracy on arbitrary prompts is much lower and much less predictable than on trained classes; prompt phrasing materially changes results; heavier than YOLO11n.
**Canonical reference.** Cheng et al., *YOLO-World: Real-Time Open-Vocabulary Object Detection*, CVPR 2024; Liu et al., *Grounding DINO*, ECCV 2024.

### Ray-casting point-in-polygon test
**Plain definition.** An algorithm that decides whether a point lies inside an arbitrary polygon.
**Why it exists.** Zones in a surveillance site are irregular shapes, not rectangles; you need a general test.
**How it works.** Draw an imaginary ray from the point in any direction and count how many polygon edges it crosses. Odd means inside, even means outside. Implemented at `camera_agent.py:34-45`.
**In this project.** Decides whether a tracked person's foot point is inside a declared zone, which triggers the intrusion and loitering rules.
**Trade-offs and failure modes.** Numerically fragile for points exactly on an edge or vertex (the implementation adds `1e-9` to the denominator to avoid division by zero). It works in **image pixel coordinates**, so a zone drawn for one camera resolution is meaningless at another, and there is no perspective correction.
**Canonical reference.** Shimrat, *Algorithm 112: Position of point relative to polygon*, CACM 1962.

### Homography
**Plain definition.** A 3×3 matrix that maps points on one flat plane to points on another — for example, from camera pixels to a floor plan.
**Why it exists.** Image coordinates are not physical coordinates. To reason about "is this person in the restricted area, in metres" you need a mapping to the ground plane.
**How it works.** Given four or more corresponding point pairs between the image and the plan, solve a linear system for the matrix; then any pixel maps to a plan location.
**In this project.** Not implemented. Recommended in `02` §B3 as the principled way to compute field-of-view overlap between cameras and zones, which is the missing input to the auction bid function.
**Trade-offs and failure modes.** Only valid for a single plane — people are not flat, so the foot point is the only reliable anchor. Requires calibration per camera, which must be redone if a camera moves.
**Canonical reference.** Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., Ch. 2.

### Histogram of Oriented Gradients (HOG)
**Plain definition.** A pre-deep-learning image feature: describe a region by the distribution of edge directions inside it, then classify with a linear model.
**Why it exists.** It was the standard person detector from 2005 until convolutional networks displaced it around 2014. It survives because it is fast, dependency-light, and needs no model weights.
**How it works.** Compute image gradients, bin their orientations into local cells, normalise across blocks, and feed the resulting vector to a support vector machine trained to say "person / not person".
**In this project.** `core/privacy.py:31-51` uses OpenCV's built-in HOG people detector as a **fallback** to locate person regions for blurring when the camera agent does not supply YOLO boxes.
**Trade-offs and failure modes.** Far weaker than a modern detector: many misses on non-upright, occluded, or small people. In this system a miss means an un-blurred face in exported evidence — a privacy failure, not just an accuracy failure. The code correctly compensates with a fail-closed path.
**Canonical reference.** Dalal & Triggs, *Histograms of Oriented Gradients for Human Detection*, CVPR 2005.

### Gaussian blur
**Plain definition.** An image smoothing operation that replaces each pixel with a weighted average of its neighbours, weights following a bell curve.
**Why it exists.** It is the standard way to remove fine detail — here, the detail that would identify a face.
**How it works.** Convolve the image with a Gaussian kernel of size `k`. Larger `k` removes more detail.
**In this project.** `core/privacy.py:21-28` blurs person boxes with `k=21`, and the upper third of each box (the head region) more strongly with `k=61`, before any evidence JPEG is written.
**Trade-offs and failure modes.** Blur strength is a fixed pixel size, but a person's face occupies very different pixel counts at different distances — so a distant face may be blurred to mush while a close-up face at `k=61` may remain recognisable. Blur is also known to be partially reversible by deep models under some conditions. The project asserts anonymisation efficacy but never measures it (`02` §A11).
**Canonical reference.** OpenCV documentation, `cv2.GaussianBlur`.

### Frames per second (FPS) and inference rate
**Plain definition.** How many images per second are captured (source FPS) or processed by the model (inference FPS).
**Why it exists.** Processing every frame of every camera is usually unaffordable; you sample.
**How it works.** `camera_agent.py:226-236` computes `stride = round(source_fps / infer_fps)` and skips frames accordingly, with `infer_fps = 5.0` by default.
**In this project.** 5 FPS per camera on CPU is the compute budget that makes the "edge-first" claim plausible.
**Trade-offs and failure modes.** Sampling at 5 FPS means a fast event (a thrown object, a brief entry) can fall entirely between processed frames. It also degrades tracking, because the tracker sees larger jumps between observations.
**Canonical reference.** —(engineering convention, no single source).

---

## 2. Tracking

### Multi-object tracking (MOT)
**Plain definition.** Linking per-frame detections of the same object across time so that each object gets a persistent identity.
**Why it exists.** Detection alone cannot express duration. "Has this person been here for eight seconds?" requires knowing it is the *same* person across 40 frames.
**How it works.** The dominant paradigm is *tracking-by-detection*: run the detector each frame, predict where existing tracks should be (usually with a motion model), and match predictions to new detections by overlap and/or appearance.
**In this project.** Every duration-based rule depends on it. `ZoneRuleEngine` keys dwell timers on `(track_id, zone)` and static-object timers on `track_id` (`camera_agent.py:56-58`).
**Trade-offs and failure modes.** Identity switches (two people crossing and swapping IDs) and fragmentation (one person becoming two tracks after an occlusion) both silently break duration rules. The project never measures tracking quality (`02` §E, TrackEval).
**Canonical reference.** Luo et al., *Multiple Object Tracking: A Literature Review*, Artificial Intelligence, 2021.

### ByteTrack
**Plain definition.** A simple, strong tracking-by-detection algorithm whose trick is to also use the detector's *low-confidence* boxes.
**Why it exists.** Most trackers throw away boxes below a confidence threshold. But an occluded person often produces exactly such a low-confidence box, so discarding it causes an identity switch.
**How it works.** Two-stage matching: first associate high-confidence detections with existing tracks by IoU, then try to match the remaining unmatched tracks against the *low*-confidence detections before declaring them lost.
**In this project.** Used through Ultralytics: `model.track(frame, persist=True, tracker="bytetrack.yaml", conf=0.35)` (`camera_agent.py:254`). `persist=True` keeps tracker state across calls; the warm-up path deliberately uses `predict` rather than `track` to avoid seeding tracker state with a dummy frame (`camera_agent.py:213-216`).
**Trade-offs and failure modes.** No appearance model, so it recovers poorly from long occlusions and cannot re-identify a person who leaves and returns. Sensitive to frame rate — at 5 FPS, fast motion breaks IoU-based association. This is the likely mechanism behind `scenarios/loitering_01.json`'s finding that no track survives more than 5.5 seconds.
**Canonical reference.** Zhang et al., *ByteTrack: Multi-Object Tracking by Associating Every Detection Box*, ECCV 2022.

### Track ID and identity switch
**Plain definition.** A track ID is an integer the tracker assigns to a trajectory. An identity switch is when the tracker gives an object a new ID, or gives one object's ID to another.
**Why it exists.** Downstream logic needs a stable handle for "this specific person".
**How it works.** IDs are allocated when a track is created and retired when it is lost for too many frames.
**In this project.** `camera_agent.py:265` reads `int(b.id)`. Rules fire at most once per `(track_id, zone)` via the `_fired` set (`camera_agent.py:58`), so an identity switch causes a *duplicate* event; a lost track causes a *reset* dwell timer.
**Trade-offs and failure modes.** Because `_dwell` is deleted the moment a track leaves the polygon (`camera_agent.py:72-73`), a single frame of missed detection resets the loitering counter to zero — see bug C21 in `02` §C.
**Canonical reference.** As ByteTrack above.

### HOTA, MOTA, IDF1
**Plain definition.** The three standard scores for tracking quality. MOTA counts detection errors and identity switches; IDF1 measures how consistently identities are preserved; HOTA balances detection accuracy and association accuracy in one number.
**Why they exist.** A tracker can look good on detection and be useless on identity, or vice versa. One number hides this, so the field uses several.
**How they work.** All three match predicted tracks to ground-truth tracks and then aggregate errors — MOTA as a penalty sum, IDF1 as an F1 over identity assignments, HOTA as a geometric mean of detection and association scores across localisation thresholds.
**In this project.** Cited in `chapter3.tex:16` and **never computed**. Since every zone rule is downstream of tracking, an unmeasured tracker is an unmeasured foundation.
**Trade-offs and failure modes.** Computing them requires per-frame ground-truth trajectories, which this project does not have — the manifests annotate incidents, not tracks. So adopting them means new annotation work (`02` §E marks this Medium effort for exactly that reason).
**Canonical reference.** Luiten et al., *HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking*, IJCV 2021.

### Re-identification (ReID)
**Plain definition.** Recognising that the person seen by camera 2 is the same person camera 1 saw earlier, using appearance.
**Why it exists.** Multi-camera systems need to follow people across non-overlapping views.
**How it works.** A network embeds each person crop into a vector; the same person's crops land close together, different people far apart. Matching is nearest-neighbour in that space.
**In this project.** **Deliberately excluded.** `chapter1.tex:46` and `chapter3.tex:16` state that no re-identification is performed, on privacy grounds; cross-camera corroboration happens at the *event* level (same incident family, same zone, same time window) rather than the identity level.
**Trade-offs and failure modes.** This is a genuine capability sacrifice: without ReID the system cannot follow an intruder across the site. But ReID is close to biometric identification under the EU AI Act, so the exclusion is a defensible and well-argued design choice — arguably one of the thesis's better ones.
**Canonical reference.** Ye et al., *Deep Learning for Person Re-identification: A Survey and Outlook*, TPAMI 2022.

---

## 3. Video anomaly detection and vision-language models

### Video anomaly detection (VAD)
**Plain definition.** Automatically flagging video segments that deviate from normal activity, without a rule that names what "abnormal" is.
**Why it exists.** You cannot enumerate every bad thing that could happen at a site. Rules catch what you anticipated; anomaly detection is meant to catch what you did not.
**How it works.** Three families: (i) *reconstruction/prediction* models trained only on normal video, flagging frames they reconstruct badly; (ii) *weakly-supervised* models trained on video-level "contains anomaly" labels; (iii) *zero-shot semantic* models comparing frames to text descriptions.
**In this project.** Family (iii) only, via `ClipAnomalyScorer` (`camera_agent.py:118-161`), and it is optional and off by default in the campaign. `chapter3.tex:20-28` surveys all three.
**Trade-offs and failure modes.** Anomaly scores are notoriously scene-dependent; a model trained or prompted for one environment transfers badly. Measured here at AUC 0.308 — worse than random (`results/clip_anomaly_calibration_notes.md`).
**Canonical reference.** Sultani et al., *Real-world Anomaly Detection in Surveillance Videos*, CVPR 2018.

### Weakly-supervised learning
**Plain definition.** Training with labels that are cheaper and coarser than what you actually want to predict — for example, "this 10-minute video contains a robbery somewhere" instead of "frames 3400–3900 contain a robbery".
**Why it exists.** Frame-level annotation of surveillance video is prohibitively expensive; video-level labels are not.
**How it works.** Typically multiple-instance learning: the model scores every segment, and the training signal only requires that the highest-scoring segment of a positive video outrank the highest-scoring segment of a negative one.
**In this project.** Not used — nothing is trained. Relevant because weakly-supervised VAD on UCF-Crime is the accuracy leader in the field, and it is the comparison class the thesis cites (`chapter3.tex:24`) but never competes against.
**Trade-offs and failure modes.** Weak labels give weak localisation; models often latch onto scene context rather than the event.
**Canonical reference.** Sultani et al., CVPR 2018 (as above).

### Zero-shot learning
**Plain definition.** Getting a model to handle a category it was never explicitly trained on, by describing it instead of showing examples.
**Why it exists.** Collecting and labelling examples for every category is impossible at scale; a model that generalises from language descriptions sidesteps that.
**How it works.** Train a model to align images and text in a shared embedding space; at inference, embed candidate class descriptions as text and pick the nearest one to the image embedding.
**In this project.** The entire visual-anomaly component is zero-shot, and the zero-training stance across the project (`chapter3.tex:44`) rests on this idea. It is the main de-risking decision of a one-month scope.
**Trade-offs and failure modes.** Performance depends heavily on prompt wording and on how close the deployment domain is to the training distribution. This project is a textbook example of the failure: prompts describing indoor warehouses, footage of outdoor streets, AUC below chance.
**Canonical reference.** Radford et al., *Learning Transferable Visual Models From Natural Language Supervision* (CLIP), ICML 2021.

### CLIP
**Plain definition.** A model trained on hundreds of millions of image–caption pairs that maps images and text into the same vector space, so you can compare a picture to a sentence numerically.
**Why it exists.** It made zero-shot image classification practical and became the backbone of most vision-language work.
**How it works.** Two encoders (one for images, one for text) trained with a contrastive objective: matching image–text pairs are pulled together, mismatched pairs pushed apart. At inference you encode an image and a set of candidate texts and compare by cosine similarity.
**In this project.** `ClipAnomalyScorer` (`camera_agent.py:118-161`) encodes 3 "normal" prompts and 5 "anomalous" prompts once at startup, then scores each sampled frame as the **softmax mass on the anomalous prompts**. `ViT-B/32` is the smallest common variant.
**Trade-offs and failure modes.** The softmax is over an arbitrary, hand-written prompt set, so the score is not calibrated and not comparable across scenes. Adding or removing a prompt changes every score. Measured AUC 0.308 here.
**Canonical reference.** Radford et al., ICML 2021; openai.com/research/clip.

### Softmax
**Plain definition.** A function that turns a list of arbitrary real numbers into positive numbers that sum to 1, so they can be read as proportions.
**Why it exists.** Model outputs are unbounded scores; downstream logic usually wants something that behaves like a probability distribution.
**How it works.** `softmax(x)_i = exp(x_i) / Σ_j exp(x_j)`. Larger inputs get exponentially larger shares.
**In this project.** `camera_agent.py:158` applies softmax to `100.0 × (image_embedding · text_embeddings)` and sums the mass over the anomalous prompts.
**Trade-offs and failure modes.** Softmax outputs *look* like probabilities but are not calibrated — a 0.9 does not mean "right 90 % of the time". The temperature (here, the hard-coded `100.0`) arbitrarily sharpens or flattens the distribution. This is precisely why the resulting number should not be fed into a probabilistic fusion model without calibration.
**Canonical reference.** Bishop, *Pattern Recognition and Machine Learning*, §4.3.4.

### Prompt, prompt engineering, prompt ensembling
**Plain definition.** A prompt is the text you give a language or vision-language model. Prompt engineering is deliberately shaping that text to get better results. Prompt ensembling averages results over several paraphrases of the same prompt.
**Why they exist.** These models are extremely sensitive to wording; small phrasing changes produce large output changes, and there is no gradient to tune, so text is the control surface.
**How they work.** For CLIP-style scoring, each prompt is embedded once; ensembling averages the embeddings of several paraphrases before comparison, which reduces the variance introduced by any single phrasing.
**In this project.** The eight hard-coded prompts at `camera_agent.py:125-135` are the sole determinant of the anomaly score. `results/clip_anomaly_calibration_notes.md` root-causes the AUC failure to those prompts describing the wrong environment. `02` §D3 proposes rewriting and ensembling them as the cheapest available accuracy win.
**Trade-offs and failure modes.** Prompt tuning on the same clips used for evaluation is a form of test-set fitting; a held-out split is required for any reported improvement to be honest.
**Canonical reference.** Radford et al., ICML 2021 §3.1.4 (prompt engineering and ensembling).

### Vision-language model (VLM)
**Plain definition.** A model that takes images (or video) *and* text as input and produces text — for example, describing what is in a photograph.
**Why it exists.** It bridges perception and language, so a system can explain what it sees rather than emitting numbers.
**How it works.** A vision encoder produces image tokens; these are projected into a language model's token space and processed alongside text tokens by the same transformer.
**In this project.** The `_describe` node of `ExplanationAgent` (`explanation_agent.py:82-105`) sends base64-encoded anonymised evidence frames to a vision-capable endpoint for a factual description, when `use_vision=True`. This path was never exercised in the campaign.
**Trade-offs and failure modes.** Expensive; prone to confident hallucination about image content; and sending images to an external endpoint conflicts with the project's "raw frames never leave the edge" framing even when the frames are blurred (`02` §D9).
**Canonical reference.** Liu et al., *Visual Instruction Tuning* (LLaVA), NeurIPS 2023.

### Instruction tuning
**Plain definition.** Further training a pretrained model on examples of instructions and desired responses, so it follows requests rather than merely continuing text.
**Why it exists.** A raw language model predicts likely next tokens; it does not natively obey "summarise this incident in JSON".
**How it works.** Supervised fine-tuning on (instruction, response) pairs, often followed by preference-based training.
**In this project.** Not performed. Relevant as the mechanism behind Holmes-VAD/Holmes-VAU, which achieve explainable anomaly understanding by instruction-tuning on purpose-built anomaly instruction data — the approach that occupies contribution C4's territory at far greater rigour.
**Canonical reference.** Wei et al., *Finetuned Language Models Are Zero-Shot Learners*, ICLR 2022.

---

## 4. Audio

### Sound event detection (SED)
**Plain definition.** Identifying what acoustic events occur in an audio stream and when — glass breaking, a scream, a siren.
**Why it exists.** Audio is cheap, omnidirectional, works in the dark, and captures events that happen outside every camera's field of view.
**How it works.** Convert the waveform to a time–frequency representation, run a classifier over short windows, and threshold per class.
**In this project.** `AudioAgent` (`aura_mas/agents/audio_agent.py`) with two backends: YAMNet (classification) and a DSP z-score scorer (undifferentiated anomaly). `SURVEILLANCE_CLASSES` (`audio_agent.py:28-40`) maps 10 AudioSet class names to 6 event types.
**Trade-offs and failure modes.** Highly sensitive to microphone placement, reverberation, and background noise. Short transients are easily missed by naive windowing — a failure this project found and fixed (`results/yamnet_integration_notes.md`).
**Canonical reference.** Mesaros et al., *Sound Event Detection: A Tutorial*, IEEE Signal Processing Magazine, 2021.

### YAMNet
**Plain definition.** A small pretrained audio classifier that recognises 521 everyday sound classes.
**Why it exists.** It gives usable audio classification with no training, from a model small enough for edge devices.
**How it works.** A MobileNet-style convolutional network over log-mel spectrogram patches. It analyses 0.96-second frames with a 0.48-second hop and outputs a score per class per frame.
**In this project.** Loaded from a **local TensorFlow SavedModel** fetched by `aura_mas/scripts/fetch_yamnet.py`, because the usual `tensorflow_hub` URL returns HTTP 404 (`CLAUDE.md`). Scores are **max-pooled** over the internal frames of a lookback-extended window (`audio_agent.py:190-192`).
**Trade-offs and failure modes.** AudioSet class names are broad and noisy ("Glass", "Shatter", "Breaking" all plausibly fire on one event — hence the per-chunk deduplication at `audio_agent.py:201-206`). Thresholds of 0.2–0.3 are low and uncalibrated. Requires TensorFlow, a heavy dependency the project keeps optional.
**Canonical reference.** Hershey et al., *CNN Architectures for Large-Scale Audio Classification*, ICASSP 2017; TensorFlow model page for YAMNet.

### AudioSet
**Plain definition.** A very large dataset of ~2 million 10-second YouTube clips labelled with an ontology of 632 sound classes.
**Why it exists.** It is to audio what ImageNet was to vision: the pretraining corpus that made general-purpose audio classifiers possible.
**How it works.** Weak, clip-level, human-verified labels over a hierarchical ontology.
**In this project.** The label space YAMNet predicts in. The `SURVEILLANCE_CLASSES` mapping is a hand-curated projection from AudioSet names to this system's event vocabulary.
**Trade-offs and failure modes.** Labels are weak and the ontology is uneven; classes like "Alarm" cover wildly different sounds. Class balance is poor for rare safety-critical events such as gunshots.
**Canonical reference.** Gemmeke et al., *Audio Set: An Ontology and Human-Labeled Dataset for Audio Events*, ICASSP 2017.

### PANNs and BEATs
**Plain definition.** Two later, stronger families of pretrained audio classifiers. PANNs are large convolutional networks trained on AudioSet; BEATs is a self-supervised audio transformer.
**Why they exist.** YAMNet is small and dated; both substantially outperform it on AudioSet benchmarks.
**How they work.** PANNs scale up the convolutional recipe; BEATs learns discrete acoustic tokens self-supervised, then fine-tunes for classification.
**In this project.** Not used. Proposed in `02` §E so that the "audio backend" ablation compares two real classifiers rather than a classifier against a label-less anomaly scorer.
**Trade-offs and failure modes.** Both are considerably heavier than YAMNet, which cuts against the edge-first argument. That trade-off is itself worth measuring.
**Canonical reference.** Kong et al., *PANNs*, IEEE/ACM TASLP 2020; Chen et al., *BEATs*, ICML 2023.

### Log-mel spectrogram
**Plain definition.** A picture of sound: time on one axis, frequency on the other, brightness for energy — with the frequency axis warped to match human hearing and the energy on a logarithmic scale.
**Why it exists.** Raw waveforms are hard for networks to learn from directly; spectrograms expose the structure that distinguishes sounds, in a form convolutional networks handle well.
**How it works.** Short-time Fourier transform → group frequency bins into mel bands → take the logarithm.
**In this project.** Internal to YAMNet; the code passes raw 16 kHz mono samples and YAMNet does the transform. The DSP fallback computes its own simpler spectrum with `numpy.fft.rfft` (`audio_agent.py:52`).
**Trade-offs and failure modes.** Window length trades time resolution against frequency resolution; short transients need short windows, which is exactly the tension this project hit.
**Canonical reference.** Mesaros et al., IEEE SPM 2021 (as above).

### Short-time energy and root-mean-square (RMS)
**Plain definition.** How loud a short chunk of audio is, computed as the square root of the mean of the squared samples.
**Why it exists.** It is the cheapest possible sound-activity feature — no model, no training, a few arithmetic operations.
**How it works.** `energy = sqrt(mean(chunk²))`, at `audio_agent.py:51`.
**In this project.** One of the two features driving the DSP fallback anomaly score.
**Trade-offs and failure modes.** Loudness alone cannot distinguish a glass break from a slammed door or a passing truck. Non-stationary background noise defeats it entirely.
**Canonical reference.** Rabiner & Schafer, *Digital Processing of Speech Signals*, Ch. 4.

### Spectral flatness
**Plain definition.** A number saying whether a sound's energy is spread evenly across frequencies (noise-like, flatness near 1) or concentrated in a few (tonal, flatness near 0).
**Why it exists.** It separates hiss and crashes from tones and speech using one cheap scalar.
**How it works.** Geometric mean of the spectrum divided by its arithmetic mean (`audio_agent.py:53`).
**In this project.** The second DSP feature. A glass break is broadband, so flatness spikes.
**Trade-offs and failure modes.** Also spikes for any broadband noise — wind, rain, applause. Combined with energy in a z-score, it yields an undifferentiated "something changed" signal.
**Canonical reference.** Peeters, *A Large Set of Audio Features for Sound Description*, CUIDADO project report, 2004.

### Z-score
**Plain definition.** How many standard deviations a value sits away from the recent average.
**Why it exists.** It converts "is this unusual?" into a scale-free number that works without knowing the absolute units.
**How it works.** `z = |x − μ| / σ`, with μ and σ estimated over a rolling history (here, the last 50 chunks, `audio_agent.py:46-61`). The result is squashed with `min(1.0, z/6.0)`.
**In this project.** The DSP fallback's entire anomaly score.
**Trade-offs and failure modes.** The rolling baseline adapts, so a sustained anomaly gradually becomes "normal" and stops firing. It also needs ≥ 10 history chunks before it produces anything (`audio_agent.py:55`), which is why `scenarios/audio_glass_break_01.json` requires a 15-second lead-in of baseline noise. The `/6.0` divisor is an arbitrary magic number.
**Canonical reference.** Any introductory statistics text; e.g. Wasserman, *All of Statistics*, §1.

### Mean-pooling versus max-pooling
**Plain definition.** Two ways to collapse many per-frame scores into one score for a window: average them, or take the largest.
**Why it matters here.** A 0.5-second glass break inside a 1-second window occupies only some frames. Averaging dilutes the peak toward the background; taking the maximum preserves it.
**How it works.** Elementwise `mean(scores, axis=0)` versus `max(scores, axis=0)` over YAMNet's internal frame axis.
**In this project.** `audio_agent.py:192` uses `.max(axis=0)`. `results/yamnet_integration_notes.md` records that mean-pooling produced confidence 0.069 on a clean glass-break clip while max-pooling produced 0.5–0.75 on the same clip — a genuinely well-diagnosed bug.
**Trade-offs and failure modes.** Max-pooling is sensitive to single-frame spikes, so it raises the false-positive rate. The correct answer depends on event duration; neither is universally right.
**Canonical reference.** Standard practice in weakly-labelled SED; see Mesaros et al., IEEE SPM 2021.

### Lookback-extended window
**Plain definition.** Scoring a chunk of audio together with a little of the audio immediately before it, instead of the chunk alone.
**Why it exists.** Fixed non-overlapping chunk boundaries can split a short event so that no analysis frame is well-centred on it.
**How it works.** `audio_agent.py:166` builds `audio[max(0, i - half) : i + n]` — the current chunk plus the trailing half of the previous one — and feeds that to YAMNet, while DSP still sees only the bare chunk.
**In this project.** One of the two fixes that made YAMNet detection work at all.
**Trade-offs and failure modes.** Overlapping windows mean the same acoustic event can be scored twice, in consecutive chunks, producing duplicate events — which is why the per-chunk deduplication and `top_k` cap exist. It also increases compute per second of audio.
**Canonical reference.** —(standard windowing practice; documented in `results/yamnet_integration_notes.md`).

### Sampling rate, chunk, hop
**Plain definition.** Sampling rate is how many audio samples per second (16,000 here). A chunk is the block of samples you process at once. Hop is how far you advance between blocks.
**Why they exist.** Audio is continuous; models need fixed-size inputs, so you must choose a segmentation.
**How they work.** `librosa.load(source, sr=16000, mono=True)` then `n = int(sr * chunk_seconds)` with `chunk_seconds = 1.0` (`audio_agent.py:156-160`).
**In this project.** Determines the system's temporal resolution for audio and, through the fusion window, how audio and video events line up in time.
**Trade-offs and failure modes.** One-second chunks are coarse relative to a 0.3-second transient, and the mismatch between YAMNet's internal 0.96 s/0.48 s framing and the agent's 1.0 s chunking is exactly what caused the diluted-transient bug.
**Canonical reference.** librosa documentation, `librosa.load`.

---

## 5. Agents, multi-agent systems, and coordination

### Agent
**Plain definition.** A software component that perceives some environment, holds its own state, and acts autonomously toward a goal — as opposed to a function that is simply called.
**Why it exists.** When responsibility is naturally distributed (one camera, one microphone, one site), modelling each unit as an autonomous actor matches the problem structure and keeps data local.
**How it works.** Typically: an identity, a private state store, an inbound message loop, and optionally a periodic timer.
**In this project.** `aura_mas/agents/base.py:11-54`: `agent_id`, a `beliefs` dictionary, bus subscriptions dispatched by callback, and an optional `tick()` on a daemon thread.
**Trade-offs and failure modes.** "Agent" is often used loosely for any class with a `run()` method. The four properties usually required — autonomy, reactivity, pro-activeness, social ability (`chapter2.tex:14-19`) — are a useful test. `FusionAgent` and `PolicyAgent` here are arguably message-driven services rather than agents in the strong sense, since they have no goals of their own.
**Canonical reference.** Wooldridge, *An Introduction to MultiAgent Systems*, 2nd ed., Ch. 2.

### Multi-agent system (MAS)
**Plain definition.** Several agents interacting — cooperating, competing, or negotiating — to achieve something none could achieve alone.
**Why it exists.** It provides principled answers to distribution, coordination, and heterogeneity, backed by decades of protocol design.
**How it works.** Agents share an interaction protocol and a communication substrate; system behaviour emerges from local decisions plus message exchange.
**In this project.** Six agents over a message bus, in three layers. Crucially, `research/.../findings/F4` establishes that multi-agent surveillance is not a novel idea — Monitorix did it in 2000 — so the MAS framing alone cannot carry a contribution claim.
**Trade-offs and failure modes.** Distribution buys robustness and scalability at the cost of consistency, debuggability, and latency. The v2 data here shows the MAS variants performing *worse* on mean F1 than the centralized baseline, which is a legitimate and interesting negative result.
**Canonical reference.** Wooldridge, *An Introduction to MultiAgent Systems*, 2nd ed.

### Belief–Desire–Intention (BDI)
**Plain definition.** A classic agent architecture: the agent holds *beliefs* (what it thinks is true), *desires* (goals), and *intentions* (plans it has committed to).
**Why it exists.** It is a middle ground between purely reactive rules and full symbolic planning, and it maps onto how people describe rational behaviour.
**How it works.** A loop: update beliefs from perception and messages, select desires consistent with beliefs, commit to intentions, execute, repeat.
**In this project.** Only the *belief* part exists — `self.beliefs` in `base.py:24`. There are no explicit desires or intentions anywhere. `chapter2.tex:25` cites BDI as background rather than claiming to implement it, which is honest.
**Trade-offs and failure modes.** Claiming BDI without desires and intentions would be an overclaim; the current text avoids it, but a reader may still expect more than a dictionary.
**Canonical reference.** Rao & Georgeff, *BDI Agents: From Theory to Practice*, ICMAS 1995.

### Reactive versus deliberative architecture
**Plain definition.** Reactive agents map perception directly to action with no internal model. Deliberative agents reason over an explicit model before acting. Hybrid layered architectures do both at different speeds.
**Why it exists.** Reactive is fast but shallow; deliberative is smart but slow. Most real systems need both.
**How it works.** A fast reactive layer handles time-critical responses; a slower layer plans over aggregated state.
**In this project.** Explicitly mirrored at the system level (`chapter2.tex:25`): edge agents are reactive frame-rate loops, coordination deliberates over aggregated hypotheses at 1 Hz, and the explanation layer performs the slowest reasoning only when an alert has already been emitted. This is a genuinely well-argued piece of the design.
**Trade-offs and failure modes.** The layering only helps if the slow layer cannot block the fast one — which is violated here: `PolicyAgent.on_hypothesis` blocks the fusion tick thread for up to four seconds during an auction (bug C10).
**Canonical reference.** Wooldridge, Ch. 5.

### FIPA Agent Communication Language (FIPA-ACL)
**Plain definition.** A standard vocabulary of message types for agents — `inform`, `request`, `cfp` (call for proposals), `propose`, `accept-proposal` — with defined meanings.
**Why it exists.** Without a shared message semantics, every multi-agent system reinvents its protocol and none interoperate.
**How it works.** Messages carry a performative (the speech act), sender, receiver, content, and conversation identifier.
**In this project.** Not implemented. `chapter2.tex:38` says AURA-MAS adopts the *spirit* of FIPA interaction protocols while using plain JSON over MQTT topics — a common and defensible engineering compromise, correctly labelled as such.
**Trade-offs and failure modes.** Dropping FIPA loses interoperability and the formal semantics that make protocol conformance checkable. For a closed prototype this costs little; for a certification argument it costs more than it looks.
**Canonical reference.** FIPA ACL Message Structure Specification, SC00061G, 2002.

### Contract Net Protocol (CNP)
**Plain definition.** A task-allocation protocol: a manager announces a task, potential contractors bid, the manager awards to the best bid.
**Why it exists.** It decentralises allocation without requiring the manager to know each contractor's capabilities in advance — the bidder computes its own suitability.
**How it works.** Four phases: announce → bid → award → report. Communication is linear in the number of bidders.
**In this project.** The basis of `CoordinatorAgent` and contribution C2. Topics `site/coordination/{tasks,bids,awards,verifications}` (`bus.py:99-102`) map directly onto the four phases.
**Trade-offs and failure modes.** CNP is optimal only in the trivial sense that it picks the best *submitted* bid; if bids carry no information — which is the case here, because `fov_overlap` is never populated (bug C1) — the protocol degenerates to arbitrary selection. It also assumes truthful bidding, which is fine among cooperative agents and unsafe otherwise.
**Canonical reference.** Smith, *The Contract Net Protocol*, IEEE Transactions on Computers, C-29(12), 1980.

### Auction, sealed-bid, single-round
**Plain definition.** An allocation mechanism where bidders submit valuations and the item goes to the best bid. *Sealed-bid* means bidders do not see each other's bids. *Single-round* means there is exactly one bidding phase, with no iteration.
**Why it exists.** Auctions convert distributed private information (each camera's own suitability) into a single allocation decision at low communication cost.
**How it works.** `coordinator_agent.py:85-99`: publish the task, wait `bid_window = 1.0 s`, take `max(bids)`, publish the award.
**In this project.** The mechanism behind contribution C2, with round-robin as the non-market ablation baseline.
**Trade-offs and failure modes.** Three concrete problems here: bids carry no real information (bug C1); the fixed one-second wait is dead latency on the in-process bus, because bids arrive synchronously before the sleep even starts (bug C9); and the "communication cost" measured is a count of in-process function calls, not network traffic (`01` §5.6).
**Canonical reference.** Dias et al., *Market-Based Multirobot Coordination: A Survey and Analysis*, Proceedings of the IEEE, 94(7), 2006.

### Bid, utility function
**Plain definition.** A utility function scores how good an outcome is for an agent. A bid is that score, submitted to the auctioneer.
**Why it exists.** It compresses everything an agent privately knows about its own fitness for a task into one comparable number.
**How it works.** `camera_agent.py:315-320`: `u = base × capacity × overlap`, where `base = 1.0` for a non-originating camera and `0.3` for the originator, `capacity = 0.2` if busy else `1.0`, and `overlap` is meant to be field-of-view overlap.
**In this project.** This is where the auction's intelligence was supposed to live. Because `overlap` always evaluates to the default `0.5`, the utility carries only "am I the originator" and "am I busy" — the reason the auction is empirically indistinguishable from round-robin.
**Trade-offs and failure modes.** Utility functions are hand-designed and therefore arbitrary; the multiplicative form means any zero factor zeroes the bid. There is no calibration and no sensitivity analysis of the constants 0.3 and 0.2.
**Canonical reference.** Dias et al., Proceedings of the IEEE 2006 (as above).

### Round-robin scheduling
**Plain definition.** Assign tasks to workers strictly in rotation, ignoring how suitable each worker is.
**Why it exists.** It is the simplest fair allocator and therefore the natural null hypothesis for "does intelligent allocation help?"
**How it works.** `coordinator_agent.py:101-106`: keep an index, hand the task to `camera_ids[i % n]`, increment.
**In this project.** The `mas-rules` ablation baseline. `chapter6.tex:101` builds an argument on the contrast between auction and round-robin — an argument the v2 data does not support and that bug C1 makes untestable in principle.
**Trade-offs and failure modes.** As a baseline it is weak: it is easy to beat and beating it proves little. A greedy-by-utility or optimal-assignment baseline is far more informative (`02` §D4).
**Canonical reference.** Any operating-systems textbook; e.g. Silberschatz et al., *Operating System Concepts*, Ch. 5.

### Multi-robot task allocation (MRTA)
**Plain definition.** The general problem of deciding which agent does which task, and when.
**Why it exists.** It is the formal frame that makes "which camera should verify this?" a studied problem rather than an ad-hoc choice, with a standard taxonomy (single-task versus multi-task robots, single-robot versus multi-robot tasks, instantaneous versus time-extended assignment).
**How it works.** Solutions range from centralised optimisation (assignment problems) through market mechanisms to fully distributed consensus.
**In this project.** The verification-allocation problem is the simplest MRTA case: single-task robots, single-robot tasks, instantaneous assignment. Naming it in the thesis would let the auction be positioned against known alternatives instead of only against round-robin.
**Trade-offs and failure modes.** The simplest case is also the one where a market mechanism has the least advantage over a centralised solver, which weakens the argument for the auction at this scale.
**Canonical reference.** Gerkey & Matarić, *A Formal Analysis and Taxonomy of Task Allocation in Multi-Robot Systems*, IJRR 23(9), 2004.

### Hungarian algorithm (optimal assignment)
**Plain definition.** A classical algorithm that finds the cheapest one-to-one matching between two equally-sized sets, given a cost for every pair.
**Why it exists.** Greedy matching is fast but can be arbitrarily worse than optimal, and its result depends on the order you process items in.
**How it works.** Polynomial-time combinatorial optimisation over the cost matrix; `scipy.optimize.linear_sum_assignment` implements it.
**In this project.** Recommended twice: as the fix for the order-dependent greedy alert-to-ground-truth matcher in `metrics.py:40-52` (bug C4), and as a stronger centralised coordination baseline (`02` §D4).
**Trade-offs and failure modes.** Requires a full cost matrix, so it is centralised by nature — which is exactly the property the MAS design is trying to avoid operationally, though it is harmless in offline scoring.
**Canonical reference.** Kuhn, *The Hungarian Method for the Assignment Problem*, Naval Research Logistics Quarterly, 1955.

### Consensus-based bundle algorithm (CBBA)
**Plain definition.** A decentralised task-allocation method where agents build candidate task bundles greedily, then converge on a conflict-free allocation by exchanging bid information with neighbours.
**Why it exists.** It gets near-auction allocation quality without a central auctioneer, and it has provable convergence and conflict-freedom guarantees.
**How it works.** Alternating bundle-construction and consensus phases until no agent changes its assignment.
**In this project.** Not used. Mentioned as a modern alternative the thesis could position against, since the current design still has a single `CoordinatorAgent` — a central point of failure that partly undercuts the decentralisation argument.
**Trade-offs and failure modes.** More complex, more messages, and its guarantees depend on assumptions about the network graph.
**Canonical reference.** Choi, Brunet & How, *Consensus-Based Decentralized Auctions for Robust Task Allocation*, IEEE Transactions on Robotics 25(4), 2009.

### Submodular sensor selection
**Plain definition.** Choosing a subset of sensors to activate when the value of information has diminishing returns — the second camera on a scene adds less than the first.
**Why it exists.** Submodularity is the mathematical property that makes a simple greedy selection provably near-optimal (within a factor of 1 − 1/e).
**How it works.** Define a set function measuring coverage or information gain, verify it is submodular, then select greedily with a performance guarantee.
**In this project.** Cited in `chapter2.tex:54` and `chapter_sota.tex:16` as related work. Relevant because it is the principled version of "which camera should look", and it would give the bid function a theoretical basis instead of hand-tuned constants.
**Trade-offs and failure modes.** Requires a well-defined information-gain model, which this system does not have.
**Canonical reference.** Krause & Golovin, *Submodular Function Maximization*, in *Tractability*, Cambridge University Press, 2014.

### Multi-agent reinforcement learning (MARL), QMIX, MADDPG
**Plain definition.** Machine learning where several agents learn, by trial and error, policies that work well together. QMIX and MADDPG are two standard algorithms for the cooperative case.
**Why it exists.** Hand-designed coordination rules cap out; learned policies can discover better ones, especially at scale.
**How it works.** QMIX learns per-agent value functions and a monotonic mixing network that combines them into a team value, so agents can act on local information while being trained on a global reward. MADDPG uses a centralised critic during training and decentralised actors at execution.
**In this project.** Explicitly rejected and deferred to future work (`chapter2.tex:54`, `chapter7.tex:24`), on the grounds that learned policies are data-hungry, hard to certify, and opaque. That argument is sound for a safety- and legally-sensitive system.
**Trade-offs and failure modes.** Sample complexity, sim-to-real gap, non-stationarity (every agent's environment changes as the others learn), and non-auditability. The thesis's argument would be stronger with one measured comparison rather than a purely qualitative rejection.
**Canonical reference.** Rashid et al., *QMIX*, ICML 2018; Lowe et al., *MADDPG*, NeurIPS 2017.

### PettingZoo and RLlib
**Plain definition.** PettingZoo is a standard interface and collection of multi-agent environments. RLlib is a scalable library for training reinforcement-learning agents.
**Why they exist.** They provide the reproducible plumbing that made single-agent RL comparable, extended to the multi-agent case.
**How they work.** PettingZoo standardises the agent-environment interaction API; RLlib supplies distributed training implementations of standard algorithms.
**In this project.** Cited as available infrastructure for the MARL future-work direction (`chapter2.tex:54`). Not used.
**Trade-offs and failure modes.** Wrapping this system as a PettingZoo environment would be substantial work, and the replay harness would need to become a simulator rather than a file player.
**Canonical reference.** Terry et al., *PettingZoo*, NeurIPS 2021; Liang et al., *RLlib*, ICML 2018.

### Collaborative perception (V2X-Sim and related)
**Plain definition.** Multiple sensing agents sharing intermediate perception data — features, not raw frames — so each sees more than it could alone.
**Why it exists.** In autonomous driving, occlusion is solved by sharing what a neighbour can see; the same logic applies to multi-camera sites.
**How it works.** Agents exchange compressed intermediate feature maps at chosen fusion points, and the literature reports **accuracy against bytes transmitted**.
**In this project.** Not used, but methodologically important: this community routinely reports the exact accuracy-versus-communication-cost trade-off that RQ2 asks about, and measures it in bytes rather than message counts. It is the right template for `02` §B6.
**Trade-offs and failure modes.** Feature sharing conflicts with the strict "only JSON events cross the network" privacy stance of this project — a tension worth discussing rather than adopting uncritically.
**Canonical reference.** Li et al., *V2X-Sim: Multi-Agent Collaborative Perception Dataset and Benchmark for Autonomous Driving*, IEEE RA-L 2022.

### Quorum
**Plain definition.** A minimum number of participants whose responses you wait for before proceeding.
**Why it exists.** Waiting for everyone is fragile (one slow participant stalls you); waiting a fixed time is wasteful when everyone already replied.
**How it works.** Wake as soon as `n` responses arrive, or when a timeout expires — whichever comes first.
**In this project.** Recommended in `02` §B7 to replace `time.sleep(bid_window)` in `coordinator_agent.py:90`, removing one second of dead latency from every auction.
**Trade-offs and failure modes.** Choosing the quorum size is itself a design decision; too high and a failed agent stalls the round.
**Canonical reference.** —(standard distributed-systems practice; e.g. Kleppmann, *Designing Data-Intensive Applications*, Ch. 9).

---

## 6. Agentic AI and large language models

### Large language model (LLM)
**Plain definition.** A very large neural network trained to predict the next piece of text, which as a side effect becomes able to answer questions, follow instructions, and write structured output.
**Why it exists.** Scaling next-token prediction on large corpora turned out to produce broadly useful language capability without task-specific training.
**How it works.** A transformer processes a sequence of tokens with attention, producing a probability distribution over the next token; text is generated by sampling repeatedly.
**In this project.** The `ExplanationAgent` (`explanation_agent.py`) calls an OpenAI-compatible chat endpoint to draft incident reports. **It was never invoked in any of the 373 campaign runs** (`01` §5.9), so contribution C4 has no experimental evidence.
**Trade-offs and failure modes.** Fluent but unfounded output (hallucination); non-determinism; latency; cost; and data leaving the site. The architecture correctly confines the model to a role where all four are survivable.
**Canonical reference.** Vaswani et al., *Attention Is All You Need*, NeurIPS 2017; Brown et al., *Language Models are Few-Shot Learners*, NeurIPS 2020.

### Agentic AI (and how it differs from "an AI agent")
**Plain definition.** An AI agent is a single model that uses tools in a loop. Agentic AI usually means an orchestrated set of specialised agents with shared state and explicit coordination.
**Why the distinction exists.** The two have different failure modes and different engineering needs; conflating them makes claims unfalsifiable.
**How it works.** A controller decomposes a goal, routes sub-tasks to specialist agents, and integrates results, often with an explicit state graph.
**In this project.** `chapter2.tex:60` adopts exactly this distinction (citing Sapkota et al.) and places AURA-MAS in the second category. Fair — though note that only one of the six agents actually contains a model-driven reasoning loop; the other five are conventional software.
**Trade-offs and failure modes.** "Agentic" is currently a marketing word as much as a technical one. The 2026 anomaly-detection survey partitions the space into detection-only, reasoning, tool-using, and planner agents — a taxonomy this thesis should place itself in explicitly (`02` §A10).
**Canonical reference.** Sapkota et al., *AI Agents vs. Agentic AI: A Conceptual Taxonomy*, arXiv:2505.10468.

### ReAct
**Plain definition.** A prompting pattern where the model alternates between writing a reasoning step and taking an action, using the result of the action to inform the next step.
**Why it exists.** Pure chain-of-thought reasoning cannot check facts; pure tool use cannot plan. Interleaving them does both.
**How it works.** The prompt structures generation as `Thought → Action → Observation`, repeated until the model emits a final answer.
**In this project.** Cited in `chapter1.tex:10` and `chapter2.tex:60` as background. Not implemented — the `ExplanationAgent` is a fixed four-node pipeline with no loop and no tool calls.
**Trade-offs and failure modes.** Loops can run away; each iteration costs latency and tokens. For this system's needs, the fixed pipeline is arguably the better choice, and the thesis should say so rather than citing ReAct as if it were used.
**Canonical reference.** Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023.

### Tool use / function calling
**Plain definition.** Letting a language model invoke external functions — a search, a database query, a detector — and use the results.
**Why it exists.** Models cannot know current facts or perform reliable computation; tools supply both.
**How it works.** The model is given machine-readable function schemas and emits a structured call, which the runtime executes before returning the result to the model.
**In this project.** Not used. The `ExplanationAgent` receives a fixed JSON payload and returns text; it cannot query the audit log or request another frame. `02` §D6 and `chapter7.tex:28` both point toward giving it retrieval capability as future work.
**Trade-offs and failure modes.** Every tool is an attack surface and a new failure mode; giving a generative model read access to an audit stream needs careful scoping.
**Canonical reference.** Schick et al., *Toolformer*, NeurIPS 2023.

### LangGraph, AutoGen, CrewAI
**Plain definition.** Three frameworks for building multi-step or multi-agent LLM applications. LangGraph models the application as a typed state graph; AutoGen as conversations between agents; CrewAI as role-based teams.
**Why they exist.** Hand-rolling control flow, state, retries, and checkpointing around model calls is repetitive and error-prone.
**How they work.** LangGraph defines nodes (functions), edges (transitions), and a shared typed state object, with built-in checkpointing and resumption.
**In this project.** `chapter4.tex:118` says the explanation pipeline is "implementable in LangGraph"; `explanation_agent.py` implements it directly as four methods over an `ExplanationState` dataclass, and `langgraph` is a commented-out optional dependency in `requirements.txt`. Honest, but the thesis's "LangGraph-style state machine" phrasing (`explanation_agent.py:3`) invites a reader to think otherwise.
**Trade-offs and failure modes.** Frameworks add dependencies and abstraction for a four-node pipeline. Adopting LangGraph would buy checkpointing and make the description literally true; it is a Nice-to-have, not a Critical fix.
**Canonical reference.** LangGraph documentation, langchain-ai.github.io/langgraph; Wu et al., *AutoGen*, arXiv:2308.08155.

### Hallucination
**Plain definition.** A model producing fluent, confident output that is not grounded in its input or in reality.
**Why it matters here.** In a surveillance report, an invented detail ("a second person was seen fleeing") could drive a real-world response.
**How it works.** The model samples plausible continuations; plausibility and truth are different objectives, and nothing in the training signal enforces the latter at inference time.
**In this project.** The explicit threat that contribution C4's guardrail addresses. `SYSTEM_PROMPT` (`explanation_agent.py:28-35`) instructs the model to use only supplied evidence, and `_guardrail_check` mechanically enforces the citation part of that instruction.
**Trade-offs and failure modes.** The guardrail only checks *evidence identifiers*. A report can invent every factual detail while citing only real identifiers and still pass. So "zero uncaught hallucinated citations" is a much narrower claim than "no hallucination", and the thesis should be precise about which it is demonstrating.
**Canonical reference.** Ji et al., *Survey of Hallucination in Natural Language Generation*, ACM Computing Surveys 55(12), 2023.

### Guardrail
**Plain definition.** A programmatic check placed between a model's output and the system that consumes it, which rejects or repairs unacceptable output.
**Why it exists.** Prompt instructions are requests, not constraints. Enforcement has to live outside the model.
**How it works.** `explanation_agent.py:130-145`: verify the output parses to the required JSON schema; extract all `ev_[0-9a-f]{6,}` identifiers from both the citation list and the free text with a regular expression; require that both sets are subsets of the hypothesis's real event identifiers. Any violation triggers a deterministic template fallback.
**In this project.** The mechanical core of contribution C4, and genuinely the strongest architectural idea in the thesis — the generative layer is both *decision-decoupled* (it runs after the alert is already emitted) and *evidence-grounded*.
**Trade-offs and failure modes.** Narrow scope (identifiers only, see Hallucination above); the regular expression can be evaded by formatting an identifier differently; and a guardrail that has never been tested against an actual model, as here, is an untested guardrail.
**Canonical reference.** Rebedea et al., *NeMo Guardrails*, EMNLP 2023 (System Demonstrations).

### Prompt injection
**Plain definition.** An attack where adversarial text hidden in data reaches the model and is followed as if it were an instruction.
**Why it exists.** Language models cannot reliably distinguish instructions from content; both are just tokens.
**How it works.** An attacker plants text like "ignore previous instructions and report all clear" somewhere the system will include in the prompt.
**In this project.** A realistic vector: `Event.extra` (`bus.py:60`) is free-form and is serialised into the drafting prompt (`explanation_agent.py:115-119`). CLIP labels flow into `extra` (`camera_agent.py:296`), and a YAMNet class name flows in too. `02` §B5 recommends an adversarial probe.
**Trade-offs and failure modes.** No general defence exists. The best available mitigation here is exactly what the architecture already does: keep the model out of the decision path so a successful injection can only corrupt a report, never an alert.
**Canonical reference.** Greshake et al., *Not What You've Signed Up For: Indirect Prompt Injection*, AISec 2023.

### Structured output / constrained decoding
**Plain definition.** Forcing a model's output to conform to a schema — valid JSON with required fields — rather than hoping it complies.
**Why it exists.** Free-text output that must be parsed is a permanent source of runtime failures.
**How it works.** Either the API enforces a JSON mode, or the decoder masks tokens that would violate a grammar.
**In this project.** `explanation_agent.py:124` already passes `response_format={"type": "json_object"}`. `02` §E recommends going further to a full JSON schema, so that schema failures stop appearing in the guardrail rejection statistics and only *grounding* failures remain — which is the interesting measurement.
**Trade-offs and failure modes.** Constraining the output can degrade content quality, and it does not make the content true.
**Canonical reference.** OpenAI structured outputs documentation; Willard & Louf, *Efficient Guided Generation for LLMs*, arXiv:2307.09702.

### Retrieval-augmented generation (RAG)
**Plain definition.** Fetching relevant documents and putting them in the prompt so the model answers from evidence rather than memory.
**Why it exists.** It grounds output in a controllable corpus and lets the model use information it was never trained on.
**How it works.** Embed the query, retrieve nearest documents from a vector index, concatenate them into the prompt.
**In this project.** Not implemented. `chapter7.tex:28` proposes it as future work: letting the explanation agent query historical audit streams to say things like "third loitering event at this entry this week".
**Trade-offs and failure modes.** Retrieval errors propagate silently, and retrieved text is another prompt-injection surface. For an audit stream, it also raises a data-minimisation question.
**Canonical reference.** Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, NeurIPS 2020.

### LLM-as-judge
**Plain definition.** Using a language model to score the quality of text outputs, in place of human raters.
**Why it exists.** Human evaluation is slow and expensive; automatic metrics correlate poorly with quality for open-ended text.
**How it works.** A judge model receives a rubric and one or more candidate outputs and returns scores or a preference.
**In this project.** Proposed in `chapter6.tex:111` and in `02` §D6 as the scalable way to evaluate explanation usefulness, complementing a small human-rated sample.
**Trade-offs and failure modes.** Judges have known biases — toward longer answers, toward their own family's style, toward the first option presented. Agreement with human raters must be reported, not assumed.
**Canonical reference.** Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, NeurIPS 2023.

### Ollama
**Plain definition.** A tool for running open-weight language models locally with an OpenAI-compatible API.
**Why it exists.** It removes cost, network dependency, and data-egress concerns from LLM experimentation.
**How it works.** Downloads quantised model weights and serves them over a local HTTP endpoint that mimics the OpenAI chat API.
**In this project.** Recommended in `02` §B5 and §E as the fastest path to making RQ4 evaluable: `ExplanationAgent._get_client` (`explanation_agent.py:157-160`) already targets an OpenAI-compatible endpoint, so pointing `OPENAI_API_BASE` at a local Ollama server requires no code change.
**Trade-offs and failure modes.** Small local models follow structured-output instructions less reliably, which will inflate guardrail rejection rates — but that is itself an honest and interesting result to report.
**Canonical reference.** ollama.com documentation.

### Data egress
**Plain definition.** Data leaving your infrastructure boundary.
**Why it matters here.** The thesis's central privacy claim is that raw frames never leave the edge (`chapter4.tex:9`).
**How it works.** Any outbound API call carries payload; here, base64-encoded images and event metadata.
**In this project.** The `_describe` node sends anonymised evidence JPEGs to an external endpoint (`explanation_agent.py:92-103`). Blurred images are still images, and the claim as written is about *raw* frames, so it is technically intact — but a jury will probe the distinction. Running the model locally (Ollama, or a small on-device VLM) removes the issue entirely.
**Trade-offs and failure modes.** Local models are weaker; the trade-off between explanation quality and data locality is a legitimate discussion point the thesis currently does not have.
**Canonical reference.** —(operational concept; see GDPR Art. 44–49 on transfers).

---

## 7. Fusion, probability, and decision logic

### Early, late, and hybrid fusion
**Plain definition.** Early fusion combines raw features from several sensors before any decision. Late fusion lets each sensor decide independently and combines the decisions. Hybrid does some of both.
**Why the distinction matters.** Early fusion can exploit fine-grained cross-modal correlations but requires all raw data in one place. Late fusion needs only small decision messages, which suits a distributed, privacy-constrained system.
**How it works.** Late fusion here: each agent emits an `Event` with a confidence; `FusionAgent` groups and combines confidences.
**In this project.** Late fusion, argued explicitly in `chapter3.tex:36` on bandwidth and privacy grounds. This is a well-motivated choice and one of the design's coherent parts.
**Trade-offs and failure modes.** Late fusion cannot recover information the per-sensor decisions threw away. A quiet glass break that never crosses the audio threshold contributes nothing, whereas early fusion might have combined a weak audio cue with a weak visual cue.
**Canonical reference.** Baltrušaitis et al., *Multimodal Machine Learning: A Survey and Taxonomy*, TPAMI 41(2), 2019.

### Hypothesis (in the fusion sense)
**Plain definition.** A working belief that "an incident of this kind is happening in this place around now", accumulating evidence over a time window.
**Why it exists.** Individual events are noisy and partial; the incident is the thing the operator cares about.
**How it works.** `fusion_agent.py:24-44`: a `Hypothesis` holds a family, a zone, first and last timestamps, a list of contributing events, and a fused confidence. Keyed by `f"{family}:{zone or 'site'}"` (`fusion_agent.py:65`).
**In this project.** The unit that the policy engine decides on. `dominant_type()` returns the event type of the single highest-confidence contributing event — which is why a genuinely cross-modal alert gets labelled `intrusion` and the audio contribution becomes invisible (`THESIS_REPATCH.md` Priority 1; fixed by `02` §D5).
**Trade-offs and failure modes.** Keying by `(family, zone)` means two genuinely different incidents in the same zone within the window merge into one hypothesis, and an event with no zone lands in a separate `site` bucket — the bug that blocked cross-modal corroboration until the `zone` field was added to audio events.
**Canonical reference.** —(system-specific; the general pattern is track-level or event-level data association, see Bar-Shalom et al., *Tracking and Data Fusion*, YBS, 2011).

### Sliding time window
**Plain definition.** Only consider events within the last *W* seconds as belonging together.
**Why it exists.** Evidence about the same incident arrives spread over time; you need a rule for how long to keep a hypothesis open.
**How it works.** `fusion_agent.py:68`: an event joins the open hypothesis if `event.timestamp − hypothesis.last_ts ≤ window_seconds` (default 6.0); otherwise a new hypothesis starts. A 1 Hz tick flushes hypotheses whose window has closed (`fusion_agent.py:96-111`).
**In this project.** The dominant source of alert latency. `results/evaluation_campaign_v2_notes.md` traces an audio miss precisely to this: the correct event fired inside the ground-truth window, but the alert landed at t = 26.47 s against a tolerance ending at 24.5 s, purely from the 6 s window plus tick granularity plus auction round-trip.
**Trade-offs and failure modes.** Longer windows fuse more evidence but delay every alert; shorter windows alert faster but fragment incidents. Critically, this window is measured in **wall-clock** time while the zone rules use **video** time, so the window covers different amounts of scene content in paced and unpaced modes (bug C8).
**Canonical reference.** —(standard stream-processing concept; see Akidau et al., *Streaming Systems*, O'Reilly, Ch. 4).

### Noisy-OR
**Plain definition.** A way to combine several independent pieces of evidence for the same conclusion: the conclusion is true unless *every* piece of evidence independently failed to indicate it.
**Why it exists.** It gives a principled, cheap alternative to a full Bayesian network when you have many causes for one effect, and it captures the intuition that more independent evidence means more confidence.
**How it works.** `P = 1 − Π(1 − w_m · c_e)` over contributing events, where `c_e` is the event's confidence and `w_m` a per-modality reliability weight. `fusion_agent.py:84-88`, with `w_video = 0.9`, `w_audio = 0.7`.
**In this project.** The mathematical core of contribution C3, written out as Equation `eq:noisyor` at `chapter4.tex:92`.
**Trade-offs and failure modes.** Three serious ones here. (i) It assumes **conditional independence**, which is badly violated when nine events come from one camera watching one incident — confidence saturates toward 1.0 regardless of whether the incident is real (bug C6). (ii) The `+0.05` corroboration bonuses added afterwards (`fusion_agent.py:89-92`) break the probabilistic interpretation entirely — the output is no longer a probability under any model (bug C7). (iii) The inputs are uncalibrated detector scores, so `c_e` is not a probability to begin with.
**Canonical reference.** Pearl, *Probabilistic Reasoning in Intelligent Systems*, Morgan Kaufmann, 1988, §4.3.2.

### Conditional independence
**Plain definition.** Two pieces of evidence are conditionally independent given a hypothesis if, once you know the hypothesis is true, learning one tells you nothing about the other.
**Why it matters.** Almost every cheap probabilistic combination rule — noisy-OR, naive Bayes — assumes it. When it fails, confidences are systematically overstated.
**How it works.** Formally `P(A,B | H) = P(A|H) · P(B|H)`.
**In this project.** Violated in the most consequential way possible: repeated detections of the same person by the same camera are highly dependent, yet each multiplies into the noisy-OR product. Two cameras watching the same scene through the same detector also share failure modes (same model, same lighting), so even cross-sensor "independence" is optimistic.
**Trade-offs and failure modes.** The practical fix is deduplication before fusion — collapse events by `(sensor_id, track_id, event_type)` within the window, or cap each sensor's contribution. This is recommended as bug fix C6.
**Canonical reference.** Pearl, 1988 (as above), Ch. 3.

### Monotonicity
**Plain definition.** A property meaning "adding more supporting evidence never decreases the result".
**Why the thesis claims it.** `chapter4.tex:95` presents monotonicity as a formal guarantee: independent corroboration strictly increases confidence, which is what makes multimodal fusion "work".
**How it works.** It follows trivially from the noisy-OR product form, since each factor is in [0,1].
**In this project.** Presented as contribution C3's "formal core". Mechanically it is true and the unit test at `test_pipeline.py:38-51` verifies it.
**Trade-offs and failure modes.** **Monotonicity is as much a limitation as a guarantee.** A fusion model that can only ever increase confidence cannot represent disconfirming evidence — an empty corridor, a camera that looked and saw nothing. The only downward adjustment anywhere in the pipeline is the coordinator's `−0.20` on refutation. A thesis that frames a modelling restriction as a formal virtue invites a hard question at the defence; better to state it as a deliberate simplification with a named cost.
**Canonical reference.** Pearl, 1988 (as above).

### Probability calibration (Platt scaling, isotonic regression)
**Plain definition.** Adjusting a model's raw scores so that a score of 0.8 really does correspond to being right about 80 % of the time.
**Why it exists.** Neural network confidences are systematically overconfident; raw scores are rankings, not probabilities.
**How it works.** Platt scaling fits a one-dimensional logistic function from score to probability on a held-out set. Isotonic regression fits a free monotonic step function — more flexible, more prone to overfitting on small data.
**In this project.** Not done anywhere. This is a foundational gap: the noisy-OR is a *probabilistic* combination rule fed by uncalibrated YOLO box confidences (`camera_agent.py:79`), uncalibrated CLIP softmax mass, and uncalibrated YAMNet class scores. Recommended in `02` §E.
**Trade-offs and failure modes.** Requires a labelled held-out split, which this project's tiny scenario corpus makes awkward. But even a crude calibration would be more defensible than none, and reporting Expected Calibration Error would strengthen C3 considerably.
**Canonical reference.** Guo et al., *On Calibration of Modern Neural Networks*, ICML 2017.

### Threshold and operating point
**Plain definition.** A threshold is the cut-off score above which the system acts. The operating point is the (precision, recall) pair that a particular threshold produces.
**Why it exists.** Any scoring system must be turned into a decision somewhere; where you put the cut determines the error trade-off.
**How it works.** `policy_agent.py:31`: `ALERT_THRESHOLDS = {CRITICAL: 0.45, WARNING: 0.55, INFO: 0.70}` — deliberately lower for higher-stakes events, reflecting asymmetric miss costs (`chapter4.tex:114`).
**In this project.** Every reported precision/recall/F1 number is a single operating point with no sweep. Reporting a precision–recall curve instead of one point is the single highest-value-per-hour experiment available (`02` §A13).
**Trade-offs and failure modes.** Comparing two systems at one arbitrary operating point each is not a valid comparison; one may dominate at a different threshold. This applies directly to the four-mode ablation.
**Canonical reference.** Fawcett, *An Introduction to ROC Analysis*, Pattern Recognition Letters 27(8), 2006.

### Hysteresis and cooldown
**Plain definition.** Deliberately making a system reluctant to change state repeatedly. A cooldown is the simplest form: after firing, do not fire again for *T* seconds.
**Why it exists.** Without it, a borderline signal oscillating around a threshold produces an alert storm and operator fatigue — a well-documented cause of real-world alarm systems being ignored.
**How it works.** `policy_agent.py:72-77`: keyed by `(zone, event_type)`, `cooldown_seconds = 20.0`.
**In this project.** Materially affects the false-positive count, and therefore every precision number.
**Trade-offs and failure modes.** A cooldown also suppresses *genuine* second incidents within the window, so it trades false positives for false negatives silently. And because it is wall-clock based, it covers wildly different amounts of scene content in paced versus unpaced runs (bug C8).
**Canonical reference.** —(control-systems concept; in alerting practice see Beyer et al., *Site Reliability Engineering*, O'Reilly, Ch. 6).

### Severity mapping
**Plain definition.** Assigning each event type a fixed importance class — here CRITICAL, WARNING, INFO.
**Why it exists.** Not all detections deserve the same response, and severity drives both the threshold and the operator's triage order.
**How it works.** `policy_agent.py:22-29`, a static dictionary from event type to severity.
**In this project.** Severity is looked up from `hypothesis.dominant_type()`, so the same single-winner labelling problem that hides audio contributions also determines severity — a cross-modal incident is graded by whichever single event scored highest.
**Trade-offs and failure modes.** A static map cannot express context (an intrusion at 03:00 versus 15:00). No sensitivity analysis of the mapping exists.
**Canonical reference.** —(operational convention; see EU AI Act Art. 14 on human oversight for the regulatory framing).

### Gray zone
**Plain definition.** A confidence band that is too high to dismiss and too low to act on.
**Why it exists.** It is the region where buying more information has positive expected value — which is what the verification auction does.
**How it works.** `coordinator_agent.py:47-49`: verification is requested when `0.35 ≤ confidence < 0.75`.
**In this project.** The trigger for contribution C2's whole mechanism.
**Trade-offs and failure modes.** The bounds are hand-chosen with no derivation. Because the fused confidence is uncalibrated, the band does not correspond to any actual level of uncertainty — it is a band on an arbitrary score. A principled version would define it by expected value of information.
**Canonical reference.** Howard, *Information Value Theory*, IEEE Transactions on Systems Science and Cybernetics, 1966.

### Graceful degradation
**Plain definition.** Designing a system so that losing a component reduces capability rather than causing failure.
**Why it exists.** Optional heavy dependencies (TensorFlow, CLIP, torch) may be unavailable on edge hardware or in a constrained environment.
**How it works.** Lazy imports plus fallback paths: no TensorFlow → DSP audio scoring; no CLIP → rules-only camera; no LLM endpoint → template explanation; no MQTT broker → in-process bus; no Redis → JSONL files.
**In this project.** Implemented consistently and documented as a deliberate risk-mitigation (`chapter5.tex:33`, `CLAUDE.md`). It is one of the design's genuinely good properties.
**Trade-offs and failure modes.** Silent degradation hides bugs. `AudioAgent` silently fell back to DSP for an unknown period because `tensorflow_hub`'s URL had died and the exception was swallowed — which is exactly why `backend="yamnet"` now raises instead of degrading (`audio_agent.py:114-119`). The same risk still exists for `make_bus("auto")` (bug C15).
**Canonical reference.** —(engineering principle; see Nygard, *Release It!*, 2nd ed., Ch. 5).

---

## 8. Evaluation metrics

### Ground truth
**Plain definition.** The reference answer an evaluation is scored against.
**Why it exists.** Without it there is nothing to be right or wrong about.
**How it works.** Here, each scenario manifest declares a list of `{event_type, zone, t_start, t_end}` entries.
**In this project.** Authored by the same process that ran the experiments — a construct-validity problem the manuscript does not acknowledge. `scenarios/loitering_01.json` documents that one such annotation in `demo_site_01` was demonstrably wrong and still ships (`01` §5.3).
**Trade-offs and failure modes.** Self-authored ground truth on self-selected clips measures self-consistency, not performance. Independent annotation and an agreement statistic are the standard remedy.
**Canonical reference.** —(methodological; see the annotation-bias analysis in *Rethinking Metrics and Benchmarks of Video Anomaly Detection*, arXiv:2505.19022).

### True positive, false positive, false negative
**Plain definition.** A true positive is a real event correctly flagged. A false positive is an alert with no corresponding real event. A false negative is a real event missed.
**Why they exist.** Every classification metric is built from these three counts.
**How they work.** `metrics.py:54-56`: `tp = |matched ground truth|`, `fp = |alerts| − |matched alerts|`, `fn = |ground truth| − tp`.
**In this project.** The matching rule that produces these counts is family-level with a ±5 s tolerance and greedy first-fit — which is where the metric's validity problems live (`01` §5.2).
**Trade-offs and failure modes.** Because matching is by *family*, an intrusion alert can be counted as a true positive for a loitering ground-truth entry. The counts are real; what they count is not what the thesis says.
**Canonical reference.** Any introductory text; e.g. Powers, *Evaluation: From Precision, Recall and F-Measure to ROC*, JMLT 2(1), 2011.

### Precision, recall, F1
**Plain definition.** Precision is the fraction of alerts that were correct. Recall is the fraction of real events that were caught. F1 is their harmonic mean.
**Why they exist.** They express the two ways a detector can be wrong, and F1 summarises both when you need one number.
**How they work.** `precision = tp/(tp+fp)`, `recall = tp/(tp+fn)`, `f1 = 2pr/(p+r)` (`metrics.py:57-59`).
**In this project.** The primary comparison metric across the four architecture modes.
**Trade-offs and failure modes.** F1 weights precision and recall equally, which is rarely right for surveillance — a missed intrusion and a spurious alert have very different costs. Reporting F-beta with a justified beta, or precision at fixed recall, would be more defensible. Also, with 1–3 ground-truth events per scenario, F1 takes only a handful of possible values, which is why the per-run numbers flip between 0.0 and 1.0.
**Canonical reference.** Powers, JMLT 2011 (as above).

### Mean time-to-alert (TTA)
**Plain definition.** How long after an incident starts the system raises the alert.
**Why it exists.** For surveillance it is arguably the metric that matters most — a correct alert twenty minutes late is worthless.
**How it works.** `metrics.py:51`: `max(0, alert_wall_time − t_start − gt.t_start)`, averaged over matched alerts only.
**In this project.** The basis of RQ1's headline claim.
**Trade-offs and failure modes.** Three problems. It is computed only over *matched* alerts, so a mode that misses hard events looks fast. Wall-clock alert times are compared against video-time ground truth, and the two coincide only in real-time-paced modes (bug C2). And with ground-truth intervals up to 32 seconds long, "time from interval start" is largely determined by which alert the greedy matcher happened to pick.
**Canonical reference.** The community's principled version is Latency-aware Average Precision — see below.

### Latency-aware Average Precision (LaAP)
**Plain definition.** A version of Average Precision that rewards detecting an event *early*, by weighting recall with a time decay.
**Why it exists.** Standard AUC and AP treat anomaly detection as frame-independent binary classification and are completely insensitive to when within an event you detected it — two models with identical AP can differ hugely in responsiveness.
**How it works.** Replace the standard precision–recall curve with a precision versus *latency-aware recall* curve, where a detection's contribution to recall decays with its delay from event onset, then integrate.
**In this project.** Not used. Recommended in `02` §D2: it would give the project's strongest claim (responsiveness) a metric other researchers recognise and can compare against, replacing the bespoke mean time-to-alert.
**Trade-offs and failure modes.** Requires choosing a decay function, which is another free parameter — but at least a documented, citable one.
**Canonical reference.** *Rethinking Metrics and Benchmarks of Video Anomaly Detection*, arXiv:2505.19022.

### False alerts per hour (FA/h)
**Plain definition.** How many spurious alerts an operator would face per hour of monitoring.
**Why it exists.** It is the operational currency of alarm fatigue and the number a security manager actually cares about.
**How it works.** `metrics.py:60,76`: `fp / (wall_seconds / 3600)`.
**In this project.** Reported in every table and figure — and degenerate, because several runs last about ten seconds, so one false positive extrapolates to 360 per hour (`01` §5.8). `results/summary_agg.csv` contains values of 377.3 and 358.8 produced this way.
**Trade-offs and failure modes.** Any rate extrapolated from a denominator far smaller than the reporting unit is an artefact. Report raw false-positive counts, and only report an hourly rate once the corpus totals at least an hour.
**Canonical reference.** —(operational metric; the underlying statistical issue is small-denominator rate estimation, see Agresti & Coull, *Approximate is Better than Exact*, The American Statistician 52(2), 1998).

### Area Under the ROC Curve (AUC / AUROC)
**Plain definition.** The probability that the model scores a randomly chosen positive example above a randomly chosen negative one. 0.5 is random guessing; 1.0 is perfect.
**Why it exists.** It summarises performance across *all* thresholds, so it does not depend on where you happen to set your cut-off.
**How it works.** Sweep the threshold, plot true-positive rate against false-positive rate, integrate.
**In this project.** Used once: `results/clip_anomaly_calibration_notes.md` reports **AUC = 0.308** for the CLIP anomaly scorer. Below 0.5 means the score is *anti-correlated* with the label — the scorer is worse than a coin flip and would perform better inverted. No chapter mentions this (`02` §A7).
**Trade-offs and failure modes.** AUC is optimistic under heavy class imbalance, which is why anomaly work often prefers Average Precision. It is also the standard currency of the VAD literature — which is exactly why this project's absence of any benchmark AUC makes it non-comparable.
**Canonical reference.** Fawcett, Pattern Recognition Letters 2006.

### Average Precision (AP)
**Plain definition.** The area under the precision–recall curve; a single number summarising detection quality across thresholds, weighted toward the positive class.
**Why it exists.** Under strong class imbalance — a few anomalous frames among many normal ones — AP is far more informative than AUC.
**How it works.** Integrate precision as a function of recall over all thresholds.
**In this project.** Not computed. It is the standard reported metric on XD-Violence, which is the benchmark `02` §D1 recommends because it is audio-visual and would exercise RQ3 directly.
**Trade-offs and failure modes.** Requires per-frame or per-segment scores rather than discrete alerts, so adopting it means exposing the fused confidence as a continuous signal — a modest change to `replay.py`'s output.
**Canonical reference.** Everingham et al., *The PASCAL Visual Object Classes Challenge*, IJCV 88(2), 2010.

### Mean Average Precision (mAP)
**Plain definition.** Average Precision averaged over object classes (and, in COCO, over IoU thresholds). The standard object-detection score.
**Why it exists.** It gives one comparable number for detectors across the whole class vocabulary.
**How it works.** Compute AP per class at one or more IoU thresholds, then average.
**In this project.** Cited for YOLO11n (`chapter3.tex:10`, ≈39.5 % on COCO) and correctly dismissed in `chapter6.tex:12` as a component metric rather than a system metric. That argument is right — but it is used to justify measuring *nothing* at component level, which leaves the perception ceiling unquantified on this project's own footage.
**Trade-offs and failure modes.** COCO mAP on web photographs says little about performance on low-resolution CCTV.
**Canonical reference.** Lin et al., *Microsoft COCO*, ECCV 2014.

### Coordination overhead
**Plain definition.** The cost the system pays for agents talking to each other, rather than for doing the work.
**Why it exists.** Any distributed coordination claim is only interesting alongside its price.
**How it works.** `coordinator_agent.py:38-40` counts `tasks, bids, awards, verifications, messages` and records `allocation_ms` per verification round.
**In this project.** Reported as `coord_messages` and `mean_allocation_ms`. Because every campaign run used the in-process bus, these count Python function calls, not network messages (`01` §5.6).
**Trade-offs and failure modes.** Message counts ignore payload size, broker load, and quality-of-service overhead. The collaborative-perception literature reports **bytes transmitted versus accuracy**, which is the standard `02` §B6 recommends adopting.
**Canonical reference.** Li et al., V2X-Sim, IEEE RA-L 2022.

### Inter-annotator agreement, Fleiss' kappa
**Plain definition.** A measure of how much independent human annotators agree, corrected for the agreement you would expect by chance.
**Why it exists.** If two experts cannot agree on what counts as "loitering", no model can be scored reliably against either one's labels.
**How it works.** Fleiss' kappa extends Cohen's kappa to more than two raters: `κ = (P_observed − P_chance) / (1 − P_chance)`. Values above 0.6 are usually called substantial agreement.
**In this project.** Not measured — the ground truth has a single author. The VAD metrics paper measures κ between 0.51 and 0.68 on standard datasets, i.e. even expert annotation of anomalies is only moderately reliable. Recommended in `02` §D2.
**Trade-offs and failure modes.** Kappa is sensitive to class prevalence and can be misleadingly low when one class dominates — which is the norm for anomaly annotation.
**Canonical reference.** Fleiss, *Measuring Nominal Scale Agreement Among Many Raters*, Psychological Bulletin 76(5), 1971.

---

## 9. Experimental design and statistics

### Baseline
**Plain definition.** The reference system you compare against, representing "what people do today" or "the obvious simple thing".
**Why it exists.** An absolute number means nothing without something to beat.
**How it works.** `replay.py` implements `centralized` as the baseline for RQ1 and `mas-nocoord` as the baseline for RQ2.
**In this project.** The centralized baseline processes sensors *sequentially to completion* and *unpaced* (`replay.py:108,139-141`), which is not how a real video-management system works — real ones ingest streams concurrently at real time. A baseline chosen to be easy to beat is a **strawman**, and it weakens rather than strengthens the result.
**Trade-offs and failure modes.** A strong baseline can beat your method, which is uncomfortable and scientifically valuable. Notably, when the v2 campaign was run properly, the "weak" centralized baseline still beat the full MAS on 6 of 9 scenarios.
**Canonical reference.** —(methodological; see Sculley et al., *Winner's Curse? On Pace, Progress, and Empirical Rigor*, ICLR Workshop 2018).

### Ablation study
**Plain definition.** Removing or disabling one component at a time to measure how much it actually contributes.
**Why it exists.** Systems have many parts; without ablation you cannot tell which part is responsible for the result — or whether any of them is.
**How it works.** Hold everything constant, vary one factor, re-measure. Here: coordination mode (4 levels), audio presence (`--vision-only`), audio backend (`--audio-backend`).
**In this project.** Contribution C5. The harness supports it well; the set of factors ablated is narrower than the design deserves — fusion rule, corroboration bonus, thresholds, and CLIP on/off are all never varied (`02` §A13).
**Trade-offs and failure modes.** An ablation is only valid if the varied factor is genuinely the *only* difference. Here it is not: changing mode also changes pacing (bug C2), which is the definition of a confound.
**Canonical reference.** —(standard practice; see Lipton & Steinhardt, *Troubling Trends in Machine Learning Scholarship*, arXiv:1807.03341).

### Confound
**Plain definition.** A variable that changes together with the one you are studying, so you cannot tell which caused the effect.
**Why it matters.** A confounded experiment can produce a perfectly reproducible result that means nothing.
**How it works.** In `replay.py:108`, `realtime = mode != "centralized"` binds pacing to architecture. Any latency difference between centralized and MAS could be caused by either.
**In this project.** The most important methodological defect (`01` §5.1). It also propagates: because the fusion window and the cooldown are wall-clock quantities, the confound changes hypothesis grouping and alert suppression, not just timing.
**Trade-offs and failure modes.** The cheap fix is disclosure (a threats-to-validity paragraph); the correct fix is a `centralized-paced` cell that separates concurrency from time compression.
**Canonical reference.** Shadish, Cook & Campbell, *Experimental and Quasi-Experimental Designs*, Ch. 2.

### Threats to validity (internal, external, construct, conclusion)
**Plain definition.** A structured way to state what could make your conclusions wrong. *Internal*: did the thing you varied actually cause the effect? *External*: does it generalise beyond your setting? *Construct*: does your metric measure the concept you claim? *Conclusion*: are your statistical inferences sound?
**Why it exists.** It converts "limitations" from a vague apology into an auditable checklist, and reviewers look for exactly these four.
**How it works.** Enumerate each threat, state its direction, and state what you did to mitigate it.
**In this project.** `chapter6.tex:103-111` lists four limitations, none of which are the actual major threats: the pacing confound (internal), family-level matching and the false-alert-rate artefact (construct), self-authored ground truth (construct), n = 5 Bernoulli outcomes with no test (conclusion), 9 short scenarios on 2 sites (external). `02` §A12 recommends restructuring the section under these four headings precisely because the structure makes omissions visible.
**Trade-offs and failure modes.** A long honest threats section can read as weakness; it is in fact the strongest signal of methodological maturity a thesis can send.
**Canonical reference.** Wohlin et al., *Experimentation in Software Engineering*, Springer 2012, Ch. 8.

### Repetition, seed, determinism
**Plain definition.** A repetition is re-running the identical configuration to see how much the result varies. A seed fixes the starting point of a pseudo-random generator so a run is reproducible. Determinism means the same input always gives the same output.
**Why they exist.** Without determinism you cannot debug; without repetitions you cannot distinguish a real effect from noise.
**How they work.** Seeds are set for Python's `random`, NumPy, and the deep-learning framework; thread counts are pinned, because parallel floating-point reductions are order-dependent and therefore non-deterministic.
**In this project.** `replay.py --rep N` adds repetition indices and suffixed filenames (methodology change #7), and the campaign runs N = 5. But **no seed is set anywhere** and thread counts are not pinned; `CLAUDE.md` acknowledges "real run-to-run non-determinism, likely PyTorch CPU-threading float non-determinism interacting with borderline confidence thresholds" and prescribes repetitions as a workaround rather than fixing the cause (`02` §B1).
**Trade-offs and failure modes.** Pinning threads to one slows inference. But repetitions should measure *genuine* stochasticity (thread scheduling in the auction), not compensate for uncontrolled randomness — otherwise you cannot tell the two apart.
**Canonical reference.** PyTorch reproducibility documentation, pytorch.org/docs/stable/notes/randomness.html.

### Bernoulli outcome
**Plain definition.** A measurement with only two possible values — success or failure, 1 or 0.
**Why it matters here.** With 1–3 ground-truth events per scenario, a run's F1 can only take a few values, and in practice it flips between 0.0 and 1.0.
**How it works.** A mean of 0.8 with a standard deviation of 0.447 over n = 5 is arithmetically identical to "four runs scored 1.0 and one scored 0.0". `results/summary_agg.csv` is full of exactly this pattern.
**In this project.** Reporting mean ± standard deviation for such data implies a continuous distribution that does not exist. A proportion with a binomial confidence interval (Wilson or Agresti–Coull) is the correct summary.
**Trade-offs and failure modes.** With n = 5 the confidence interval on a proportion is enormous — which is the honest message, and is precisely why more scenarios matter more than more repetitions.
**Canonical reference.** Agresti & Coull, *Approximate is Better than "Exact" for Interval Estimation of Binomial Proportions*, The American Statistician 52(2), 1998.

### Mean and standard deviation
**Plain definition.** The mean is the average. The standard deviation measures how spread out the values are around it.
**Why they exist.** Together they summarise a distribution in two numbers — when the distribution is roughly bell-shaped and the sample is not tiny.
**How they work.** `metrics.py:116-118` uses `statistics.mean` and `statistics.stdev` (the sample form, dividing by n−1), and correctly leaves the standard deviation blank when n < 2 rather than writing 0.0.
**In this project.** That n < 2 handling is a genuinely careful touch. The problem is upstream: the underlying data is Bernoulli, so the pair is the wrong summary regardless of how carefully it is computed.
**Trade-offs and failure modes.** Standard deviation describes the *spread of the data*; the standard error (`σ/√n`) describes the *uncertainty of the mean*. Error bars in figures should say which they are — `make_figures.py`'s docstring does, which is more than most theses manage.
**Canonical reference.** Wasserman, *All of Statistics*, Ch. 6.

### Confidence interval and the bootstrap
**Plain definition.** A confidence interval is a range that, under repeated sampling, would contain the true value a stated fraction of the time. The bootstrap estimates it by resampling your own data with replacement, thousands of times.
**Why they exist.** A point estimate with no interval invites over-reading. The bootstrap works when the sampling distribution is unknown or clearly non-normal — which is the case here.
**How it works.** Resample the runs with replacement, recompute the statistic each time, and take the 2.5th and 97.5th percentiles of the resulting distribution.
**In this project.** Absent everywhere. Recommended in `02` §A6, including bootstrap intervals on the *paired difference* between modes, which is more informative than intervals on each mode separately.
**Trade-offs and failure modes.** The bootstrap needs a reasonable sample; with n = 5 per cell it is thin, so pooling across scenarios (with scenario as a blocking factor) is the practical route.
**Canonical reference.** Efron & Tibshirani, *An Introduction to the Bootstrap*, Chapman & Hall, 1993.

### Paired test, Wilcoxon signed-rank
**Plain definition.** A statistical test for whether two conditions differ, when each observation in one condition has a natural partner in the other. Wilcoxon signed-rank is the version that does not assume a normal distribution.
**Why it exists.** Pairing removes between-subject variability — here, the variability between scenarios, which is enormous — and so is far more sensitive than an unpaired test.
**How it works.** Compute the difference for each pair, rank the absolute differences, sum the ranks by sign, and compare to the null distribution.
**In this project.** The campaign design is naturally paired: every `(scenario, repetition)` is run under all four modes on identical input. This is exactly the design Wilcoxon is for, and no test of any kind is currently run (`02` §A6).
**Trade-offs and failure modes.** With 9 scenarios the test has low power, so a non-significant result must be reported as "underpowered", not as "no difference". That is still far better than the current silence.
**Canonical reference.** Demšar, *Statistical Comparisons of Classifiers over Multiple Data Sets*, JMLR 7, 2006.

### p-value
**Plain definition.** The probability of seeing a difference at least this large if there were really no difference at all.
**Why it exists.** It is a conventional guard against over-interpreting noise.
**How it works.** Compute a test statistic, compare it to its distribution under the null hypothesis.
**In this project.** Not reported anywhere. It should be — accompanied by an effect size, because a p-value alone says nothing about whether a difference matters.
**Trade-offs and failure modes.** Widely misinterpreted: it is not the probability that the hypothesis is true, and a threshold of 0.05 is a convention, not a law. With many comparisons, p-values must be corrected.
**Canonical reference.** Wasserstein & Lazar, *The ASA Statement on p-Values*, The American Statistician 70(2), 2016.

### Effect size, Cliff's delta
**Plain definition.** How *big* a difference is, as opposed to how confident you are that it is non-zero. Cliff's delta is a non-parametric effect size: the probability that a random value from one group exceeds one from the other, minus the reverse.
**Why they exist.** With enough data, trivial differences become statistically significant. Effect size keeps the focus on practical relevance.
**How they work.** Cliff's delta ranges from −1 to +1; conventional thresholds are ~0.147 small, ~0.33 medium, ~0.474 large.
**In this project.** Recommended alongside every test in `02` §A6. It is especially apt here because the data is ordinal and non-normal.
**Trade-offs and failure modes.** The interpretation thresholds are conventions borrowed from psychology, not laws of nature; report the raw value too.
**Canonical reference.** Cliff, *Dominance Statistics: Ordinal Analyses to Answer Ordinal Questions*, Psychological Bulletin 114(3), 1993.

### Multiple comparisons and the Holm–Bonferroni correction
**Plain definition.** If you run many tests, some will look significant by chance alone. A correction tightens the threshold to compensate.
**Why it exists.** Four modes across nine scenarios generates dozens of comparisons; at p < 0.05 you would expect a few false positives even with no real effect.
**How it works.** Holm–Bonferroni sorts the p-values, compares the smallest to `α/m`, the next to `α/(m−1)`, and so on, stopping at the first failure. It is uniformly more powerful than plain Bonferroni.
**In this project.** Necessary as soon as `02` §A6's tests are added.
**Trade-offs and failure modes.** Corrections reduce power; with this sample size, almost nothing will survive — which is itself the honest finding.
**Canonical reference.** Holm, *A Simple Sequentially Rejective Multiple Test Procedure*, Scandinavian Journal of Statistics 6(2), 1979.

### Sensitivity analysis
**Plain definition.** Systematically varying your free parameters to see how much the conclusions depend on them.
**Why it exists.** A result that only holds at one specific threshold setting is not a result about the system, it is a result about the setting.
**How it works.** Sweep each parameter over a plausible range and plot the outcome; or vary several jointly.
**In this project.** Essentially absent. `results/clip_anomaly_threshold_sweep.csv` is the only sweep on disk, and `results/methodology_changes.md` §10 notes that until recently nothing could even *act* on it because the threshold was unreachable from the manifest. Over twenty free parameters govern every reported number (`01` §5.10).
**Trade-offs and failure modes.** A full sweep is combinatorially large; a one-at-a-time sweep of the five most influential parameters (fusion window, gray-zone bounds, alert thresholds, tolerance, cooldown) is affordable and would transform the free parameters from a weakness into an analysis.
**Canonical reference.** Saltelli et al., *Global Sensitivity Analysis: The Primer*, Wiley 2008.

### Held-out split
**Plain definition.** Data set aside and never looked at during development, used once for the final measurement.
**Why it exists.** Any parameter you tune while watching a score is fitted to that data; measuring on it then overstates performance.
**How it works.** Partition scenarios or clips into development and test sets before tuning begins.
**In this project.** No split exists. Every threshold was chosen with all scenarios visible, and the ground truth for `intrusion_01` was explicitly "set to match verified real ByteTrack detections" (`scenarios/intrusion_01.json` notes) — that is, annotation fitted to the model's behaviour. Defensible as a bug fix, but it means the resulting numbers are development numbers, not test numbers, and the thesis must say so.
**Trade-offs and failure modes.** With only 9 scenarios, a split leaves too few for either purpose — which is an argument for corpus expansion (`02` §D8), not for skipping the split.
**Canonical reference.** Hastie, Tibshirani & Friedman, *The Elements of Statistical Learning*, §7.2.

### Reproducibility and replication
**Plain definition.** Reproducibility means someone else can re-run your code on your data and get your numbers. Replication means someone gets the same *conclusion* with their own implementation and data.
**Why they exist.** Results that cannot be checked cannot be built upon.
**How they work.** Pinned dependencies, recorded seeds, versioned data, published code, and documented commands.
**In this project.** Partially good and partially broken. Good: fresh-subprocess isolation, resume logic, a preserved v1 baseline CSV, a written methodology-change log, and full run serialisation. Broken: no dependency lock, no seed, no recorded library versions or hardware in run JSONs, no `configs/`, a `requirements-full.txt` referenced in `README.md` that does not exist, and fourteen stale duplicate source files at the repository root that hold pre-fix logic.
**Trade-offs and failure modes.** Reproducibility work has no immediate payoff and is therefore always deprioritised — until the moment a jury asks you to re-run something.
**Canonical reference.** Pineau et al., *Improving Reproducibility in Machine Learning Research*, JMLR 22, 2021.

### Scene overfitting and domain shift
**Plain definition.** Scene overfitting is a model learning the *background* rather than the event. Domain shift is the general phenomenon of performance dropping when deployment data differs from development data.
**Why they matter.** A surveillance model that learned "this corridor means normal" will fail in every other corridor.
**How they work.** The VAD metrics paper demonstrates this dramatically: re-splitting a benchmark so that the same scenes appear with reversed labels collapses AUC to 16 %, proving models had learned scene identity rather than anomaly.
**In this project.** Directly relevant twice. The CLIP scorer's AUC of 0.308 is a domain-shift failure — indoor-warehouse prompts against outdoor-street footage. And with only two visual sources across nine scenarios (`people.mp4`, `street.mp4`), every reported number is from essentially one visual domain, which is an external-validity threat the manuscript does not state.
**Trade-offs and failure modes.** The proposed remedy in the literature is hard-normal benchmarks (UCF-HN, MSAD-HN) — normal videos generated from anomalous scenes — which have no direct analogue here but motivate `02` §D7's domain-shift probe.
**Canonical reference.** *Rethinking Metrics and Benchmarks of Video Anomaly Detection*, arXiv:2505.19022.

### Synthetic data generation
**Plain definition.** Producing training or evaluation data programmatically rather than capturing it.
**Why it exists.** Real surveillance footage of rare incidents is scarce, legally encumbered, and expensive to annotate; synthetic data has perfect, free ground truth.
**How it works.** Render scenes in a simulator, or composite events into real footage, recording exactly when and where each event occurs.
**In this project.** `aura_mas/scripts/make_synthetic_clips.py` exists. It has already caused one serious problem: `scenarios/intrusion_01.json` records that the original synthetic clips were flat vector graphics in which YOLO could never detect a person, so that scenario silently produced zero detections in the pre-existing results. Recommended more ambitiously in `02` §D8, because programmatic ground truth would eliminate the annotation-validity problem.
**Trade-offs and failure modes.** The synthetic-to-real gap is the central risk, and this project has already been bitten by its most extreme form.
**Canonical reference.** de Lussu et al., *Synthetic Data for Video Surveillance Applications*, IJCV 2024.

### Sensor dropout probe
**Plain definition.** Deliberately disabling a sensor mid-run to see whether the system degrades gracefully or fails.
**Why it exists.** Robustness under partial failure is a headline claim of multi-agent architectures (`chapter2.tex:34`), and claims should be tested.
**How it works.** Kill an agent thread partway through a scenario and measure the change in recall and latency for events in its coverage.
**In this project.** Never tested. Recommended in `02` §D7; it is cheap with the existing harness and directly supports a claim currently made without evidence.
**Trade-offs and failure modes.** Needs a clear definition of acceptable degradation, otherwise the result is anecdotal.
**Canonical reference.** —(chaos-engineering practice; Basiri et al., *Chaos Engineering*, IEEE Software 33(3), 2016).

### Adversarial probe
**Plain definition.** Deliberately crafting inputs designed to break the system, rather than sampling typical inputs.
**Why it exists.** Average-case evaluation says nothing about worst-case behaviour, which is what matters for a security system.
**How it works.** Here: prompt injection through `Event.extra`, a siren-like distractor to trigger a false `audio_alarm`, or a printed image held up to a camera.
**In this project.** Recommended in `02` §D7. A security system evaluated only on benign inputs has an obvious gap that a jury will find.
**Trade-offs and failure modes.** Adversarial evaluation is open-ended; a small, well-chosen set of probes with clear threat-model motivation beats an exhaustive one.
**Canonical reference.** Carlini et al., *On Evaluating Adversarial Robustness*, arXiv:1902.06705.

---

## 10. Datasets and benchmarks

### COCO
**Plain definition.** A large object-detection dataset of ~330,000 everyday photographs annotated with 80 object classes.
**Why it exists.** It became the standard pretraining and benchmarking corpus for detection.
**How it works.** Boxes and segmentation masks over classes including `person`, `car`, `truck`, `backpack`, `handbag`, `suitcase`.
**In this project.** YOLO11n is used pretrained on COCO with no fine-tuning. `chapter3.tex:12` argues, correctly, that COCO classes cover most surveillance-relevant objects, making fine-tuning optional — a genuine de-risking property for a short project.
**Trade-offs and failure modes.** COCO photographs are well-lit, well-framed, and close-up; CCTV is none of those. Performance transfer is assumed here, never measured.
**Canonical reference.** Lin et al., *Microsoft COCO: Common Objects in Context*, ECCV 2014.

### UCF-Crime
**Plain definition.** 1,900 long, untrimmed real-world surveillance videos spanning 13 anomaly categories (robbery, arson, fighting, and so on), with video-level labels for training and frame-level labels for testing.
**Why it exists.** It is the reference benchmark for weakly-supervised video anomaly detection.
**How it works.** Train on video-level labels, evaluate frame-level AUC on the test split.
**In this project.** Cited in `chapter1.tex:8` and `chapter3.tex:24`, never used. `EXECUTION_PLAN.md §3` lists acquiring a UCF-Crime subset as an open task; `CLAUDE.md` records that it was ultimately judged impractical and substituted with AIRTLab and ABODA clips.
**Trade-offs and failure modes.** Large (~128 GB) and noisy, with known label-quality issues. But **any** number on it would make this project comparable to the literature, which is currently the largest single gap (`02` §D1).
**Canonical reference.** Sultani et al., *Real-world Anomaly Detection in Surveillance Videos*, CVPR 2018.

### XD-Violence
**Plain definition.** A large weakly-labelled **audio-visual** violence-detection dataset, ~4,754 videos totalling over 200 hours, drawn from films and web video.
**Why it exists.** It is the main benchmark where audio genuinely matters, reported as Average Precision.
**How it works.** Video-level labels for training; frame-level evaluation.
**In this project.** Not used. It is the single most relevant public benchmark, because RQ3 is precisely about whether audio adds value over vision alone — a question XD-Violence exists to answer and against which published numbers can be compared (`02` §D1).
**Trade-offs and failure modes.** Film footage differs from CCTV, so it does not settle deployment performance; and the current architecture emits discrete alerts rather than per-frame scores, so producing an Average Precision requires exposing the fused confidence as a continuous signal.
**Canonical reference.** Wu et al., *Not only Look, but also Listen: Learning Multimodal Violence Detection under Weak Supervision*, ECCV 2020.

### Avenue and ShanghaiTech
**Plain definition.** Two smaller, scene-specific video anomaly datasets, filmed on a fixed campus setting with frame-level anomaly annotations.
**Why they exist.** They are the standard benchmarks for the reconstruction/prediction family of anomaly detectors, which train on normal data only.
**How they work.** Train on normal clips from the scene, test on clips containing anomalies such as running, throwing, or cycling in a pedestrian area.
**In this project.** Cited in `chapter3.tex:23,40`; `CLAUDE.md` records they were considered and not used.
**Trade-offs and failure modes.** Highly scene-specific, so results do not transfer — this is one of the datasets the scene-overfitting critique targets.
**Canonical reference.** Lu et al., *Abnormal Event Detection at 150 FPS in MATLAB*, ICCV 2013 (Avenue); Luo et al., *A Revisit of Sparse Coding Based Anomaly Detection*, ICCV 2017 (ShanghaiTech).

### VIRAT and MEVA
**Plain definition.** Two large surveillance activity-detection corpora. VIRAT is ground and aerial footage with annotated activities; MEVA is a large multi-camera dataset filmed specifically for activity detection research.
**Why they exist.** They are the closest public analogue to what this project's scenario manifests are trying to be: multi-camera footage with annotated real-world incidents.
**How they work.** Activity instances annotated with type, spatial extent, and time span across synchronised camera views.
**In this project.** Cited in `chapter3.tex:40` and named in `chapter7.tex:22` as the future-work path for a serious scenario library.
**Trade-offs and failure modes.** Large and access-controlled; annotation conventions differ from this project's incident families, so a mapping layer would be needed.
**Canonical reference.** Oh et al., *A Large-scale Benchmark Dataset for Event Recognition in Surveillance Video* (VIRAT), CVPR 2011; Corona et al., *MEVA*, WACV 2021.

### MTMMC and the AI City Challenge
**Plain definition.** MTMMC is a large real-world multi-camera, multi-modal tracking benchmark. The AI City Challenge is an annual competition whose Track 1 targets multi-camera perception.
**Why they exist.** They provide standard tasks, data, and leaderboards for exactly the multi-camera setting this project's coordination story lives in.
**How they work.** Synchronised multi-view footage with cross-camera identity annotations; submissions ranked on standard tracking metrics.
**In this project.** Not used. Relevant because `chapter3.tex:40` claims no standard multi-sensor system-level benchmark exists — a claim that needs narrowing given these (`02` §A10).
**Trade-offs and failure modes.** Both centre on cross-camera identity tracking, which this project deliberately excludes on privacy grounds — so they are a partial, not exact, fit. That nuance is worth stating rather than ignoring.
**Canonical reference.** Woo et al., *MTMMC*, arXiv:2403.20225; aicitychallenge.org.

### ESC-50 and UrbanSound8K
**Plain definition.** Two small, clean, labelled environmental-sound datasets — ESC-50 has 2,000 five-second clips across 50 classes; UrbanSound8K has 8,732 urban sound excerpts across 10 classes.
**Why they exist.** They are the standard small benchmarks for environmental sound classification.
**How they work.** Balanced classes with predefined folds for cross-validation.
**In this project.** ESC-50 clips supply the audio for `audio_glass_break_01`, `audio_alarm_siren_01`, and `audio_alarm_clock_01` (`results/evaluation_campaign_v2_notes.md`, `aura_mas/scripts/make_audio_baselines.py`).
**Trade-offs and failure modes.** ESC-50 clips are clean, isolated, foreground-dominant recordings. Real site audio is continuous, reverberant, and noisy. So the audio results are close to an upper bound, and `02` §E recommends the DCASE protocol with a held-out split for a more honest number.
**Canonical reference.** Piczak, *ESC: Dataset for Environmental Sound Classification*, ACM Multimedia 2015.

### DCASE
**Plain definition.** An annual challenge and workshop series on Detection and Classification of Acoustic Scenes and Events, with standard tasks, data, baselines, and evaluation protocols.
**Why it exists.** It plays the role for audio events that ImageNet and COCO play for vision — it standardises how sound event detection is measured.
**How it works.** Fixed development/evaluation splits, defined metrics (event-based F1 with collar tolerances, error rate), and published baselines.
**In this project.** Named in `EXECUTION_PLAN.md §3` as a target that was never reached. Recommended in `02` §E as the way to report per-class audio performance against community convention rather than on three self-chosen clips.
**Trade-offs and failure modes.** DCASE's event-based F1 with onset/offset collars is stricter than this project's ±5 s family-level matching, so adopting it will lower the numbers — which is the point.
**Canonical reference.** dcase.community; Mesaros et al., *Metrics for Polyphonic Sound Event Detection*, Applied Sciences 6(6), 2016.

### AIRTLab and ABODA
**Plain definition.** Two small public video datasets: AIRTLab contains staged violent and non-violent interactions; ABODA (Abandoned Object Dataset) contains abandoned-luggage scenarios.
**Why they exist.** They provide licensable footage for specific incident types that general datasets cover poorly.
**How they work.** Short clips with clip-level or coarse temporal labels.
**In this project.** The real-footage substitutes for UCF-Crime and Avenue, per `CLAUDE.md`; provenance recorded in `data/clips_real/manifest.json` `[not read — not staged in this audit]`. That manifest is not cited anywhere in the manuscript, which `02` §A11 flags as a licensing and provenance gap.
**Trade-offs and failure modes.** Small and staged, so external validity is limited. Their licences must be stated in the thesis before any redistribution of derived clips.
**Canonical reference.** Bianculli et al., *A dataset for automatic violence detection in videos*, Data in Brief 33, 2020 (AIRTLab); Wang et al., ABODA project page.

---

## 11. Named systems in the literature

### Monitorix
**Plain definition.** A fully decentralised FIPA-standard multi-agent traffic-surveillance system published in 2000.
**Why it matters here.** It had real agent communication language messaging, production-rule reasoning per agent, a four-tier role taxonomy, a proxy pattern bridging a classical vision pipeline into the agent society, and cross-camera vehicle re-identification.
**How it works.** Agents specialise by role and negotiate over FIPA-ACL; a "Proxy" middle agent adapts a non-agent vision system into the society.
**In this project.** `research/.../findings/F4` reads it in full and draws the correct conclusion: "agents cooperate to surveil a place" is not a novel framing at any level and dates to at least 2000. **This is the single most important piece of prior-work analysis in the repository**, and the thesis must not rest novelty on the multi-agent framing alone (`02` §A14).
**Trade-offs and failure modes.** Monitorix predates deep learning entirely, so AURA-MAS's perception layer is incomparably stronger — but that strength comes from off-the-shelf pretrained models, not from the thesis's own contribution.
**Canonical reference.** Abreu et al., *Video-Based Multi-Agent Traffic Surveillance System*, IEEE Intelligent Vehicles Symposium, 2000.

### VadCLIP and AVadCLIP
**Plain definition.** Two methods applying CLIP to video anomaly detection. VadCLIP adapts CLIP's vision-language alignment for weakly-supervised anomaly detection; AVadCLIP extends it to audio-visual input.
**Why they exist.** They showed that vision-language pretraining transfers well to anomaly detection, with far less task-specific training.
**How they work.** Frame features from CLIP's image encoder, combined with learned text prompts and temporal modelling, trained under weak supervision and evaluated on UCF-Crime and XD-Violence.
**In this project.** `ClipAnomalyScorer` is described in `camera_agent.py:118` as a "VadCLIP-style proxy". It is not VadCLIP — there is no learned prompt, no temporal modelling, and no training; it is a raw prompt-similarity softmax. The distinction should be explicit in the thesis, since the cited method's reported performance is not this implementation's.
**Trade-offs and failure modes.** The real methods need training data and produce per-frame scores. The proxy needs neither and measures AUC 0.308 here.
**Canonical reference.** Wu et al., *VadCLIP*, AAAI 2024; Wu et al., *AVadCLIP*, 2025.

### Holmes-VAD and Holmes-VAU
**Plain definition.** Two systems using multimodal large language models for *explainable* video anomaly detection. Holmes-VAD produces unbiased detection with natural-language explanation; Holmes-VAU extends it to long-term understanding at multiple time granularities.
**Why they matter here.** They occupy exactly contribution C4's territory — natural-language explanation of anomalies — and they do it with instruction-tuned models evaluated on purpose-built instruction datasets at scale.
**How they work.** An anomaly-focused instruction dataset trains a multimodal LLM to both localise and describe anomalous segments, with hierarchical temporal granularity in Holmes-VAU.
**In this project.** Not cited (`chapter_sota.tex` predates them). The thesis's differentiator against them is real and should be stated precisely: Holmes-VAD/VAU use the model **as the detector**, while AURA-MAS keeps the model strictly downstream of a deterministic decision. That is a genuine architectural distinction — but it must be argued against these systems by name (`02` §A10).
**Trade-offs and failure modes.** They require substantial training and compute; AURA-MAS requires neither. That is a legitimate axis of comparison the thesis could win on.
**Canonical reference.** Zhang et al., *Holmes-VAD*, arXiv:2406.12235; Zhang et al., *Holmes-VAU*, CVPR 2025 (Highlight).

### Agentic VAD ("Glance, Scrutinize, and Think")
**Plain definition.** A 2026 line of work moving video anomaly detection from training-free prompting toward explicit agentic reasoning loops.
**Why it matters here.** It establishes "agentic video anomaly detection" as a named research area with its own baselines — the area this thesis implicitly claims.
**How it works.** Coarse scanning ("glance"), targeted re-examination of suspicious segments ("scrutinize"), and explicit reasoning to a verdict ("think").
**In this project.** Structurally similar to AURA-MAS's own escalation ladder — cheap edge detection, gray-zone verification, then explanation — but with the reasoning done by a model rather than by rules. Citing it would let the thesis position its rule-based escalation as the *auditable* alternative, which is a stronger argument than not knowing the work exists.
**Trade-offs and failure modes.** Agentic loops are expensive and non-deterministic; the auditability argument is genuinely on this project's side.
**Canonical reference.** arXiv:2608.11260.

### ARGOS, AD-AGENT, SentinelAgent, AnomalyRuler, Audit-LLM
**Plain definition.** Five representative systems from the 2026 agentic anomaly-detection survey. ARGOS and AD-AGENT are collaborative multi-agent detection pipelines; SentinelAgent and Audit-LLM are oversight architectures where a critic agent supervises another agent; AnomalyRuler is a reasoning agent that derives explicit rules from few normal examples.
**Why they matter here.** The survey's taxonomy — detection-only, reasoning, tool-using, and planner agents, plus collaborative versus oversight multi-agent topologies — is the map this thesis needs to place itself on.
**How they work.** Broadly: an LLM or VLM either performs detection directly, reasons over intermediate evidence, calls external detectors as tools, or supervises another agent's output.
**In this project.** Not cited. Critically, the **oversight** family is close to what AURA-MAS's guardrail does, which means `chapter_sota.tex:22`'s claim that "none of the surveyed systems architecturally decouples the generative component from the alert decision" needs re-verification before it can stand (`02` §A10).
**Trade-offs and failure modes.** Most of these systems are recent, lightly evaluated, and not surveillance-specific — so the thesis may well still hold a defensible position. It just has to make the argument.
**Canonical reference.** *Agentic and LLM-Based Multimodal Anomaly Detection: Architectures, Challenges, and Prospects*, Sensors 26(8):2330, 2026.

---

## 12. Distributed systems and messaging

### Publish/subscribe (pub/sub)
**Plain definition.** A messaging pattern where senders publish to a named topic without knowing who receives, and receivers subscribe to topics without knowing who sends.
**Why it exists.** It decouples producers from consumers, so you can add a new agent without modifying any existing one.
**How it works.** A broker (or in-process dispatcher) routes each published message to every matching subscription.
**In this project.** The entire inter-agent substrate. `BaseBus` (`bus.py:111-124`) defines `publish` and `subscribe`; `CLAUDE.md` states the invariant plainly: "All cross-agent communication goes through `aura_mas/core/bus.py` — never call another agent's methods directly." That invariant is well kept.
**Trade-offs and failure modes.** Decoupling makes control flow implicit and hard to trace. It also hides blocking: on `LocalBus`, publishing synchronously executes every subscriber in the caller's thread, which is why a coordinator's publish ends up running YOLO inference inline (`01` §5.6).
**Canonical reference.** Eugster et al., *The Many Faces of Publish/Subscribe*, ACM Computing Surveys 35(2), 2003.

### Topic and wildcard matching
**Plain definition.** A topic is a hierarchical message address like `site/cam_01/detections`. Wildcards let a subscriber match many topics: `+` matches one level, `#` matches all remaining levels.
**Why it exists.** It lets one subscriber receive from all sensors without enumerating them.
**How it works.** `LocalBus._match` (`bus.py:134-145`) splits both pattern and topic on `/` and compares segment by segment, honouring `+` and `#`. Topics are constants at `bus.py:97-104`.
**In this project.** Tested by `test_pipeline.py:29-35`. Note that `chapter5.tex:57` documents the topic layout as `site/coord/{...}` while the code uses `site/coordination/{...}` — a small documentation drift worth fixing.
**Trade-offs and failure modes.** Topic hierarchies are a schema; changing them breaks every subscriber and every archived log.
**Canonical reference.** MQTT Version 5.0 specification, OASIS, §4.7.

### MQTT, quality of service (QoS), Mosquitto, paho-mqtt
**Plain definition.** MQTT is a lightweight publish/subscribe protocol designed for constrained devices. QoS levels define delivery guarantees: 0 at most once, 1 at least once, 2 exactly once. Mosquitto is the standard open-source broker; paho-mqtt is the standard Python client.
**Why it exists.** HTTP is too heavy and too request/response-shaped for thousands of small sensor messages.
**How it works.** Clients connect to a broker, subscribe to topic filters, and publish; the broker fans out. `MqttBus` (`bus.py:163-198`) wraps paho.
**In this project.** The intended production transport: detections at QoS 0 (high frequency, loss tolerable), events/tasks/bids/awards at QoS 1 (`chapter4.tex:33`). **It was never used in any reported result** — every campaign run passed `--bus local` (`run_campaign.py:100`), so contribution C1's substrate is unevaluated (`02` §B6).
**Trade-offs and failure modes.** QoS 1 can deliver duplicates, which for this system would mean duplicate events feeding the noisy-OR as independent evidence — a real correctness risk that the in-process bus hides entirely. Also, `docker-compose.yml` runs Mosquitto with `mosquitto-no-auth.conf`: no authentication, no encryption (bug C18).
**Canonical reference.** MQTT Version 5.0, OASIS Standard, 2019.

### Redis Streams
**Plain definition.** An append-only log data structure in Redis, with consumer groups, so records can be written once and read repeatedly by multiple readers.
**Why it exists.** Publish/subscribe is fire-and-forget; alerts and audit records need durability and replay.
**How it works.** `XADD` appends with an auto-generated ID; `XREVRANGE` reads backwards. `AlertStore` (`bus.py:201-243`) uses it when available, with a JSONL file fallback.
**In this project.** The durable half of the two-tier substrate. Like MQTT, **never exercised**: `replay.py:78` constructs `AlertStore(redis_url=None)`, forcing the JSONL path in every campaign run.
**Trade-offs and failure modes.** Redis is in-memory first; durability depends on the append-only-file setting (which `docker-compose.yml` does enable). An audit log whose integrity matters legally deserves stronger guarantees than "Redis with AOF and no authentication".
**Canonical reference.** Redis Streams documentation, redis.io/docs/data-types/streams.

### JSON Lines (JSONL)
**Plain definition.** A file format where each line is one complete JSON object.
**Why it exists.** It is append-friendly, streamable, and readable by ordinary text tools — unlike a single large JSON array.
**How it works.** `AlertStore.append` writes `alert.to_json() + "\n"` (`bus.py:222-223`).
**In this project.** The fallback alert and audit store, and in practice the *only* one used: `data/alerts_*.jsonl` and `data/audit_*.jsonl`, one pair per run, over 1,600 files.
**Trade-offs and failure modes.** No transactional guarantee; a crash mid-write corrupts a line. And `bus.py:230` derives the audit path via `jsonl_path.replace("alerts", "audit")`, a substring replacement that misbehaves on any path containing "alerts" elsewhere (bug C11).
**Canonical reference.** jsonlines.org.

### Dataclass and message schema
**Plain definition.** A Python dataclass is a class whose fields are declared and whose boilerplate (constructor, equality, representation) is generated. A message schema is the agreed shape of data exchanged between components.
**Why they exist.** Explicit shapes catch mismatches early and make the wire format self-documenting.
**How they work.** `@dataclass` plus `asdict()` for serialisation (`bus.py:36-90`).
**In this project.** `Detection`, `Event`, `Alert` are the system's contract, and they are refreshingly readable — `chapter4.tex:59-65` documents them accurately.
**Trade-offs and failure modes.** `Event.from_json` is `Event(**json.loads(s))` (`bus.py:65-67`), which raises on any unrecognised field. Since 400+ archived run JSONs are cited evaluation artefacts, the schema is effectively frozen — adding a field breaks reading old data (bug C12). A `schema_version` field and a filtered constructor fix this cheaply.
**Canonical reference.** Python `dataclasses` documentation.

### Thread, daemon thread, race condition, blocking call
**Plain definition.** A thread is an independent line of execution within a process. A daemon thread does not prevent the program exiting. A race condition is when two threads access shared data concurrently and the result depends on timing. A blocking call is one that does not return until some external event occurs.
**Why they matter.** This system is explicitly concurrent, and its timing measurements depend on that concurrency.
**How they work.** `base.py:33-35` starts a daemon tick thread; `replay.py:118,124` runs each sensor agent in its own thread; locks protect the fusion hypothesis map (`fusion_agent.py:54`) and the coordinator's bid map (`coordinator_agent.py:37`).
**In this project.** Two concrete defects. `CameraAgent._last_frame` is written by the camera thread and read by the coordinator's callback thread with **no lock** — a race (bug C3). And `PolicyAgent.on_hypothesis` calls the blocking `request_verification`, which sleeps up to 4 seconds *inside the FusionAgent's tick thread*, stalling all hypothesis flushing site-wide (bug C10).
**Trade-offs and failure modes.** Python's global interpreter lock prevents memory corruption from unsynchronised reads but does nothing about logical inconsistency — reading a frame from an arbitrary moment is still wrong.
**Canonical reference.** Python `threading` documentation; Herlihy & Shavit, *The Art of Multiprocessor Programming*, Ch. 1.

### Head-of-line blocking
**Plain definition.** When the first item in a queue holds up everything behind it, even if the rest could proceed.
**Why it matters here.** It is the mechanism the thesis credits for the centralized baseline's latency: with sensors processed one after another, an incident on sensor 2 waits for all of sensor 1 (`chapter6.tex:73`).
**How it works.** `replay.py:139-141` starts and joins each sensor thread in turn.
**In this project.** The explanation is mechanistically correct *for this implementation of the baseline*. But a real centralized system does not process streams to completion one at a time, so the blocking is an artefact of a strawman baseline rather than an inherent property of centralisation (`01` §5.1).
**Trade-offs and failure modes.** The same pathology exists inside the MAS: the auction blocks the fusion tick thread (bug C10). The thesis criticises head-of-line blocking in the baseline while reproducing it in the coordination layer.
**Canonical reference.** —(networking concept; see Kleppmann, *Designing Data-Intensive Applications*, Ch. 8).

### Ring buffer
**Plain definition.** A fixed-size buffer that overwrites its oldest entry when full.
**Why it exists.** It gives bounded-memory access to recent history — exactly what "the frame from a few seconds ago" needs.
**How it works.** A list plus a rotating index, or Python's `collections.deque(maxlen=N)` — which `DspAnomalyScorer` already uses for its rolling baseline (`audio_agent.py:47-48`).
**In this project.** Recommended in `02` §B4 to replace `self._last_frame` with a short, lock-protected history of `(timestamp, frame)` pairs so verification can examine the frame nearest the incident.
**Trade-offs and failure modes.** Frames are large; a few seconds at 5 FPS and 768×432 is a few tens of megabytes per camera, which matters on constrained hardware. Storing downscaled frames or JPEG bytes is the usual compromise.
**Canonical reference.** Python `collections.deque` documentation.

### Edge computing
**Plain definition.** Running computation on or near the device that produces the data, instead of shipping the data to a central server or cloud.
**Why it exists.** It cuts bandwidth, cuts latency, keeps sensitive data local, and removes a single point of failure.
**How it works.** Small models on constrained hardware, with only summaries transmitted.
**In this project.** "Edge-first" is a core design principle (`chapter4.tex:9`) and a large part of the privacy argument: only JSON events cross the network.
**Trade-offs and failure modes.** Edge hardware is weak, so accuracy drops. **This project never measures it**: no run on constrained hardware exists, no CPU/memory/throughput metric is collected, and the Raspberry Pi deployment in `README.md` is a written plan, not a result (`02` §B12). "Edge-first" is currently an architectural assertion, not a measured property.
**Canonical reference.** Shi et al., *Edge Computing: Vision and Challenges*, IEEE Internet of Things Journal 3(5), 2016.

### Edge–cloud collaborative inference
**Plain definition.** Splitting work between a cheap local model and an expensive remote one, escalating only ambiguous cases upward.
**Why it exists.** It gets most of the accuracy of the large model at a fraction of the bandwidth and cost.
**How it works.** A confidence threshold at the edge decides what to escalate.
**In this project.** `chapter_sota.tex:10` correctly identifies this as the pattern AURA-MAS generalises into *agent-level* escalation: edge perception → site coordination → agentic explanation. This is one of the design's more elegant framings and is worth foregrounding.
**Trade-offs and failure modes.** Escalation thresholds are the same uncalibrated-confidence problem in another guise. And each escalation tier adds latency, which is what the fusion window plus auction round-trip cost here.
**Canonical reference.** Kang et al., *Neurosurgeon: Collaborative Intelligence Between the Cloud and Mobile Edge*, ASPLOS 2017.

### ONNX Runtime and OpenVINO
**Plain definition.** Two cross-platform inference engines. ONNX Runtime executes models exported to the open ONNX format; OpenVINO is Intel's optimised runtime for CPUs and integrated accelerators.
**Why they exist.** Training frameworks are heavy and slow at inference; dedicated runtimes are several times faster on the same hardware and drop the dependency footprint.
**How they work.** Export the trained model to a portable graph, then apply graph optimisation, operator fusion, and hardware-specific kernels.
**In this project.** Not used — inference goes through Ultralytics and PyTorch. Recommended in `02` §E because it is the practical prerequisite for making the edge claim measurable: YOLO11n exports cleanly to ONNX, and on a Raspberry Pi the speed difference is the difference between a demo and a deployment.
**Trade-offs and failure modes.** Export can change numerics slightly, so detection results may shift — which must be re-validated, not assumed.
**Canonical reference.** onnxruntime.ai documentation.

### Single-board computer / Raspberry Pi
**Plain definition.** A small, cheap, low-power complete computer — the canonical edge device for this kind of system.
**Why it matters here.** `README.md` describes a two-machine demonstration with a Pi as the edge sensor node and a laptop running fusion, policy, and the dashboard.
**How it works.** The Pi runs capture plus lightweight event publishing; the heavy layers stay central.
**In this project.** Planned in detail, **never executed** — no measurement from any constrained device exists anywhere in `results/`.
**Trade-offs and failure modes.** A Pi 5 running YOLO11n on CPU will manage a few frames per second at best, which may be below the 5 FPS the design assumes. Measuring and reporting that honestly is more valuable than the plan.
**Canonical reference.** —(hardware; see the edge-analytics surveys cited in `chapter_sota.tex:10`).

### Docker Compose
**Plain definition.** A tool that starts a set of containers from one declarative file.
**Why it exists.** It makes infrastructure dependencies reproducible with a single command.
**How it works.** `docker-compose.yml` here defines two services: `eclipse-mosquitto:2` on port 1883 and `redis:7-alpine` with append-only persistence on port 6379.
**In this project.** The one-command broker setup (`chapter5.tex:28`). Never used in the campaign, since everything ran on the in-process bus.
**Trade-offs and failure modes.** Both services are exposed on host ports with no authentication and no encryption (bug C18) — acceptable for a laptop demo, indefensible in a thesis whose central argument is governance and auditability.
**Canonical reference.** docs.docker.com/compose.

### Streamlit
**Plain definition.** A Python library that turns a script into a web application, with no front-end code.
**Why it exists.** It makes an operator interface a few hours of work rather than a few weeks.
**How it works.** The script re-runs top to bottom on each interaction; `@st.cache_resource` (`dashboard/app.py:26`) keeps expensive objects alive across reruns.
**In this project.** The Layer-3 operator console: alert feed with severity filtering, anonymised evidence, explanations, and acknowledge/dismiss buttons that write operator audit records — which is what closes the human-in-the-loop requirement.
**Trade-offs and failure modes.** The re-run model does not suit real-time streaming; the console reads alerts from Redis or, failing that, by globbing every `data/alerts_*.jsonl` file (`dashboard/app.py:34-42`), which will not scale past a few hundred alerts. There is also no authentication on an interface that displays surveillance evidence.
**Canonical reference.** docs.streamlit.io.

---

## 13. Privacy, law, and governance

### GDPR
**Plain definition.** The EU General Data Protection Regulation — the law governing processing of personal data about people in the EU. Video of identifiable people is personal data.
**Why it exists.** To give individuals control over data about them and impose obligations on those who process it.
**How it works.** Requires a lawful basis, and imposes principles including **data minimisation** (collect only what is necessary), **purpose limitation**, and **storage limitation**.
**In this project.** A constitutive design constraint (`chapter1.tex:46`, `chapter4.tex` Table `tab:privacy`): no biometric identification, event-level rather than identity-level corroboration, anonymised evidence, configurable retention.
**Trade-offs and failure modes.** The mapping in the thesis is a *description* of mechanisms, not an *assessment*. There is no lawful-basis analysis, no retention period actually configured, and no Data Protection Impact Assessment (`02` §A11).
**Canonical reference.** Regulation (EU) 2016/679, Articles 5, 6, 35.

### EU AI Act
**Plain definition.** The EU regulation governing artificial-intelligence systems, structured by risk tier. It prohibits certain uses outright and imposes heavy obligations on "high-risk" ones.
**Why it matters here.** Real-time remote biometric identification in publicly accessible spaces is prohibited (with narrow exceptions), and most other surveillance AI falls into the high-risk tier, which mandates risk management, logging, human oversight, transparency, and technical documentation.
**How it works.** Obligations attach to providers and deployers by tier, with conformity assessment for high-risk systems.
**In this project.** Cited as a design driver. The architecture responds concretely: no biometric identification, an immutable audit stream of every decision, and operator acknowledge/dismiss authority (`chapter4.tex:114`). `chapter7.tex:30` proposes a compliance-artefact generator as future work — a genuinely good idea.
**Trade-offs and failure modes.** The thesis describes obligations without applying them: no risk-management documentation, no accuracy/robustness/cybersecurity evidence (Article 15), and the deployed transport is unauthenticated, which cuts directly against the cybersecurity requirement.
**Canonical reference.** Regulation (EU) 2024/1689, Articles 5, 6, 12–15.

### Privacy by design
**Plain definition.** Building privacy protections into a system's architecture from the start, rather than adding controls afterwards.
**Why it exists.** Retrofitted privacy is usually a policy document; designed-in privacy is a property of the code.
**How it works.** Here: raw frames never leave the edge agent; all exported evidence passes through one anonymisation choke point; only JSON events cross the network; no identity is ever computed.
**In this project.** The single choke point (`core/privacy.py:68-77`) is a genuinely good architectural decision — one function that all evidence must pass through is auditable in a way that scattered blur calls would not be.
**Trade-offs and failure modes.** The property is *asserted by construction* but never *verified*. No test asserts that no code path writes an unblurred frame; no measurement shows the blur defeats recognition; and the vision-language description path sends images to an external endpoint (`02` §D9). A static check plus one test would convert an assertion into evidence.
**Canonical reference.** Cavoukian, *Privacy by Design: The 7 Foundational Principles*, 2009; GDPR Article 25.

### Anonymisation versus pseudonymisation
**Plain definition.** Anonymisation makes it impossible to identify the individual, irreversibly. Pseudonymisation replaces identifiers with tokens that could be reversed with extra information. Under GDPR, only true anonymisation takes data out of scope.
**Why the distinction matters.** Calling something anonymised when it is merely obscured is a legal misstatement, not a semantic quibble.
**How it works.** Here, blurring of person regions in exported evidence JPEGs.
**In this project.** The thesis says "anonymised" throughout. Whether Gaussian blur at a fixed kernel size achieves legal anonymisation for a person occupying 400 pixels of frame is at best unproven — and blur has known partial reversibility. Tracks also retain `track_id`, which is a pseudonymous identifier within a run.
**Trade-offs and failure modes.** Overclaiming here is exactly the kind of thing a jury with a legal background will probe. The safe framing is "de-identification measures applied; efficacy not formally evaluated" (`02` §A11).
**Canonical reference.** Article 29 Working Party, *Opinion 05/2014 on Anonymisation Techniques*, WP216.

### Data Protection Impact Assessment (DPIA)
**Plain definition.** A structured, documented assessment of the privacy risks of a processing activity and the measures taken to mitigate them.
**Why it exists.** GDPR Article 35 makes it *mandatory* for systematic monitoring of publicly accessible areas on a large scale — which is precisely what a surveillance system does.
**How it works.** Describe the processing, assess necessity and proportionality, identify risks to individuals, and document mitigations.
**In this project.** Absent. `02` §A11 recommends adding at least a sketch: a thesis arguing that governance is constitutive, on a system that legally requires a DPIA, that does not contain one, has an obvious gap.
**Trade-offs and failure modes.** A DPIA is a couple of pages of structured writing and directly demonstrates the applied-governance competence the thesis claims.
**Canonical reference.** GDPR Article 35; Article 29 Working Party, *Guidelines on DPIA*, WP248.

### Audit log and immutability
**Plain definition.** An append-only record of every decision and action, which cannot be silently altered after the fact.
**Why it exists.** Accountability requires being able to reconstruct what the system decided and why. The EU AI Act mandates automatic logging for high-risk systems.
**How it works.** `PolicyAgent` writes an audit record for **every** decision — alert *and* suppression, with a reason (`policy_agent.py:82-87`), and the operator console appends acknowledge/dismiss actions.
**In this project.** Auditing every *suppression* as well as every alert is a well-judged detail: the decisions a surveillance system does *not* make are exactly what an investigator needs.
**Trade-offs and failure modes.** The log is called immutable but is a plain appendable JSONL file (or an unauthenticated Redis stream) that any process can rewrite. Real immutability needs hash chaining or append-only storage with access control. The claim in `chapter4.tex:138` overstates what the implementation provides.
**Canonical reference.** EU AI Act Article 12; Haber & Stornetta, *How to Time-Stamp a Digital Document*, Journal of Cryptology 3(2), 1991.

### Human-in-the-loop / human oversight
**Plain definition.** Requiring a person to review, approve, or be able to override an automated decision.
**Why it exists.** It is both an ethical position and, under the EU AI Act, a legal requirement for high-risk systems.
**How it works.** Here, the system alerts but never acts: no automated enforcement, and the operator acknowledges or dismisses through the console, with each action audited.
**In this project.** Genuinely implemented, and the design's "no automated enforcement actions" stance (`chapter4.tex` Table `tab:privacy`) is the right one.
**Trade-offs and failure modes.** Human oversight degrades into rubber-stamping when alert volume is high — which makes the false-alert-rate metric an oversight-quality metric, not just an accuracy metric. That connection is worth making explicitly in the thesis.
**Canonical reference.** EU AI Act Article 14.

### Threat model
**Plain definition.** An explicit statement of who might attack the system, what they want, and what they can do.
**Why it exists.** Security claims are meaningless without it — "secure" always means "against whom".
**How it works.** Enumerate assets (evidence, audit log, alert stream), adversaries (external attacker, malicious insider, a person trying to evade detection), and capabilities.
**In this project.** Absent. Relevant concrete exposures: an unauthenticated MQTT broker and Redis instance on host ports (bug C18); an unauthenticated Streamlit console displaying surveillance evidence; and prompt injection through `Event.extra` into the explanation layer.
**Trade-offs and failure modes.** A thesis need not implement full security, but it must state the model and admit what the prototype does not do.
**Canonical reference.** Shostack, *Threat Modeling: Designing for Security*, Wiley 2014.

### Dual use
**Plain definition.** Technology that serves a legitimate purpose and an abusive one equally well.
**Why it matters here.** Automated detection of "loitering" and "intrusion" has an obvious history of discriminatory application, and the system's own zone rules encode a judgement about who belongs where.
**How it works.** In practice, disclosure: a short section stating foreseeable misuse and any design choices that limit it.
**In this project.** Not discussed. Note that the design already contains real mitigations worth claiming — no biometric identification, no re-identification, no automated enforcement, mandatory human review. Those are dual-use mitigations; the thesis simply never frames them as such (`02` §A11).
**Trade-offs and failure modes.** Its absence is conspicuous in 2026 and invites a question the author will otherwise answer unprepared.
**Canonical reference.** Brundage et al., *The Malicious Use of Artificial Intelligence*, arXiv:1802.07228.

### Semi-closed site
**Plain definition.** A location with a known perimeter, a known sensor inventory, and a responsible operator — a warehouse, campus, or industrial facility — as opposed to open public space.
**Why the distinction matters.** It is the scoping decision that makes the whole project legally tractable: declared zones are possible, consent and signage are manageable, and the prohibited "public space biometric identification" category is avoided.
**How it works.** `chapter1.tex:46` defines it and derives the assumptions from it.
**In this project.** One of the thesis's best-argued choices, and worth defending explicitly at a defence.
**Trade-offs and failure modes.** It also limits generalisability: nothing here should be claimed to transfer to city-scale deployment, which is an external-validity boundary the manuscript should state.
**Canonical reference.** —(scoping convention; see the EU AI Act's definition of "publicly accessible space", Article 3).

---

## 14. Software engineering, tooling, and reproducibility

### Code smell and technical debt
**Plain definition.** A code smell is a surface symptom that usually indicates a deeper design problem. Technical debt is the accumulated cost of shortcuts, which must eventually be paid with interest.
**Why they matter here.** In a thesis, code quality is not the deliverable — but code that quietly does something different from what the manuscript says is a correctness problem, not a style problem.
**How they work.** Smells here: duplicated source files, monkey-patched methods, magic numbers, unbounded state, silent exception swallowing.
**In this project.** The specific instances are catalogued in `02` §C. The most consequential are the ones where the code and the thesis disagree — `fov_overlap` (bug C1) above all.
**Trade-offs and failure modes.** Chasing smells in a time-boxed thesis is a poor use of time; fixing the ones that change reported numbers is not optional.
**Canonical reference.** Fowler, *Refactoring*, 2nd ed., Ch. 3.

### Dead code and duplicate source
**Plain definition.** Code that is never executed, or that exists in more than one place with the copies drifting apart.
**Why it matters.** A reader cannot tell which copy is authoritative, and someone will eventually run the wrong one.
**How it works.** Fourteen `.py` files exist both at the repository root and under `aura_mas/`. `CLAUDE.md` documents the root copies as byte-identical historical artefacts; `results/methodology_changes.md` then records that after the v2 pass they hold **pre-fix** logic and explicitly warns "do not run anything from the root-level copies expecting v2 behavior".
**In this project.** Also two LaTeX trees, with the root one a failed build whose `main.pdf` is a 15-byte stub.
**Trade-offs and failure modes.** Documenting a trap is much weaker than removing it. `02` §B9 recommends quarantining the duplicates in a `legacy/` directory.
**Canonical reference.** —(engineering practice; see Fowler, *Refactoring*, "Duplicated Code").

### Monkey patching
**Plain definition.** Replacing a method or attribute on an object at run time, from outside the class.
**Why it exists.** It is a quick way to add behaviour without changing the original code.
**How it works.** `replay.py:96-101` replaces `store.append` with a `timed_append` wrapper that records wall-clock arrival times.
**In this project.** Functional, but it means the measured code path differs from the production path — and the wall-clock timestamps that every latency number depends on come from this patched wrapper.
**Trade-offs and failure modes.** Fragile and invisible to readers of `AlertStore`. A first-class callback hook on `AlertStore` would be a few lines and would make the measurement path explicit.
**Canonical reference.** —(Python idiom; see Ramalho, *Fluent Python*, 2nd ed., Ch. 24 on the risks).

### Magic number
**Plain definition.** A bare numeric literal in code with no name and no explanation of where it came from.
**Why it matters.** Every magic number is an undocumented decision, and in a research system each one is a free parameter that shapes the results.
**How it works.** Here, over twenty of them govern every reported number — modality weights 0.9/0.7, bonuses 0.05, window 6.0 s, gray zone 0.35–0.75, thresholds 0.45/0.55/0.70, cooldown 20 s, verification ±0.15/−0.20, tolerance ±5 s, loiter 8 s, abandoned 10 s, IoU 0.6, inference 5 FPS, YOLO confidence 0.35, verification confidence 0.25 at 960 px, z-score divisor 6.0, YAMNet thresholds 0.2–0.3.
**In this project.** None is derived, calibrated, or swept (`01` §5.10). Externalising them into a configuration file (`02` §B8) and sweeping the influential ones (`02` §A13) converts a weakness into an analysis chapter.
**Trade-offs and failure modes.** Defaults chosen once and never revisited become invisible; nobody remembers that `6.0` was a guess.
**Canonical reference.** —(engineering practice; the research framing is sensitivity analysis, Saltelli et al. 2008).

### Unit test, integration test, coverage
**Plain definition.** A unit test checks one component in isolation. An integration test checks components working together. Coverage measures which lines the tests actually execute.
**Why they exist.** They let you change code without silently breaking it, and they document intended behaviour.
**How they work.** `aura_mas/tests/test_pipeline.py` has six tests exercising bus wildcards, noisy-OR monotonicity, auction best-bidder selection, policy thresholds and cooldown, metric computation, and the guardrail hallucination probe — all with synthetic events, no models, under one second.
**In this project.** A real asset, and the guardrail test is the *only* evidence for contribution C4. But coverage is unmeasured, the perception path is untested, and no test asserts the privacy invariant.
**Trade-offs and failure modes.** Six fast tests are worth far more than a hundred slow ones. The gap is not test count, it is which claims are covered: the tests validate the decision chain and nothing about perception, privacy, or reproducibility.
**Canonical reference.** pytest documentation; Beck, *Test-Driven Development: By Example*, 2002.

### Continuous integration (CI/CD), GitHub Actions
**Plain definition.** Automatically building and testing on every change, so breakage is caught immediately.
**Why it exists.** "The tests pass on my machine" is not a verifiable claim.
**How it works.** A workflow file describes jobs that run on push or pull request.
**In this project.** None exists. `02` §B10 recommends a minimal workflow running the six offline tests plus linting — under an hour of work, and it turns `chapter5.tex:91`'s "six offline tests" claim into a checkable artefact.
**Trade-offs and failure modes.** CI on a private repository with a heavy dependency set needs care; the offline tests need no models, so the job is fast and cheap.
**Canonical reference.** docs.github.com/actions.

### Linting and static type checking (ruff, mypy)
**Plain definition.** Linting flags stylistic and likely-buggy patterns without running the code. Static type checking verifies that declared types are used consistently.
**Why they exist.** They catch a class of errors — undefined names, unreachable branches, type mismatches — before runtime.
**How they work.** `ruff` is a fast Python linter; `mypy` checks annotations.
**In this project.** Neither is configured, though the codebase is unusually well-suited to both: it uses `from __future__ import annotations` and type hints throughout, so `mypy` in non-strict mode would run almost out of the box.
**Trade-offs and failure modes.** Strict typing on scientific Python with `numpy` and `cv2` produces noise; non-strict mode on the agent and bus modules is the useful subset.
**Canonical reference.** docs.astral.sh/ruff; mypy-lang.org.

### Dependency pinning and lockfiles
**Plain definition.** Recording the exact versions of every library, including transitive ones, so an environment can be recreated exactly.
**Why it exists.** Library updates change numerical results. Without a lock, "the same code" produces different numbers next month.
**How it works.** A lockfile records resolved versions and hashes for every package.
**In this project.** `requirements.txt` uses `>=` bounds only, and the dependencies that actually determine results — `tensorflow-cpu`, CLIP, torch — are *commented out*, so the file cannot recreate the campaign environment at all. `README.md` references a `requirements-full.txt` that does not exist. `results/env/pip-freeze-{pre,post}-tf.txt` capture a snapshot but are not tied to individual runs.
**Trade-offs and failure modes.** Pinning can conflict with platform-specific wheels — the torch CPU-versus-CUDA trap that `CLAUDE.md` documents at length is exactly this problem, and it is a good argument *for* a lockfile, not against.
**Canonical reference.** pip-tools / `uv` documentation.

### Virtual environment
**Plain definition.** An isolated Python installation for one project, so its dependencies do not collide with the system's or another project's.
**Why it exists.** It prevents one project's upgrade from breaking another, and keeps the system Python clean.
**How it works.** `python -m venv .venv` then activate.
**In this project.** `.venv/` exists and is gitignored. `EXECUTION_PLAN.md §5` records that it was found **silently broken** and "about to pollute the global Python env" during the v1 hardening pass — a real bug, found and fixed, and a good illustration of why environment capture matters.
**Trade-offs and failure modes.** A virtual environment is not a lockfile: it isolates but does not record. Both are needed.
**Canonical reference.** Python `venv` documentation.

### Packaging (`pyproject.toml`), `uv`
**Plain definition.** `pyproject.toml` is the standard file declaring a Python project's metadata, dependencies, and build configuration. `uv` is a fast modern installer and resolver that produces a lockfile.
**Why they exist.** They make a project installable, importable from anywhere, and reproducible.
**How they work.** Declare the package and dependencies, then `pip install -e .` or `uv sync`.
**In this project.** Absent for AURA-MAS — the package only imports when the working directory is the repository root. (Interestingly, the abandoned `pfe_agentic_ai/` sibling project *does* have a `pyproject.toml`, so the skill exists; it simply was not applied here.)
**Trade-offs and failure modes.** Minimal downside; an hour of work.
**Canonical reference.** packaging.python.org; docs.astral.sh/uv.

### Configuration as code (`hydra`, `pydantic-settings`)
**Plain definition.** Keeping all tunable parameters in versioned configuration files rather than scattered through the source, with a library to compose, override, and validate them.
**Why it exists.** It makes every experiment's exact settings explicit, versioned, and sweepable.
**How it works.** `hydra` composes YAML configuration groups and supports command-line overrides and multi-run sweeps; `pydantic-settings` validates configuration against typed models.
**In this project.** The missing `configs/` layer (`02` §B8). `README.md`, `chapter5.tex:50` and `CLAUDE.md` all describe a `configs/` directory; `aura_mas/configs/` is empty and no top-level one exists. Adding it is the prerequisite for the threshold sweeps in `02` §A13 and for recording resolved settings per run.
**Trade-offs and failure modes.** Hydra has a learning curve and can obscure control flow; for this scale, a plain typed YAML loader would suffice.
**Canonical reference.** hydra.cc documentation.

### Instrumentation (`psutil`, `tracemalloc`)
**Plain definition.** `psutil` reads process and system resource usage (CPU, memory, I/O). `tracemalloc` tracks Python memory allocations.
**Why they exist.** Resource claims need measurement, and memory leaks need attribution.
**How they work.** Sample process metrics periodically and record them alongside results.
**In this project.** Recommended in `02` §E to produce the per-agent CPU, memory, and throughput numbers that the edge-first claim requires, and to catch the unbounded-state leak (bug C14) empirically.
**Trade-offs and failure modes.** Instrumentation perturbs what it measures; sample at low frequency and record the overhead.
**Canonical reference.** psutil documentation; Python `tracemalloc` documentation.

### Data versioning (DVC) and provenance manifests
**Plain definition.** Tracking which exact version of a dataset produced which result, usually by storing content hashes in version control while the data itself lives elsewhere.
**Why it exists.** Results are a function of code *and* data; versioning only the code is half a system.
**How it works.** DVC stores pointers and checksums in git and the payload in remote storage.
**In this project.** `data/clips_real/manifest.json` already records sources and rationale, which is most of the value at this scale. What is missing is checksums, and — more importantly — any citation of that manifest in the manuscript, where licence and provenance belong (`02` §A11).
**Trade-offs and failure modes.** DVC is overhead for a few hundred megabytes; a manifest with SHA-256 hashes is the pragmatic version and is a couple of hours of work.
**Canonical reference.** dvc.org documentation.

### `cloc`
**Plain definition.** A small tool that counts lines of code by language, separating code from comments and blanks.
**Why it matters here.** `chapter5.tex:6` and `chapter7.tex:8` both claim "approximately 2,500 lines of tested Python". This audit could not verify that figure, so it is marked `[uncertain]`.
**How it works.** `cloc aura_mas/` produces the breakdown in seconds.
**In this project.** Run it, and state the real number with the command that produced it. An unverifiable quantitative claim in a thesis is an unnecessary risk when verifying it takes ten seconds.
**Trade-offs and failure modes.** Line counts are a poor proxy for effort or quality; better to report them as a scale indicator only, which is how the thesis uses it.
**Canonical reference.** github.com/AlDanial/cloc.

### `scipy`
**Plain definition.** The standard Python scientific-computing library: optimisation, statistics, signal processing, linear algebra.
**Why it matters here.** Two of this audit's most important recommendations are one `scipy` call each: `scipy.optimize.linear_sum_assignment` fixes the greedy matcher (bug C4), and `scipy.stats.wilcoxon` supplies the missing paired significance test (`02` §A6).
**How it works.** Pure-Python interface over compiled implementations.
**In this project.** Not currently a dependency; adding it is trivial and unlocks disproportionate methodological improvement.
**Trade-offs and failure modes.** None meaningful at this scale.
**Canonical reference.** docs.scipy.org.

### `librosa` and OpenCV
**Plain definition.** `librosa` is the standard Python audio-analysis library; OpenCV is the standard computer-vision library.
**Why they exist.** They provide the loading, decoding, and signal-processing primitives that everything else builds on.
**How they work.** `librosa.load(source, sr=16000, mono=True)` decodes and resamples audio (`audio_agent.py:157`); `cv2.VideoCapture` reads video frames (`camera_agent.py:223`), and `cv2.GaussianBlur`/`cv2.imwrite` implement the privacy path.
**In this project.** Both are load-bearing. Note that the project uses `opencv-python-headless`, which lacks GUI functions — and whose availability of `HOGDescriptor` the privacy module explicitly checks for, falling back to whole-frame blur if absent (`core/privacy.py:41-42`). That is careful defensive coding.
**Trade-offs and failure modes.** `librosa` is slow for large corpora; OpenCV's video decoding depends on system codecs, which is a portability risk for the Raspberry Pi deployment.
**Canonical reference.** librosa.org; docs.opencv.org.

### TensorFlow SavedModel
**Plain definition.** TensorFlow's portable serialised format containing a model's computation graph and weights, loadable without the original source code.
**Why it exists.** It decouples model distribution from training code.
**How it works.** `tf.saved_model.load(model_dir)` returns a callable; `audio_agent.py:121-135` loads it and reads the class map from the model's own assets, with a filesystem fallback.
**In this project.** How YAMNet is loaded, after `tensorflow_hub`'s `tfhub.dev` URL was found to return HTTP 404 — a genuinely useful piece of debugging captured in `results/yamnet_integration_notes.md` and `aura_mas/scripts/fetch_yamnet.py`.
**Trade-offs and failure modes.** Pulls in TensorFlow, a heavy dependency, which is why it is optional. `CLAUDE.md` correctly warns to install `tensorflow-cpu` rather than `tensorflow`, and to install torch from the CPU wheel index first — both to avoid silently downloading gigabytes of CUDA packages on a machine with no GPU. Those warnings came from a real incident that consumed half the available disk.
**Canonical reference.** tensorflow.org/guide/saved_model.

### Base64
**Plain definition.** A way of representing binary data as plain text, so it can travel through text-only channels.
**Why it exists.** JSON and HTTP headers cannot carry raw bytes.
**How it works.** Every three bytes become four printable characters, expanding size by about a third.
**In this project.** `explanation_agent.py:91` base64-encodes anonymised evidence JPEGs into the vision-language request payload.
**Trade-offs and failure modes.** The 33 % expansion matters for bandwidth on edge links, and it is the mechanism by which images leave the site in the vision path (see Data egress).
**Canonical reference.** RFC 4648.

### Regular expression
**Plain definition.** A compact pattern language for matching text.
**Why it matters here.** The guardrail's free-text check depends on one.
**How it works.** `explanation_agent.py:140-141`: `re.findall(r"ev_[0-9a-f]{6,}", summary + " " + reasoning)` extracts every evidence-identifier-shaped token from the model's prose, and the guardrail requires that set to be a subset of the real identifiers.
**In this project.** Simple and effective for the expected format — and exactly as brittle as any regular-expression-based validation. A model that writes `ev - ab12cd` or `[ev_AB12CD]` (uppercase) evades the pattern.
**Trade-offs and failure modes.** Validation by pattern matching over free text is inherently incomplete; combining it with constrained decoding (see Structured output) is the more robust design.
**Canonical reference.** Python `re` documentation.

### `PYTHONHASHSEED`
**Plain definition.** An environment variable that fixes the randomisation of Python's string hashing, which otherwise varies per process.
**Why it exists.** Hash randomisation is a security feature, but it makes set and dictionary iteration order vary between runs — a subtle source of non-reproducibility.
**How it works.** Setting it to a fixed value before the interpreter starts makes hashing deterministic.
**In this project.** Mentioned in `run_campaign.py`'s docstring as a reason to use fresh subprocesses, but **never actually set**. Since the code iterates over sets in places (for example `hypothesis.sensors` at `coordinator_agent.py:58`, whose `next(iter(...))` picks an arbitrary element), iteration order can genuinely affect behaviour.
**Trade-offs and failure modes.** Setting it must happen before interpreter start, so it belongs in the subprocess environment in `run_campaign.py:110`, not inside `replay.py`.
**Canonical reference.** Python command-line and environment-variable documentation.

### Git commit hash
**Plain definition.** The unique identifier of a specific state of a repository.
**Why it matters here.** Recording it in every run JSON makes each result traceable to the exact code that produced it.
**How it works.** `git rev-parse HEAD`, captured at run start.
**In this project.** Not recorded. Recommended in `02` §B1, and it directly addresses the resume-logic weakness where an old run is silently kept because its output file exists (bug C22).
**Trade-offs and failure modes.** Only meaningful if the working tree is clean; record the dirty flag too.
**Canonical reference.** git-scm.com documentation.

---

## Closing note on terminology

Two words in this project's vocabulary deserve a final caution, because they do the most rhetorical work and the least technical work.

**"Agentic"** currently means, in AURA-MAS, that one of six components calls a language model in a fixed four-step pipeline with no loop, no tool use, and no autonomy — and that component never ran during evaluation. The other five components are ordinary message-driven services. That is a defensible and arguably wise design, but the thesis should describe it as *rule-guarded generative explanation within a multi-agent system*, not lean on "agentic AI" as if the term itself carried a contribution.

**"Multi-agent"** is architecturally accurate and, per `research/.../findings/F4`, twenty-six years old in this exact application. It describes the system correctly and claims nothing.

The strongest version of this thesis is the one that says plainly: *here is a well-engineered, privacy-constrained, auditable surveillance architecture; here is one architectural pattern in it that the current literature does not standardise on — keeping the generative layer strictly downstream of a deterministic decision, with mechanical evidence grounding; here is a rigorous system-level evaluation methodology; and here is the honest, partly negative result of applying it.*

That thesis is defensible, and almost all of the material for it is already on disk.
