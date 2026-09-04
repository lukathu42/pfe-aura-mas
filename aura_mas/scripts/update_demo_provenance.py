"""Add checksum-complete provenance for media referenced by demo manifests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable

import cv2
import soundfile as sf


def assets(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from assets(child)
    elif isinstance(value, list):
        for child in value:
            yield from assets(child)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        return round(sf.info(path).duration, 3)
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    capture.release()
    return round(frames / fps, 3) if fps else 0.0


def describe(relative: str) -> Dict[str, Any]:
    name = Path(relative).name
    value: Dict[str, Any] = {"path": relative}
    if relative.startswith("caviar/"):
        stem = Path(relative).stem
        dataset = "CAVIARDATA2" if stem.endswith(("cor", "front")) else "CAVIARDATA1"
        value.update(dataset_id=f"CAVIAR/{dataset}", clip_id=stem,
                     source_url=f"https://groups.inf.ed.ac.uk/vision/DATASETS/CAVIAR/{dataset}/{stem}/{stem}.mpg",
                     contributor="EC-funded CAVIAR project / IST 2001 37540",
                     license="Creative Commons BY-SA",
                     normalization="MPEG-1 decoded at source frame rate; H.264 CRF 23 yuv420p faststart; no trim and unchanged scene-time origin")
    elif relative.startswith("abandoned_object/"):
        clip = "video3" if "video3" in name else "video1"
        value.update(dataset_id="ABODA", clip_id=clip,
                     source_url="https://github.com/kevinlin311tw/ABODA",
                     contributor="Lin et al., ABODA",
                     license="Public research dataset; non-commercial academic evaluation",
                     normalization="Original AVI" if name.endswith(".avi") else "Browser-compatible H.264 yuv420p; no trim")
    elif relative.startswith("violence/"):
        clip = "violent_10" if "10" in name else "violent_1"
        value.update(dataset_id="AIRTLab violence dataset", clip_id=clip,
                     source_url="https://github.com/airtlab/A-Dataset-for-Automatic-Violence-Detection-in-Videos",
                     contributor="Bianculli et al., Data in Brief 33 (2020)",
                     license="Free for research and educational purposes",
                     normalization="Original source" if "demo" not in name else "Browser-compatible H.264 yuv420p; no trim")
    elif "fsd50k" in relative:
        clip_id = name.split("_")[1]
        details = {
            "9429": ("thanvannispen", "CC BY 3.0"),
            "169628": ("Dinsfire", "CC0 1.0"),
            "48052": ("JohnnyDiamond", "CC BY 3.0"),
        }[clip_id]
        value.update(dataset_id="FSD50K", clip_id=clip_id,
                     source_url=f"https://freesound.org/s/{clip_id}/",
                     contributor=details[0], license=details[1],
                     normalization="Original FSD50K WAV" if "with_baseline" not in name else "15 s seeded measured quiet baseline prepended; PCM16; event unchanged")
    elif "urbansound8k" in relative:
        clip_id = name.split("_")[2].split("-")[0]
        folds = {"111048": (6, "GaryQ", "CC0 1.0"),
                 "147317": (7, "udikagan", "CC0 1.0"),
                 "131571": (8, "deleted_user_389799", "CC BY 3.0"),
                 }
        fold, contributor, license = folds[clip_id]
        value.update(dataset_id="UrbanSound8K", clip_id=clip_id, fold=fold,
                     source_url=f"https://freesound.org/s/{clip_id}/",
                     contributor=contributor, license=license,
                     normalization="Official metadata onset/offset applied; mono PCM16" if "with_baseline" not in name else "Official excerpt plus 15 s seeded measured quiet baseline; mono PCM16")
    else:
        clip = name.replace("_with_baseline", "").removesuffix(".wav")
        value.update(dataset_id="ESC-50", clip_id=clip,
                     source_url=f"https://github.com/karolpiczak/ESC-50/blob/master/audio/{clip}.wav",
                     contributor="Karol J. Piczak / source contributor recorded in ESC-50 metadata",
                     license="CC BY-NC 3.0; non-commercial thesis use",
                     normalization="Original ESC-50 WAV" if "with_baseline" not in name else "15 s seeded measured quiet baseline prepended; PCM16")
    return value


def main() -> None:
    root = Path(".")
    manifest_path = root / "data/clips_real/manifest.json"
    provenance = json.loads(manifest_path.read_text())
    existing = {item["path"]: item for item in assets(provenance)}
    referenced = set()
    for scenario_path in (root / "scenarios").glob("*.json"):
        scenario = json.loads(scenario_path.read_text())
        for sensor in scenario.get("sensors", []):
            source = sensor.get("source", "")
            if source.startswith("data/clips_real/"):
                referenced.add(source.removeprefix("data/clips_real/"))
    generated = []
    for relative in sorted(referenced):
        path = root / "data/clips_real" / relative
        if not path.is_file():
            continue
        described = describe(relative)
        item = existing.get(relative) or described
        for key, value in described.items():
            item.setdefault(key, value)
        item["sha256"] = sha256(path)
        item["duration_seconds"] = duration(path)
        if relative not in existing:
            generated.append(item)
    provenance.setdefault("catalogue_v2_assets", []).extend(generated)
    provenance["catalogue_schema_version"] = 2
    provenance["catalogue_media_budget_bytes"] = 250 * 1024 * 1024
    manifest_path.write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"updated {len(existing)} existing assets and added {len(generated)} referenced assets")


if __name__ == "__main__":
    main()
