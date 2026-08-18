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
                 out_path: str | None = None,
                 vision_only: bool = False,
                 audio_backend: str = "auto",
                 rep: int | None = None) -> Dict:
    """mode: mas-auction | mas-rules | mas-nocoord | centralized

    vision_only: drop audio sensors at run time (vision-only vs. audio-visual
    ablation) without needing a duplicate manifest per scenario.

    audio_backend: auto | yamnet | dsp -- forwarded to every AudioAgent, so
    DSP-vs-YAMNet becomes a documented ablation (see run_campaign.py) instead
    of an accident of what happens to be installed.

    rep: repetition index for a multi-run campaign. When set, output
    filenames get a "-rN" suffix so repeat runs don't overwrite each other
    (results/run_*.json and data/alerts_*.jsonl previously used a fixed
    per-(scenario,mode) path and silently clobbered prior runs on rerun).
    None (the default) preserves the original, unsuffixed filenames exactly,
    so the 44 already-cited run/alert files from the v1 campaign stay
    byte-identical in name.
    """
    with open(manifest_path) as f:
        manifest = json.load(f)

    bus = make_bus(bus_kind)
    tag = mode
    if vision_only:
        tag += "-visiononly"
    if audio_backend != "auto":
        tag += f"-{audio_backend}"
    if rep is not None:
        tag += f"-r{rep}"
    store = AlertStore(redis_url=None,
                       jsonl_path=f"data/alerts_{manifest['name']}_{tag}.jsonl")

    camera_specs = [s for s in manifest["sensors"] if s["type"] == "camera"]
    audio_specs = [] if vision_only else [
        s for s in manifest["sensors"] if s["type"] == "audio"]
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
    realtime = mode != "centralized"

    for spec in camera_specs:
        cam = CameraAgent(spec["id"], bus, spec["source"],
                          zones=spec.get("zones", []),
                          enable_clip=spec.get("enable_clip", False),
                          anomaly_threshold=spec.get("anomaly_threshold", 0.55),
                          realtime=realtime)
        cam.start()  # runs setup(): loads YOLO (+ CLIP if enabled)
        agents.append(cam)
        threads.append(threading.Thread(target=cam.run, daemon=True))
    for spec in audio_specs:
        aud = AudioAgent(spec["id"], bus, spec["source"], realtime=realtime,
                         backend=audio_backend, zone=spec.get("zone"))
        aud.start()  # runs setup(): loads YAMNet if backend allows it
        agents.append(aud)
        threads.append(threading.Thread(target=aud.run, daemon=True))

    # Warm up every agent (one dummy inference each) BEFORE starting the
    # timer, so YOLO/CLIP/YAMNet cold-start load latency (~seconds on CPU)
    # doesn't count against time-to-alert -- previously the timer started
    # before agents were even constructed, penalizing short scenarios (see
    # results/evaluation_campaign_notes.md, the fight_01 f1=0 finding).
    for a in agents:
        if hasattr(a, "warmup"):
            a.warmup()
    t_scenario_start = time.time()

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
        "scenario": manifest["name"], "mode": mode, "vision_only": vision_only,
        "audio_backend": audio_backend, "rep": rep, "tag": tag,
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
    out_path = out_path or f"results/run_{manifest['name']}_{tag}.json"
    import os
    os.makedirs("results", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("scenario %s [%s]: %d alerts -> %s",
             manifest["name"], tag, len(alerts_log), out_path)
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
    p.add_argument("--vision-only", action="store_true",
                   help="drop audio sensors (vision-only vs audio-visual ablation)")
    p.add_argument("--audio-backend", default="auto",
                   choices=["auto", "yamnet", "dsp"],
                   help="force the audio classification backend (default: "
                        "auto-detect YAMNet, fall back to DSP)")
    p.add_argument("--rep", type=int, default=None,
                   help="repetition index; appends -rN to output filenames "
                        "so repeat runs don't overwrite each other")
    p.add_argument("--out", default=None,
                   help="override the output run JSON path")
    args = p.parse_args()
    run_scenario(args.manifest, mode=args.mode, bus_kind=args.bus,
                 use_llm=args.llm, vision_only=args.vision_only,
                 audio_backend=args.audio_backend, rep=args.rep,
                 out_path=args.out)


if __name__ == "__main__":
    main()
