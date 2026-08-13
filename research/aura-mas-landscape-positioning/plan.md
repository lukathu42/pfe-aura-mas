# Plan — Agentic Multi-Agent Surveillance: Landscape & Positioning Research

## 0. Context discovered before search began (existing-work check)

This is not a greenfield literature search. The working directory already contains:

- **AURA-MAS**: a fully implemented prototype (`aura_mas/`), a compiled Master's thesis PDF, a
  compiled Engineer thesis PDF, a 94-entry `bibliography.bib`, a `chapter_sota.tex`, and several
  vision/planning docs (`AURA-MAS: Modernized PFE Theme and Project Vision.md`,
  `AURA-MAS_Deep_Dive_Report.en/fr.md`, `pasted_content_2.txt`). These were produced by a prior
  autonomous-agent session (self-labeled "Manus AI", sandbox paths `/home/ubuntu/pfe/...`,
  see `STATE_NOTES.md`). The compiled title pages carry the name **BELMANA Soufyane** and
  supervisor **Pr. AMAR BENSABER Djamel** at **ESI-SBA** — inherited from the LaTeX template and,
  per `STATE_NOTES.md`'s own change-log, apparently never overwritten with the actual author's
  identity.
- **`pfe_surviellance_pfe/`**: an earlier, simpler prototype of the same surveillance direction
  (warehouse intrusion/abandoned-object/fall detection, Streamlit app), with its own scope doc and
  a prior `deep-research-report.md`.
- **`pfe_agentic_ai/`**: an unrelated project (an "agentic educational toy" for resource-constrained
  systems, driven by a separate official "Sujet de Stage" PDF). Treated as **out of scope** for
  this surveillance-positioning research; flagged, not analyzed in depth.
- **`../Documents/`**: 7 PDFs — theses/papers from the user's own academic environment, not yet
  read or incorporated into any prior AI-generated synthesis. **This is the primary novel corpus**
  for this investigation.
- **`Research_Paper/`, `ResearchPapers/`**: ~22 arXiv-style papers, general ML/AI reading, only
  partially relevant (surveillance/agents subset to be triaged).

**Implication for sourcing strategy**: the previously-generated `chapter_sota.tex` and
`bibliography.bib` are treated as *artifacts to audit*, not as ground truth — they were produced
by an AI agent from an external, no-longer-accessible search session, and have not been
human-verified. A verification spot-check is part of this plan (Phase 6.5 equivalent).

## 1. Reframed question

Not: *"Is an agentic multi-agent surveillance system a good thesis idea?"*
Instead: *"Given an existing, AI-drafted architecture (AURA-MAS) already built on an unverified
literature base, what — if anything — in that direction is genuinely novel against (a) the user's
own local academic corpus and (b) the broader MAS/agentic-AI literature; and how can the work be
split into two independently defensible academic contributions (State Engineer diploma +
Master's) without one being a rebrand of the other?"*

## 2. Hypotheses (falsifiable)

- **H1**: The AURA-MAS system-level framing (hierarchical edge MAS + auditable auction coordination
  + decision/generation-decoupled LLM explanation) is not duplicated wholesale by any single local
  prior thesis in `Documents/` — i.e., no local thesis combines multi-agent coordination *and*
  agentic LLM explanation *and* privacy-by-design for surveillance.
- **H2**: Multi-agent surveillance *architecture* per se (multiple cooperating detection/tracking
  modules) is not new — it is well established in the broader literature (and likely partially in
  local theses) — so "multi-agent" alone cannot be the contribution; novelty, if any, sits in the
  coordination mechanism and/or the evaluation methodology, not in agent decomposition.
- **H3**: The existing "experimental results" in `STATE_NOTES.md` / thesis chapters (2 real video
  clips + 1 synthetic audio clip, single scenario) do not constitute sufficient evidence for the
  comparative claims already written into the thesis chapters, and the bibliography contains
  entries that need independent verification before reuse.
- **H4**: A defensible two-thesis split separates system/engineering scope (build, integrate,
  deploy — Engineer diploma) from a narrower research question about one specific mechanism
  (coordination auditability or grounded explanation — Master's), rather than splitting by
  "breadth" of the same system.

## 3. Genre & blocks

Genre: **landscape + validation hybrid** (literature landscape *and* validating/critiquing a
specific proposed direction). Blocks: existing-work audit, per-document structured analysis,
comparison matrix, terminology analysis (MAS vs agentic AI vs orchestration), gap ranking,
contribution candidates, two-thesis structuring, risk register, adversarial pass.

## 4. Sourcing strategy

| Channel | Role | Priority |
|---|---|---|
| `../Documents/*.pdf` (7 files) | Primary — local academic corpus, same institution/context | Highest |
| `AURA-MAS_Thesis_LaTeX/Bibliography/bibliography.bib` + `chapter_sota.tex` | Secondary — prior AI-drafted SOTA, to be spot-verified, not trusted blindly | Audit, not primary evidence |
| `pasted_content_2.txt`, `AURA-MAS_Deep_Dive_Report.*.md`, `pfe_surviellance_pfe/deep-research-report.md` | Tertiary — prior AI research syntheses, same treatment as above | Audit |
| `Research_Paper/`, `ResearchPapers/` (~22 files) | Supplementary — general AI/ML corpus, triage for MAS/agentic relevance | Medium |
| WebSearch (spot checks only) | Verify a sample of bibliography entries and check for very recent (2025-2026) directly competing work | Verification |

## 5. Stop criteria

- All 7 Documents/ PDFs read and structurally extracted.
- Research_Paper/ResearchPapers triaged; relevant subset (est. 3-6) analyzed.
- ≥10 bibliography.bib entries spot-checked against the web.
- Comparison table, gap ranking, terminology section, contribution candidates, and two-thesis
  structure all grounded in the above, not invented.

## Changelog
- Init: scoped after discovering existing AURA-MAS build + prior AI-drafted thesis materials.
