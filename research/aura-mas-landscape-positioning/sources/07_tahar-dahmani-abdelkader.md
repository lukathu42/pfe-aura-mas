---
source_type: thesis
credibility: 2
recency: 2014
directly_relevant: no
---

# Indexation et recherche d'images pour la vidéosurveillance intelligente

## Bibliographic metadata

- **Title**: "Indexation et recherche d'images pour la vidéosurveillance intelligente" (Indexing and image retrieval for intelligent video-surveillance)
- **Author(s)**: TAHAR DAHMANI Abdelkader
- **Year**: 2013/2014 (Promotion 2013/2014, as stated on the cover page)
- **Institution / Degree type**: Université Saâd Dahlab, Blida (USDB), Faculté des Sciences, Département d'Informatique — Master's diploma ("diplôme de master"), Domaine Mathématique et Informatique, Filière Informatique, Spécialité Informatique, Option Ingénierie de logiciel. Produced under the Laboratoire de Recherche des Systèmes Informatique (LRDSI).
- **Supervisor(s)**: Promotrice: Mlle Benblidia Nadjia; Encadreur: Mlle Reguieg F. Zohra; Présidente du jury: Mme Bensettiti Souad; Examinateurs: Mlle Ameur Khadidja.
- **Length**: 63 numbered pages (Introduction générale p.1 through Annexe ending p.63), plus unnumbered front matter (title, acknowledgments, dedication, résumé FR/EN/AR, table of contents, list of figures/tables) — a compact, thin Master's thesis with a single implementation chapter.

Note on document quality: the thesis itself contains internal inconsistencies (the implementation chapter is titled "CHAPITRE VI" in the body text and figure captions while the table of contents and cross-references call it "Chapitre IV"; there are two different "Tableau III.1" entries; the stated "Conclusion générale" listed in the table of contents at page 59 could not be located as a distinct page in the document — it appears to be missing/omitted from the scan, with the chapter‑level "IV.4. Conclusion" on p.58 apparently substituting for it). These are read as evidence of low editorial rigor rather than as errors introduced by this analysis.

## Research problem (in the document's own terms)

The thesis frames video-surveillance as split into two types: "normal" (a human operator watching camera feeds) and "intelligent/automatic" (software identifies people via biological or behavioral traits). The author argues that normal surveillance depends entirely on the human element and is therefore insufficient given growing security needs, and sets out to build a minimal "intelligent" video-surveillance system that automatically recognizes a specific wanted/registered person's face across networked cameras and alerts a server/operator when a match occurs. There is no discussion of multi-camera reasoning, behavior/anomaly detection, or any autonomous decision-making beyond a single "detected face matches database → send alert" rule.

## Objectives

- Design and build ("conception et réalisation") an intelligent/automatic video-surveillance system based on face recognition of a single "wanted" person ("la seule personne requise").
- Store the target person's face(s) in a database; compare faces captured live by networked cameras against this database.
- On a positive match, have the camera send an alert to a central server.
- Explicitly framed by the author as only a starting point: "Ce projet est le début du développement des systèmes vidéosurveillance intelligente ou automatique" (résumé, unnumbered page) — i.e., the author himself frames this as a first proof-of-concept, not a mature system.

## Proposed approach (high-level)

A client–server IP video-surveillance pipeline: multiple networked cameras (client side) capture video/frames; a face-detection/recognition module (server or camera side, using OpenCV/Viola–Jones) scans frames for faces; each detected face is compared to a face database of enrolled/wanted individuals; on a match, the system sends the person's ID and camera IP to a central server application, which displays the alert with a marker on a geographic map (using camera latitude/longitude) and lets an operator view a historical log of detections by date/ID.

## System architecture

Single-module, pipeline architecture — **not** multi-agent, not multi-component-cooperating in any autonomous sense. It is a conventional client–server IP-video-surveillance application:

