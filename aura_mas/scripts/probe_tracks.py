"""Track-aware zone probe: measures what YOLO + ByteTrack actually produce.

`probe_zones.py` calls `model.predict`, so it yields no track IDs and cannot
answer the three questions a multi-zone scenario must answer before its
ground truth can be written: how long does one track actually dwell inside a
polygon, how many distinct people are inside a polygon at once, and which way
does a track move through it.

This mirrors `CameraAgent._process_frame` exactly -- same
`model.track(persist=True, tracker="bytetrack.yaml", conf=0.35)` call, same
`infer_fps` frame stride, same blank-frame warmup (which uses `predict`
precisely so ByteTrack state is not seeded with a phantom frame and track IDs
are not shifted), same `video_ts = frame_id / src_fps` clock, and the same
foot-point convention `(cx, y2)` -- so what it reports is what
`ZoneRuleEngine` will see at run time, not an approximation of it.

Dwell runs are broken on zone exit exactly as `ZoneRuleEngine` breaks them
(it pops `_dwell[(tid, zone)]` on the first not-inside frame), so a reported
max dwell is directly comparable to `loiter_seconds`. Static-object runs
apply the same IoU >= 0.6 reset rule as the abandoned-object heuristic.

Usage:
  python -m aura_mas.scripts.probe_tracks data/clips/people.mp4
  python -m aura_mas.scripts.probe_tracks data/clips/people.mp4 \\
      --manifest scenarios/demo_site_01.json --sensor cam_01
  python -m aura_mas.scripts.probe_tracks data/clips/street.mp4 \\
      --dump-tracks --out /tmp/street_probe.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from aura_mas.agents.camera_agent import _iou, point_in_polygon

STATIC_IOU = 0.6


def _load_zones(manifest: Optional[str], sensor: Optional[str],
                zones_json: Optional[str], w: int, h: int) -> List[Dict[str, Any]]:
    if manifest:
        with open(manifest) as f:
            specs = [s for s in json.load(f)["sensors"]
                     if s.get("type") == "camera"]
        if sensor:
            specs = [s for s in specs if s["id"] == sensor]
        if not specs:
            raise SystemExit(f"no camera {sensor!r} in {manifest}")
        zones = [z for s in specs for z in s.get("zones", [])]
        if zones:
            return zones
    if zones_json:
        with open(zones_json) as f:
            return json.load(f)
    return [{"name": "full_frame", "type": "restricted",
             "polygon": [[0, 0], [w, 0], [w, h], [0, h]]}]


def probe(source: str, zones: Optional[List[Dict[str, Any]]] = None,
          infer_fps: float = 5.0, conf: float = 0.35,
          model_path: str = "yolo11n.pt",
          manifest: Optional[str] = None, sensor: Optional[str] = None,
          zones_json: Optional[str] = None) -> Dict[str, Any]:
    from ultralytics import YOLO
    model = YOLO(model_path)
    model.predict(np.zeros((480, 640, 3), dtype=np.uint8), verbose=False)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {source}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_src = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if zones is None:
        zones = _load_zones(manifest, sensor, zones_json, w, h)
    stride = max(1, round(src_fps / infer_fps))

    open_runs: Dict[Tuple[int, str], Dict[str, Any]] = {}
    dwell_runs: List[Dict[str, Any]] = []
    occupancy: Dict[str, List[Dict[str, Any]]] = {z["name"]: [] for z in zones}
    track_classes: Dict[int, Counter] = {}
    track_span: Dict[int, List[float]] = {}
    static_state: Dict[int, Tuple[float, Tuple]] = {}
    static_runs: Dict[int, float] = {}
    foot_points: List[Tuple[float, float, float, int]] = []
    frame_id = 0
    sampled = 0

    def close_run(key: Tuple[int, str]) -> None:
        run = open_runs.pop(key, None)
        if run is not None:
            dwell_runs.append(run)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_id += 1
        if frame_id % stride:
            continue
        video_ts = frame_id / src_fps
        sampled += 1
        r = model.track(frame, persist=True, verbose=False,
                        tracker="bytetrack.yaml", conf=conf)[0]
        names = r.names
        objects = []
        if r.boxes is not None:
            for b in r.boxes:
                tid = int(b.id) if b.id is not None else None
                objects.append({"class": names[int(b.cls)],
                                "confidence": float(b.conf),
                                "bbox": [float(v) for v in b.xyxy[0].tolist()],
                                "track_id": tid})

        inside_now: Dict[str, List[int]] = {z["name"]: [] for z in zones}
        for obj in objects:
            tid = obj["track_id"]
            if tid is None:
                continue
            track_classes.setdefault(tid, Counter())[obj["class"]] += 1
            span = track_span.setdefault(tid, [video_ts, video_ts, 0])
            span[1] = video_ts
            span[2] += 1
            cx = (obj["bbox"][0] + obj["bbox"][2]) / 2
            cy = obj["bbox"][3]
            if obj["class"] == "person":
                foot_points.append((round(video_ts, 2), round(cx, 1),
                                    round(cy, 1), tid))
            for zone in zones:
                key = (tid, zone["name"])
                if not point_in_polygon((cx, cy), zone["polygon"]):
                    close_run(key)
                    continue
                if obj["class"] == "person":
                    inside_now[zone["name"]].append(tid)
                run = open_runs.get(key)
                if run is None:
                    open_runs[key] = {
                        "track_id": tid, "zone": zone["name"],
                        "class": obj["class"], "t_start": round(video_ts, 2),
                        "t_end": round(video_ts, 2), "frames": 1,
                        "p_start": [round(cx, 1), round(cy, 1)],
                        "p_end": [round(cx, 1), round(cy, 1)],
                        "path_len": 0.0}
                else:
                    prev = run["p_end"]
                    run["path_len"] = round(
                        run["path_len"] + float(np.hypot(cx - prev[0], cy - prev[1])), 1)
                    run["p_end"] = [round(cx, 1), round(cy, 1)]
                    run["t_end"] = round(video_ts, 2)
                    run["frames"] += 1

            if obj["class"] != "person":
                prev = static_state.get(tid)
                if prev is None or _iou(prev[1], obj["bbox"]) < STATIC_IOU:
                    static_state[tid] = (video_ts, tuple(obj["bbox"]))
                else:
                    held = video_ts - prev[0]
                    static_runs[tid] = max(static_runs.get(tid, 0.0), held)

        for name, tids in inside_now.items():
            occupancy[name].append({"t": round(video_ts, 2),
                                    "count": len(set(tids)),
                                    "track_ids": sorted(set(tids))})
    cap.release()
    for key in list(open_runs):
        close_run(key)

    for run in dwell_runs:
        run["dwell_s"] = round(run["t_end"] - run["t_start"], 2)
        run["net_dx"] = round(run["p_end"][0] - run["p_start"][0], 1)
        run["net_dy"] = round(run["p_end"][1] - run["p_start"][1], 1)
    dwell_runs.sort(key=lambda r: (-r["dwell_s"], r["t_start"]))

    return {
        "source": source, "width": w, "height": h,
        "src_fps": round(src_fps, 3), "n_src_frames": n_src,
        "video_seconds": round(n_src / src_fps, 2) if n_src else None,
        "infer_fps": infer_fps, "stride": stride, "sampled_frames": sampled,
        "conf": conf,
        "zones": [{"name": z["name"], "type": z.get("type"),
                   "polygon": z["polygon"]} for z in zones],
        "dwell_runs": dwell_runs,
        "occupancy": occupancy,
        "tracks": {str(t): {"class": track_classes[t].most_common(),
                            "t_first": round(track_span[t][0], 2),
                            "t_last": round(track_span[t][1], 2),
                            "frames": track_span[t][2]}
                   for t in sorted(track_span)},
        "static_object_runs": {str(t): round(v, 2)
                               for t, v in sorted(static_runs.items())},
        "foot_points": foot_points,
    }


def report(res: Dict[str, Any], dump_tracks: bool = False) -> None:
    print(f"source          {res['source']}")
    print(f"frame           {res['width']}x{res['height']} @ {res['src_fps']} fps"
          f"  ({res['n_src_frames']} frames, {res['video_seconds']}s)")
    print(f"sampling        stride={res['stride']} -> {res['sampled_frames']} "
          f"sampled frames at infer_fps={res['infer_fps']}, conf={res['conf']}")
    print(f"zones           {', '.join(z['name'] for z in res['zones'])}")

    fp = res["foot_points"]
    if fp:
        xs = [p[1] for p in fp]
        ys = [p[2] for p in fp]
        print(f"\nperson foot-points  n={len(fp)}  "
              f"x=[{min(xs):.0f},{max(xs):.0f}]  y=[{min(ys):.0f},{max(ys):.0f}]")
    else:
        print("\nperson foot-points  NONE -- no person detected at this conf")

    print("\n-- tracks (any class) ------------------------------------------")
    for tid, t in res["tracks"].items():
        labels = "/".join(f"{c}x{n}" for c, n in t["class"])
        print(f"  track {tid:>4}  {t['t_first']:>6.2f}-{t['t_last']:>6.2f}s "
              f"({t['frames']:>3} frames)  {labels}")

    print("\n-- in-zone dwell runs (comparable to loiter_seconds) ----------")
    if not res["dwell_runs"]:
        print("  none")
    for run in res["dwell_runs"][:25]:
        print(f"  {run['zone']:<12} track {run['track_id']:>4} {run['class']:<10} "
              f"{run['t_start']:>6.2f}-{run['t_end']:>6.2f}s  dwell={run['dwell_s']:>5.2f}s  "
              f"net=({run['net_dx']:>7.1f},{run['net_dy']:>7.1f})  "
              f"path={run['path_len']:>7.1f}px  frames={run['frames']}")

    print("\n-- peak person occupancy per zone ------------------------------")
    for name, samples in res["occupancy"].items():
        if not samples:
            print(f"  {name:<12} no samples")
            continue
        peak = max(s["count"] for s in samples)
        print(f"  {name:<12} peak={peak}")
        for k in range(2, peak + 1):
            windows = [s["t"] for s in samples if s["count"] >= k]
            if windows:
                print(f"      count>={k}: {min(windows):.2f}-{max(windows):.2f}s "
                      f"({len(windows)} sampled frames)")

    if res["static_object_runs"]:
        print("\n-- longest static non-person hold (abandoned_seconds) ---------")
        for tid, held in res["static_object_runs"].items():
            print(f"  track {tid:>4}  {held:.2f}s")

    if dump_tracks:
        print("\n-- foot-point trace (t, cx, cy, track) ------------------------")
        for t, cx, cy, tid in fp:
            print(f"  {t:>6.2f}  {cx:>7.1f}  {cy:>7.1f}  {tid}")


def main() -> None:
    p = argparse.ArgumentParser(description="track-aware zone probe")
    p.add_argument("source", help="video file or device index")
    p.add_argument("--manifest", default=None,
                   help="scenario JSON to take zones from")
    p.add_argument("--sensor", default=None,
                   help="camera id within --manifest (default: all cameras)")
    p.add_argument("--zones-json", default=None,
                   help="JSON file holding a list of zone dicts")
    p.add_argument("--infer-fps", type=float, default=5.0)
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--model", default="yolo11n.pt")
    p.add_argument("--dump-tracks", action="store_true",
                   help="print every person foot-point (for authoring polygons)")
    p.add_argument("--out", default=None, help="also write the raw probe JSON here")
    args = p.parse_args()

    res = probe(args.source, infer_fps=args.infer_fps, conf=args.conf,
                model_path=args.model, manifest=args.manifest,
                sensor=args.sensor, zones_json=args.zones_json)
    report(res, dump_tracks=args.dump_tracks)
    if args.out:
        with open(args.out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
