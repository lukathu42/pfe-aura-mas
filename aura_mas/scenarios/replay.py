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

from aura_mas.core.bus import (
    AlertStore, TOPIC_AWARDS, TOPIC_BIDS, TOPIC_EVENTS, TOPIC_TASKS,
    TOPIC_VERIFICATIONS, make_bus,
)
from aura_mas.agents.camera_agent import CameraAgent
from aura_mas.agents.audio_agent import AudioAgent
from aura_mas.agents.fusion_agent import FusionAgent
from aura_mas.agents.coordinator_agent import CoordinatorAgent
from aura_mas.agents.policy_agent import PolicyAgent
from aura_mas.agents.explanation_agent import ExplanationAgent
from aura_mas.streaming.stream_server import LiveStreamServer, StreamRegistry
from aura_mas.telemetry import configure_logging, configure_tracing
from aura_mas.scenarios.demo_catalog import metadata_for

log = logging.getLogger("aura.replay")


def normalize_timeline(items: List[Dict], scenario_start: float) -> List[Dict]:
    """Convert captured wall timestamps to stable prepared-replay offsets."""
    normalized = []
    for item in items:
        normalized.append({
            "kind": item["kind"],
            "scene_time_seconds": item.get("scene_time_seconds"),
            "wall_offset_seconds": round(
                max(0.0, item["wall_timestamp"] - scenario_start), 3),
            "payload": item["payload"],
        })
    normalized.sort(key=lambda item: (
        item["scene_time_seconds"]
        if item["scene_time_seconds"] is not None
        else item["wall_offset_seconds"],
        item["wall_offset_seconds"],
    ))
    return normalized


