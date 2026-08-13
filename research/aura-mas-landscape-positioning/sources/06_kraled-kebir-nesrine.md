---
source_type: thesis
credibility: 2
recency: 2016
directly_relevant: no
---

# Vidéosurveillance intelligente : Détection et suivi des personnes

## Bibliographic metadata

- **Title**: "Vidéosurveillance intelligente : Détection et suivi des personnes" (Intelligent video-surveillance: detection and tracking of persons)
- **Author(s)**: Kraled Kebir Nesrine & Chennouf Bahaeddine (co-authored, two-student Master's mémoire)
- **Year**: 2015/2016 ("Promotion 2015/2016" on cover page)
- **Institution / Degree type**: Université Saad Dahlab, Blida (USDB), Faculté des Sciences, Département d'Informatique — Master's diploma ("diplôme de master"), Domaine Mathématique et Informatique, Filière Informatique, Spécialité Informatique, Option Ingénierie de logiciel. The project is explicitly stated to be part of a research protocol proposed by the VAANIM team (Vision Artificielle et Analyse d'Image) of the Robotics division of CDTA (Centre de Développement des Technologies Avancées), titled "Système de vision pour la robotique de surveillance."
- **Supervisor(s)**: Promoteur: Mr. Kameche Abdalah; Encadreur: Mr. Djekoun Oualid.
- **Document completeness caveat (important)**: pdfinfo reports the scanned PDF has only **87 physical pages**, but the thesis's own table of contents indicates the document runs to a numbered page 99 (Chapitre IV ends at p.98, "Conclusion générale et perspectives" at p.99). Reading through to the last physical page of the file lands at numbered page ~90 (mid-way through Chapter IV, "Présentation de l'application," camera-selection screenshots). **The final ~9 numbered pages — the person-detection/tracking demo (§IV.5), the test-and-validation section with quantitative results (§IV.6), and the general conclusion/perspectives (§IV.7 / p.99) — are missing from this scanned copy.** All fields below marked "not available in this copy" reflect this truncation, not necessarily an absence in the original thesis.
- **Format note**: the PDF is a scanned (image-only, no embedded text layer) photocopy with owner-password print/copy restrictions; content was read visually page-by-page rather than via text extraction.

## Research problem (in the document's own terms)

Security personnel monitoring IP camera networks cannot attentively watch more than roughly 9–12 cameras for more than about 15 minutes, and the probability of a human operator reacting live to an event captured on a large camera network is estimated (citing a source in their literature review) at about 1 in 1000. Combined with the repetitive nature of the task and the low frequency of genuinely dangerous/abnormal events, this makes manual video surveillance impractical at scale — motivating automated/intelligent video-surveillance. The thesis frames its own contribution narrowly: it is explicitly presented as a **continuation/improvement of a pre-existing internal platform** (built by earlier work at the same lab) that already handled distributed visualization and management of an IP-camera network; the new contribution is to fix that platform's known problems (unreliable detection algorithm, no restriction to moving persons specifically, storage growth from continuous recording, uneven camera-load distribution across monitoring staff) and to add reliable person detection/tracking to it.

## Objectives

Stated explicitly (Introduction générale, p.14):
- Contribute to improving an already-developed video-surveillance platform that has a number of execution problems.
- Add functionalities and reliable detection/tracking methods for moving objects/persons from a video stream captured through the IP camera network.
- Determine, as efficiently and precisely as possible, an object's position in each frame and its trajectory.
- Handle partial occlusions and local deformations of tracked objects.
- (From the platform-level goals on p.13) manage real-time visualization of camera streams on user demand, save recordings with minimal disk usage, facilitate managing saved videos for later investigation, secure system access, allow integration of detection/tracking algorithms, and support remote access via Wi-Fi.

## Proposed approach (high-level)

Improve/extend an existing distributed IP-video-surveillance visualization platform by plugging in a person detection-and-tracking module. Detection and tracking are both performed using the HOG (Histogram of Oriented Gradients) descriptor: background/foreground separation combined with HOG-based classification of image regions into "human" / "non-human," followed by frame-to-frame tracking of detected persons using a bounding box (each tracked person gets a distinct color and a simple trajectory is drawn). The resulting module is integrated into the pre-existing master–slave visualization platform so that detections trigger recording and alert notifications to supervisor/monitoring-staff clients.

## System architecture

**Explicitly a master–slave (maître-esclave) distributed client-server architecture — not agent-based, and the thesis does not use agent terminology anywhere in the material read.** Three human-facing roles and one automated worker role:

- **Superviseur** ("master"/super-user): authenticates, configures the system (add/remove cameras, camera groups, list of slave IP addresses), manages recordings, handles failover (if a slave or a surveillant stops responding, the supervisor reassigns that slave's cameras to remaining slaves), receives detection notifications, and can view any camera live or from storage.
- **Surveillant** (monitoring staff, one of several "masters" for viewing purposes): authenticated user restricted to real-time viewing of the camera group assigned to them by the supervisor; no configuration rights.
- **Administrateur**: a separate role whose only job is creating/editing/deleting user accounts (supervisor/surveillant accounts).
- **Esclaves** ("slaves"): autonomous machines (one or more, addressed by IP in a config file) that each own a subset of cameras and perform: (1) acquisition — pull frames from an IP camera over HTTP; (2) recording (permanent or detection-triggered) to AVI; (3) motion/person detection (HOG-based); (4) tracking; and (5) forwarding video frames and detection notifications to the supervisor and to the relevant surveillant(s).
- **Database server**: stores users, cameras, camera groups, recordings metadata, detections/notifications (UML class diagram, Fig. 19).
- Communication between supervisor, surveillants, and slaves happens over the network via **WCF (Windows Communication Foundation) web services**.

The thesis's own diagram (Figure 27, "Paradigme Maître/Esclaves") and text are unambiguous: "nous avons opté pour une architecture distribuée... en utilisant le paradigme maître-esclaves. Dans ce paradigme, le maître distribue une partie des tâches sur un ensemble d'esclaves." The "esclaves" are described as "des machines autonomes" only in the sense of being independently running processing nodes (task executors) — there is no description of autonomous goal-setting, negotiation, planning, inter-slave communication/coordination, or any decision-making beyond "run the fixed detection/tracking pipeline and report results/notifications to the master." This is task distribution/load-balancing across worker nodes, not a multi-agent system in the AI sense.

## AI/ML techniques used

- **HOG (Histogram of Oriented Gradients) descriptor** (Dalal & Triggs-style pipeline, cited via a secondary source [27]/[28] in the thesis) for both person detection and as the feature representation feeding tracking. The pipeline: convert to grayscale → gamma/intensity normalization → compute horizontal/vertical gradients with a centered [-1,0,1] mask → per-pixel gradient magnitude/orientation → divide image into cells (8×8 px) grouped into overlapping blocks (50% overlap) → per-cell orientation histograms (their example: 105 blocks, 4 cells/block × 9 orientation bins = 36-dim per block, ~3780-dim total descriptor for a 64×128 window) → classify each candidate window/region as human vs. non-human.
- The document names the classification step ("classifier comme une région humain/non humain") in its pseudocode (Figure 13) but does not specify the classifier algorithm in the pages read (no explicit mention of SVM being the classifier actually trained/used, despite SVM appearing generically in the earlier literature-review taxonomy of kernel-based tracking methods). Given the toolchain (EMGU CV / OpenCV, cited as a used library), it is plausible — but **not confirmed by the text read** — that they relied on OpenCV/EMGU CV's built-in pretrained HOG people-detector (the classic Dalal–Triggs SVM) rather than training a custom classifier; no training dataset or training procedure for a classifier is described anywhere in the chapters read.
- No deep learning, no CNNs, no modern object detectors (YOLO/SSD/Faster R-CNN, etc.) — consistent with the 2015/2016 timeframe and the pre-deep-learning-dominant toolset (EMGU CV, classic background subtraction + handcrafted-feature pipeline).

## Computer vision techniques

- **Motion/background modeling literature review** (Chapter II, Part I) surveys — but does not commit the implementation to — several families: frame differencing, spatio-temporal entropy, optical flow (all "no background modeling"); statistical/predictive (Kalman/Wiener-filter-based) local background modeling; region/texture-based semi-local modeling; and global modeling (k-means-based multi-model switching, eigenbackgrounds). Background subtraction is presented as the standard operation for producing a foreground mask once a background model exists.
- **Tracking literature review** (Chapter II, Part II) surveys point tracking (Kalman filter, particle filter/Condensation, Multiple Hypothesis Tracking), kernel tracking (template matching, Mean-Shift, SVM-based tracking, layering-based tracking), and silhouette tracking (contour tracking, shape matching/Hough-transform-based). This is a generic survey; the thesis states only that a rectangle bounding box with a per-person color and a simple trajectory line is used for the actual tracking output.
- **Actually implemented (as far as read)**: HOG-based human region classification (used for detection) plus a bounding-box tracker per detected person; the exact tracking association algorithm (e.g., whether Kalman filtering or simple nearest-neighbor bounding-box matching is used frame-to-frame) is not spelled out in the pages available in this copy — likely covered in the missing §IV.5 ("La détection de suivi des piétons") which precedes the missing test/validation section.

## Agent-based / multi-agent / distributed / coordination components

**None in the AI/multi-agent sense.** The system is explicitly and repeatedly described (own diagrams, own words) as a **master–slave distributed architecture** for load-balancing camera processing across machines, not as a multi-agent system with autonomous cooperating decision-making units. There is no negotiation protocol, no agent communication language, no planning/reasoning component, no autonomy beyond "execute the fixed detection/tracking pipeline on assigned cameras and report to the master." The only "intelligence" is local, per-camera-stream computer vision (HOG-based detection + bounding-box tracking); there is no cross-camera reasoning, hand-off/re-identification across camera views, or any higher-level orchestration described beyond simple failover (reassigning a dead slave's cameras to other slaves) and routing recordings/notifications to the correct human client. This thesis is squarely a **distributed CV-pipeline / client-server platform paper**, not an agentic or multi-agent-systems paper.

## Dataset(s) used, and whether public benchmark or custom/collected

Not clearly stated in the pages available. The hardware setup used for development/testing is a small network of **Axis M1011 fixed IP cameras** (up to 30 fps at VGA resolution), i.e., live camera feeds captured by the authors' own lab setup rather than a named public benchmark dataset (no PETS, CAVIAR, MOT-Challenge, etc. mentioned in the chapters read). No description of a labeled training set for the human/non-human classifier is present in the material read — consistent with likely reliance on a pretrained/off-the-shelf HOG people detector, but this is not confirmed. The test/validation chapter that would describe evaluation data is in the missing final pages.

## Evaluation methodology and metrics

**Not available in this copy** — the "Test et validation" section (Chapter IV, §6, numbered p.95–98 per the table of contents) falls in the missing final pages of the scanned PDF.

## Main quantitative results

**Not available in this copy** — for the same reason (missing final pages). No accuracy, precision/recall, IoU, FPS, or other performance numbers were found in the ~90 pages that could be read.

## Stated limitations

**Not available in this copy** — the "Conclusion générale et perspectives" (numbered p.99) that would normally state limitations and future work is in the missing final pages. The introduction (p.14) does implicitly acknowledge the pre-existing platform's limitations that this work is trying to fix: an unreliable detection algorithm, lack of restriction to person-only motion, disk-storage growth from unmanaged recording, and uneven distribution of camera groups across monitoring staff — but these are framed as problems of the prior platform being addressed, not as limitations of the present authors' own final results.

## Claimed contributions

From the stated objectives (p.14, own words, translated): a contribution to improving an already-developed video-surveillance platform, by adding functionalities and "reliable methods" for detecting and tracking moving objects/persons from an IP-camera video stream, aiming to determine an object's position and trajectory as efficiently and precisely as possible, "while managing partial occlusions and local deformations of objects." No further contribution claims (e.g., novel algorithmic contribution, benchmark superiority) were found in the material read; the framing throughout is incremental engineering improvement of an existing internal platform rather than a claim of a new detection/tracking method.

## Critical assessment (own analysis)

- **Not a multi-agent or agentic system.** Despite superficial vocabulary ("esclaves," distributed architecture) that might sound agent-like, this is a conventional master–slave load-distribution pattern common in distributed-systems engineering, with zero autonomous reasoning, negotiation, or planning components. It should not be cited as prior "multi-agent surveillance" work; at most it demonstrates that a distributed processing topology for camera networks was already considered "obvious" groundwork in this research environment as early as 2015/2016.
- **Methodologically dated even for its time.** HOG-based person detection (2005-era technique) with no deep learning is a reasonable choice for a 2015/2016 Algerian Master's thesis given hardware/tooling constraints (EMGU CV wrapper around OpenCV, C#/.NET stack), but it means the detection/tracking core offers no methodological novelty — it is textbook computer vision glued onto an existing platform.
- **Weak specification of the actually-implemented classifier and tracker.** The pseudocode in Fig. 13 says "classifier comme une région humain/non humain" without naming the classifier (SVM vs. something else), and no training data/procedure is described in the material read. This mirrors a pattern seen in other student theses from this environment (cf. the sibling analysis of Tahar Dahmani Abdelkader's thesis) where a central "comparison/classification" step is asserted rather than technically specified.
- **Document itself is incomplete as scanned.** The absence of the test/validation and conclusion chapters in this copy is a serious constraint on this analysis: no quantitative evidence of the detection/tracking module's actual accuracy or robustness (to occlusion, lighting change, multiple people, etc.) could be found, despite the objectives explicitly promising occlusion-handling. Any claim about how well the system actually performs is therefore unverifiable from this source.
- **Contribution is explicitly incremental**, built directly on top of a named prior internal platform and prior lab research protocol (VAANIM/CDTA), reinforcing that this local research environment already had a lineage of successive, mostly-non-agentic surveillance-platform theses (distributed visualization → detection/tracking add-on) rather than a jump to autonomous multi-agent reasoning.

## Direct verbatim quotes

1. On the architecture (own words, p.81/82, French original): "nous avons opté pour une architecture distribuée pour répartir les données et ainsi les traitements sur plusieurs sites (ordinateurs), en utilisant le paradigme maître-esclaves. Dans ce paradigme, le maître distribue une partie des tâches sur un ensemble d'esclaves." — "we opted for a distributed architecture to spread data and thus processing across several sites (computers), using the master-slaves paradigm. In this paradigm, the master distributes a portion of the tasks across a set of slaves."
2. On the detection/tracking method actually used (p.59/60): "Pour la détection et suivi des personnes dans la vidéo, on a utilisé la méthode HOG (Histogramme Of Oriented Gradient)." — "For the detection and tracking of persons in video, we used the HOG (Histogram of Oriented Gradient) method."
3. On the research problem/motivation, citing a source on operator attention limits (p.32/33): "un surveillant ne peut suivre attentivement 9 à 12 caméras plus de 15 minutes... où la probabilité de réagir sur le fait à un événement capté par un réseau de caméras de surveillance est estimée à 1 sur 1000." — "a monitoring operator cannot attentively watch 9 to 12 cameras for more than 15 minutes... where the probability of reacting live to an event captured by a surveillance camera network is estimated at 1 in 1000."
4. On the objectives (p.14): "Notre contribution se situe en rajoutant des fonctionnalités, et des méthodes fiables de détection et de suivi des objets ou des personnes en mouvement à partir d'un flux vidéo capturé à travers le réseau de caméras IP en cherchant à déterminer le plus efficacement et précisément possible sa position dans chaque trame et connaitre sa trajectoire." — "Our contribution consists in adding functionalities, and reliable methods of detection and tracking of moving objects or persons from a video stream captured through the IP camera network, seeking to determine as efficiently and precisely as possible its position in each frame and know its trajectory."
5. On the role of "esclaves" (p.66): "Les esclaves contiennent des algorithmes d'analyse vidéo de base (acquisition, détection et suivi des personnes), leur rôle c'est de faire l'acquisition, envoyer les flux vidéo au surveillant et au superviseur, exécuter les algorithmes de détection et suivi des personnes, et envoyer les résultats vers le superviseur et les surveillants." — "The slaves contain basic video-analysis algorithms (acquisition, detection and tracking of persons); their role is to perform acquisition, send video streams to the monitoring staff and supervisor, execute the person detection and tracking algorithms, and send the results to the supervisor and monitoring staff."

## Relevance to an "agentic multi-agent surveillance system" research direction

Overlap is minimal. The thesis contributes a distributed **master–slave** processing platform (not an agent architecture) for IP-camera visualization, plus a classical HOG-based person detection/tracking module bolted onto it — no multi-camera reasoning/re-identification, no autonomous or cooperating decision-making agents, no LLM-based or rule-based reasoning layer, no explainable alerting beyond a simple sound/notification on detection, and (as far as this incomplete copy shows) no anomaly-detection layer beyond "a person moved." Its main positioning value for a new agentic multi-agent surveillance thesis is negative/contrastive evidence: it demonstrates that within this exact academic environment (USDB/CDTA, VAANIM lab lineage), even a 2015/2016 thesis explicitly reaching for a "distributed" architecture stopped at basic master–slave task distribution and single-modality classical CV, never approaching autonomous multi-agent coordination, cross-camera reasoning, or LLM/agentic reasoning — reinforcing that a genuinely agentic multi-agent surveillance system would be a clear, non-duplicative contribution relative to this local research lineage.
