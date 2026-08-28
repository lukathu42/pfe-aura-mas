"""Optional OpenAI-compatible VLM annotation for prepared replays.

Annotations are presentation/search context only. They are never published on
the event bus and therefore cannot create or alter alerts or evaluation data.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2


def deterministic_annotation(replay: Dict[str, Any], status: str = "generated") -> Dict[str, Any]:
    metadata = replay.get("metadata", {})
    start = min((float(a.get("scene_time_seconds") or 0.0)
                 for a in replay.get("alerts", [])), default=0.0)
    return {
        "context_id": f"ctx_{replay['scenario']}_deterministic",
        "scenario": replay["scenario"],
        "summary": metadata.get("description", "Prepared surveillance incident."),
        "object_labels": [],
        "safety_observations": metadata.get("detected_event_types", []),
        "source": "deterministic", "status": status, "model": None,
        "provider": None, "source_frame_times": [start],
        "generated_at": time.time(),
    }


def _jpeg_data_urls(video_path: Path, times: List[float]) -> List[str]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open context source {video_path}")
    values: List[str] = []
    try:
        for scene_time in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, scene_time) * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                values.append("data:image/jpeg;base64," +
                              base64.b64encode(encoded).decode("ascii"))
    finally:
        cap.release()
    return values


def vlm_annotation(replay: Dict[str, Any], video_path: Path,
                   frame_times: List[float]) -> Dict[str, Any]:
    from openai import OpenAI
    base_url = os.environ.get("AURA_VLM_BASE_URL")
    model = os.environ.get("AURA_VLM_MODEL")
    if not base_url or not model:
        raise RuntimeError("AURA_VLM_BASE_URL and AURA_VLM_MODEL are required")
    client = OpenAI(base_url=base_url,
                    api_key=os.environ.get("AURA_VLM_API_KEY", "local"))
    content: List[Dict[str, Any]] = [{
        "type": "text",
        "text": ("Describe only visible people, objects and safety-relevant actions. "
                 "Return JSON with summary, object_labels, safety_observations. "
                 "Do not decide whether an alert should exist."),
    }]
    for url in _jpeg_data_urls(video_path, frame_times):
        content.append({"type": "image_url", "image_url": {"url": url}})
    response = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": content}],
        response_format={"type": "json_object"}, timeout=120,
    )
    parsed = json.loads(response.choices[0].message.content or "{}")
    return {
        "context_id": f"ctx_{replay['scenario']}_vlm",
        "scenario": replay["scenario"],
        "summary": str(parsed.get("summary", "")),
        "object_labels": [str(value) for value in parsed.get("object_labels", [])],
        "safety_observations": [str(value) for value in parsed.get("safety_observations", [])],
        "source": "vlm", "status": "generated", "model": model,
        "provider": base_url, "source_frame_times": frame_times,
        "generated_at": time.time(),
    }


def add_annotation(replay: Dict[str, Any], annotation: Dict[str, Any]) -> None:
    replay["schema_version"] = 2
    replay.setdefault("metadata", {})["has_context"] = True
    replay.setdefault("timeline", []).append({
        "kind": "context",
        "scene_time_seconds": min(annotation.get("source_frame_times") or [0.0]),
        "wall_offset_seconds": 0.0,
        "payload": annotation,
    })
    replay["timeline"].sort(key=lambda item: (
        item.get("scene_time_seconds") if item.get("scene_time_seconds") is not None
        else item.get("wall_offset_seconds", 0.0), item.get("wall_offset_seconds", 0.0)))


def annotation_with_fallback(replay: Dict[str, Any], video_path: Path,
                             frame_times: List[float]) -> Dict[str, Any]:
    """Never let an optional provider failure remove deterministic context."""
    try:
        return vlm_annotation(replay, video_path, frame_times)
    except Exception as exc:  # noqa: BLE001 - adapter/network failures are optional
        annotation = deterministic_annotation(replay, status="failed")
        annotation["failure_reason"] = type(exc).__name__
        return annotation


def main() -> None:
    parser = argparse.ArgumentParser(description="Add optional VLM context to a prepared replay")
    parser.add_argument("replay")
    parser.add_argument("video")
    parser.add_argument("--times", default="0")
    args = parser.parse_args()
    path = Path(args.replay)
    replay = json.loads(path.read_text())
    times = [float(value) for value in args.times.split(",")]
    annotation = annotation_with_fallback(replay, Path(args.video), times)
    add_annotation(replay, annotation)
    path.write_text(json.dumps(replay, indent=2) + "\n")
    print(f"added VLM context to {path}")


if __name__ == "__main__":
    main()
