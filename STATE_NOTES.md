# Task state notes (internal)

## Key paths
- /home/ubuntu/pfe/00_PROJECT_VISION.md — modernized theme doc (done)
- /home/ubuntu/pfe/01_ONE_MONTH_SCHEDULE.md — 30-day schedule (done)
- /home/ubuntu/pfe/research/*.md — 12 wide-research reports with BibTeX sections at end of each
- /home/ubuntu/pfe/research/summary.json — key findings + stacks per subtopic
- /home/ubuntu/pfe/code/ — AURA-MAS codebase (done, tested: 6/6 unit tests pass)
- /home/ubuntu/pfe/thesis/latex/ — thesis workspace copied from user's master template
- /home/ubuntu/upload/extracted/master — original template (main.tex uses extreport, polyglossia+Arabic → needs XeLaTeX, biblatex backend=bibtex, glossaries acronyms, fncychap Glenn, parts + \input{Chapters/chapterN})
- TeXLive with xetex INSTALLED (session tex)

## Template structure (main.tex)
- Title page: ESI-SBA, Arabic/English headers, logo Assets/Logo_ESI_SBA.png, Master's thesis, IASD specialization, presented by BELMANA Soufyane, supervisor Pr. AMAR BENSABER Djamel, jury (Dr. BEZZAOUCHA Fatima Souad president, Dr. CHIKH Asma examiner, Dr. ABDELHAK Soumia incubator rep), academic year 2025/2026
- Acknowledgement, Abstract EN, Résumé FR, ملخص AR, TOC/LOF/LOT/acronyms
- Parts each with \input{Chapters/chapterX}; bibliography via \printbibliography, Bibliography/bibliography.bib
- Chapters dir emptied; need new chapter1..7 + chapter_sota equivalents

## Experimental results (real, from sandbox runs on scenario demo_site_01)
| mode | f1 | precision | recall | time-to-alert (s) | false alerts/h | coord msgs |
| centralized | 0.667 | 0.667 | 0.667 | 21.56 | 67.9 | 0 |
| mas-nocoord | 0.571 | 0.5 | 0.667 | 13.25 | 107.5 | 0 |
| mas-rules | 0.571 | 0.5 | 0.667 | 13.3 | 106.9 | 4 |
| mas-auction | 0.667 | 0.667 | 0.667 | 13.8 | 53.6 | 10 |
Narrative: MAS reduces time-to-alert ~36% vs centralized (13.8 vs 21.6 s); auction coordination restores precision (0.667 vs 0.5) and halves false alerts/h vs no-coord (53.6 vs 107.5) at modest message overhead (10 msgs). Scenario: 2 cameras (real pedestrian clips people.mp4/street.mp4 from intel-iot-devkit sample-videos GitHub), 1 synthetic glass-break audio; GT: intrusion zone_A 3-35s, loitering entry 16-46s, audio_glass_break 14-16s.
Unit tests: 6 passed (bus wildcards, noisy-OR fusion corroboration, auction best-bidder, policy thresholds+cooldown, metrics eval, guardrail rejects fabricated evidence).

## Figures in thesis/latex/Assets/
- fig_detection_quality.png (F1+precision bars)
- fig_system_metrics.png (time-to-alert + false alerts/h)
- fig_coordination_overhead.png (messages)
- evidence_anonymized.jpg (blurred person evidence example)
- Logo_ESI_SBA.png
- architecture.mmd at /home/ubuntu/pfe/thesis/architecture.mmd (needs manus-render-diagram → Assets/fig_architecture.png)

## Thesis plan (7 chapters, adapt template part structure)
1. General Introduction (context, problem, objectives, contributions C1-C5)
2. Background: MAS & agentic AI fundamentals
3. Background: intelligent surveillance perception (detection/tracking/VAD/audio)
4 (chapter_sota). State of the art: edge video analytics, coordination, agentic frameworks, privacy/regulation
5 (chapter4). AURA-MAS design: architecture, agents, protocols, schemas, privacy-by-design
6 (chapter5). Implementation: stack, code structure, algorithms
7 (chapter6). Evaluation & results: setup, metrics, ablations (table above), discussion, limitations
8 (chapter7). Conclusion & future work
Title: "AURA-MAS: Agentic and Multi-Agent Intelligent Surveillance — A Privacy-Aware, Edge-First Hierarchical Multi-Agent System for Multimodal Event Detection, Inter-Sensor Coordination, and Explainable Alerting"

## Bibliography: harvest BibTeX blocks from research/*.md files (each has 8-15 entries at end)

## Progress (Phase 5)
- DONE: architecture diagram rendered -> thesis/latex/Assets/fig_architecture.png
- DONE: main.tex adapted (title AURA-MAS, EN/FR/AR abstracts replaced, 30 new acronyms incl \gls{mas},\gls{llm},\gls{vlm},\gls{cnp},\gls{yolo},\gls{vad},\gls{sed},\gls{mqtt},\gls{qos},\gls{gdpr},\gls{clip},\gls{fps},\gls{iou},\gls{json},\gls{dsp},\gls{marl},\gls{bdi},\gls{fipa},\gls{acl},\gls{reid},\gls{iot},\gls{map}; parts: I Introduction(ch1), II Background+SOTA(ch2,ch3,chapter_sota), III Design(ch4), IV Implementation(ch5), V Evaluation(ch6), Conclusion(ch7))
- DONE: bibliography.bib with 94 entries (harvested 82 from research/*.md + 12 classics: smith1980contract, wooldridge2009introduction, rao1995bdi, zhang2022bytetrack, radford2021clip, sultani2018ucfcrime, parker2002alliance, euaiact2024, gdpr2016, hershey2017cnn, yao2023react, langgraph2024)
- DONE: chapters 1,2,3,chapter_sota,4,5 written (labels: chap:introduction, chap:background_mas, chap:background_perception, chap:sota, chap:design incl eq:noisyor + fig:architecture + tab:agents + tab:privacy + sec:design_fusion + sec:design_coordination, chap:implementation incl tab:stack)
- TeXLive installed (texlive-xetex etc). Template needs XeLaTeX (polyglossia/Arabic, Noto Sans Arabic font from fonts-noto)

## Remaining steps
1. Write chapter6 (evaluation: use results table above; figures fig_detection_quality.png, fig_system_metrics.png, fig_coordination_overhead.png, evidence_anonymized.jpg; label chap:evaluation) and chapter7 (conclusion; label chap:conclusion)
2. Compile: cd /home/ubuntu/pfe/thesis/latex && latexmk -xelatex main.tex (needs makeglossaries + bibtex backend; biblatex backend=bibtex so run: xelatex, bibtex main, makeglossaries main, xelatex x2)
3. Package: zip code (exclude data/clips large files? keep, ~17MB), thesis latex+PDF, research reports; deliver with 00_PROJECT_VISION.md + 01_ONE_MONTH_SCHEDULE.md

## PDF verification (main.pdf, 53 pages, compiled OK)
- Title page correct (AURA-MAS title, ESI-SBA, jury, 2025/2026)
- EN/FR/AR abstracts render correctly (Arabic RTL OK)
- Architecture figure renders p28; agent roles table p29; noisy-OR eq 5.1 p30
- 1 remaining benign LaTeX warning; no undefined citations/references
- Fixed: bidi ordering (polyglossia moved to end of preamble), biblatex moved after polyglossia, escaped & in 2 bib titles, installed texlive-lang-arabic
- Remaining: check eval chapter figures pages (~40-45), then package everything
