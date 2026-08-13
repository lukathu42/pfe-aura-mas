"""Scenario replay runner.

A scenario is a JSON manifest describing sensors (video/audio files), zones,
and ground-truth events with timestamps. The runner instantiates the full
MAS (or the centralized baseline), replays the sources, and records every
alert with wall-clock timing so system metrics (time-to-alert, false alerts
per hour) can be computed by `aura_mas.eval.metrics`.

Manifest example (scenarios/intrusion_01.json):
{
  "name": "intrusion_01",
  "duration_seconds": 60,
  "sensors": [
    {"type": "camera", "id": "cam_01", "source": "data/clips/intrusion.mp4",
     "zones": [{"name": "zone_A", "type": "restricted",
                "polygon": [[100,200],[500,200],[500,470],[100,470]]}]},
    {"type": "audio", "id": "mic_01", "source": "data/clips/glass.wav"}
  ],
  "ground_truth": [
    {"event_type": "intrusion", "zone": "zone_A", "t_start": 12.0, "t_end": 30.0}
  ]
}
"""
from __future__ import annotations

import argparse
import json
import logging
import threading
import time
from typing import Dict, List

from aura_mas.core.bus import AlertStore, make_bus
from aura_mas.agents.camera_agent import CameraAgent
from aura_mas.agents.audio_agent import AudioAgent
from aura_mas.agents.fusion_agent import FusionAgent
from aura_mas.agents.coordinator_agent import CoordinatorAgent
from aura_mas.agents.policy_agent import PolicyAgent
from aura_mas.agents.explanation_agent import ExplanationAgent

log = logging.getLogger("aura.replay")


def run_scenario(manifest_path: str, mode: str = "mas-auction",
                 bus_kind: str = "auto", use_llm: bool = False,
                 out_path: str | None = None) -> Dict:
    """mode: mas-auction | mas-rules | mas-nocoord | centralized"""
    with open(manifest_path) as f:
        manifest = json.load(f)

    bus = make_bus(bus_kind)
    store = AlertStore(redis_url=None,
                       jsonl_path=f"data/alerts_{manifest['name']}_{mode}.jsonl")

    camera_specs = [s for s in manifest["sensors"] if s["type"] == "camera"]
    audio_specs = [s for s in manifest["sensors"] if s["type"] == "audio"]
    cam_ids = [s["id"] for s in camera_specs]

    coord_mode = {"mas-auction": "auction", "mas-rules": "roundrobin",
                  "mas-nocoord": "off", "centralized": "off"}[mode]
    coordinator = CoordinatorAgent("coordinator", bus, mode=coord_mode,
                                   camera_ids=cam_ids)
    explainer = ExplanationAgent() if use_llm else None
    policy = PolicyAgent("policy", bus, store, coordinator=coordinator,
                         explainer=explainer)
    fusion = FusionAgent("fusion", bus, on_hypothesis=policy.on_hypothesis)

    alerts_log: List[Dict] = []
    original_append = store.append

    def timed_append(alert):
        alerts_log.append({"t_wall": time.time(), **json.loads(alert.to_json())})
        original_append(alert)
    store.append = timed_append  # type: ignore[assignment]

    coordinator.start()
    fusion.start()
    policy.start()

    agents, threads = [], []
    t_scenario_start = time.time()
    realtime = mode != "centralized"

    for spec in camera_specs:
        cam = CameraAgent(spec["id"], bus, spec["source"],
                          zones=spec.get("zones", []),
                          enable_clip=spec.get("enable_clip", False),
                          realtime=realtime)
        cam.start()
        agents.append(cam)
        threads.append(threading.Thread(target=cam.run, daemon=True))
    for spec in audio_specs:
        aud = AudioAgent(spec["id"], bus, spec["source"], realtime=realtime)
        aud.start()
        agents.append(aud)
        threads.append(threading.Thread(target=aud.run, daemon=True))

    if mode == "centralized":
        # centralized baseline: process sources sequentially in ONE process,
        # no edge parallelism -> measures the architectural benefit of the MAS
        for th in threads:
            th.start()
            th.join()
    else:
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=manifest.get("duration_seconds", 120) + 30)

    time.sleep(fusion.window_seconds + 1.5)
    fusion.flush_all()
    time.sleep(0.5)

    result = {
        "scenario": manifest["name"], "mode": mode,
        "t_start": t_scenario_start, "wall_seconds": time.time() - t_scenario_start,
        "ground_truth": manifest.get("ground_truth", []),
        "alerts": alerts_log,
        "agent_metrics": {
            "fusion": fusion.metrics, "policy": policy.metrics,
            "coordinator": coordinator.metrics,
            **{a.agent_id: {k: (round(sum(v) / len(v), 1) if k == "infer_ms" and v else v)
                            for k, v in a.metrics.items()} for a in agents},
        },
    }
    out_path = out_path or f"results/run_{manifest['name']}_{mode}.json"
    import os
    os.makedirs("results", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("scenario %s [%s]: %d alerts -> %s",
             manifest["name"], mode, len(alerts_log), out_path)
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="AURA-MAS scenario replay")
    p.add_argument("manifest", help="path to scenario manifest JSON")
    p.add_argument("--mode", default="mas-auction",
                   choices=["mas-auction", "mas-rules", "mas-nocoord",
                            "centralized"])
    p.add_argument("--bus", default="auto", choices=["auto", "mqtt", "local"])
    p.add_argument("--llm", action="store_true",
                   help="enable LLM explanation agent")
    args = p.parse_args()
    run_scenario(args.manifest, mode=args.mode, bus_kind=args.bus,
                 use_llm=args.llm)


if __name__ == "__main__":
    main()
