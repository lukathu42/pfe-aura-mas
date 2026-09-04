"""AudioAgent: edge perception agent for one audio source.

Two operating modes, selected by `backend`:
- YAMNet mode (`backend="yamnet"`, or `"auto"` if a local model is present):
  521-class AudioSet event classification from a local SavedModel fetched by
  `aura_mas/scripts/fetch_yamnet.py`; surveillance-relevant classes are
  mapped to events via `SURVEILLANCE_CLASSES`.
- DSP fallback mode (`backend="dsp"`, or `"auto"` when YAMNet is unavailable):
  librosa/numpy-only unsupervised anomaly scoring from short-time energy +
  spectral flatness z-scores against a rolling baseline — dependency-light,
  but only emits a generic `audio_anomaly` event (no class label), which is
  why it cannot corroborate with class-specific ground truth in the fusion
  metrics. See `results/yamnet_integration_notes.md` for a measured DSP vs
  YAMNet comparison.
"""
from __future__ import annotations

import os
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
                 realtime: bool = True,
                 backend: str = "auto",
                 top_k: int = 1,
                 zone: Optional[str] = None) -> None:
        """backend: "auto" (YAMNet if the local model loads, else DSP),
        "yamnet" (required -- raise if unavailable, no silent fallback), or
        "dsp" (force the fallback, e.g. for an ablation run).

        top_k: max distinct event_types emitted per chunk after collapsing
        YAMNet classes that map to the same event_type (see SURVEILLANCE_CLASSES
        -- "Glass" and "Shatter" both -> audio_glass_break) down to their
        highest-confidence match. Without this, one chunk can emit several
        near-duplicate events that noisy-OR fusion (fusion_agent.py) treats as
        independent corroborating evidence, inflating confidence.

        zone: the sensor's zone, if any -- propagated onto emitted Events so
        an audio event can land in the same FusionAgent hypothesis key as a
        camera event in the same zone (fusion_agent.py keys hypotheses by
        f"{family}:{zone or 'site'}"). Without this, audio events default to
        "site" and can never corroborate a zoned video event.
        """
        super().__init__(agent_id, bus)
        self.source = source
        self.chunk_seconds = chunk_seconds
        self.anomaly_threshold = anomaly_threshold
        self.realtime = realtime
        self.backend = backend
        self.top_k = top_k
        self.zone = zone
        self._yamnet = None
        self._class_names: List[str] = []
        self._class_idx: Dict[str, int] = {}
        self._dsp = DspAnomalyScorer()
        self.backend_used = "dsp"
        self.metrics = {"chunks": 0, "events": 0, "backend": "dsp",
                        "suppressed_dupes": 0}

    def setup(self) -> None:
        if self.backend == "dsp":
            return
        try:
            self._load_yamnet()
            self.backend_used = "yamnet"
            self.metrics["backend"] = "yamnet"
            self.log.info("YAMNet loaded (%d classes)", len(self._class_names))
        except Exception as exc:  # noqa: BLE001
            if self.backend == "yamnet":
                raise  # a requested backend that silently degrades hides bugs
            self.log.warning("YAMNet unavailable (%s: %s); using DSP fallback",
                             type(exc).__name__, exc)
            self.log.debug("YAMNet load traceback", exc_info=True)

    def _load_yamnet(self) -> None:
        import csv
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        import tensorflow as tf
        model_dir = os.environ.get("AURA_YAMNET_DIR", "models/yamnet")
        self._yamnet = tf.saved_model.load(model_dir)
        try:
            class_map_path = self._yamnet.class_map_path().numpy().decode()
        except Exception:  # noqa: BLE001
            class_map_path = os.path.join(model_dir, "assets",
                                          "yamnet_class_map.csv")
        with open(class_map_path) as f:
            self._class_names = [row["display_name"]
                                 for row in csv.DictReader(f)]
        self._class_idx = {name: i for i, name in enumerate(self._class_names)}

    def warmup(self) -> None:
        """Run one dummy inference so the timed scenario window doesn't
        absorb model load / graph tracing latency. No-op for DSP: pushing
        zeros through DspAnomalyScorer would poison its rolling baseline."""
        if self.backend_used == "yamnet":
            n = int(16000 * self.chunk_seconds)
            self._infer(np.zeros(n + n // 2, np.float32))

    def _infer(self, chunk: np.ndarray):
        chunk = np.asarray(chunk, dtype=np.float32)
        try:
            return self._yamnet(chunk)
        except (TypeError, ValueError):
            import tensorflow as tf
            out = self._yamnet.signatures["serving_default"](
                waveform=tf.constant(chunk))
            return out["output_0"], out.get("output_1"), out.get("output_2")

    def run(self, max_chunks: Optional[int] = None) -> Dict:
        import librosa
        audio, sr = librosa.load(self.source, sr=16000, mono=True)
        n = int(sr * self.chunk_seconds)
        half = n // 2
        # Include the trailing partial chunk. Short transient clips are often
        # appended after a baseline and the former ``len(audio) - n`` bound
        # silently discarded their final second. Pad only the DSP chunk;
        # YAMNet accepts the natural lookback window length.
        for i in range(0, len(audio), n):
            chunk = audio[i:i + n]
            if len(chunk) < n // 4:
                break
            if len(chunk) < n:
                chunk = np.pad(chunk, (0, n - len(chunk)))
            # YAMNet is scored over a lookback-extended window (chunk plus the
            # trailing half of the previous chunk), not the bare 1s chunk --
            # see _process_chunk docstring for why. DSP scoring is unaffected,
            # it still only ever sees `chunk`.
            yamnet_window = audio[max(0, i - half):min(len(audio), i + n)]
            self._process_chunk(chunk, sr, yamnet_window=yamnet_window,
                                scene_time_seconds=i / sr)
            self.metrics["chunks"] += 1
            if max_chunks and self.metrics["chunks"] >= max_chunks:
                break
            if self.realtime:
                time.sleep(self.chunk_seconds * 0.9)
        return self.metrics

    def _process_chunk(self, chunk: np.ndarray, sr: int,
                       yamnet_window: Optional[np.ndarray] = None,
                       scene_time_seconds: Optional[float] = None) -> None:
        """yamnet_window, max-pooling: independently re-windowing YAMNet on
        each non-overlapping 1s chunk resets its internal 0.96s/0.48s-hop
        frame boundaries every call, so a short transient (e.g. a ~0.5s glass
        break) straddling a chunk boundary gets analyzed by no frame that's
        well-centered on it in either chunk -- confirmed empirically: mean-
        pooled scores on non-overlapping 1s chunks never exceeded 0.11 on a
        clean single-event ESC-50 glass-break clip. Extending the window
        backward by half a chunk plus taking max (not mean) across internal
        frames recovers the transient (observed 0.5-0.75 on the same clip)
        without touching DSP's chunking/thresholds at all. See
        results/yamnet_integration_notes.md."""
        ts = now_ts()
        if self._yamnet is not None:
            infer_input = yamnet_window if yamnet_window is not None else chunk
            scores, _, _ = self._infer(infer_input)
            agg_scores = scores.numpy().max(axis=0)
            candidates = []
            for cls, (event_type, min_conf) in SURVEILLANCE_CLASSES.items():
                idx = self._class_idx.get(cls)
                if idx is None:
                    continue
                conf = float(agg_scores[idx])
                if conf >= min_conf:
                    candidates.append((conf, event_type, cls))
            best: Dict[str, tuple] = {}
            for conf, event_type, cls in candidates:
                if conf > best.get(event_type, (0.0, ""))[0]:
                    best[event_type] = (conf, cls)
            ranked = sorted(best.items(), key=lambda kv: -kv[1][0])[:self.top_k]
            self.metrics["suppressed_dupes"] += len(candidates) - len(ranked)
            for rank, (event_type, (conf, cls)) in enumerate(ranked):
                self._emit(event_type, conf, ts, {
                    "yamnet_class": cls, "yamnet_rank": rank,
                    "n_candidates": len(candidates),
                }, scene_time_seconds)
        else:
            score = self._dsp.score(chunk, sr)
            if score >= self.anomaly_threshold:
                self._emit("audio_anomaly", score, ts, {"method": "dsp_zscore"},
                           scene_time_seconds)

    def _emit(self, event_type: str, conf: float, ts: float, extra: Dict,
              scene_time_seconds: Optional[float] = None) -> None:
        ev = Event(event_id=new_id("ev"), sensor_id=self.agent_id, timestamp=ts,
                   event_type=event_type, confidence=round(conf, 3),
                   modality="audio", zone=self.zone, extra=extra,
                   scene_time_seconds=scene_time_seconds)
        self.metrics["events"] += 1
        self.log.info("AUDIO EVENT %s conf=%.2f", event_type, conf)
        self.bus.publish(TOPIC_EVENTS, ev.to_json(), qos=1)
