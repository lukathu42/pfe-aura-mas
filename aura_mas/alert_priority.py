"""Learned alert prioritization for operator triage.

This module intentionally uses only the Python standard library. The project
does not carry scikit-learn, and this model is small enough that a compact
logistic-regression trainer is easier to audit than a new dependency.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from aura_mas.core.taxonomy import EVENT_FAMILIES

MODEL_VERSION = "alert-priority-logreg-v1"
DEFAULT_MODEL_PATH = "results/alert_priority_model.json"

HASH_BUCKETS = 8
NUMERIC_FEATURES = (
    "bias",
    "confidence",
    "severity_level",
    "n_sensors",
    "n_evidence",
    "n_fused_events",
    "has_audio",
    "has_video",
    "is_composite",
    "verified",
)
CATEGORICAL_PREFIXES = ("event_type", "family", "zone")


@dataclass
class PriorityPrediction:
    priority_score: float
    false_positive_risk: float
    priority_label: str
    priority_model_version: str

    def as_alert_fields(self) -> Dict[str, Any]:
        return {
            "priority_score": round(self.priority_score, 3),
            "false_positive_risk": round(self.false_positive_risk, 3),
            "priority_label": self.priority_label,
            "priority_model_version": self.priority_model_version,
        }


def _severity_level(severity: str) -> float:
    return {"INFO": 0.33, "WARNING": 0.66, "CRITICAL": 1.0}.get(severity, 0.33)


def _hash_feature(prefix: str, value: Optional[str]) -> str:
    text = value or "unknown"
    digest = hashlib.sha1(f"{prefix}:{text}".encode("utf-8")).hexdigest()
    return f"{prefix}_{int(digest[:8], 16) % HASH_BUCKETS}"


def feature_names() -> List[str]:
    names = list(NUMERIC_FEATURES)
    for prefix in CATEGORICAL_PREFIXES:
        names.extend(f"{prefix}_{i}" for i in range(HASH_BUCKETS))
    return names


FEATURE_NAMES = feature_names()


def alert_features(alert: Dict[str, Any]) -> List[float]:
    sensors = alert.get("sensors") or []
    evidence = alert.get("evidence") or []
    fused_events = alert.get("fused_events") or []
    contributing = alert.get("contributing_types") or [alert.get("event_type", "unknown")]
    event_type = alert.get("event_type", "unknown")
    family = EVENT_FAMILIES.get(event_type, event_type)
    extra = alert.get("priority_extra") or {}

    values = {name: 0.0 for name in FEATURE_NAMES}
    values.update({
        "bias": 1.0,
        "confidence": float(alert.get("confidence") or 0.0),
        "severity_level": _severity_level(str(alert.get("severity", "INFO"))),
        "n_sensors": min(len(sensors), 4) / 4.0,
        "n_evidence": min(len(evidence), 5) / 5.0,
        "n_fused_events": min(len(fused_events), 8) / 8.0,
        "has_audio": 1.0 if any(str(s).startswith("mic") for s in sensors) else 0.0,
        "has_video": 1.0 if any(str(s).startswith("cam") for s in sensors) else 0.0,
        "is_composite": 1.0 if len(set(contributing)) > 1 else 0.0,
        "verified": 1.0 if extra.get("verified") else 0.0,
    })
    for prefix, value in (
        ("event_type", event_type),
        ("family", family),
        ("zone", alert.get("zone") or "site"),
    ):
        values[_hash_feature(prefix, str(value))] = 1.0
    return [values[name] for name in FEATURE_NAMES]


def _alert_scene_time(alert: Dict[str, Any], run: Dict[str, Any]) -> float:
    if alert.get("scene_time_seconds") is not None:
        return float(alert["scene_time_seconds"])
    return float(alert.get("t_wall", 0.0)) - float(run.get("t_start", 0.0))


def label_alerts(run: Dict[str, Any], tolerance: float = 5.0) -> List[Tuple[Dict[str, Any], int]]:
    """Return (alert, useful_label) rows using the same family/time matching
    policy as eval.metrics. Each ground-truth event can match at most one
    alert; unmatched alerts become negative examples."""
    gt = run.get("ground_truth", [])
    matched_gt, matched_alerts = set(), set()
    alerts = list(run.get("alerts", []))
    for gi, g in enumerate(gt):
        g_family = EVENT_FAMILIES.get(g["event_type"], g["event_type"])
        for ai, alert in enumerate(alerts):
            if ai in matched_alerts:
                continue
            a_family = EVENT_FAMILIES.get(alert.get("event_type"), alert.get("event_type"))
            a_t = _alert_scene_time(alert, run)
            if a_family == g_family and (g["t_start"] - tolerance) <= a_t <= (
                    g.get("t_end", g["t_start"]) + tolerance):
                matched_gt.add(gi)
                matched_alerts.add(ai)
                break
    return [(alert, 1 if i in matched_alerts else 0) for i, alert in enumerate(alerts)]


def build_dataset(paths: Sequence[str], tolerance: float = 5.0) -> List[Tuple[List[float], int, Dict[str, Any]]]:
    rows: List[Tuple[List[float], int, Dict[str, Any]]] = []
    for path in paths:
        with open(path) as f:
            run = json.load(f)
        for alert, label in label_alerts(run, tolerance=tolerance):
            meta = {
                "path": path,
                "scenario": run.get("scenario"),
                "mode": run.get("mode"),
                "alert_id": alert.get("alert_id"),
            }
            rows.append((alert_features(alert), label, meta))
    return rows


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def train_logreg(rows: Sequence[Tuple[List[float], int, Dict[str, Any]]],
                 epochs: int = 500, learning_rate: float = 0.15,
                 l2: float = 0.001) -> List[float]:
    if not rows:
        raise ValueError("no training rows")
    dim = len(rows[0][0])
    weights = [0.0] * dim
    positives = sum(y for _, y, _ in rows)
    negatives = len(rows) - positives
    pos_weight = len(rows) / (2.0 * positives) if positives else 1.0
    neg_weight = len(rows) / (2.0 * negatives) if negatives else 1.0
    for _ in range(epochs):
        grad = [0.0] * dim
        for x, y, _ in rows:
            pred = _sigmoid(sum(w * v for w, v in zip(weights, x)))
            err = (pred - y) * (pos_weight if y == 1 else neg_weight)
            for i, value in enumerate(x):
                grad[i] += err * value
        n = float(len(rows))
        for i in range(dim):
            penalty = 0.0 if FEATURE_NAMES[i] == "bias" else l2 * weights[i]
            weights[i] -= learning_rate * (grad[i] / n + penalty)
    return weights


def evaluate_weights(rows: Sequence[Tuple[List[float], int, Dict[str, Any]]],
                     weights: Sequence[float], threshold: float = 0.5) -> Dict[str, Any]:
    tp = fp = tn = fn = 0
    losses = []
    for x, y, _ in rows:
        p = _sigmoid(sum(w * v for w, v in zip(weights, x)))
        pred = p >= threshold
        tp += int(pred and y == 1)
        fp += int(pred and y == 0)
        tn += int((not pred) and y == 0)
        fn += int((not pred) and y == 1)
        p = min(max(p, 1e-6), 1 - 1e-6)
        losses.append(-(y * math.log(p) + (1 - y) * math.log(1 - p)))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": len(rows), "positives": sum(y for _, y, _ in rows),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "log_loss": round(sum(losses) / len(losses), 4) if losses else None,
    }


class AlertPriorityScorer:
    def __init__(self, weights: Sequence[float],
                 version: str = MODEL_VERSION,
                 threshold_high: float = 0.75,
                 threshold_medium: float = 0.45) -> None:
        self.weights = list(weights)
        self.version = version
        self.threshold_high = threshold_high
        self.threshold_medium = threshold_medium

    @classmethod
    def load(cls, path: str = DEFAULT_MODEL_PATH) -> "AlertPriorityScorer":
        with open(path) as f:
            data = json.load(f)
        return cls(
            weights=data["weights"],
            version=data.get("model_version", MODEL_VERSION),
            threshold_high=float(data.get("threshold_high", 0.75)),
            threshold_medium=float(data.get("threshold_medium", 0.45)),
        )

    def predict(self, alert: Dict[str, Any]) -> PriorityPrediction:
        x = alert_features(alert)
        score = _sigmoid(sum(w * v for w, v in zip(self.weights, x)))
        if score >= self.threshold_high:
            label = "HIGH"
        elif score >= self.threshold_medium:
            label = "MEDIUM"
        else:
            label = "LOW"
        return PriorityPrediction(
            priority_score=score,
            false_positive_risk=1.0 - score,
            priority_label=label,
            priority_model_version=self.version,
        )


def save_model(path: str, weights: Sequence[float], metrics: Dict[str, Any],
               source_paths: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump({
            "model_version": MODEL_VERSION,
            "feature_names": FEATURE_NAMES,
            "weights": list(weights),
            "threshold_high": 0.75,
            "threshold_medium": 0.45,
            "metrics": metrics,
            "sources": list(source_paths),
        }, f, indent=2)


def expand_paths(patterns: Iterable[str]) -> List[str]:
    paths: List[str] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        paths.extend(matches if matches else [pattern])
    return [p for p in paths if os.path.exists(p)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train learned alert-priority model")
    parser.add_argument("runs", nargs="+", help="run JSON files or globs")
    parser.add_argument("--out", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--tolerance", type=float, default=5.0)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--learning-rate", type=float, default=0.15)
    parser.add_argument("--l2", type=float, default=0.001)
    args = parser.parse_args()

    paths = expand_paths(args.runs)
    rows = build_dataset(paths, tolerance=args.tolerance)
    if not rows:
        raise SystemExit("no alert rows found in requested run files")
    weights = train_logreg(rows, epochs=args.epochs,
                           learning_rate=args.learning_rate, l2=args.l2)
    metrics = evaluate_weights(rows, weights)
    save_model(args.out, weights, metrics, paths)
    print(f"trained {MODEL_VERSION}: {metrics}")
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
