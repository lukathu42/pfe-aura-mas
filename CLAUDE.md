# AURA-MAS — CLAUDE.md

Guidance for Claude Code sessions working in this repository.

## What this project is

**AURA-MAS** (Agentic and Multi-Agent Intelligent Surveillance) is a Master's
thesis project (PFE, AI & Data Science, ESI-SBA). It is a privacy-aware,
edge-first, hierarchical multi-agent system for multimodal (video + audio)
event detection, inter-sensor coordination via an auction protocol, and
LLM-guarded explainable alerting on semi-closed sites (e.g. warehouses,
campuses).

The repository doubles as: (1) a runnable Python prototype, and (2) the
source material (research, figures, results, LaTeX) for the written thesis.

**Read `research/aura-mas-landscape-positioning/` before claiming novelty
in thesis text** — it documents where AURA-MAS sits relative to prior local
theses and published work (findings F1-F6), and flags that prior results
(see below) come from a small toy scenario that needs to be scaled up before
being presented as the thesis's real evaluation numbers.

## Current state (important — read before planning work)

This is **not a Day-1 scaffold**. A working prototype already exists and
implements most of Weeks 1-3 of
`research/planning/One-Month Execution Schedule — AURA-MAS PFE.md`:
all six agents run end-to-end, the auction coordination protocol works, a
Streamlit dashboard exists, unit tests pass (6/6), a first evaluation run
(`research/reports/STATE_NOTES.md`) compared centralized vs. MAS-nocoord vs.
MAS-rules vs. MAS-auction, and a thesis PDF already compiles
(`AURA-MAS_Thesis_LaTeX/main.pdf`).

**However**, this was produced in a single fast sandbox pass, not through
the 30 days of iterative work the schedule describes. Treat it as a strong
first draft / scaffold to understand deeply, validate, and harden — not as
finished, submittable work. In particular, before trusting or extending
anything:

- **Update (2026-08-13, `code-hardening` branch):** the original n=1
  `demo_site_01`-only evaluation described above has been superseded by a
  44-run campaign across a real 6-scenario pack (`results/summary.csv`,
  `results/evaluation_campaign_notes.md`). Read that notes file before
  trusting anything in `results/` — it documents three real, pre-existing
  bugs found and fixed (a silently-broken `.venv`; `centralized` mode's
  timing rules using wall-clock instead of video time, so it could never
  detect loitering/abandoned-object; `intrusion_01`'s original video sources
  being synthetic placeholder graphics YOLO can never see a person in, so
  that scenario never worked even in the results already on disk before this
  branch started). `data/clips_real/` now holds real, citably-licensed
  video/audio (AIRTLab violence dataset, ABODA, ESC-50) — see
  `data/clips_real/manifest.json` for sources and why UCF-Crime/Avenue
  weren't used. `data/clips/intrusion.mp4` and `overview.mp4` are still on
  disk but nothing in `scenarios/` references them anymore — don't reuse
  them, they're synthetic stick-figure placeholders, not real footage.
- CLIP anomaly scoring is now calibrated (`results/clip_anomaly_calibration_notes.md`,
  AUC=0.308 — worse than random, root-caused to a prompt/scene domain
  mismatch, not a broken scorer).
- **Update (2026-08-18, `code-hardening` branch):** YAMNet is now installed
  (`tensorflow-cpu`, local SavedModel fetched by
  `aura_mas/scripts/fetch_yamnet.py` — `tensorflow_hub`'s `tfhub.dev` URL is
  dead, HTTP 404) and `AudioAgent` emits class-specific events
  (`audio_glass_break`, `audio_alarm`, ...) instead of generic
  `audio_anomaly` when it loads successfully. See
  `results/yamnet_integration_notes.md` for the install process and two real
  bugs found and fixed while making it actually work end-to-end (mean-pooling
  on independently-rewindowed 1s chunks was diluting short transients below
  threshold; `AudioAgent` never set `zone` on emitted events, which
  independently blocked the FusionAgent corroboration claim C3 even with the
  right event labels). `AudioAgent(backend=...)` now supports `auto | yamnet
  | dsp` so DSP-vs-YAMNet is a selectable, documented ablation — pass
  `--audio-backend` to `aura_mas.scenarios.replay`, or check
  `run["audio_backend"]` / `agent_metrics["<mic_id>"]["backend"]` in a run
  JSON before citing a result, rather than assuming YAMNet ran. See
  `results/evaluation_campaign_v2_notes.md` for the re-run campaign numbers
  and `results/methodology_changes.md` for every scoring-affecting change
  made in this pass, mapped old→new.
