"""CameraAgent: edge perception agent for one video source.

Pipeline per frame (sampled at `infer_fps`):
  1. YOLO11n detection (person/vehicle classes) + ByteTrack track IDs
     (via ultralytics `model.track`).
  2. Zone rules: intrusion (restricted polygon), loitering (dwell time),
     abandoned object (static non-person object), and -- only when the zone
     declares the enabling key -- zone occupancy (`max_occupancy`) and
     wrong-direction movement (`flow_direction`). Line crossing is NOT
     implemented; this docstring claimed it until 2026-08-26.
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
import threading
import time
from collections import defaultdict, deque
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


def _project(dx: float, dy: float, axis: Tuple[float, float]) -> float:
    """Signed displacement along a zone's declared flow axis, in pixels.

    The axis is an arbitrary vector in the scenario JSON, so it is normalised
    here: otherwise `[10, 0]` and `[1, 0]` would express the same direction
    while scaling the `min_flow_px` threshold by 10x.
    """
    ax, ay = axis
    norm = (ax * ax + ay * ay) ** 0.5
    if norm < 1e-9:
        return 0.0
    return (dx * ax + dy * ay) / norm


class ZoneRuleEngine:
    """Stateful zone rules evaluated on tracked objects."""

    def __init__(self, zones: List[Dict[str, Any]], loiter_seconds: float = 8.0,
                 abandoned_seconds: float = 10.0,
                 min_flow_px: float = 40.0,
                 person_down_seconds: float = 1.5,
                 rapid_window_seconds: float = 1.0,
                 rapid_min_duration: float = 0.6) -> None:
        self.zones = zones                      # {name, type: restricted|entry, polygon}
        self.loiter_seconds = loiter_seconds
        self.abandoned_seconds = abandoned_seconds
        self.min_flow_px = min_flow_px
        self.person_down_seconds = person_down_seconds
        self.rapid_window_seconds = rapid_window_seconds
        self.rapid_min_duration = rapid_min_duration
        self._dwell: Dict[Tuple[int, str], float] = {}      # (track_id, zone) -> first_seen
        self._entry_point: Dict[Tuple[int, str], Tuple[float, float]] = {}
        self._static_objects: Dict[int, Tuple[float, Tuple]] = {}  # track -> (t0, bbox)
        self._posture_since: Dict[Tuple[int, str], float] = {}
        self._speed_history: Dict[Tuple[int, str], deque] = defaultdict(deque)
        self._rapid_since: Dict[Tuple[int, str], float] = {}
        self._fired: set = set()

    @staticmethod
    def _person_is_down(obj: Dict[str, Any], aspect_threshold: float) -> bool:
        """Conservative posture test over a tracked person.

        Pose keypoints are optional because old YOLO detection scenarios do
        not expose them.  A valid shoulder/hip layout can corroborate the
        bounding-box orientation; the explicit aspect threshold remains the
        deterministic fallback for low-resolution footage.
        """
        x1, y1, x2, y2 = obj["bbox"]
        width, height = max(1.0, x2 - x1), max(1.0, y2 - y1)
        horizontal_box = width / height >= aspect_threshold
        keypoints = obj.get("keypoints") or []
        # COCO: shoulders 5/6, hips 11/12. Values are [x, y, confidence].
        usable = [keypoints[i] for i in (5, 6, 11, 12)
                  if i < len(keypoints) and len(keypoints[i]) >= 3
                  and keypoints[i][2] >= 0.25]
        if len(usable) < 3:
            return horizontal_box
        xs = [point[0] for point in usable]
        ys = [point[1] for point in usable]
        horizontal_torso = (max(xs) - min(xs)) >= 1.25 * max(1.0, max(ys) - min(ys))
        return horizontal_box and horizontal_torso

    def _trajectory_events(self, obj: Dict[str, Any], zone: Dict[str, Any],
                           key: Tuple[int, str], cx: float, cy: float,
                           ts: float) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        if obj["class"] != "person":
            return events

        down_ratio = zone.get("down_aspect_ratio")
        if down_ratio is not None:
            if self._person_is_down(obj, float(down_ratio)):
                since = self._posture_since.setdefault(key, ts)
                if (ts - since >= self.person_down_seconds
                        and ("person_down", key) not in self._fired):
                    self._fired.add(("person_down", key))
                    events.append({"event_type": "person_down", "zone": zone["name"],
                                   "track_id": key[0],
                                   "confidence": max(0.72, obj["confidence"])})
            else:
                self._posture_since.pop(key, None)

        speed_limit = zone.get("max_speed_zone_lengths_per_second")
        if speed_limit is not None:
            history = self._speed_history[key]
            history.append((ts, cx, cy))
            while history and ts - history[0][0] > self.rapid_window_seconds:
                history.popleft()
            polygon = zone["polygon"]
            xs, ys = [point[0] for point in polygon], [point[1] for point in polygon]
            diagonal = max(1.0, ((max(xs) - min(xs)) ** 2 +
                                 (max(ys) - min(ys)) ** 2) ** 0.5)
            rapid = False
            normalized_speed = 0.0
            if len(history) >= 2:
                t0, x0, y0 = history[0]
                elapsed = ts - t0
                if elapsed > 1e-6:
                    normalized_speed = (((cx - x0) ** 2 + (cy - y0) ** 2) ** 0.5
                                        / elapsed / diagonal)
                    rapid = normalized_speed >= float(speed_limit)
            if rapid:
                since = self._rapid_since.setdefault(key, ts)
                if (ts - since >= self.rapid_min_duration
                        and ("rapid_movement", key) not in self._fired):
                    self._fired.add(("rapid_movement", key))
                    events.append({"event_type": "rapid_movement", "zone": zone["name"],
                                   "track_id": key[0],
                                   "confidence": max(0.72, obj["confidence"]),
                                   "normalized_speed": round(normalized_speed, 4)})
            else:
                self._rapid_since.pop(key, None)
        return events

    def _occupancy_events(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Headcount rule, evaluated per frame rather than per track.

        Occupancy is a property of the whole frame, so unlike every other rule
        here it cannot be folded into `evaluate`'s per-object loop. Firing is
        keyed on the count itself, so a crowd that keeps growing keeps
        reporting while a steady one goes quiet after the first report.
        """
        events: List[Dict[str, Any]] = []
        for zone in self.zones:
            limit = zone.get("max_occupancy")
            if limit is None:
                continue
            # A detector can occasionally emit duplicate boxes carrying the
            # same ByteTrack identity in one frame. Occupancy is explicitly a
            # unique-track count, so retain only the strongest box per ID.
            inside_by_track: Dict[int, Dict[str, Any]] = {}
            for obj in tracks:
                track_id = obj.get("track_id")
                if (obj["class"] != "person" or track_id is None
                        or not point_in_polygon(
                            ((obj["bbox"][0] + obj["bbox"][2]) / 2,
                             obj["bbox"][3]), zone["polygon"])):
                    continue
                previous = inside_by_track.get(track_id)
                if previous is None or obj["confidence"] > previous["confidence"]:
                    inside_by_track[track_id] = obj
            inside = list(inside_by_track.values())
            n = len(inside)
            if n <= limit:
                continue
            key = ("occupancy", zone["name"], n)
            if key in self._fired:
                continue
            self._fired.add(key)
            mean_conf = sum(o["confidence"] for o in inside) / n
            lead = max(inside, key=lambda o: o["confidence"])
            events.append({"event_type": "zone_occupancy", "zone": zone["name"],
                           # the highest-confidence occupant, never None:
                           # _process_frame looks the re-ID vector up by
                           # track_id and a None would silently drop it.
                           "track_id": lead["track_id"],
                           # A single view cannot resolve occlusion or prove a
                           # site-level headcount. Cap it in the coordinator's
                           # gray zone; a second camera can then verify it.
                           "confidence": min(0.82, mean_conf + 0.1 * (n - limit - 1))})
        return events

    def evaluate(self, tracks: List[Dict[str, Any]], ts: float) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = self._occupancy_events(tracks)
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
                    self._entry_point.pop(key, None)
                    self._posture_since.pop(key, None)
                    self._speed_history.pop(key, None)
                    self._rapid_since.pop(key, None)
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
                # --- wrong direction: sustained counter-flow movement --------
                p0 = self._entry_point.setdefault(key, (cx, cy))
                axis = zone.get("flow_direction")
                if (axis and obj["class"] == "person"
                        and ("wrong_direction", key) not in self._fired):
                    # measured from the zone entry point, not the previous
                    # frame: per-frame deltas at infer_fps are dominated by
                    # bbox jitter, which flips sign constantly.
                    if _project(cx - p0[0], cy - p0[1], axis) <= -self.min_flow_px:
                        self._fired.add(("wrong_direction", key))
                        events.append({"event_type": "wrong_direction",
                                       "zone": zone["name"], "track_id": tid,
                                       "confidence": min(1.0, obj["confidence"])})
                events.extend(self._trajectory_events(obj, zone, key, cx, cy, ts))
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