- **Cameras** (client role) capture video and are administered via IP addresses in the server UI ("Liste Caméra").
- **Server application** (built in C#/Visual Studio, SQL Server backend, OpenCV for CV) provides three tabs: "En ligne Cam" (live camera view + face-recognition overlay), "Enregistrer facial" (enroll a new face + push updates to all cameras), and "Map" (Google-Maps-based display of camera locations and detection events with a history/search panel).
- **Detection/recognition module**: Viola–Jones cascade classifier (Haar features + AdaBoost + cascade of boosted classifiers) via OpenCV, used purely for face *detection*; the thesis frames "reconnaissance faciale" as detection + database comparison, but the comparison/matching mechanism itself is never described algorithmically (no embedding, no distance metric, no classifier for identity — this is a significant gap, see Critical assessment).
- Chapter III discusses generic 2-tier/3-tier/N-tier client-server architectures, IP video transport protocols (FTP/SMTP/HTTP/HTTPS/RTP/RTSP), and network security (authentication/authorization/confidentiality) at a textbook level, but the thesis's own concrete implementation is a plain 2-tier client/server app (camera clients + one server + SQL Server DB), not an N-tier or distributed design.
- UML models (use-case diagram, one sequence diagram, one class diagram with 3 classes: `personne`, `LocalisationCam`, `date`) describe a simple CRUD/detection-alert workflow: user adds a face → system pushes update to cameras → camera searches/detects → sends id_personne + camera IP → system displays localization on map.

There is no cooperating set of autonomous decision-making units, no agent communication protocol, no negotiation/coordination logic between cameras, and no planning/reasoning component. Camera "clients" only capture and forward; all decision logic (if any) lives centrally in the server UI thread that reacts to a match message.

## AI/ML techniques used

- **Viola–Jones algorithm** (Haar-like features + integral image + AdaBoost-boosted cascade classifier) — used exclusively for face *detection* (localizing a face rectangle in a frame), not identity classification. This is the only ML/CV technique actually implemented; chapters I and II survey many other biometric/face-recognition families (PCA/Eigenfaces, SVM, HMM, neural networks, LDA, ICA, LBP, AAM, EBGM, LG-PCA, etc.) purely as literature background — none of these alternatives are implemented.
- No deep learning, no CNNs, no embeddings (e.g., FaceNet-style), no explicit identity-matching algorithm is described for the "comparison of faces" step that is central to the stated objective — this is asserted as happening but never technically specified (see Critical assessment).
- OpenCV is cited as also offering K-means, AdaBoost, artificial neural networks, SVM, and statistical estimators (p.52), but the thesis states only Viola–Jones/cascade detection is actually used.

## Computer vision techniques

- Face **detection** only: Haar-feature cascade classifier (Viola–Jones, 2001), using the integral-image trick for O(1) feature evaluation and an AdaBoost-trained cascade of "weak classifiers" for real-time performance.
- No tracking, no segmentation, and no anomaly/behavior detection are implemented (tracking is mentioned once in a background figure — "Détection du visage / Tracking" as a generic pipeline box in Chapter II — but never implemented or discussed further).
- Face *recognition* (identity matching against the database) is asserted functionally in the résumé/abstract/objectives but the "extraction de caractéristiques" / "comparaison des caractéristiques" steps shown generically in Figure II.2 are never instantiated with a concrete algorithm in the implementation chapter.

## Agent-based / multi-agent / distributed / coordination components

**None.** There is no agent framework, no autonomous reasoning units, no negotiation or coordination protocol between cameras, and no LLM or symbolic-reasoning component of any kind. The system is a conventional centralized client–server CCTV application with one detection module. Chapter III's discussion of "architecture multi-niveaux" (N-tier client/server, p.43) is purely a generic software-architecture concept (application/DB server tiers), not a multi-agent system — no autonomy, no goal-directed behavior, and no inter-camera communication beyond forwarding a detected ID to the central server.

## Dataset(s) used

Not stated as a formal, described dataset. No public benchmark (no LFW, WIDER FACE, etc.) is used or mentioned for evaluating the author's own system. The only quantitative face-detection figures cited in the document (130 images, 507 faces, ROC curve, 88.8% detection rate at 50 false positives) are **taken directly from the original Viola–Jones (2001) paper** as background citation (Chapter III.4, p.24), not results the author produced. The face database used in the actual application appears to be a small, informally collected set of enrolled photos entered manually via the "Enregistrer facial" UI (the screenshot in Fig. IV.5 shows two enrolled entries, one of which is the author himself: "tahar dahmani abdelkader"). No dataset size, collection protocol, or demographic/scene diversity is documented.

## Evaluation methodology and metrics

Essentially absent for the author's own system. The thesis:
- Never runs a controlled experiment on its own implementation.
- Never reports precision/recall/F1/false-accept-rate/false-reject-rate/detection-rate for the built system.
- Never compares against a baseline or alternative method empirically.
- Only reproduces performance figures from the literature (Viola–Jones's own 2001 benchmark, and citations claiming Viola-Jones is "15x faster than Rowley-Kanade, 600x faster than Schneiderman-Kanade" — again literature claims, not measurements by the author).
- Chapter IV ("Implémentation") is purely descriptive: it walks through the development environment (SQL Server, C#/Visual Studio, OpenCV, VMware Workstation for the virtual test network) and screenshots of the four UI tabs (Login, En ligne Cam, Traitement Vidéo, Enregistrer Facial, Map), without any test protocol, sample size, or measured outcome.

## Main quantitative results

None produced by the author. The only numbers in the document are secondary citations: Viola–Jones's original 130-image/507-face benchmark and 88.8% detection rate at 50 false positives (attributed to the cited paper, p.24), and the well-known "15x/600x faster than Rowley-Kanade/Schneiderman-Kanade" speed claims (also cited from the literature, not measured).

## Stated limitations

The thesis does not contain an explicit "Limitations" section. The closest statements are:
- The résumé's admission that "Ce projet est le début du développement des systèmes vidéosurveillance intelligente ou automatique" (this project is [only] the beginning of the development of intelligent/automatic video-surveillance systems) — an implicit acknowledgment of incompleteness.
- Chapter II lists generic disadvantages of face recognition as a biometric modality (sensitive to lighting/expression, sensitive to appearance changes like beard/moustache/surgery/piercings, cannot distinguish identical twins) but these are presented as background knowledge about face recognition in general, not as limitations specific to the author's implementation.
- No discussion of accuracy shortfalls, failure cases, computational cost, scalability to many cameras, or false-alarm rate of the actual built system.

## Claimed contributions

- Design and implementation of a client–server intelligent-video-surveillance prototype that detects faces in live camera feeds and recorded video files (mp4/avi/wmv) using Viola–Jones, matches against an enrolled-persons database, and displays alerts with camera geolocation on a map, plus a searchable detection history.
- A survey/background synthesis of biometric modalities (Chapter I) and face-detection method families (Chapter II: geometry-based, skin-color-based, PCA/Eigenfaces, probabilistic/Bayesian, neural-network-based, hybrid methods).
- A description of IP-video-surveillance infrastructure options (server-PC platforms vs. NVR appliances, transport protocols, 2-tier/3-tier/N-tier client-server models) as design-space background for the chosen architecture.

## Critical assessment (my own)

- **The central claimed capability — face *recognition*/identity matching — is never technically specified.** Viola–Jones is a face *detector*, not a recognizer; it outputs "there is a face here," not "this face belongs to person X." The thesis's own architecture diagram (Fig. II.2) correctly shows detection → normalization → feature extraction → feature comparison → identity as four distinct steps, but the implementation chapter only ever discusses/implements the detection step. How "faces entering by camera" are actually compared to the enrolled database (what feature vector, what distance/similarity threshold, what matching algorithm) is left completely unspecified — a serious gap between the stated objective ("comparaison de ces visages... si la comparaison est positive... alerte") and what is demonstrably built.
- **No evaluation of the author's own system whatsoever.** All quantitative figures in the document belong to the original Viola–Jones paper, not to this thesis's contribution. This makes it impossible to assess accuracy, false-alarm rate, or real-world viability of the system as built.
- **Chapters I–III are dominated by generic literature/textbook background** (biometrics taxonomy, face-detection method survey, client-server tiering, IP video transport protocols, network security basics) rather than original analysis; very little of this material is specific to video-surveillance research problems or connects tightly to what is eventually implemented.
- **Single camera / single "wanted person" framing.** The scenario is explicitly a one-person watchlist match-and-alert system, not general multi-object or multi-person analytics, and does not address crowd scenes, multi-camera hand-off/re-identification, or behavior analysis at all — despite the thesis title referencing "vidéosurveillance intelligente" broadly.
- **No comparison to alternative/competing systems**, either qualitatively or empirically, weakening any claim that Viola–Jones was the "right" choice beyond restating its historical reputation.
- **Editorial/structural weaknesses** (mislabeled chapter numbers, duplicate table IDs, an apparently missing "Conclusion générale" page) suggest limited proofreading and, by extension, limited depth of critical self-review — consistent with this being an entry-level Master's PFE rather than a polished research contribution.
- Overall this document is best read as a competent but shallow, single-technique face-detection-triggered-alert prototype from 2013/2014 — useful as a data point on the low end of the local research landscape's technical maturity, not as prior art that meaningfully anticipates agentic or multi-agent surveillance architectures.

## Verbatim quotes

1. Objective statement (Introduction générale, p.1–2): *"L'objectif de notre travail est la conception et la réalisation d'un système de Vidéosurveillance intelligente."*
2. English abstract (unnumbered abstract page): *"The aim of our work is the realization of Video-surveillance systems intelligent or automatic based face recognition only person required, which are stored in a database of faces, comparison of these faces with entrant faces by the cameras if the comparison is positive camera sent a warning to the server."*
3. Self-assessment of scope (Résumé, unnumbered page): *"Ce projet est le début du développement des systèmes vidéosurveillance intelligente ou automatique."*
4. System description (Chapter IV, p.53): *"Le système vidéosurveillance se compose de deux applications application serveur et application client qui Capture des images de caméra et les envoie au serveur. Application Serveur : reçoit les vidéo en ligne et si une caméra détecte un visage d'une personne est tenue Caméra envoyer l'ID au Serveur, à la réception ID le serveur affiche ID de ce personne et la localisation de camera qui envoyer le message dans un carte géographique le système lance un alerte à l'utilisateur."*
5. Chapter III method framing (p.23): *"Le but de notre travail est la réalisation d'un système de la vidéosurveillance intelligente basé sur la reconnaissance faciale. Nous présentons dans ce chapitre d'une part l'approche viola et Jones pour la détection visage dans un temps real."*

## Relevance to "agentic multi-agent surveillance system" research direction

Low/none. This thesis is a single-technique (Viola–Jones face detection), single-server, client-camera CCTV alerting prototype with no autonomous agents, no inter-camera coordination or negotiation, no anomaly/behavior reasoning, no explainability layer, and no LLM or planning component of any kind. Its only tangential connection to a multi-camera surveillance narrative is superficial: multiple IP cameras report to one central server and their locations are shown on a shared map — a topology, not a multi-agent architecture, since there is no autonomy or decision-making distributed to the cameras themselves. For an "agentic multi-agent surveillance system" positioning analysis, this document is useful primarily as evidence of the *baseline* technical maturity of prior local (USDB/LRDSI) student work circa 2013–2014 — i.e., a floor to contrast against when arguing the novelty of an agentic/multi-agent, autonomous-reasoning-based surveillance system.
