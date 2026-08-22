"""GT-annotation aid: locate coarse motion windows in a clip.

The public datasets used to build the scenario pack (ABODA, AIRTLab violence
dataset) ship without frame-level ground truth. This script gives a
reproducible, non-manual starting point for the ground_truth timestamps in
scenarios/*.json: it downsamples frames, computes grayscale frame-to-frame
difference, and reports contiguous windows where the mean difference exceeds
a threshold. Output still needs a human sanity pass (see scenario manifests
for the timestamps actually used and how they were adjusted).

Usage: python -m aura_mas.scripts.estimate_motion_windows <video_path> [--threshold 3.0] [--stride 5]
"""
from __future__ import annotations

import argparse

import cv2

from aura_mas.core.video import iter_frames, open_video


def motion_windows(path: str, threshold: float = 3.0, stride: int = 5,
                    merge_gap: float = 2.0) -> list[tuple[float, float]]:
    cap, fps = open_video(path)
    prev = None
    hits: list[float] = []
    for frame_idx, frame in iter_frames(cap, stride):
        gray = cv2.cvtColor(cv2.resize(frame, (160, 120)), cv2.COLOR_BGR2GRAY)
        if prev is not None:
            diff = cv2.absdiff(gray, prev).mean()
            if diff > threshold:
                hits.append(frame_idx / fps)
        prev = gray

    windows: list[tuple[float, float]] = []
    for ts in hits:
        if windows and ts - windows[-1][1] <= merge_gap:
            windows[-1] = (windows[-1][0], ts)
        else:
            windows.append((ts, ts))
    return windows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--threshold", type=float, default=3.0)
    ap.add_argument("--stride", type=int, default=5)
    args = ap.parse_args()
    for start, end in motion_windows(args.video, args.threshold, args.stride):
        print(f"{start:6.1f}s - {end:6.1f}s")
