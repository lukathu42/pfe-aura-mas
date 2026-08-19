"""Privacy-by-design utilities.

Every piece of visual evidence leaving an edge agent passes through
`anonymize_and_save`, which blurs person regions (and faces when a face
detector is available) before writing to the evidence store. Raw frames
are never persisted or transmitted.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import List, Optional, Tuple

import cv2
import numpy as np

_person_detector = None  # lazy singleton (HOG fallback, YOLO if provided)


def _blur_region(img: np.ndarray, box: Tuple[int, int, int, int],
                 k: int = 41) -> None:
    x1, y1, x2, y2 = [max(0, int(v)) for v in box]
    x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return
    roi = img[y1:y2, x1:x2]
    img[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)


def _detect_persons(img: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Lightweight person localization for anonymization (HOG; fast, CPU).

    Preferred path: the caller (CameraAgent) passes YOLO person boxes, so
    this fallback is only used when no boxes are supplied. If OpenCV lacks
    HOGDescriptor (headless minimal builds), we return a full-frame region
    so the evidence is still anonymized (fail-closed privacy).
    """
    global _person_detector
    if _person_detector is None:
        if not hasattr(cv2, "HOGDescriptor"):
            return [(0, 0, img.shape[1], img.shape[0])]  # fail-closed: blur all
        _person_detector = cv2.HOGDescriptor()
        _person_detector.setSVMDetector(
            cv2.HOGDescriptor_getDefaultPeopleDetector())
    scale = 640 / max(img.shape[:2])
    small = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img
    rects, _ = _person_detector.detectMultiScale(small, winStride=(8, 8))
    inv = 1 / scale if scale < 1 else 1.0
    return [(int(x * inv), int(y * inv), int((x + w) * inv), int((y + h) * inv))
            for (x, y, w, h) in rects]


def anonymize_frame(frame: np.ndarray,
                    boxes: Optional[List[Tuple[int, int, int, int]]] = None
                    ) -> np.ndarray:
    """Return a copy of `frame` with person regions blurred."""
    out = frame.copy()
    regions = boxes if boxes is not None else _detect_persons(out)
    for box in regions:
        # blur upper third (head region) strongly + whole box lightly
        x1, y1, x2, y2 = box
        _blur_region(out, (x1, y1, x2, y1 + (y2 - y1) // 3), k=61)
        _blur_region(out, box, k=21)
    return out


def anonymize_and_save(frame: np.ndarray, evidence_dir: str,
                       prefix: str = "evidence",
                       boxes: Optional[List[Tuple[int, int, int, int]]] = None
                       ) -> str:
    os.makedirs(evidence_dir, exist_ok=True)
    anon = anonymize_frame(frame, boxes)
    name = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
    path = os.path.join(evidence_dir, name)
    cv2.imwrite(path, anon, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return path



