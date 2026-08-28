"""FusionAgent: site-level spatio-temporal event fusion (late fusion).

Groups edge events into hypotheses within a sliding time window, keyed by
(zone | site). Confidence combination uses a noisy-OR with per-modality
reliability weights, so corroborating evidence from a second sensor or a
second modality strictly increases confidence — the core multimodal claim
of the thesis (C3).
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aura_mas.agents.base import Agent
from aura_mas.core.bus import Event, TOPIC_EVENTS, new_id, now_ts
from aura_mas.core.taxonomy import EVENT_FAMILIES

MODALITY_RELIABILITY = {"video": 0.9, "audio": 0.7}


@dataclass
class Hypothesis:
    hypothesis_id: str
    family: str
    zone: Optional[str]
    first_ts: float
    last_ts: float
    events: List[Event] = field(default_factory=list)
    confidence: float = 0.0
    global_entity_id: Optional[str] = None

    @property
    def modalities(self) -> set:
        return {e.modality for e in self.events}

    @property
    def sensors(self) -> set:
        return {e.sensor_id for e in self.events}

    @property
    def contributing_types(self) -> List[str]:
        seen = []
        for e in self.events:
            if e.event_type not in seen:
                seen.append(e.event_type)
        return seen

    @property
    def scene_time_seconds(self) -> Optional[float]:
        """Earliest source-video time represented by this hypothesis."""
        values = [e.scene_time_seconds for e in self.events
                  if e.scene_time_seconds is not None]
        return min(values) if values else None

    def dominant_type(self) -> str:
        best = max(self.events, key=lambda e: e.confidence)
        return best.event_type


class FusionAgent(Agent):
    def __init__(self, agent_id: str, bus, window_seconds: float = 6.0,
                 on_hypothesis=None) -> None:
        super().__init__(agent_id, bus, tick_interval=1.0)
        self.window_seconds = window_seconds
        self.on_hypothesis = on_hypothesis  # callback(Hypothesis)
        self._hypotheses: Dict[str, Hypothesis] = {}
        # Re-ID entity gallery: entity_id -> {"feat": vector, "last_ts": ts, "zones": [z1, z2]}
        self._entity_gallery: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.metrics = {"events_in": 0, "hypotheses_out": 0, "reid_matches": 0}

    def setup(self) -> None:
        self.bus.subscribe(TOPIC_EVENTS, self._on_event)

    def _match_or_register_entity(self, feat: List[float], zone: Optional[str],
                                  ts: float, threshold: float = 0.70) -> str:
        """Find matching global entity ID in gallery or register a new entity."""
        import numpy as np
        v1 = np.array(feat, dtype=np.float32)
        best_id, best_sim = None, -1.0
        for eid, data in list(self._entity_gallery.items()):
            if ts - data["last_ts"] > 120.0:
                del self._entity_gallery[eid]
                continue
            v2 = np.array(data["feat"], dtype=np.float32)
            sim = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6))
            if sim > best_sim:
                best_sim = sim
                best_id = eid

        if best_sim >= threshold and best_id:
            self.metrics["reid_matches"] += 1
            entry = self._entity_gallery[best_id]
            entry["last_ts"] = ts
            updated = (np.array(entry["feat"]) * 0.7 + v1 * 0.3)
            entry["feat"] = (updated / (np.linalg.norm(updated) + 1e-6)).tolist()
            if zone and zone not in entry["zones"]:
                entry["zones"].append(zone)
            return best_id

        new_eid = new_id("entity")
        self._entity_gallery[new_eid] = {
            "feat": feat,
            "last_ts": ts,
            "zones": [zone] if zone else [],
        }
        return new_eid

    # ------------------------------------------------------------------ fuse
    def _on_event(self, topic: str, payload: str) -> None:
        ev = Event.from_json(payload)
        self.metrics["events_in"] += 1
        family = EVENT_FAMILIES.get(ev.event_type, "other")
        key = f"{family}:{ev.zone or 'site'}"
        with self._lock:
            hyp = self._hypotheses.get(key)
            if hyp is None or ev.timestamp - hyp.last_ts > self.window_seconds:
                hyp = Hypothesis(hypothesis_id=new_id("hyp"), family=family,
                                 zone=ev.zone, first_ts=ev.timestamp,
                                 last_ts=ev.timestamp)
                self._hypotheses[key] = hyp
            hyp.events.append(ev)
            hyp.last_ts = ev.timestamp
            hyp.confidence = self._fuse_confidence(hyp)
            if "reid_feat" in ev.extra and isinstance(ev.extra["reid_feat"], list):
                eid = self._match_or_register_entity(ev.extra["reid_feat"], ev.zone, ev.timestamp)
                hyp.global_entity_id = eid

    @staticmethod
    def _fuse_confidence(hyp: Hypothesis) -> float:
        """Noisy-OR with modality reliability weighting.

        P(incident) = 1 - prod(1 - w_m * conf_e). Cross-modality corroboration
        adds a small calibrated bonus (capped at 1.0).
        """
        p_not = 1.0
        for e in hyp.events:
            w = MODALITY_RELIABILITY.get(e.modality, 0.5)
            p_not *= (1.0 - w * min(1.0, e.confidence))
        conf = 1.0 - p_not
        if len(hyp.modalities) > 1:
            conf = min(1.0, conf + 0.05)          # cross-modal bonus
        if len(hyp.sensors) > 1:
            conf = min(1.0, conf + 0.05)          # cross-sensor bonus
        return round(conf, 3)

    # ------------------------------------------------------------------ tick
    def tick(self) -> None:
        """Flush hypotheses whose window has closed."""
        now = now_ts()
        flushed = []
        with self._lock:
            for key, hyp in list(self._hypotheses.items()):
                if now - hyp.last_ts > self.window_seconds:
                    flushed.append(hyp)
                    del self._hypotheses[key]
        for hyp in flushed:
            self.metrics["hypotheses_out"] += 1
            self.log.info("HYPOTHESIS %s conf=%.2f events=%d modalities=%s",
                          hyp.dominant_type(), hyp.confidence,
                          len(hyp.events), hyp.modalities)
            if self.on_hypothesis:
                self.on_hypothesis(hyp)

    def flush_all(self) -> None:
        """Force-flush at end of a replay run."""
        with self._lock:
            hyps = list(self._hypotheses.values())
            self._hypotheses.clear()
        for hyp in hyps:
            self.metrics["hypotheses_out"] += 1
            if self.on_hypothesis:
                self.on_hypothesis(hyp)
