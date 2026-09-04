"""Deterministic replay/incident search documents.

This is deliberately lexical retrieval, not an embedding or anomaly model.
It indexes only records already produced by the surveillance pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

SEARCH_ALIASES = {
    "audio_scream": ["scream", "yell", "distress", "cry for help"],
    "audio_gunshot": ["gunshot", "gun fire", "weapon discharge", "impulse"],
}


def documents_from_replay(replay: Dict[str, Any]) -> List[Dict[str, Any]]:
    metadata = replay.get("metadata", {})
    scenario = replay["scenario"]
    anomaly = metadata.get("anomaly_key", metadata.get("anomaly_type", "unknown"))
    documents: List[Dict[str, Any]] = []

    for index, item in enumerate(replay.get("timeline", [])):
        if item.get("kind") not in {"event", "alert", "context"}:
            continue
        payload = item.get("payload", {})
        kind = item["kind"]
        summary = payload.get("summary") or payload.get("explanation") or metadata.get("description", "")
        event_type = payload.get("event_type")
        aliases = SEARCH_ALIASES.get(str(event_type), [])
        labels = payload.get("object_labels", [])
        extra = payload.get("extra", {})
        if isinstance(extra, dict):
            labels = [*labels, *[str(value) for key, value in extra.items()
                                if key in {"clip_label", "yamnet_class"}]]
        sensors = payload.get("sensors") or ([payload["sensor_id"]]
                                              if payload.get("sensor_id") else [])
        evidence = payload.get("evidence") or []
        document = {
            "schema_version": 1,
            "document_id": f"{scenario}:{kind}:{index}",
            "scenario": scenario,
            "anomaly_key": anomaly,
            "title": metadata.get("title", scenario),
            "sample_label": metadata.get("sample_label", scenario),
            "summary": summary,
            "search_text": " ".join(str(value) for value in (
                metadata.get("title", ""), metadata.get("sample_label", ""),
                metadata.get("description", ""), metadata.get("dataset", ""),
                event_type or "", payload.get("zone") or "", summary,
                " ".join(labels), " ".join(sensors), " ".join(aliases),
            )).lower(),
            "event_type": event_type,
            "zone": payload.get("zone"),
            "sensors": sensors,
            "scene_time_seconds": float(item.get("scene_time_seconds") or 0.0),
            "evidence_path": evidence[0] if evidence else payload.get("evidence_path"),
            "context_source": (payload.get("source", "deterministic")
                               if kind == "context" else kind),
        }
        documents.append(document)
    return documents


def build_index(replays: Iterable[Path], output: Path) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    for path in sorted(replays):
        try:
            replay = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if replay.get("schema_version") not in {1, 2}:
            continue
        documents.extend(documents_from_replay(replay))
    documents.sort(key=lambda item: (item["anomaly_key"], item["scenario"],
                                     item["scene_time_seconds"], item["document_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(item, sort_keys=True) + "\n"
                              for item in documents))
    return documents


def search_documents(documents: Iterable[Dict[str, Any]], query: str = "", **filters: Any) -> List[Dict[str, Any]]:
    """Deterministic phrase/token ranking shared by tests and non-web clients."""
    phrase = query.strip().lower()
    terms = re.findall(r"[\w-]+", phrase)
    results = []
    for document in documents:
        if any(value not in (None, "") and (
            (key == "sensor" and value not in document.get("sensors", [])) or
            (key != "sensor" and document.get(key) != value)
        ) for key, value in filters.items()):
            continue
        text = document.get("search_text", "").lower()
        if any(term not in text for term in terms):
            continue
        score = (8 if phrase and phrase in text else 0)
        score += sum(4 for term in terms if term in document.get("title", "").lower())
        score += sum(3 for term in terms if term in (document.get("event_type") or "").lower())
        score += sum(text.count(term) for term in terms)
        results.append({**document, "score": float(score)})
    return sorted(results, key=lambda item: (-item["score"], item["scene_time_seconds"],
                                              item["document_id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic prepared-replay search documents")
    parser.add_argument("--replays", default="results/prepared_replays")
    parser.add_argument("--out", default="results/search_documents.jsonl")
    args = parser.parse_args()
    docs = build_index(Path(args.replays).glob("*.json"), Path(args.out))
    print(f"wrote {len(docs)} search documents to {args.out}")


if __name__ == "__main__":
    main()
