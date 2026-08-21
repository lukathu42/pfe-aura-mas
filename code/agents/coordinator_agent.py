"""CoordinatorAgent: auction-based task allocation (single-round contract-net).

When the FusionAgent produces a suspicious-but-uncertain hypothesis
(confidence in the "gray zone"), the coordinator announces a *verification
task*. CameraAgents bid with a view-utility score; the coordinator awards
the task to the best bidder and integrates the verification result back
into the hypothesis confidence before it reaches the PolicyAgent.

A rule-based scheduler (round-robin) is included as the ablation baseline.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Dict, List, Optional

from aura_mas.agents.base import Agent
from aura_mas.core.bus import (TOPIC_TASKS, TOPIC_BIDS, TOPIC_AWARDS,
                               TOPIC_VERIFICATIONS, new_id, now_ts)


class CoordinatorAgent(Agent):
    def __init__(self, agent_id: str, bus, mode: str = "auction",
                 camera_ids: Optional[List[str]] = None,
                 bid_window: float = 1.0,
                 gray_zone: tuple = (0.35, 0.75)) -> None:
        super().__init__(agent_id, bus)
        assert mode in ("auction", "roundrobin", "off")
        self.mode = mode
        self.camera_ids = camera_ids or []
        self.bid_window = bid_window
        self.gray_zone = gray_zone
        self._bids: Dict[str, List[Dict]] = {}
        self._verifications: Dict[str, Dict] = {}
        self._rr_index = 0
        self._lock = threading.Lock()
        self.metrics = {"tasks": 0, "bids": 0, "awards": 0,
                        "verifications": 0, "messages": 0,
                        "allocation_ms": []}

    def setup(self) -> None:
        self.bus.subscribe(TOPIC_BIDS, self._on_bid)
        self.bus.subscribe(TOPIC_VERIFICATIONS, self._on_verification)

    # ------------------------------------------------------------- public API
    def needs_verification(self, confidence: float) -> bool:
        lo, hi = self.gray_zone
        return self.mode != "off" and lo <= confidence < hi

    def request_verification(self, hypothesis) -> Optional[Dict]:
        """Blocking verification round; returns verification result or None."""
        task_id = new_id("task")
        task = {"task_id": task_id, "type": "verify",
                "hypothesis_id": hypothesis.hypothesis_id,
                "event_type": hypothesis.dominant_type(),
                "zone": hypothesis.zone,
                "origin_sensor": next(iter(hypothesis.sensors)),
                "timestamp": now_ts()}
        self.metrics["tasks"] += 1
        t0 = time.time()

        if self.mode == "auction":
            winner = self._run_auction(task)
        else:  # roundrobin baseline
            winner = self._round_robin()
        if winner is None:
            return None

        award = {"task_id": task_id, "winner": winner, "timestamp": now_ts()}
        self.bus.publish(TOPIC_AWARDS, json.dumps(award), qos=1)
        self.metrics["awards"] += 1
        self.metrics["messages"] += 1

        result = self._await_verification(task_id, timeout=3.0)
        self.metrics["allocation_ms"].append((time.time() - t0) * 1000)
        if result:
            self.metrics["verifications"] += 1
            self.log.info("verification by %s: verified=%s score=%.2f",
                          winner, result["verified"],
                          result["verification_score"])
        return result

    # ---------------------------------------------------------------- auction
    def _run_auction(self, task: Dict) -> Optional[str]:
        with self._lock:
            self._bids[task["task_id"]] = []
        self.bus.publish(TOPIC_TASKS, json.dumps(task), qos=1)
        self.metrics["messages"] += 1
        time.sleep(self.bid_window)                       # collect bids
        with self._lock:
            bids = self._bids.pop(task["task_id"], [])
        if not bids:
            self.log.warning("no bids for task %s", task["task_id"])
            return None
        best = max(bids, key=lambda b: b["bid"])
        self.log.info("auction %s: %d bids, winner=%s (%.2f)",
                      task["task_id"], len(bids), best["agent_id"], best["bid"])
        return best["agent_id"]

    def _round_robin(self) -> Optional[str]:
        if not self.camera_ids:
            return None
        winner = self.camera_ids[self._rr_index % len(self.camera_ids)]
        self._rr_index += 1
        return winner

    # -------------------------------------------------------------- callbacks
    def _on_bid(self, topic: str, payload: str) -> None:
        bid = json.loads(payload)
        self.metrics["bids"] += 1
        self.metrics["messages"] += 1
        with self._lock:
            if bid["task_id"] in self._bids:
                self._bids[bid["task_id"]].append(bid)

    def _on_verification(self, topic: str, payload: str) -> None:
        result = json.loads(payload)
        self.metrics["messages"] += 1
        with self._lock:
            self._verifications[result["task_id"]] = result

    def _await_verification(self, task_id: str, timeout: float) -> Optional[Dict]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if task_id in self._verifications:
                    return self._verifications.pop(task_id)
            time.sleep(0.05)
        return None