- No `configs/` directory exists yet despite the README describing one;
  zone/threshold config currently lives inline in `scenarios/*.json`.

Before writing thesis prose or citing metrics, regenerate the numbers
yourself and check `results/summary.csv` timestamps against what's cited.
Detection showed real run-to-run non-determinism during this campaign
(likely PyTorch CPU-threading float non-determinism interacting with
borderline confidence thresholds) — treat any single run as noisy; rerun
N≥3 times before citing a number as final.

## Architecture

```
Layer 3  Governance  : Streamlit operator console · audit log (SQLite/JSONL) · evidence store
Layer 2  Coordination: FusionAgent · CoordinatorAgent (auction) · PolicyAgent · ExplanationAgent (LLM, rule-guarded)
Layer 1  Edge        : CameraAgent (YOLO11n + ByteTrack + zone rules + optional CLIP anomaly)
                        AudioAgent (YAMNet if available, else DSP energy/flatness fallback)
Bus                  : MQTT (events, high-frequency) + Redis Streams (durable alerts)
                        LocalBus (in-process pub/sub) as fallback for tests/single-process demos
```

Agents are message-driven (`aura_mas/agents/base.py:Agent`): a belief store
(`self.beliefs`), bus subscriptions dispatched by callbacks, and an optional
periodic `tick()`. All cross-agent communication goes through
`aura_mas/core/bus.py` — never call another agent's methods directly.

### Message flow / topics (`aura_mas/core/bus.py`)

Schemas are plain dataclasses (`Detection`, `Event`, `Alert`) serialized to
JSON — keep changes to these backward-compatible with `results/*.json` and
`data/*.jsonl` already on disk, or regenerate them.

### Fusion & coordination logic worth knowing before touching it

- **FusionAgent**: sliding-window, keyed by `(zone, EVENT_FAMILY)`; combines
  confidences with **noisy-OR** weighted by `MODALITY_RELIABILITY`
  (video 0.9, audio 0.7) — corroborating evidence from a second
  sensor/modality strictly increases confidence. This is thesis claim C3.
- **CoordinatorAgent**: when FusionAgent's confidence lands in the
  "gray zone" (default `0.35–0.75`), it announces a verification task;
  CameraAgents bid a view-utility score; best bidder re-verifies. Modes:
  `auction | roundrobin | off` — `roundrobin`/`off` exist specifically as
  ablation baselines, don't remove them.
- **ExplanationAgent**: state-graph (collect evidence → describe → draft →
  **guardrail check** → emit). The guardrail rejects any report that cites
  an `evidence_id` not present in the alert — this is a thesis safety
  claim, keep it strict, don't loosen it to "fix" a failing report.

### Privacy

`aura_mas/core/privacy.py` blurs faces/persons before any evidence image is
exported. This is a stated design invariant ("no biometric identification
anywhere in the system") — any new evidence-export path must go through it.

## Repository layout

### Repo cleanup (2026-08-21) — the duplication described in older notes is gone

A prior pass through this repo was a flattened extraction of several
delivery bundles and had real, confusing duplication. A 2026-08-21 cleanup
resolved it; if you're reading an older note (commit message, research
finding) that references any of the following, treat it as historical, not
current:

- **Root-level `.py` files** (`camera_agent.py`, `bus.py`, `app.py`, etc.)
  that duplicated `aura_mas/` have been deleted. `aura_mas/` is the sole
  copy — by the time they were removed several had already drifted from the
  `aura_mas/` versions, so never trust or edit a root-level agent file if
  one reappears; nothing imports it.
