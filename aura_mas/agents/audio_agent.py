"""AudioAgent: edge perception agent for one audio source.

Two operating modes (auto-selected):
- YAMNet mode (if tensorflow + tensorflow_hub available): 521-class AudioSet
  event classification; surveillance-relevant classes are mapped to events.
- DSP fallback mode (librosa/numpy only): unsupervised anomaly scoring from
  short-time energy + spectral flatness z-scores against a rolling baseline —
  robust, dependency-light, and sufficient for the fusion ablation.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Dict, List, Optional

import numpy as np

from aura_mas.agents.base import Agent
from aura_mas.core.bus import Event, TOPIC_EVENTS, new_id, now_ts

SURVEILLANCE_CLASSES = {
    # YAMNet class name -> (event_type, min_confidence)
    "Screaming": ("audio_scream", 0.25),
    "Yell": ("audio_scream", 0.3),
    "Glass": ("audio_glass_break", 0.25),
    "Shatter": ("audio_glass_break", 0.25),
    "Gunshot, gunfire": ("audio_gunshot", 0.2),
    "Explosion": ("audio_explosion", 0.2),
    "Alarm": ("audio_alarm", 0.3),
    "Siren": ("audio_alarm", 0.3),
    "Smoke detector, smoke alarm": ("audio_alarm", 0.25),
    "Breaking": ("audio_breaking", 0.3),
}


class DspAnomalyScorer:
    """Rolling-baseline audio anomaly detector (no deep model needed)."""

    def __init__(self, history: int = 50) -> None:
        self.energy_hist: deque = deque(maxlen=history)
        self.flatness_hist: deque = deque(maxlen=history)

    def score(self, chunk: np.ndarray, sr: int) -> float:
        energy = float(np.sqrt(np.mean(chunk ** 2)) + 1e-9)
        spec = np.abs(np.fft.rfft(chunk * np.hanning(len(chunk)))) + 1e-9
        flatness = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))
        z = 0.0
        if len(self.energy_hist) >= 10:
            for hist, val in ((self.energy_hist, energy),
                              (self.flatness_hist, flatness)):
                mu, sd = np.mean(hist), np.std(hist) + 1e-6
                z = max(z, abs(val - mu) / sd)
        self.energy_hist.append(energy)
        self.flatness_hist.append(flatness)
        return float(min(1.0, z / 6.0))  # normalize z-score to [0, 1]


class AudioAgent(Agent):
    def __init__(self, agent_id: str, bus, source: str,
                 chunk_seconds: float = 1.0,
                 anomaly_threshold: float = 0.5,
                 realtime: bool = True) -> None:
        super().__init__(agent_id, bus)
        self.source = source
        self.chunk_seconds = chunk_seconds
        self.anomaly_threshold = anomaly_threshold
        self.realtime = realtime
        self._yamnet = None
        self._class_names: List[str] = []
        self._dsp = DspAnomalyScorer()
        self.metrics = {"chunks": 0, "events": 0}

    def setup(self) -> None:
        try:
            import tensorflow_hub as hub
            import csv
            import urllib.request
            self._yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
            class_map_path = self._yamnet.class_map_path().numpy().decode()
            with open(class_map_path) as f:
                self._class_names = [row["display_name"]
                                     for row in csv.DictReader(f)]
            self.log.info("YAMNet loaded (%d classes)", len(self._class_names))
        except Exception:  # noqa: BLE001
            self.log.warning("YAMNet unavailable; using DSP anomaly fallback")

    def run(self, max_chunks: Optional[int] = None) -> Dict:
        import librosa
        audio, sr = librosa.load(self.source, sr=16000, mono=True)
        n = int(sr * self.chunk_seconds)
        for i in range(0, len(audio) - n, n):
            chunk = audio[i:i + n]
            self._process_chunk(chunk, sr)
            self.metrics["chunks"] += 1
            if max_chunks and self.metrics["chunks"] >= max_chunks:
                break
            if self.realtime:
                time.sleep(self.chunk_seconds * 0.9)
        return self.metrics

    def _process_chunk(self, chunk: np.ndarray, sr: int) -> None:
        ts = now_ts()
        if self._yamnet is not None:
            scores, _, _ = self._yamnet(chunk)
            mean_scores = scores.numpy().mean(axis=0)
            for cls, (event_type, min_conf) in SURVEILLANCE_CLASSES.items():
                if cls in self._class_names:
                    idx = self._class_names.index(cls)
                    conf = float(mean_scores[idx])
                    if conf >= min_conf:
                        self._emit(event_type, conf, ts, {"yamnet_class": cls})
        else:
            score = self._dsp.score(chunk, sr)
            if score >= self.anomaly_threshold:
                self._emit("audio_anomaly", score, ts, {"method": "dsp_zscore"})

    def _emit(self, event_type: str, conf: float, ts: float, extra: Dict) -> None:
        ev = Event(event_id=new_id("ev"), sensor_id=self.agent_id, timestamp=ts,
                   event_type=event_type, confidence=round(conf, 3),
                   modality="audio", extra=extra)
        self.metrics["events"] += 1
        self.log.info("AUDIO EVENT %s conf=%.2f", event_type, conf)
        self.bus.publish(TOPIC_EVENTS, ev.to_json(), qos=1)
