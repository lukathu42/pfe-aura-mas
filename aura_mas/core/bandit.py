"""Toy contextual-bandit bidder for CoordinatorAgent's `auction-bandit` mode.

Disjoint LinUCB (Li, Chu, Langford, Wang, WSDM 2011, arXiv:1003.5956): one
independent linear model per arm (camera_id), selecting the arm with the
highest upper-confidence bound on expected reward given the current task
context. This is a deliberately small, illustrative learner trained purely
against this project's own CPU replay harness -- see
results/auction_bandit_notes.md and docs/ai-enhancement-research.md Section
4.2 for why it must be read as a mechanism demonstration, not a validated
improvement over the hand-coded `auction` heuristic.

Context features mirror what `CameraAgent._view_score` already reads off the
same task dict (origin_sensor, zone, event_type); `fov_overlap`/`busy` are
not available to the coordinator (they live only inside each CameraAgent's
own process) and are a known, explicitly-documented simplification of this
toy PoC, not an oversight.
"""
from __future__ import annotations

import json
import zlib
from typing import Dict, List, Optional, Tuple

import numpy as np

N_HASH_BUCKETS = 3
FEATURE_DIM = 2 + 2 * N_HASH_BUCKETS  # bias, is_origin, zone-hash, event_type-hash


def _hash_bucket(value: Optional[str], n_buckets: int = N_HASH_BUCKETS) -> List[float]:
    """Deterministic feature hashing (stable across processes/PYTHONHASHSEED,
    unlike Python's built-in `hash()`) for the small, open-ended vocabulary
    of zone names and event types across scenarios."""
    vec = [0.0] * n_buckets
    if value:
        vec[zlib.crc32(value.encode()) % n_buckets] = 1.0
    return vec


def build_context(candidate_id: str, task: Dict) -> np.ndarray:
    bias = [1.0]
    is_origin = [1.0 if task.get("origin_sensor") == candidate_id else 0.0]
    zone = _hash_bucket(task.get("zone"))
    event = _hash_bucket(task.get("event_type"))
    return np.array(bias + is_origin + zone + event, dtype=float)


class LinUCBBidder:
    """One (A, b) pair per arm; `alpha` controls the exploration bonus
    (`alpha=0` reduces to pure greedy exploitation of the current estimate,
    used in tests for determinism)."""

    def __init__(self, arms: List[str], alpha: float = 1.0,
                 dim: int = FEATURE_DIM) -> None:
        self.arms: List[str] = list(arms)
        self.alpha = alpha
        self.dim = dim
        self._A: Dict[str, np.ndarray] = {a: np.identity(dim) for a in self.arms}
        self._b: Dict[str, np.ndarray] = {a: np.zeros(dim) for a in self.arms}
        self.n_updates = 0

    def ensure_arm(self, arm: str) -> None:
        if arm not in self.arms:
            self.arms.append(arm)
            self._A[arm] = np.identity(self.dim)
            self._b[arm] = np.zeros(self.dim)

    def select(self, task: Dict,
              candidates: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[np.ndarray]]:
        candidates = candidates if candidates is not None else self.arms
        best_arm, best_score, best_ctx = None, -float("inf"), None
        for arm in candidates:
            self.ensure_arm(arm)
            x = build_context(arm, task)
            A_inv = np.linalg.inv(self._A[arm])
            theta = A_inv @ self._b[arm]
            score = float(theta @ x + self.alpha * np.sqrt(max(x @ A_inv @ x, 0.0)))
            if score > best_score:
                best_arm, best_score, best_ctx = arm, score, x
        return best_arm, best_ctx

    def update(self, arm: str, context: np.ndarray, reward: float) -> None:
        self.ensure_arm(arm)
        self._A[arm] += np.outer(context, context)
        self._b[arm] += reward * context
        self.n_updates += 1

    def to_dict(self) -> Dict:
        return {
            "arms": self.arms, "alpha": self.alpha, "dim": self.dim,
            "n_updates": self.n_updates,
            "A": {a: self._A[a].tolist() for a in self.arms},
            "b": {a: self._b[a].tolist() for a in self.arms},
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "LinUCBBidder":
        obj = cls(data["arms"], alpha=data["alpha"], dim=data["dim"])
        obj.n_updates = data.get("n_updates", 0)
        for a in obj.arms:
            if a in data.get("A", {}):
                obj._A[a] = np.array(data["A"][a])
                obj._b[a] = np.array(data["b"][a])
        return obj

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "LinUCBBidder":
        with open(path) as f:
            return cls.from_dict(json.load(f))
