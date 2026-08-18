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
implements most of Weeks 1-3 of `One-Month Execution Schedule — AURA-MAS PFE.md`:
all six agents run end-to-end, the auction coordination protocol works, a
Streamlit dashboard exists, unit tests pass (6/6), a first evaluation run
(`STATE_NOTES.md`) compared centralized vs. MAS-nocoord vs. MAS-rules vs.
MAS-auction, and a 53-page thesis PDF already compiles.

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

- `site/{sensor_id}/detections` — per-frame `Detection` (QoS 0, high freq)
- `site/events` — semantic `Event` from CameraAgent/AudioAgent (QoS 1):
  `intrusion | loitering | abandoned_object | anomaly | audio_scream | audio_glass_break | ...`
- `site/coordination/tasks|bids|awards|verifications` — single-round
  contract-net auction (CoordinatorAgent)
- `aura:alerts` (Redis stream) — final `Alert` from PolicyAgent, durable
- `aura:audit` (Redis stream) — every policy decision + operator action

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

```
aura_mas/            the actual Python package (canonical source of truth)
  core/               bus.py (transports+schemas), privacy.py
  agents/             base, camera_agent, audio_agent, fusion_agent,
                       coordinator_agent, policy_agent, explanation_agent
  scenarios/          replay.py (scenario runner incl. centralized baseline)
  eval/               metrics.py (F1, time-to-alert, false alerts/h, msg overhead)
  dashboard/          app.py (Streamlit operator console)
  tests/              test_pipeline.py (offline, no models needed, <1s)
scenarios/            scenario manifests (also duplicated under aura_mas/scenarios — check both if editing)
data/                 clips/ (legacy — includes 2 synthetic placeholder clips, don't reuse),
                       clips_real/ (real licensed video+audio, see manifest.json),
                       evidence/, alerts_*.jsonl, audit_*.jsonl
results/              summary.csv, run_*.json, figures/
research/             wide-research reports + landscape-positioning study (has its own BibTeX + findings)
AURA-MAS_Thesis_LaTeX/  the real, compiling LaTeX thesis project (main.pdf here is the good one)
docker-compose.yml    Mosquitto + Redis
```

### Known duplication — don't get confused by it

This directory is a flattened extraction of several delivery bundles. Some
duplication is real and you should be aware of it rather than "fixing" it
without asking:

- **Root-level `.py` files** (`camera_agent.py`, `bus.py`, `app.py`, etc.)
  are byte-identical copies of the files under `aura_mas/`. Treat
  `aura_mas/` as canonical; if you edit logic, edit there (the root copies
  will silently go stale — flag this to the user if it matters for a task).
- **LaTeX**: `AURA-MAS_Thesis_LaTeX/main.pdf` is the real, compiled 53-page
  thesis. The root-level `main.tex`/`chapter*.tex`/`main.pdf` are a stale,
  *failed* build (`main.pdf` there is a 15-byte stub) — don't edit those or
  cite that PDF.
- `engineerthesis/` is a different, unrelated reference thesis (original
  template source), not part of AURA-MAS.
- Several `*.zip` files at the root (`AURA-MAS_Code.zip`,
  `AURA-MAS_Thesis_LaTeX.zip`, `masterthesis.zip` [66MB], `engineerthesis.zip`)
  are frozen snapshots of the above — not tracked in git, safe to ignore
  unless the user asks to diff against them.

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
