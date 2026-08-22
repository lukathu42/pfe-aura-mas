"""Offline tests for the toy `auction-bandit` mode
(docs/ai-enhancement-research.md Section 4.2; results/auction_bandit_notes.md).

Pure numpy logic + in-process bus, no models, no video -- consistent with
the rest of aura_mas/tests (see test_pipeline.py docstring).
"""
from __future__ import annotations

import json

from aura_mas.agents.coordinator_agent import CoordinatorAgent
from aura_mas.core.bandit import LinUCBBidder, build_context
from aura_mas.core.bus import (LocalBus, TOPIC_AWARDS, TOPIC_VERIFICATIONS,
                               new_id, now_ts)


def test_linucb_prefers_arm_with_better_observed_reward():
    # alpha=0 disables the exploration bonus, so selection is deterministic
    # given the observed reward alone.
    bandit = LinUCBBidder(["cam_01", "cam_02"], alpha=0.0)
    task = {"origin_sensor": "mic_01", "zone": "zone_A", "event_type": "intrusion"}
    ctx = build_context("cam_02", task)
    bandit.update("cam_02", ctx, reward=1.0)
    winner, _ = bandit.select(task)
    assert winner == "cam_02"


def test_linucb_roundtrip_save_load(tmp_path):
    bandit = LinUCBBidder(["cam_01"], alpha=0.5)
    ctx = build_context("cam_01", {"zone": "zone_A", "event_type": "intrusion"})
    bandit.update("cam_01", ctx, reward=1.0)
    path = str(tmp_path / "bandit.json")
    bandit.save(path)
    loaded = LinUCBBidder.load(path)
    assert loaded.n_updates == 1
    assert loaded.arms == ["cam_01"]


def test_linucb_select_restricted_to_candidates():
    bandit = LinUCBBidder(["cam_01", "cam_02", "cam_03"], alpha=0.0)
    winner, _ = bandit.select({"zone": "zone_A", "event_type": "intrusion"},
                              candidates=["cam_02"])
    assert winner == "cam_02"


def test_coordinator_auction_bandit_mode_selects_and_learns():
    bus = LocalBus()
    coord = CoordinatorAgent("coord", bus, mode="auction-bandit",
                             camera_ids=["cam_01", "cam_02"])
    coord.setup()

    def verifier(topic, payload):
        award = json.loads(payload)
        bus.publish(TOPIC_VERIFICATIONS, json.dumps(
            {"task_id": award["task_id"], "agent_id": award["winner"],
             "verified": True, "verification_score": 0.8,
             "timestamp": now_ts()}))
    bus.subscribe(TOPIC_AWARDS, verifier)

    class Hyp:
        hypothesis_id = "hyp_test"
        zone = "zone_A"
        sensors = {"cam_01"}
        def dominant_type(self): return "intrusion"

    result = coord.request_verification(Hyp())
    assert result and result["verified"]
    assert coord.metrics["bandit_decisions"] == 1
    assert coord._bandit.n_updates == 1


def test_coordinator_auction_bandit_loads_existing_weights(tmp_path):
    bandit_path = str(tmp_path / "weights.json")
    seeded = LinUCBBidder(["cam_01", "cam_02"], alpha=0.0)
    ctx = build_context("cam_02", {"origin_sensor": "mic_01", "zone": "zone_A",
                                   "event_type": "intrusion"})
    seeded.update("cam_02", ctx, reward=1.0)
    seeded.save(bandit_path)

    bus = LocalBus()
    coord = CoordinatorAgent("coord", bus, mode="auction-bandit",
                             camera_ids=["cam_01", "cam_02"],
                             bandit_path=bandit_path, bandit_alpha=0.0)
    coord.setup()
    assert coord._bandit.n_updates == 1  # loaded, not re-initialized
