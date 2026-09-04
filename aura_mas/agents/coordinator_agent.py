"""CoordinatorAgent: auction-based task allocation (single-round contract-net).

When the FusionAgent produces a suspicious-but-uncertain hypothesis
(confidence in the "gray zone"), the coordinator announces a *verification
task*. CameraAgents bid with a view-utility score; the coordinator awards
the task to the best bidder and integrates the verification result back
into the hypothesis confidence before it reaches the PolicyAgent.

A rule-based scheduler (round-robin) is included as the ablation baseline.

`auction-bandit` is a fourth, additive mode: a toy contextual-bandit
(LinUCB, `aura_mas.core.bandit`) picks the winner centrally instead of
collecting camera bids, and learns from the verification outcome. This is a
research-pass illustrative PoC, not a fifth thesis ablation baseline -- see
results/auction_bandit_notes.md and docs/ai-enhancement-research.md Section
4.2 before citing anything from it as a performance result.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Dict, List, Optional

from aura_mas.agents.base import Agent
from aura_mas.core.bandit import LinUCBBidder
from aura_mas.core.bus import (TOPIC_TASKS, TOPIC_BIDS, TOPIC_AWARDS,
                               TOPIC_VERIFICATIONS, new_id, now_ts)


class CoordinatorAgent(Agent):
    def __init__(self, agent_id: str, bus, mode: str = "auction",
                 camera_ids: Optional[List[str]] = None,
                 bid_window: float = 1.0,
                 gray_zone: tuple = (0.35, 0.75),
                 bandit_path: Optional[str] = None,
                 bandit_alpha: float = 1.0,
                 fov_overlap: Optional[Dict[str, Dict[str, float]]] = None) -> None:
        super().__init__(agent_id, bus)
        assert mode in ("auction", "roundrobin", "off", "auction-bandit")
        self.mode = mode
        self.camera_ids = camera_ids or []
        self.bid_window = bid_window
        self.gray_zone = gray_zone
        # {zone_name: {camera_id: overlap}}; consumed by CameraAgent._view_score,
        # which falls back to 0.5 for any camera absent from the announced map.
        self.fov_overlap = fov_overlap or {}
        self._bids: Dict[str, List[Dict]] = {}
        self._verifications: Dict[str, Dict] = {}
        self._rr_index = 0
        self._lock = threading.Lock()
        self.metrics = {"tasks": 0, "bids": 0, "awards": 0,
                        "verifications": 0, "messages": 0,
                        "allocation_ms": [], "bandit_decisions": 0,
                        "feedback_updates": 0}
        self._bandit: Optional[LinUCBBidder] = None
        self._task_history: Dict[str, Dict[str, Any]] = {}  # task_id -> {winner, ctx, hypothesis_id}
        self._hyp_to_task: Dict[str, str] = {}  # hypothesis_id -> task_id
        if self.mode == "auction-bandit":
            import os
            if bandit_path and os.path.exists(bandit_path):
                self._bandit = LinUCBBidder.load(bandit_path)
            else:
                self._bandit = LinUCBBidder(self.camera_ids, alpha=bandit_alpha)
            for cam in self.camera_ids:
                self._bandit.ensure_arm(cam)

    def setup(self) -> None:
        self.bus.subscribe(TOPIC_BIDS, self._on_bid)
        self.bus.subscribe(TOPIC_VERIFICATIONS, self._on_verification)
        self.bus.subscribe("site/feedback", self._on_feedback)

    # ------------------------------------------------------------- public API
    def needs_verification(self, confidence: float) -> bool:
        lo, hi = self.gray_zone
        # Self-verification is not independent evidence and can suppress a
        # valid single-camera event merely because a later frame changed.
        return self.mode != "off" and len(self.camera_ids) > 1 and lo <= confidence < hi

    def request_verification(self, hypothesis) -> Optional[Dict]:
        """Blocking verification round; returns verification result or None."""
        task_id = new_id("task")
        task = {"task_id": task_id, "type": "verify",
                "hypothesis_id": hypothesis.hypothesis_id,
                "event_type": hypothesis.dominant_type(),
                "zone": hypothesis.zone,
                "origin_sensor": next(iter(hypothesis.sensors)),
                "scene_time_seconds": getattr(hypothesis, "scene_time_seconds", None),
                "fov_overlap": self.fov_overlap.get(hypothesis.zone or "site", {}),
                "timestamp": now_ts()}
        self.metrics["tasks"] += 1
        t0 = time.time()

        bandit_ctx = None
        if self.mode == "auction":
            winner = self._run_auction(task)
        elif self.mode == "auction-bandit":
            winner, bandit_ctx = self._run_bandit_auction(task)
        else:  # roundrobin baseline
            winner = self._round_robin()
        if winner is None:
            return None

        award = {"task_id": task_id, "winner": winner, "timestamp": now_ts()}
        self._task_history[task_id] = {
            "winner": winner,
            "ctx": bandit_ctx,
            "hypothesis_id": hypothesis.hypothesis_id,
            "timestamp": now_ts(),
        }
        self._hyp_to_task[hypothesis.hypothesis_id] = task_id
        self.bus.publish(TOPIC_AWARDS, json.dumps(award), qos=1)
        self.metrics["awards"] += 1
        self.metrics["messages"] += 1

        result = self._await_verification(task_id, timeout=3.0)
        self.metrics["allocation_ms"].append((time.time() - t0) * 1000)
        if self.mode == "auction-bandit" and self._bandit is not None and bandit_ctx is not None:
            # Reward proxy: did the awarded camera confirm the event on
            # re-check? No external ground truth is available inside the
            # coordinator, so this in-process verification signal is the
            # default reward source. Operator feedback will further refine this.
            reward = 1.0 if (result and result.get("verified")) else 0.0
            self._bandit.update(winner, bandit_ctx, reward)
        if result:
            self.metrics["verifications"] += 1
            self.log.info("verification by %s: verified=%s score=%.2f",
                          winner, result["verified"],
                          result["verification_score"])
        return result

    def _on_feedback(self, topic: str, payload: str) -> None:
        """Reinforcement Learning from Operator Feedback (RLOF)."""
        try:
            data = json.loads(payload)
            action = data.get("action", "").upper()
            reward = float(data.get("reward", 1.0 if action == "ACKNOWLEDGE" else -1.0))
            task_id = data.get("task_id")
            if not task_id and "hypothesis_id" in data:
                task_id = self._hyp_to_task.get(data["hypothesis_id"])
            if task_id and task_id in self._task_history:
                entry = self._task_history[task_id]
                winner, ctx = entry["winner"], entry["ctx"]
                if self.mode == "auction-bandit" and self._bandit is not None and ctx is not None:
                    self._bandit.update(winner, ctx, reward)
                    self.metrics["feedback_updates"] += 1
                    self.log.info("RLOF update for camera %s with reward %.2f", winner, reward)
        except Exception:  # noqa: BLE001
            self.log.exception("Error processing operator feedback in coordinator")

    def save_bandit(self, path: str) -> None:
        if self._bandit is not None:
            self._bandit.save(path)

    # ---------------------------------------------------------------- auction
    def _run_bandit_auction(self, task: Dict):
        """Coordinator-side LinUCB selection: unlike `_run_auction`, no bid
        messages are exchanged over the bus -- the coordinator already has
        every context feature the bandit needs (origin_sensor, zone,
        event_type) and picks directly, mirroring the no-broadcast pattern
        `_round_robin` already uses."""
        if not self.camera_ids or self._bandit is None:
            return None, None
        winner, ctx = self._bandit.select(task, candidates=self.camera_ids)
        self.metrics["bandit_decisions"] += 1
        self.log.info("bandit auction %s: winner=%s", task["task_id"], winner)
        return winner, ctx

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
