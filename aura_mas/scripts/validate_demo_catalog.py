"""Validate that every declared defence replay is complete and evidence-backed."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable

from aura_mas.core.taxonomy import EVENT_FAMILIES
from aura_mas.scenarios.demo_catalog import DEMO_SCENARIOS

ALLOWED_LICENSES = ("CC0", "CC BY", "Creative Commons BY-SA", "research", "educational")
MULTI_CAMERA_FAMILIES = {"perimeter_intrusion", "loitering", "zone_occupancy", "wrong_direction"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _provenance_assets(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from _provenance_assets(child)
    elif isinstance(value, list):
        for child in value:
            yield from _provenance_assets(child)


def validate_catalog(root: Path) -> Dict[str, Any]:
    provenance_path = root / "data/clips_real/manifest.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {}
    by_path = {item["path"]: item for item in _provenance_assets(provenance)}
    results = []
    for name, metadata in sorted(DEMO_SCENARIOS.items()):
        errors: list[str] = []
        manifest_path = root / "scenarios" / f"{name}.json"
        replay_path = root / "results/prepared_replays" / f"{name}.json"
        manifest = replay = None
        if not manifest_path.exists():
            errors.append("missing scenario manifest")
        else:
            try:
                manifest = json.loads(manifest_path.read_text())
            except json.JSONDecodeError:
                errors.append("invalid scenario JSON")
        if manifest:
            if manifest.get("name") != name:
                errors.append("manifest name does not match filename")
            expected = set(metadata.get("detected_event_types", []))
            ground_truth = {item.get("event_type") for item in manifest.get("ground_truth", [])}
            if not expected.issubset(ground_truth):
                errors.append("ground truth does not contain expected event type")
            cameras = [sensor for sensor in manifest.get("sensors", []) if sensor.get("type") == "camera"]
            if metadata["anomaly_key"] in MULTI_CAMERA_FAMILIES and len(cameras) < 2:
                errors.append("multi-camera family has fewer than two cameras")
            for sensor in manifest.get("sensors", []):
                source = sensor.get("source")
                if not isinstance(source, str) or not source.startswith("data/clips_real/"):
                    errors.append(f"invalid real-media source for {sensor.get('id', 'sensor')}")
                    continue
                media = root / source
                if not media.is_file() or media.stat().st_size == 0:
                    errors.append(f"missing media: {source}")
                relative = source.removeprefix("data/clips_real/")
                asset = by_path.get(relative)
                if not asset:
                    errors.append(f"missing provenance: {relative}")
                else:
                    license_name = str(asset.get("license", ""))
                    if not any(marker.lower() in license_name.lower() for marker in ALLOWED_LICENSES):
                        errors.append(f"unapproved or absent license: {relative}")
                    expected_hash = asset.get("sha256") or asset.get("generated_sha256")
                    if expected_hash and media.is_file() and sha256(media) != expected_hash:
                        errors.append(f"checksum mismatch: {relative}")
        if not replay_path.exists():
            errors.append("missing prepared replay")
        else:
            try:
                replay = json.loads(replay_path.read_text())
            except json.JSONDecodeError:
                errors.append("invalid prepared replay JSON")
        if replay:
            if replay.get("schema_version") not in {1, 2}:
                errors.append("unsupported prepared replay schema")
            expected = set(metadata.get("detected_event_types", []))
            actual = {alert.get("event_type") for alert in replay.get("alerts", [])}
            if not expected.intersection(actual):
                errors.append("prepared replay has no expected real alert")
            if metadata["anomaly_key"] in MULTI_CAMERA_FAMILIES:
                coordinated = any(len(alert.get("sensors", [])) >= 2 for alert in replay.get("alerts", []))
                coordinated |= any(item.get("kind") in {"task", "award", "verification"}
                                   for item in replay.get("timeline", []))
                if not coordinated:
                    errors.append("multi-camera replay has no coordination evidence")
        results.append({"scenario": name, "anomaly_key": metadata["anomaly_key"],
                        "status": "ready" if not errors else "incomplete", "errors": errors})
    groups = Counter(item["anomaly_key"] for item in DEMO_SCENARIOS.values())
    summary_errors = []
    if len(DEMO_SCENARIOS) != 36 or len(groups) != 12 or any(count != 3 for count in groups.values()):
        summary_errors.append("catalogue must contain exactly 36 entries in 12 groups of three")
    return {
        "schema_version": 1,
        "summary": {"declared": len(results), "ready": sum(r["status"] == "ready" for r in results),
                    "incomplete": sum(r["status"] != "ready" for r in results),
                    "errors": summary_errors},
        "families": dict(sorted(groups.items())), "scenarios": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = validate_catalog(args.root.resolve())
    rendered = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(rendered, end="")
    raise SystemExit(1 if report["summary"]["incomplete"] or report["summary"]["errors"] else 0)


if __name__ == "__main__":
    main()