def run_scenario(manifest_path: str, mode: str = "mas-auction",
                 bus_kind: str = "auto", use_llm: bool = False,
                 out_path: str | None = None,
                 vision_only: bool = False,
                 audio_backend: str = "auto",
                 rep: int | None = None,
                 bandit_path: str | None = None,
                 priority_model_path: str | None = None,
                 stream: bool = False,
                 stream_port: int = 8080,
                 prepared_out_path: str | None = None) -> Dict:
    """mode: mas-auction | mas-rules | mas-nocoord | centralized |
    mas-auction-bandit

    mas-auction-bandit is a toy research-pass mode (a LinUCB contextual
    bandit picks the auction winner instead of the hand-coded
    `_view_score` heuristic, see aura_mas.core.bandit and
    docs/ai-enhancement-research.md Section 4.2) -- NOT a fifth thesis
    ablation baseline. bandit_path, if given, loads existing bandit weights
    before the run and saves updated weights back to the same path after,
    so a self-play trainer (aura_mas.scripts.train_auction_bandit) can
    accumulate learning across repeated calls.

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
    timeline: List[Dict] = []
    task_scene_times: Dict[str, float | None] = {}
    timeline_lock = threading.Lock()

    def record_timeline(kind: str):
        def callback(topic: str, payload: str) -> None:
            try:
                data = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                return
            scene_time = data.get("scene_time_seconds")
            task_id = data.get("task_id")
            if kind == "task" and task_id:
                task_scene_times[task_id] = scene_time
            elif scene_time is None and task_id:
                scene_time = task_scene_times.get(task_id)
            with timeline_lock:
                timeline.append({
                    "kind": kind,
                    "scene_time_seconds": scene_time,
                    "wall_timestamp": data.get("timestamp", time.time()),
                    "payload": data,
                })
        return callback

    for topic, kind in (
        (TOPIC_EVENTS, "event"), (TOPIC_TASKS, "task"),
        (TOPIC_BIDS, "bid"), (TOPIC_AWARDS, "award"),
        (TOPIC_VERIFICATIONS, "verification"),
    ):
        bus.subscribe(topic, record_timeline(kind))
    tag = mode
    if vision_only:
        tag += "-visiononly"
    if audio_backend != "auto":
        tag += f"-{audio_backend}"
    if rep is not None:
        tag += f"-r{rep}"
    store = AlertStore(redis_url=None,
                       jsonl_path=f"data/alerts_{manifest['name']}_{tag}.jsonl",
                       db_path=None)

    camera_specs = [s for s in manifest["sensors"] if s["type"] == "camera"]
    audio_specs = [] if vision_only else [
        s for s in manifest["sensors"] if s["type"] == "audio"]
    cam_ids = [s["id"] for s in camera_specs]

    coord_mode = {"mas-auction": "auction", "mas-rules": "roundrobin",
                  "mas-nocoord": "off", "centralized": "off",
                  "mas-auction-bandit": "auction-bandit"}[mode]
    coordinator = CoordinatorAgent("coordinator", bus, mode=coord_mode,
                                   camera_ids=cam_ids, bandit_path=bandit_path,
                                   fov_overlap=manifest.get("fov_overlap"),
                                   gray_zone=tuple(manifest.get(
                                       "verification_gray_zone", (0.35, 0.75))))
    explainer = None
    if use_llm:
        configure_tracing()
        explainer = ExplanationAgent()
    policy = PolicyAgent("policy", bus, store, coordinator=coordinator,
                         explainer=explainer,
                         priority_model_path=priority_model_path)
    fusion = FusionAgent("fusion", bus, on_hypothesis=policy.on_hypothesis)

    alerts_log: List[Dict] = []
    original_append = store.append

    def timed_append(alert):
        entry = {"t_wall": time.time(), **json.loads(alert.to_json())}
        alerts_log.append(entry)
        with timeline_lock:
            contributing_scene_times = [
                item.get("scene_time_seconds") for item in timeline
                if item["kind"] == "event"
                and item["payload"].get("event_id") in alert.fused_events
                and item.get("scene_time_seconds") is not None
            ]
            timeline.append({
                "kind": "alert",
                # Reveal the prepared alert only after its last contributing
                # source event; Alert.scene_time_seconds remains the earliest
                # incident time used by evaluation metrics.
                "scene_time_seconds": max(contributing_scene_times)
                if contributing_scene_times else alert.scene_time_seconds,
                "wall_timestamp": entry["t_wall"],
                "payload": json.loads(alert.to_json()),
            })
        original_append(alert)
    store.append = timed_append  # type: ignore[assignment]

    coordinator.start()
    fusion.start()
    policy.start()

    agents, threads = [], []
    realtime = mode != "centralized"

    stream_server = None
    if stream:
        stream_server = LiveStreamServer(port=stream_port)
        stream_server.start()

    for spec in camera_specs:
        cam = CameraAgent(spec["id"], bus, spec["source"],
                          zones=spec.get("zones", []),
                          enable_clip=spec.get("enable_clip", False),
                          anomaly_threshold=spec.get("anomaly_threshold", 0.55),
                          realtime=realtime,
                          loiter_seconds=spec.get("loiter_seconds", 8.0),
                          abandoned_seconds=spec.get("abandoned_seconds", 10.0),
                          min_flow_px=spec.get("min_flow_px", 40.0),
                          person_down_seconds=spec.get("person_down_seconds", 1.5),
                          rapid_window_seconds=spec.get("rapid_window_seconds", 1.0),
                          rapid_min_duration=spec.get("rapid_min_duration", 0.6),
                          detection_conf=spec.get("detection_conf", 0.35))
        cam.start()  # runs setup(): loads YOLO (+ CLIP if enabled)
        StreamRegistry.get_instance().register(cam.agent_id, cam.get_latest_jpeg)
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

    if coord_mode == "auction-bandit" and bandit_path:
        coordinator.save_bandit(bandit_path)

    for spec in camera_specs:
        StreamRegistry.get_instance().unregister(spec["id"])
    if stream_server:
        stream_server.stop()

    # compute per-agent metrics and build final result
    agent_metrics = {a.agent_id: a.metrics for a in agents}
    agent_metrics["coordinator"] = coordinator.metrics
    agent_metrics["fusion"] = fusion.metrics
    agent_metrics["policy"] = policy.metrics
    if explainer:
        agent_metrics["explanation"] = explainer.metrics

    wall_seconds = time.time() - t_scenario_start
    result = {
        "scenario": manifest["name"],
        "mode": mode,
        "vision_only": vision_only,
        "audio_backend": audio_backend,
        "rep": rep,
        "tag": tag,
        "t_start": t_scenario_start,
        "wall_seconds": wall_seconds,
        "ground_truth": manifest.get("ground_truth", []),
        "alerts": alerts_log,
        "agent_metrics": agent_metrics,
    }

    if out_path is None:
        out_path = f"results/run_{manifest['name']}_{tag}.json"
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    if prepared_out_path:
        with timeline_lock:
            captured = list(timeline)
        normalized_timeline = normalize_timeline(captured, t_scenario_start)
        metadata = metadata_for(manifest["name"])
        ground_truth = manifest.get("ground_truth", [])
        context_time = min((gt.get("t_start", 0.0) for gt in ground_truth), default=0.0)
        normalized_timeline.append({
            "kind": "context",
            "scene_time_seconds": context_time,
            "wall_offset_seconds": 0.0,
            "payload": {
                "context_id": f"ctx_{manifest['name']}_deterministic",
                "scenario": manifest["name"],
                "summary": metadata["description"],
                "object_labels": [],
                "safety_observations": metadata.get("detected_event_types", []),
                "source": "deterministic",
                "status": "generated",
                "model": None,
                "provider": None,
                "source_frame_times": [context_time],
                "generated_at": time.time(),
            },
        })
        normalized_timeline.sort(key=lambda item: (
            item["scene_time_seconds"] if item["scene_time_seconds"] is not None
            else item["wall_offset_seconds"], item["wall_offset_seconds"],
        ))
        prepared = {
            "schema_version": 2,
            "scenario": manifest["name"],
            "mode": mode,
            "duration_seconds": manifest.get("duration_seconds", 0),
            "source_run": out_path,
            "metadata": metadata,
            "alerts": [
                {k: v for k, v in alert.items() if k != "t_wall"}
                for alert in alerts_log
            ],
            "timeline": normalized_timeline,
        }
        import os
        os.makedirs(os.path.dirname(prepared_out_path) or ".", exist_ok=True)
        with open(prepared_out_path, "w") as f:
            json.dump(prepared, f, indent=2)
        log.info("prepared replay written to %s", prepared_out_path)
    log.info("scenario %s (%s) finished: %d alerts written to %s",
             manifest["name"], tag, len(alerts_log), out_path)
    return result


def main() -> None:
    configure_logging()
    p = argparse.ArgumentParser(description="AURA-MAS scenario replay")
    p.add_argument("manifest", help="path to scenario manifest JSON")
    p.add_argument("--mode", default="mas-auction",
                   choices=["mas-auction", "mas-rules", "mas-nocoord",
                            "centralized", "mas-auction-bandit"])
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
    p.add_argument("--stream", action="store_true",
                   help="start live HTTP MJPEG stream server for CameraWall frontend")
    p.add_argument("--stream-port", type=int, default=8080,
                   help="port for HTTP MJPEG stream server (default: 8080)")
    p.add_argument("--prepared-out", default=None,
                   help="also write a versioned prepared-replay timeline JSON")
    p.add_argument("--out", default=None,
                   help="override the output run JSON path")
    p.add_argument("--bandit-path", default=None,
                   help="load/save LinUCB weights for --mode mas-auction-bandit "
                        "(default: results/auction_bandit_weights.json)")
    p.add_argument("--priority-model", default=None,
                   help="optional alert-priority model JSON produced by "
                        "aura_mas.scripts.train_alert_priority")
    args = p.parse_args()
    bandit_path = args.bandit_path
    if args.mode == "mas-auction-bandit" and bandit_path is None:
        bandit_path = "results/auction_bandit_weights.json"
    run_scenario(args.manifest, mode=args.mode, bus_kind=args.bus,
                 use_llm=args.llm, vision_only=args.vision_only,
                 audio_backend=args.audio_backend, rep=args.rep,
                 stream=args.stream, stream_port=args.stream_port,
                 prepared_out_path=args.prepared_out,
                 out_path=args.out, bandit_path=bandit_path,
                 priority_model_path=args.priority_model)


if __name__ == "__main__":
    main()
