"""Privacy invariant tests: evidence frames must never leave unblurred.

Exercises `core/privacy.py` without any ML model: explicit boxes, the
HOG fallback, and the fail-closed path taken on OpenCV builds with no
HOGDescriptor.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from aura_mas.core import privacy


@pytest.fixture
def noise_frame() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)


def test_anonymize_frame_blurs_only_given_boxes(noise_frame):
    out = privacy.anonymize_frame(noise_frame, boxes=[(10, 10, 60, 70)])
    assert not np.array_equal(out[10:70, 10:60], noise_frame[10:70, 10:60])
    assert np.array_equal(out[:, 100:], noise_frame[:, 100:])
    assert not np.shares_memory(out, noise_frame)


def test_anonymize_frame_head_region_blurred_more_than_body(noise_frame):
    box = (20, 20, 140, 110)
    out = privacy.anonymize_frame(noise_frame, boxes=[box])
    head = out[20:50, 20:140]
    body = out[80:110, 20:140]
    assert float(head.std()) < float(body.std())


def test_blur_region_clamps_to_frame_and_ignores_empty_box(noise_frame):
    out = noise_frame.copy()
    privacy._blur_region(out, (-50, -50, 10_000, 10_000))
    assert not np.array_equal(out, noise_frame)

    out2 = noise_frame.copy()
    privacy._blur_region(out2, (30, 30, 30, 40))
    privacy._blur_region(out2, (30, 30, 40, 30))
    assert np.array_equal(out2, noise_frame)


def test_detect_persons_fails_closed_without_hog(monkeypatch, noise_frame):
    monkeypatch.setattr(privacy, "_person_detector", None)
    monkeypatch.delattr(cv2, "HOGDescriptor", raising=False)
    assert privacy._detect_persons(noise_frame) == [(0, 0, 160, 120)]


def test_anonymize_frame_without_boxes_uses_detector(monkeypatch, noise_frame):
    monkeypatch.setattr(privacy, "_detect_persons",
                        lambda img: [(0, 0, img.shape[1], img.shape[0])])
    out = privacy.anonymize_frame(noise_frame)
    assert not np.array_equal(out, noise_frame)


def test_detect_persons_rescales_boxes_to_full_resolution(monkeypatch):
    big = np.zeros((1280, 1920, 3), dtype=np.uint8)

    class FakeHog:
        def setSVMDetector(self, _):
            pass

        def detectMultiScale(self, img, winStride):
            assert max(img.shape[:2]) <= 640, "detection must run downscaled"
            return [(10, 20, 30, 40)], None

    monkeypatch.setattr(privacy, "_person_detector", None)
    monkeypatch.setattr(cv2, "HOGDescriptor", FakeHog, raising=False)
    monkeypatch.setattr(cv2, "HOGDescriptor_getDefaultPeopleDetector",
                        lambda: None, raising=False)
    (x1, y1, x2, y2), = privacy._detect_persons(big)
    assert (x1, y1, x2, y2) == (30, 60, 120, 180)


def test_anonymize_and_save_writes_blurred_jpeg(tmp_path, noise_frame):
    out_dir = tmp_path / "evidence" / "nested"
    path = privacy.anonymize_and_save(noise_frame, str(out_dir),
                                      prefix="cam_01_intrusion",
                                      boxes=[(0, 0, 160, 120)])
    assert path.startswith(str(out_dir)) and path.endswith(".jpg")
    assert "cam_01_intrusion" in path
    saved = cv2.imread(path)
    assert saved is not None and saved.shape == noise_frame.shape
    assert not np.array_equal(saved, noise_frame)


def test_anonymize_and_save_paths_are_unique(tmp_path, noise_frame):
    paths = {privacy.anonymize_and_save(noise_frame, str(tmp_path),
                                        boxes=[(0, 0, 10, 10)])
             for _ in range(5)}
    assert len(paths) == 5
