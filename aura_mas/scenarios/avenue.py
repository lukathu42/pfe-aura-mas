"""Build replay manifests from the official CUHK Avenue dataset.

The dataset is intentionally not vendored. This adapter turns an extracted
Avenue archive into the repository's existing scenario schema and preserves
the official split and mask-derived time windows in every generated manifest.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List, Optional

import numpy as np


DATASET_NAME = "CUHK Avenue"
DATASET_URL = "https://www.cse.cuhk.edu.hk/~leojia/projects/detectabnormal/Avenue_Dataset.zip"
GROUND_TRUTH_URL = "https://www.cse.cuhk.edu.hk/~leojia/projects/detectabnormal/ground_truth_demo.zip"


def _video_dir(root: Path, split: str) -> Path:
    candidates = [root / f"{split}_videos", root / "ground_truth_demo" / f"{split}_videos"]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Avenue {split}_videos directory not found under {root}")


def _mask_path(root: Path, index: int) -> Optional[Path]:
    names = (f"{index:02d}_label.mat", f"{index}_label.mat")
    for base in (root, root / "ground_truth_demo"):
        for name in names:
            matches = sorted(base.rglob(name))
            if matches:
                return matches[0]
    return None


def _mask_frame_flags(mask_path: Path) -> List[bool]:
    try:
        from scipy.io import loadmat
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "scipy is required to convert Avenue ground-truth masks") from exc

    data = loadmat(mask_path)
    if "volLabel" not in data:
        raise ValueError(f"{mask_path} has no volLabel variable")
    value = data["volLabel"]
    if value.dtype == object:
        return [bool(np.asarray(item).any())
                for item in value.reshape(-1)]

    array = np.asarray(value)
    if array.ndim == 1:
        return [bool(item) for item in array]
    frame_axis = max(range(array.ndim), key=lambda axis: array.shape[axis])
    reduced = np.moveaxis(array, frame_axis, 0).reshape(array.shape[frame_axis], -1)
    return [bool(frame.any()) for frame in reduced]


def _intervals(mask_path: Optional[Path], fps: float) -> List[dict[str, Any]]:
    if mask_path is None:
        return []
    flags = _mask_frame_flags(mask_path)
    intervals: List[dict[str, Any]] = []
    start: Optional[int] = None
    for index, active in enumerate(flags + [False]):
        if active and start is None:
            start = index
        elif not active and start is not None:
            intervals.append({
                "event_type": "anomaly", "zone": None,
                "t_start": round(start / fps, 3),
                "t_end": round(index / fps, 3),
            })
            start = None
    return intervals


def _clips(root: Path, split: str) -> List[Path]:
    return sorted(_video_dir(root, split).glob("*.avi"))


def _source_path(path: Path, dataset_root: Path, source_prefix: Optional[str]) -> str:
    if source_prefix:
        relative = path.relative_to(dataset_root).as_posix()
        return f"{source_prefix.rstrip('/')}/{relative}"
    return path.as_posix()


def _duration_seconds(path: Path) -> Optional[float]:
    try:
        import cv2
        capture = cv2.VideoCapture(str(path))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        capture.release()
    except Exception:  # pragma: no cover - codec/environment dependent
        return None
    if fps <= 0 or frames <= 0:
        return None
    return round(frames / fps, 3)


def build_avenue_manifests(dataset_root: Path, output_dir: Path,
                           count: int = 30, fps: float = 25.0,
                           source_prefix: Optional[str] = None) -> List[Path]:
    """Write up to ``count`` distinct Avenue clip manifests.

    Test clips are selected first, followed by training clips as explicit
    normal controls. The default count therefore produces 21 test clips plus
    9 normal controls, matching the requested 30 scenario identities.
    """
    dataset_root = Path(dataset_root)
    if count < 1:
        raise ValueError("count must be positive")
    test_clips = _clips(dataset_root, "testing")
    train_clips = _clips(dataset_root, "training")
    clips = [("test", path) for path in test_clips]
    clips.extend(("train", path) for path in train_clips)
    if len(clips) < count:
        raise ValueError(f"requested {count} clips, but only {len(clips)} are available")

    manifests: List[Path] = []
    for split, path in clips[:count]:
        index = int(path.stem)
        ground_truth = _intervals(_mask_path(dataset_root, index), fps) if split == "test" else []
        manifest = {
            "name": f"avenue_{split}_{index:02d}",
            "dataset": DATASET_NAME,
            "dataset_url": DATASET_URL,
            "ground_truth_url": GROUND_TRUTH_URL,
            "split": split,
            "clip_id": f"{index:02d}",
            "sensors": [{
                "type": "camera", "id": "cam_01",
                "source": _source_path(path, dataset_root, source_prefix),
                "zones": [],
                "enable_clip": True,
            }],
            "ground_truth": ground_truth,
            "notes": (
                "CUHK Avenue clip. Test intervals are derived from the official "
                "volLabel mask at the declared source FPS; training clips are "
                "normal controls with no anomaly ground truth."
            ),
        }
        duration = _duration_seconds(path)
        if duration is not None:
            manifest["duration_seconds"] = duration
        output_path = output_dir / f"{manifest['name']}.json"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, indent=2) + "\n")
        manifests.append(output_path)
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--out", type=Path, default=Path("scenarios"))
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--source-prefix", default=None,
                        help="manifest path prefix, e.g. data/avenue")
    args = parser.parse_args()
    paths = build_avenue_manifests(args.dataset_root, args.out, args.count,
                                   args.fps, args.source_prefix)
    print(f"wrote {len(paths)} Avenue manifests to {args.out}")


if __name__ == "__main__":
    main()
