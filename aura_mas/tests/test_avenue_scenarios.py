from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.io import savemat

from aura_mas.scenarios.avenue import build_avenue_manifests


def _avenue_fixture(root: Path) -> None:
    (root / "training_videos").mkdir(parents=True)
    (root / "testing_videos").mkdir()
    (root / "ground_truth_demo" / "testing_label_mask").mkdir(parents=True)
    for index in range(1, 4):
        (root / "testing_videos" / f"{index:02d}.avi").write_bytes(b"video")
        (root / "training_videos" / f"{index:02d}.avi").write_bytes(b"video")
    labels = np.zeros((10, 2, 2), dtype=np.uint8)
    labels[2:5, 0, 0] = 1
    savemat(root / "ground_truth_demo" / "testing_label_mask" / "01_label.mat",
            {"volLabel": labels})


def test_builds_distinct_test_and_normal_control_manifests(tmp_path):
    dataset = tmp_path / "avenue"
    output = tmp_path / "scenarios"
    _avenue_fixture(dataset)

    written = build_avenue_manifests(dataset, output, count=4, fps=10.0)

    assert [path.name for path in written] == [
        "avenue_test_01.json", "avenue_test_02.json",
        "avenue_test_03.json", "avenue_train_01.json",
    ]
    test_manifest = json.loads(written[0].read_text())
    train_manifest = json.loads(written[-1].read_text())
    assert test_manifest["ground_truth"] == [{
        "event_type": "anomaly", "zone": None,
        "t_start": 0.2, "t_end": 0.5,
    }]
    assert train_manifest["ground_truth"] == []
    assert test_manifest["dataset"] == "CUHK Avenue"
    assert test_manifest["split"] == "test"
    assert "duration_seconds" not in test_manifest
    assert test_manifest["sensors"][0]["source"] == str(
        dataset / "testing_videos" / "01.avi")


def test_requires_enough_distinct_clips(tmp_path):
    dataset = tmp_path / "avenue"
    output = tmp_path / "scenarios"
    _avenue_fixture(dataset)

    try:
        build_avenue_manifests(dataset, output, count=7)
    except ValueError as exc:
        assert "only 6" in str(exc)
    else:
        raise AssertionError("expected insufficient-clip failure")


def test_missing_dataset_fails_before_writing(tmp_path):
    output = tmp_path / "scenarios"

    try:
        build_avenue_manifests(tmp_path / "missing", output)
    except FileNotFoundError as exc:
        assert "testing_videos" in str(exc)
    else:
        raise AssertionError("expected missing dataset failure")
    assert not output.exists()
