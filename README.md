# AURA-MAS — Agentic Multi-Agent Intelligent Surveillance

Privacy-aware, edge-first, hierarchical multi-agent system for multimodal event
detection, inter-sensor coordination, and explainable alerting on semi-closed
sites. Final-year Master's project (PFE) — AI & Data Science.

## Architecture

```
Layer 3  Governance  : Streamlit operator console · audit log · evidence store
Layer 2  Coordination: FusionAgent · CoordinatorAgent (auction) · PolicyAgent · ExplanationAgent (LLM, rule-guarded)
Layer 1  Edge        : CameraAgent (YOLO11n + ByteTrack + zones + CLIP anomaly) · AudioAgent (YAMNet / DSP)
Bus                  : MQTT (events) + Redis Streams (durable alerts) — LocalBus fallback for single-process demos
```

## Quick start

```bash
# 1. environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # core; see requirements-full.txt for ML extras

# 2. brokers (optional — everything falls back to in-process bus / JSONL)
./deploy/init_secrets.sh                 # broker credentials -> .env (git-ignored)
set -a && source .env && set +a
docker compose up -d                     # Mosquitto + Redis, bound to 127.0.0.1 only

# 3. offline tests (no models needed, <5 s)
python -m pytest aura_mas/tests -q

# 4. run a scenario end-to-end (needs ultralytics + a video clip)
python -m aura_mas.scenarios.replay scenarios/intrusion_01.json --mode mas-auction

# 5. compare architectures (the thesis ablation)
for m in centralized mas-nocoord mas-rules mas-auction; do
  python -m aura_mas.scenarios.replay scenarios/intrusion_01.json --mode $m
done
python -m aura_mas.eval.metrics "results/run_*.json" --out results/summary.csv

# 6. operator dashboard (password from .env; see deploy/README.md)
streamlit run aura_mas/dashboard/app.py --server.address 127.0.0.1
```

See [`deploy/README.md`](deploy/README.md) for the security configuration:
broker authentication, the console's fail-closed password gate, TLS for remote
edge nodes, and every environment variable the code reads.

## Raspberry Pi showcase

The cleanest demo is to use the Raspberry Pi as an edge sensor node and keep
fusion, policy, and the dashboard on a laptop or mini-PC. That matches the
project architecture and avoids asking the Pi to do heavy vision work.

Recommended split:

- Raspberry Pi: camera/audio capture, lightweight event publishing, optional
  MQTT transport.
- Main machine: FusionAgent, CoordinatorAgent, PolicyAgent, ExplanationAgent,
  Redis, and the Streamlit operator console.

For a low-friction showcase, run the Pi in a minimal mode:

1. Install the core Python dependencies on the Pi.
2. Use a small camera source or a prerecorded clip for the edge demo.
3. Disable the heaviest optional features on the Pi, especially CLIP and LLM
   explanation.
4. Keep the dashboard on the main machine and feed it events over MQTT or the
   local JSONL fallback.

If you want a full two-machine demo, a practical layout is:

```bash
# Raspberry Pi: edge node
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m aura_mas.scenarios.replay scenarios/demo_site_01.json --mode mas-nocoord --bus local

# Laptop / control room
docker compose up -d
streamlit run aura_mas/dashboard/app.py
```

This gives you a credible showcase story: the Pi performs edge detection, the
central machine handles coordination and operator review, and the UI displays
the resulting alerts.

## Repository layout

```
aura_mas/
  core/       bus.py (MQTT/Redis/local transports, schemas)  privacy.py (anonymization)
  agents/     base.py  camera_agent.py  audio_agent.py  fusion_agent.py
              coordinator_agent.py  policy_agent.py  explanation_agent.py
  scenarios/  replay.py (scenario runner + centralized baseline)  *.json manifests
  eval/       metrics.py (F1, time-to-alert, false alerts/hour, coordination overhead)
  dashboard/  app.py (Streamlit operator console)
  tests/      test_pipeline.py (offline unit tests)
configs/      site zones, thresholds
docker-compose.yml  Mosquitto + Redis
```

## Thesis ablations produced by this code

| Comparison | Command axis | Metrics |
|---|---|---|
| Centralized vs hierarchical MAS | `--mode centralized` vs `mas-*` | time-to-alert, F1, wall time |
| No coordination vs rules vs auction | `mas-nocoord/mas-rules/mas-auction` | F1, verified↑/↓, messages, allocation ms |
| Vision-only vs audio-visual | include/exclude audio sensors in manifest | precision, false alerts/hour |
| Template vs LLM explanation | `--llm` flag | guardrail rejections, evidence completeness |

## Privacy by design

Raw frames never leave the edge agent. All exported evidence passes through
`core/privacy.py` (person/face blurring). Every policy decision and operator
action is appended to an immutable audit stream. No biometric identification
anywhere in the system.