- **LaTeX**: the stale, failed root-level build (`main.tex`, `chapter*.tex`,
  a 15-byte stub `main.pdf`, plus their compile artifacts) has been deleted.
  `AURA-MAS_Thesis_LaTeX/main.pdf` (compiled from `AURA-MAS_Thesis_LaTeX/main.tex`)
  is the only compiled thesis now. That directory is intentionally left at
  the repo root rather than moved into `research/`: dozens of citations
  across `research/aura-mas-landscape-positioning/` and
  `research/reports/research-report-v1/` reference exact paths like
  `AURA-MAS_Thesis_LaTeX/Chapters/chapter6.tex:84` as evidence, and moving
  the directory would silently break that audit trail.
- `engineerthesis/` (an unrelated reference thesis by a different author)
  and `AURA-MAS_Thesis_LaTeX/Master_BELMANA_Soufyane.pdf` (a different named
  student's compiled thesis, kept only as a LaTeX formatting reference) have
  both been deleted outright — they were other people's academic work and
  didn't belong in a public repo. Prior research notes had already flagged
  the PDF for removal (`research/reports/research-report-v1/01-project-summary.md:332`).
- No `*.zip` delivery-bundle snapshots exist in the working tree anymore.

### `research/` layout

Non-code prose — planning docs, literature notes, status/audit reports,
presentation material — lives under `research/`, one folder per category:
`research/planning/`, `research/literature-review/`, `research/reports/`,
`research/presentation/`, plus the pre-existing
`research/aura-mas-landscape-positioning/` (left un-renamed for the same
citation-integrity reason as the LaTeX dir above — its own findings files
cite `research/aura-mas-landscape-positioning/findings/F*` by path). Files
were relocated with `git mv` (history preserved) and, except for
`research/planning/EXECUTION_PLAN.md`'s corrected reference to the deleted
stale root `AURA-MAS_Thesis.pdf`, moved without editing their content — so
other documents' bare-filename citations (e.g. `` `STATE_NOTES.md` ``)
remain textually valid; they were always prose pointers meant to be
grepped, not clickable relative links, so a moved file is still findable by
name even though its directory changed.

## Running things

```bash
source .venv/bin/activate               # venv already exists with core deps
python -m pytest aura_mas/tests -q      # offline unit tests, no models, <1s

docker compose up -d                    # Mosquitto + Redis (optional — LocalBus fallback works without)

python -m aura_mas.scenarios.replay scenarios/intrusion_01.json --mode mas-auction
for m in centralized mas-nocoord mas-rules mas-auction; do
  python -m aura_mas.scenarios.replay scenarios/intrusion_01.json --mode $m
done
python -m aura_mas.eval.metrics "results/run_*.json" --out results/summary.csv

streamlit run aura_mas/dashboard/app.py
```

Heavy optional deps (`tensorflow`+`tensorflow_hub` for YAMNet, CLIP+torch,
`langgraph`) are commented out in `requirements.txt` and lazily imported —
the system is designed to degrade gracefully without them. Don't make them
hard requirements without checking with the user; this fallback behavior is
a deliberate risk-mitigation from the execution plan's "Risk fallback table".

**If reinstalling `torch`/`ultralytics` from scratch**, install torch from
the CPU wheel index first (`pip install torch torchvision --index-url
https://download.pytorch.org/whl/cpu`) *before* `pip install -r
requirements.txt`. A plain `pip install torch` (or letting `ultralytics`
pull it in transitively) resolves to the CUDA build by default even on a
machine with no GPU, silently downloading several GB of `nvidia-*`/`triton`
packages — this happened during the 2026-08-13 evaluation pass and ate half
the available disk before being caught.

## Working conventions

- No comments explaining *what* code does; existing style uses module/class
  docstrings for *why* (see `fusion_agent.py`, `coordinator_agent.py` for
  the level of terseness expected) and inline comments only for non-obvious
  algorithmic choices (noisy-OR weighting, gray-zone thresholds).
- Keep `roundrobin`/`off`/`centralized`/`mas-nocoord` code paths alive even
  though `mas-auction` is the "main" mode — they're the thesis's ablation
  baselines (Results chapter, comparison table in README).
- When changing message schemas (`Detection`/`Event`/`Alert`), check
  `data/*.jsonl` and `results/run_*.json` for consumers before breaking
  compatibility — those files are cited evaluation artifacts.
- This is thesis material: don't silently rewrite evaluation numbers,
  chapter text, or research findings. Surface discrepancies to the user
  instead of "fixing" them unilaterally — academic integrity matters here.