class ReIdFeatureExtractor:
    """Lightweight CPU-friendly appearance descriptor for cross-camera Re-ID.
    Extracts multi-zone HSV color histogram + spatial features."""

    @staticmethod
    def extract(crop: np.ndarray) -> Optional[List[float]]:
        if crop is None or crop.shape[0] < 20 or crop.shape[1] < 10:
            return None
        resized = cv2.resize(crop, (64, 128))
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        feats = []
        # 3 horizontal body strips: head/shoulders, torso, legs
        for y1, y2 in ((0, 42), (42, 85), (85, 128)):
            part = hsv[y1:y2, :]
            hist = cv2.calcHist([part], [0, 1], None, [8, 4], [0, 180, 0, 256])
            hist = hist.flatten()
            norm = float(np.linalg.norm(hist) + 1e-6)
            feats.extend((hist / norm).tolist())
        vec = np.array(feats, dtype=np.float32)
        norm = float(np.linalg.norm(vec) + 1e-6)
        return (vec / norm).tolist()


class CameraAgent(Agent):
    def __init__(self, agent_id: str, bus, source: Any,
                 zones: Optional[List[Dict[str, Any]]] = None,
                 infer_fps: float = 5.0,
                 model_path: str = "yolo11n.pt",
                 enable_clip: bool = False,
                 clip_every_n: int = 15,
                 anomaly_threshold: float = 0.55,
                 evidence_dir: str = "data/evidence",
                 realtime: bool = True,
                 loiter_seconds: float = 8.0,
                 abandoned_seconds: float = 10.0,
                 min_flow_px: float = 40.0,
                 person_down_seconds: float = 1.5,
                 rapid_window_seconds: float = 1.0,
                 rapid_min_duration: float = 0.6,
                 detection_conf: float = 0.35) -> None:
        super().__init__(agent_id, bus)
        # Parse device index if string is integer (e.g. "0" -> 0 for webcam)
        if isinstance(source, str) and source.isdigit():
            self.source = int(source)
        else:
            self.source = source
        self.zones = zones or []
        self.infer_fps = infer_fps
        self.model_path = model_path
        self.enable_clip = enable_clip
        self.clip_every_n = clip_every_n
        self.anomaly_threshold = anomaly_threshold
        self.evidence_dir = evidence_dir
        self.realtime = realtime
        self.detection_conf = detection_conf
        self.rule_engine = ZoneRuleEngine(self.zones,
                                          loiter_seconds=loiter_seconds,
                                          abandoned_seconds=abandoned_seconds,
                                          min_flow_px=min_flow_px,
                                          person_down_seconds=person_down_seconds,
                                          rapid_window_seconds=rapid_window_seconds,
                                          rapid_min_duration=rapid_min_duration)
        self._pending_tasks: Dict[str, Dict] = {}
        self._busy = False
        self._model = None
        self._clip = None
        self._last_frame: Optional[np.ndarray] = None
        self._latest_jpeg: Optional[bytes] = None
        self._frame_lock = threading.Lock()
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

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Return the most recent JPEG frame for live HTTP/MJPEG streaming."""
        with self._frame_lock:
            return self._latest_jpeg

    def _process_frame(self, frame: np.ndarray, frame_id: int, ts: float,
                       video_ts: Optional[float] = None) -> None:
        t0 = time.time()
        results = self._model.track(frame, persist=True, verbose=False,
                                    tracker="bytetrack.yaml",
                                    conf=self.detection_conf)
        self.metrics["infer_ms"].append((time.time() - t0) * 1000)
        self.metrics["frames"] += 1

        objects = []
        r = results[0]
        names = r.names
        h, w = frame.shape[:2]
        if r.boxes is not None:
            keypoints_xy = r.keypoints.xy.cpu().tolist() if r.keypoints is not None else []
            keypoints_conf = (r.keypoints.conf.cpu().tolist()
                              if r.keypoints is not None and r.keypoints.conf is not None else [])
            for box_index, b in enumerate(r.boxes):
                cls_name = names[int(b.cls)]
                tid = int(b.id) if b.id is not None else None
                bbox = [float(v) for v in b.xyxy[0].tolist()]
                obj_data: Dict[str, Any] = {
                    "class": cls_name,
                    "confidence": float(b.conf),
                    "bbox": bbox,
                    "track_id": tid,
                }
                if box_index < len(keypoints_xy):
                    confs = keypoints_conf[box_index] if box_index < len(keypoints_conf) else []
                    obj_data["keypoints"] = [
                        [float(point[0]), float(point[1]),
                         float(confs[index]) if index < len(confs) else 0.0]
                        for index, point in enumerate(keypoints_xy[box_index])
                    ]
                # Extract Re-ID embedding for person detections
                if cls_name == "person":
                    x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
                    x2, y2 = min(w, x2), min(h, y2)
                    if y2 > y1 and x2 > x1:
                        crop = frame[y1:y2, x1:x2]
                        reid_vec = ReIdFeatureExtractor.extract(crop)
                        if reid_vec:
                            obj_data["reid_feat"] = reid_vec
                objects.append(obj_data)
        self.metrics["detections"] += len(objects)

        # Update streaming JPEG buffer
        try:
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                with self._frame_lock:
                    self._latest_jpeg = buf.tobytes()
        except Exception:  # noqa: BLE001
            pass

        det = Detection(sensor_id=self.agent_id, frame_id=frame_id,
                        timestamp=ts, objects=objects)
        self.bus.publish(f"site/{self.agent_id}/detections", det.to_json(), qos=0)

        # zone rules ---------------------------------------------------------
        person_boxes = [tuple(int(v) for v in o["bbox"])
                        for o in objects if o["class"] == "person"]
        self._last_person_boxes = person_boxes
        scene_time = video_ts if video_ts is not None else None
        for ev in self.rule_engine.evaluate(objects, scene_time if scene_time is not None else ts):
            # attach reid feature to event extra if available
            tid = ev.get("track_id")
            matching_obj = next((o for o in objects if o.get("track_id") == tid and "reid_feat" in o), None)
            extra = {"reid_feat": matching_obj["reid_feat"]} if matching_obj else {}
            event_fields = {key: ev[key] for key in
                            ("event_type", "zone", "track_id", "confidence")}
            extra.update({key: value for key, value in ev.items()
                          if key not in event_fields})
            self._emit_event(frame, ts, modality="video", extra=extra,
                             scene_time_seconds=scene_time, **event_fields)

        # CLIP anomaly -------------------------------------------------------
        if self._clip is not None and frame_id % self.clip_every_n == 0:
            score, label = self._clip.score(frame)
            if score >= self.anomaly_threshold:
                self._emit_event(frame, ts, event_type="anomaly", zone=None,
                                 track_id=None, confidence=score,
                                 modality="video", extra={"clip_label": label},
                                 scene_time_seconds=scene_time)

    def _emit_event(self, frame: np.ndarray, ts: float, event_type: str,
                    zone: Optional[str], track_id: Optional[int],
                    confidence: float, modality: str = "video",
                    extra: Optional[Dict] = None,
                    scene_time_seconds: Optional[float] = None) -> None:
        evidence_path = anonymize_and_save(
            frame, self.evidence_dir,
            prefix=f"{self.agent_id}_{event_type}",
            boxes=getattr(self, "_last_person_boxes", None))
        ev = Event(event_id=new_id("ev"), sensor_id=self.agent_id, timestamp=ts,
                   event_type=event_type, confidence=round(confidence, 3),
                   modality=modality, zone=zone, track_id=track_id,
                   evidence_path=evidence_path,
                   scene_time_seconds=scene_time_seconds, extra=extra or {})
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
