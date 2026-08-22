"""Shared video-source helpers: open with an fps fallback, strided frame
iteration. Used by CameraAgent and the offline analysis scripts
(probe_zones, estimate_motion_windows, calibrate_clip), which previously
each re-implemented the same capture/stride/release loop."""
from __future__ import annotations

from typing import Iterator, Tuple

import cv2
import numpy as np


def open_video(source) -> Tuple["cv2.VideoCapture", float]:
    """Open a video source, raising if it cannot be read; returns
    (capture, fps) with a 25 fps fallback for containers that report 0."""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open source {source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    return cap, fps


def iter_frames(cap: "cv2.VideoCapture", stride: int = 1,
                start: int = 0) -> Iterator[Tuple[int, np.ndarray]]:
    """Yield (frame_idx, frame) for frames whose index is a multiple of
    `stride`, counting indices from `start`. Releases the capture when
    the source is exhausted or the caller stops iterating."""
    idx = start
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % stride == 0:
                yield idx, frame
            idx += 1
    finally:
        cap.release()
