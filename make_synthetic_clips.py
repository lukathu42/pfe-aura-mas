"""Generate synthetic test clips so the full pipeline can be demoed without
downloading surveillance datasets.

- intrusion.mp4 : a synthetic 'person-like' figure walks into restricted
  zone_A (YOLO detects a rendered pedestrian sprite is unreliable, so this
  clip is mainly for pipeline plumbing; for the thesis use real UCF-Crime /
  Avenue clips or phone-recorded scripted scenes).
- overview.mp4  : mostly-empty scene (second camera).
- glass_break.wav : synthetic burst noise resembling glass break (triggers
  the DSP anomaly fallback of the AudioAgent).

Usage: python -m aura_mas.scripts.make_synthetic_clips
"""
from __future__ import annotations

import os

import cv2
import numpy as np


def draw_person(frame: np.ndarray, cx: int, cy: int, h: int = 120) -> None:
    """Draw a simple pedestrian-ish figure (torso, head, legs)."""
    w = h // 3
    color = (30, 60, 200)
    # torso
    cv2.rectangle(frame, (cx - w // 2, cy - h + h // 4),
                  (cx + w // 2, cy - h // 3), color, -1)
    # head
    cv2.circle(frame, (cx, cy - h + h // 8), h // 8, (80, 120, 220), -1)
    # legs
    cv2.rectangle(frame, (cx - w // 2, cy - h // 3), (cx - w // 8, cy), color, -1)
    cv2.rectangle(frame, (cx + w // 8, cy - h // 3), (cx + w // 2, cy), color, -1)


def make_video(path: str, seconds: int = 40, fps: int = 25,
               with_person: bool = True) -> None:
    w, h = 640, 480
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    rng = np.random.default_rng(7)
    for i in range(seconds * fps):
        t = i / fps
        frame = np.full((h, w, 3), 60, np.uint8)
        # floor + restricted zone marking
        cv2.rectangle(frame, (0, 300), (w, h), (80, 80, 80), -1)
        cv2.polylines(frame, [np.array([[100, 200], [500, 200],
                                        [500, 470], [100, 470]])],
                      True, (0, 0, 255), 2)
        cv2.putText(frame, "ZONE A - RESTRICTED", (110, 195),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        # noise for realism
        frame = cv2.add(frame, rng.integers(0, 12, (h, w, 3), dtype=np.uint8))
        if with_person and t >= 8.0:
            # person walks from left edge into zone A (t=12s) and loiters
            x = int(min(60 + (t - 8.0) * 60, 300))
            draw_person(frame, x, 460)
        vw.write(frame)
    vw.release()
    print("wrote", path)


def make_audio(path: str, seconds: int = 40, sr: int = 16000) -> None:
    rng = np.random.default_rng(3)
    audio = rng.normal(0, 0.005, seconds * sr)             # room noise
    # glass-break burst at t=14 s: sharp wideband transient + ringing
    t0 = 14 * sr
    burst = rng.normal(0, 0.6, sr // 4) * np.exp(-np.linspace(0, 8, sr // 4))
    ring = 0.3 * np.sin(2 * np.pi * 3200 * np.linspace(0, 0.5, sr // 2)) \
        * np.exp(-np.linspace(0, 10, sr // 2))
    audio[t0:t0 + sr // 4] += burst
    audio[t0 + sr // 4:t0 + sr // 4 + sr // 2] += ring
    # write WAV (16-bit PCM)
    import wave
    import struct
    data = np.clip(audio, -1, 1)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(struct.pack(f"<{len(data)}h",
                                  *(data * 32767).astype(np.int16)))
    print("wrote", path)


if __name__ == "__main__":
    os.makedirs("data/clips", exist_ok=True)
    make_video("data/clips/intrusion.mp4", with_person=True)
    make_video("data/clips/overview.mp4", with_person=False)
    make_audio("data/clips/glass_break.wav")
