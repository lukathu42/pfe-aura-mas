"""CameraAgent: edge perception agent for one video source.

Pipeline per frame (sampled at `infer_fps`):
  1. YOLO11n detection (person/vehicle classes) + ByteTrack track IDs
     (via ultralytics `model.track`).
  2. Zone rules: intrusion (restricted polygon), loitering (dwell time),
     line crossing, abandoned object (static non-person object).
  3. Optional CLIP-based zero-shot semantic anomaly scoring on sampled frames.
  4. Publishes Detection messages (high-frequency) and semantic Event
     messages (only when a rule/anomaly fires) on the bus.
  5. Answers coordination auctions with bids and executes verification tasks.

Privacy-by-design: raw frames never leave the agent. Only JSON events and
anonymized (blurred) evidence crops are exported.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from aura_mas.agents.base import Agent
from aura_mas.core.bus import (Detection, Event, TOPIC_BIDS, TOPIC_EVENTS,
                               TOPIC_TASKS, TOPIC_AWARDS, TOPIC_VERIFICATIONS,
                               new_id, now_ts)
from aura_mas.core.privacy import anonymize_and_save


def point_in_polygon(pt: Tuple[float, float], poly: List[Tuple[float, float]]) -> bool:
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


class ZoneRuleEngine:
    """Stateful zone rules evaluated on tracked objects."""

    def __init__(self, zones: List[Dict[str, Any]], loiter_seconds: float = 8.0,
                 abandoned_seconds: float = 10.0) -> None:
        self.zones = zones                      # {name, type: restricted|entry, polygon}
        self.loiter_seconds = loiter_seconds
        self.abandoned_seconds = abandoned_seconds
        self._dwell: Dict[Tuple[int, str], float] = {}      # (track_id, zone) -> first_seen
        self._static_objects: Dict[int, Tuple[float, Tuple]] = {}  # track -> (t0, bbox)
        self._fired: set = set()

    def evaluate(self, tracks: List[Dict[str, Any]], ts: float) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for obj in tracks:
            tid = obj.get("track_id")
            if tid is None:
                continue
            cx = (obj["bbox"][0] + obj["bbox"][2]) / 2
            cy = obj["bbox"][3]                              # foot point
            for zone in self.zones:
                inside = point_in_polygon((cx, cy), zone["polygon"])
                key = (tid, zone["name"])
                if not inside:
                    self._dwell.pop(key, None)
                    continue
                # --- intrusion: person inside a restricted zone --------------
                if (zone.get("type") == "restricted" and obj["class"] == "person"
                        and ("intrusion", key) not in self._fired):
                    self._fired.add(("intrusion", key))
                    events.append({"event_type": "intrusion", "zone": zone["name"],
                                   "track_id": tid, "confidence": obj["confidence"]})
                # --- loitering: dwell time exceeded --------------------------
                first = self._dwell.setdefault(key, ts)
                if (ts - first > self.loiter_seconds and obj["class"] == "person"
                        and ("loitering", key) not in self._fired):
                    self._fired.add(("loitering", key))
                    events.append({"event_type": "loitering", "zone": zone["name"],
                                   "track_id": tid,
                                   "confidence": min(1.0, (ts - first) / 30.0 + 0.5)})
            # --- abandoned object: non-person object static too long ---------
            if obj["class"] not in ("person",):
                prev = self._static_objects.get(tid)
                if prev is None:
                    self._static_objects[tid] = (ts, tuple(obj["bbox"]))
                else:
                    t0, bbox0 = prev
                    iou = _iou(bbox0, obj["bbox"])
                    if iou < 0.6:
                        self._static_objects[tid] = (ts, tuple(obj["bbox"]))
                    elif (ts - t0 > self.abandoned_seconds
                          and ("abandoned", tid) not in self._fired):
                        self._fired.add(("abandoned", tid))
                        events.append({"event_type": "abandoned_object",
                                       "zone": None, "track_id": tid,
                                       "confidence": 0.7})
        return events


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / (ua + 1e-9)


class ClipAnomalyScorer:
    """Zero-shot semantic anomaly scoring with CLIP (VadCLIP-style proxy).

    Compares frame embedding against 'normal' vs 'anomalous' text prompts;
    the anomaly score is the softmax mass on anomalous prompts.
    """

    NORMAL_PROMPTS = [
        "a normal scene of a warehouse with workers",
        "an empty corridor under surveillance",
        "people walking calmly in a building",
    ]
    ANOMALY_PROMPTS = [
        "people fighting violently",
        "a person falling on the ground",
        "fire and smoke in a building",
        "a person breaking into a restricted area",
        "a person stealing and running away",
    ]

    def __init__(self, device: str = "cpu") -> None:
        import torch
        import clip  # openai/CLIP or open_clip fallback handled by caller
        self.torch = torch
        self.model, self.preprocess = clip.load("ViT-B/32", device=device)
        self.device = device
        prompts = self.NORMAL_PROMPTS + self.ANOMALY_PROMPTS
        with torch.no_grad():
            tokens = clip.tokenize(prompts).to(device)
            self.text_feat = self.model.encode_text(tokens)
            self.text_feat /= self.text_feat.norm(dim=-1, keepdim=True)
        self.n_normal = len(self.NORMAL_PROMPTS)

    def score(self, frame_bgr: np.ndarray) -> Tuple[float, str]:
        from PIL import Image
        img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        with self.torch.no_grad():
            x = self.preprocess(img).unsqueeze(0).to(self.device)
            f = self.model.encode_image(x)
            f /= f.norm(dim=-1, keepdim=True)
            sims = (100.0 * f @ self.text_feat.T).softmax(dim=-1).squeeze(0)
        anomaly_mass = float(sims[self.n_normal:].sum())
        top_idx = int(sims[self.n_normal:].argmax()) if anomaly_mass > 0 else 0
        label = self.ANOMALY_PROMPTS[top_idx]
        return anomaly_mass, label


class CameraAgent(Agent):
    def __init__(self, agent_id: str, bus, source: str,
                 zones: Optional[List[Dict[str, Any]]] = None,
                 infer_fps: float = 5.0,
                 model_path: str = "yolo11n.pt",
                 enable_clip: bool = False,
                 clip_every_n: int = 15,
                 anomaly_threshold: float = 0.55,
                 evidence_dir: str = "data/evidence",
                 realtime: bool = True) -> None:
        super().__init__(agent_id, bus)
        self.source = source
        self.zones = zones or []
        self.infer_fps = infer_fps
        self.model_path = model_path
        self.enable_clip = enable_clip
        self.clip_every_n = clip_every_n
        self.anomaly_threshold = anomaly_threshold
        self.evidence_dir = evidence_dir
        self.realtime = realtime
        self.rule_engine = ZoneRuleEngine(self.zones)
        self._pending_tasks: Dict[str, Dict] = {}
        self._busy = False
        self._model = None
        self._clip = None
        self._last_frame: Optional[np.ndarray] = None
        self.metrics = {"frames": 0, "detections": 0, "events": 0,
                        "infer_ms": []}

    # ------------------------------------------------------------------ setup
    def setup(self) -> None:
        from ultralytics import YOLO
        self._model = YOLO(self.model_path)
        if self.enable_clip:
            try:
                self._clip = ClipAnomalyScorer()
            except Exception:  # noqa: BLE001
                self.log.warning("CLIP unavailable; anomaly scoring disabled")
        os.makedirs(self.evidence_dir, exist_ok=True)
        # coordination: listen for task announcements and awards
        self.bus.subscribe(TOPIC_TASKS, self._on_task_announce)
        self.bus.subscribe(TOPIC_AWARDS, self._on_award)

    def warmup(self) -> None:
        """Run one dummy inference so YOLO/CLIP cold-start load doesn't land
        inside the timed scenario window (see replay.py -- t_scenario_start
        is now captured after all agents warm up, not before they load)."""
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        if self._model is not None:
            self._model.predict(dummy, verbose=False)  # predict, not track:
            # track(persist=True) would seed ByteTrack state with a phantom
            # frame and shift real track_ids.
        if self._clip is not None:
            self._clip.score(dummy)

    # ------------------------------------------------------------- main loop
    def run(self, max_frames: Optional[int] = None) -> Dict[str, Any]:
        """Process the video source; blocking. Returns run metrics."""
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise RuntimeError(f"cannot open source {self.source}")
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        stride = max(1, round(src_fps / self.infer_fps))
        frame_id = 0
        t_start = time.time()
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame_id += 1
            if frame_id % stride:
                continue
            if max_frames and self.metrics["frames"] >= max_frames:
                break
            ts = now_ts()
            video_ts = frame_id / src_fps
            self._last_frame = frame
            self._process_frame(frame, frame_id, ts, video_ts)
            if self.realtime:
                # simulate real-time pacing of the source
                budget = frame_id / src_fps - (time.time() - t_start)
                if budget > 0:
                    time.sleep(min(budget, 0.5))
        cap.release()
        return self.metrics

    def _process_frame(self, frame: np.ndarray, frame_id: int, ts: float,
                       video_ts: Optional[float] = None) -> None:
        t0 = time.time()
        results = self._model.track(frame, persist=True, verbose=False,
                                    tracker="bytetrack.yaml", conf=0.35)
        self.metrics["infer_ms"].append((time.time() - t0) * 1000)
        self.metrics["frames"] += 1

        objects = []
        r = results[0]
        names = r.names
        if r.boxes is not None:
            for b in r.boxes:
                cls_name = names[int(b.cls)]
                tid = int(b.id) if b.id is not None else None
                objects.append({
                    "class": cls_name,
                    "confidence": float(b.conf),
                    "bbox": [float(v) for v in b.xyxy[0].tolist()],
                    "track_id": tid,
                })
        self.metrics["detections"] += len(objects)

        det = Detection(sensor_id=self.agent_id, frame_id=frame_id,
                        timestamp=ts, objects=objects)
        self.bus.publish(f"site/{self.agent_id}/detections", det.to_json(), qos=0)

        # zone rules ---------------------------------------------------------
        person_boxes = [tuple(int(v) for v in o["bbox"])
                        for o in objects if o["class"] == "person"]
        self._last_person_boxes = person_boxes
        # duration-based rules (loitering, abandoned_object) key off video
        # playback time, not wall-clock time: in non-realtime modes (e.g. the
        # centralized baseline, which processes frames as fast as the CPU
        # allows) wall-clock elapsed time can be far shorter than the elapsed
        # scene time, so these rules would otherwise almost never fire.
        for ev in self.rule_engine.evaluate(objects, video_ts if video_ts is not None else ts):
            self._emit_event(frame, ts, modality="video", **ev)

        # CLIP anomaly -------------------------------------------------------
        if self._clip is not None and frame_id % self.clip_every_n == 0:
            score, label = self._clip.score(frame)
            if score >= self.anomaly_threshold:
                self._emit_event(frame, ts, event_type="anomaly", zone=None,
                                 track_id=None, confidence=score,
                                 modality="video", extra={"clip_label": label})

    def _emit_event(self, frame: np.ndarray, ts: float, event_type: str,
                    zone: Optional[str], track_id: Optional[int],
                    confidence: float, modality: str = "video",
                    extra: Optional[Dict] = None) -> None:
        evidence_path = anonymize_and_save(
            frame, self.evidence_dir,
            prefix=f"{self.agent_id}_{event_type}",
            boxes=getattr(self, "_last_person_boxes", None))
        ev = Event(event_id=new_id("ev"), sensor_id=self.agent_id, timestamp=ts,
                   event_type=event_type, confidence=round(confidence, 3),
                   modality=modality, zone=zone, track_id=track_id,
                   evidence_path=evidence_path, extra=extra or {})
        self.metrics["events"] += 1
        self.log.info("EVENT %s conf=%.2f zone=%s", event_type, confidence, zone)
        self.bus.publish(TOPIC_EVENTS, ev.to_json(), qos=1)

    # -------------------------------------------------------- coordination --
    def _view_score(self, task: Dict) -> float:
        """Bid utility: can this camera verify the event? Higher = better."""
        base = 1.0 if task.get("origin_sensor") != self.agent_id else 0.3
        capacity = 0.2 if self._busy else 1.0
        overlap = task.get("fov_overlap", {}).get(self.agent_id, 0.5)
        return round(base * capacity * overlap, 3)

    def _on_task_announce(self, topic: str, payload: str) -> None:
        task = json.loads(payload)
        bid = {"task_id": task["task_id"], "agent_id": self.agent_id,
               "bid": self._view_score(task), "timestamp": now_ts()}
        self.bus.publish(TOPIC_BIDS, json.dumps(bid), qos=1)

    def _on_award(self, topic: str, payload: str) -> None:
        award = json.loads(payload)
        if award.get("winner") != self.agent_id:
            return
        self._busy = True
        try:
            result = self._verify(award)
            self.bus.publish(TOPIC_VERIFICATIONS, json.dumps(result), qos=1)
        finally:
            self._busy = False

    def _verify(self, award: Dict) -> Dict:
        """High-scrutiny re-check: re-run detection at higher resolution/conf."""
        frame = self._last_frame
        verified, score = False, 0.0
        if frame is not None:
            results = self._model.predict(frame, imgsz=960, conf=0.25, verbose=False)
            persons = [b for b in results[0].boxes
                       if results[0].names[int(b.cls)] == "person"] \
                if results[0].boxes is not None else []
            score = max((float(b.conf) for b in persons), default=0.0)
            verified = score > 0.4
        return {"task_id": award["task_id"], "agent_id": self.agent_id,
                "verified": verified, "verification_score": round(score, 3),
                "timestamp": now_ts()}
