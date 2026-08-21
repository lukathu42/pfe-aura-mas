"""Offline tests: validate the full event pipeline WITHOUT video/ML models.

These tests exercise bus, fusion, coordination, policy, guardrails, and
metrics using synthetic events, so they run in <5 s on any machine
(`python -m pytest aura_mas/tests -q`).
"""
from __future__ import annotations

import json
import time

from aura_mas.core.bus import (Alert, AlertStore, Event, LocalBus,
                               TOPIC_EVENTS, TOPIC_TASKS, TOPIC_BIDS,
                               TOPIC_AWARDS, TOPIC_VERIFICATIONS, new_id,
                               now_ts)
from aura_mas.agents.fusion_agent import FusionAgent
from aura_mas.agents.coordinator_agent import CoordinatorAgent
from aura_mas.agents.policy_agent import PolicyAgent
from aura_mas.eval.metrics import evaluate_run


def make_event(sensor="cam_01", etype="intrusion", conf=0.8, zone="zone_A",
               modality="video") -> Event:
    return Event(event_id=new_id("ev"), sensor_id=sensor, timestamp=now_ts(),
                 event_type=etype, confidence=conf, modality=modality,
                 zone=zone)


def test_local_bus_wildcards():
    bus = LocalBus()
    got = []
    bus.subscribe("site/+/detections", lambda t, p: got.append(t))
    bus.publish("site/cam_01/detections", "{}")
    bus.publish("site/events", "{}")
    assert got == ["site/cam_01/detections"]


def test_fusion_noisy_or_increases_with_corroboration():
    bus = LocalBus()
    out = []
    fusion = FusionAgent("fusion", bus, window_seconds=5.0,
                         on_hypothesis=out.append)
    fusion.setup()
    bus.publish(TOPIC_EVENTS, make_event(conf=0.6).to_json())
    single_conf = list(fusion._hypotheses.values())[0].confidence
    bus.publish(TOPIC_EVENTS, make_event(sensor="mic_01", etype="audio_glass_break",
                                         conf=0.6, modality="audio").to_json())
    fused_conf = list(fusion._hypotheses.values())[0].confidence
    assert fused_conf > single_conf, "corroboration must increase confidence"
    fusion.flush_all()
    assert len(out) == 1 and len(out[0].events) == 2


def test_auction_selects_best_bidder():
    bus = LocalBus()
    coord = CoordinatorAgent("coord", bus, mode="auction",
                             camera_ids=["cam_01", "cam_02"], bid_window=0.2)
    coord.setup()

    # two fake camera bidders
    def bidder(agent_id, utility):
        def on_task(topic, payload):
            task = json.loads(payload)
            bus.publish(TOPIC_BIDS, json.dumps(
                {"task_id": task["task_id"], "agent_id": agent_id,
                 "bid": utility, "timestamp": now_ts()}))
        bus.subscribe(TOPIC_TASKS, on_task)

    bidder("cam_01", 0.4)
    bidder("cam_02", 0.9)

    winners = []
    bus.subscribe(TOPIC_AWARDS, lambda t, p: winners.append(
        json.loads(p)["winner"]))

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
    assert winners == ["cam_02"], "auction must select the highest bid"
    assert result and result["verified"]


def test_policy_thresholds_and_cooldown(tmp_path):
    bus = LocalBus()
    store = AlertStore(redis_url=None, jsonl_path=str(tmp_path / "alerts.jsonl"))
    policy = PolicyAgent("policy", bus, store, cooldown_seconds=60)

    class Hyp:
        def __init__(self, conf, events):
            self.hypothesis_id = new_id("hyp")
            self.zone = "zone_A"
            self.confidence = conf
            self.events = events
            self.sensors = {e.sensor_id for e in events}
            self.modalities = {e.modality for e in events}
        def dominant_type(self):
            return max(self.events, key=lambda e: e.confidence).event_type

    ev = make_event(conf=0.9)
    # high-confidence intrusion -> CRITICAL alert
    a1 = policy.on_hypothesis(Hyp(0.9, [ev]))
    assert a1 is not None and a1.severity == "CRITICAL"
    # immediate repeat -> suppressed by cooldown
    a2 = policy.on_hypothesis(Hyp(0.9, [ev]))
    assert a2 is None
    # low-confidence loitering -> below INFO threshold, suppressed
    ev2 = make_event(etype="loitering", conf=0.3)
    a3 = policy.on_hypothesis(Hyp(0.3, [ev2]))
    assert a3 is None
    assert policy.metrics["alerts"] == 1
    assert policy.metrics["suppressed"] == 2


def test_metrics_evaluation():
    t0 = time.time()
    run = {
        "scenario": "test", "mode": "mas-auction", "t_start": t0,
        "wall_seconds": 60.0,
        "ground_truth": [
            {"event_type": "intrusion", "zone": "zone_A",
             "t_start": 5.0, "t_end": 15.0}],
        "alerts": [
            {"t_wall": t0 + 8.0, "event_type": "intrusion",
             "severity": "CRITICAL"},                       # TP (+3 s)
            {"t_wall": t0 + 40.0, "event_type": "audio_scream",
             "severity": "WARNING"}],                       # FP
        "agent_metrics": {"coordinator": {"messages": 10, "tasks": 1,
                                          "allocation_ms": [120.0]}},
    }
    m = evaluate_run(run)
    assert m["tp"] == 1 and m["fp"] == 1 and m["fn"] == 0
    assert m["precision"] == 0.5 and m["recall"] == 1.0
    assert m["mean_time_to_alert_s"] == 3.0
    assert m["false_alerts_per_hour"] == 60.0


def test_explanation_guardrail_rejects_fabricated_evidence():
    from aura_mas.agents.explanation_agent import (ExplanationAgent,
                                                   ExplanationState)
    agent = ExplanationAgent()
    ev = make_event()

    class Hyp:
        events = [ev]
    alert = Alert(alert_id="alt_x", timestamp=now_ts(), severity="WARNING",
                  event_type="intrusion", confidence=0.8, zone="zone_A",
                  sensors=["cam_01"], evidence=[], fused_events=[ev.event_id])
    state = ExplanationState(alert=alert, hypothesis=Hyp())
    state.evidence_ids = [ev.event_id]
    # draft citing a fabricated evidence id must be rejected
    state.draft = {"summary": "intrusion seen [ev_fabricated123]",
                   "reasoning": "because", "cited_evidence": ["ev_fabricated123"],
                   "recommended_action": "review"}
    agent._guardrail_check(state)
    assert not state.guardrail_passed
    # draft citing only real evidence passes
    state.draft = {"summary": f"intrusion [{ev.event_id}]",
                   "reasoning": "grounded", "cited_evidence": [ev.event_id],
                   "recommended_action": "review"}
    agent._guardrail_check(state)
    assert state.guardrail_passed
