"""ExplanationAgent tests: guardrail, LLM path and deterministic fallback.

No network: `_get_client` is monkeypatched with a fake OpenAI-compatible
client that returns canned chat completions.
"""
from __future__ import annotations

import json

import pytest

from aura_mas.agents.explanation_agent import (ExplanationAgent,
                                               ExplanationState, SYSTEM_PROMPT)
from aura_mas.agents.fusion_agent import Hypothesis
from aura_mas.core.bus import Alert, Event, new_id, now_ts


def event(event_type="intrusion", modality="video", sensor="cam_01",
          conf=0.8, evidence_path="data/evidence/e.jpg") -> Event:
    return Event(event_id=new_id("ev"), sensor_id=sensor, timestamp=now_ts(),
                 event_type=event_type, confidence=conf, modality=modality,
                 zone="zone_A", track_id=1, evidence_path=evidence_path)


def hypothesis(events) -> Hypothesis:
    return Hypothesis(hypothesis_id=new_id("hyp"), family="security",
                      zone="zone_A", first_ts=events[0].timestamp,
                      last_ts=events[-1].timestamp, events=list(events),
                      confidence=0.9)


def alert(events, evidence=(), severity="CRITICAL") -> Alert:
    return Alert(alert_id=new_id("alt"), timestamp=now_ts(), severity=severity,
                 event_type="intrusion", confidence=0.91, zone="zone_A",
                 sensors=sorted({e.sensor_id for e in events}),
                 evidence=list(evidence),
                 fused_events=[e.event_id for e in events])


class FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self._responses.pop(0)
        if isinstance(content, Exception):
            raise content
        message = type("Msg", (), {"content": content})()
        choice = type("Choice", (), {"message": message})()
        return type("Resp", (), {"choices": [choice]})()


class FakeClient:
    def __init__(self, *responses):
        self.completions = FakeCompletions(responses)
        self.chat = type("Chat", (), {"completions": self.completions})()


def install(agent: ExplanationAgent, monkeypatch, *responses) -> FakeClient:
    client = FakeClient(*responses)
    monkeypatch.setattr(agent, "_get_client", lambda: client)
    return client


def draft(cited, summary="Person entered the restricted zone.",
          reasoning="Two sensors agree.") -> str:
    return json.dumps({"summary": summary, "reasoning": reasoning,
                       "cited_evidence": list(cited),
                       "recommended_action": "Dispatch operator review."})


def test_collect_evidence_takes_ids_from_the_hypothesis():
    events = [event(), event(modality="audio", sensor="mic_01")]
    state = ExplanationState(alert=alert(events), hypothesis=hypothesis(events))
    ExplanationAgent()._collect_evidence(state)
    assert state.evidence_ids == [e.event_id for e in events]


def test_grounded_draft_is_rendered_into_the_operator_report(monkeypatch):
    events = [event()]
    agent = ExplanationAgent()
    install(agent, monkeypatch, draft([events[0].event_id]))
    text = agent.explain(alert(events), hypothesis(events))
    assert "Person entered the restricted zone." in text
    assert "Reasoning: Two sensors agree." in text
    assert f"Evidence: {events[0].event_id}" in text
    assert "Recommended action: Dispatch operator review." in text
    assert agent.metrics == {"requests": 1, "guardrail_rejections": 0,
                             "fallbacks": 0}


def test_draft_request_sends_the_system_prompt_and_grounding_payload(monkeypatch):
    events = [event(), event(modality="audio", sensor="mic_01", conf=0.6)]
    agent = ExplanationAgent(model="local-model")
    client = install(agent, monkeypatch,
                     draft([e.event_id for e in events]))
    agent.explain(alert(events), hypothesis(events))
    call = client.completions.calls[0]
    assert call["model"] == "local-model"
    assert call["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert call["response_format"] == {"type": "json_object"}
    payload = json.loads(call["messages"][1]["content"])
    assert payload["alert"]["severity"] == "CRITICAL"
    assert [e["id"] for e in payload["events"]] == [e.event_id for e in events]
    assert {e["modality"] for e in payload["events"]} == {"video", "audio"}
    assert payload["frame_descriptions"] == []


def test_fabricated_citation_falls_back_and_is_counted(monkeypatch):
    events = [event()]
    agent = ExplanationAgent()
    install(agent, monkeypatch, draft(["ev_deadbeef01"]))
    text = agent.explain(alert(events), hypothesis(events))
    assert agent.metrics["guardrail_rejections"] == 1
    assert agent.metrics["fallbacks"] == 1
    assert "ev_deadbeef01" not in text
    assert events[0].event_id in text


def test_fabricated_id_hidden_in_free_text_is_also_rejected():
    events = [event()]
    agent = ExplanationAgent()
    state = ExplanationState(alert=alert(events), hypothesis=hypothesis(events))
    state.evidence_ids = [events[0].event_id]
    state.draft = json.loads(draft(
        [events[0].event_id],
        reasoning="Corroborated by ev_abc123def which does not exist."))
    agent._guardrail_check(state)
    assert state.guardrail_passed is False
    assert agent.metrics["guardrail_rejections"] == 1


def test_guardrail_requires_every_report_field():
    events = [event()]
    agent = ExplanationAgent()
    state = ExplanationState(alert=alert(events), hypothesis=hypothesis(events))
    state.evidence_ids = [events[0].event_id]
    state.draft = {"summary": "x", "cited_evidence": [events[0].event_id]}
    agent._guardrail_check(state)
    assert state.guardrail_passed is False
    assert agent.metrics["guardrail_rejections"] == 1


def test_guardrail_rejects_a_report_citing_nothing():
    events = [event()]
    agent = ExplanationAgent()
    state = ExplanationState(alert=alert(events), hypothesis=hypothesis(events))
    state.evidence_ids = [events[0].event_id]
    state.draft = json.loads(draft([]))
    agent._guardrail_check(state)
    assert state.guardrail_passed is False


def test_guardrail_accepts_a_subset_of_the_supplied_evidence():
    events = [event(), event(sensor="cam_02")]
    agent = ExplanationAgent()
    state = ExplanationState(alert=alert(events), hypothesis=hypothesis(events))
    state.evidence_ids = [e.event_id for e in events]
    state.draft = json.loads(draft([events[1].event_id]))
    agent._guardrail_check(state)
    assert state.guardrail_passed is True
    assert agent.metrics["guardrail_rejections"] == 0


def test_llm_failure_degrades_to_the_deterministic_template(monkeypatch):
    events = [event(), event(modality="audio", sensor="mic_01")]
    agent = ExplanationAgent()
    install(agent, monkeypatch, RuntimeError("endpoint down"))
    text = agent.explain(alert(events), hypothesis(events))
    assert text.startswith("[CRITICAL] intrusion in zone 'zone_A'")
    assert "(confidence 0.91)" in text
    assert "2 corroborating event(s) from 2 sensor(s) (audio/video)" in text
    assert all(e.event_id in text for e in events)
    assert agent.metrics["fallbacks"] == 1
    assert agent.metrics["guardrail_rejections"] == 0


def test_malformed_json_degrades_to_the_template(monkeypatch):
    events = [event()]
    agent = ExplanationAgent()
    install(agent, monkeypatch, "not json at all")
    text = agent.explain(alert(events), hypothesis(events))
    assert text.startswith("[CRITICAL]")
    assert agent.metrics["fallbacks"] == 1


def test_fallback_names_the_site_when_no_zone_is_known():
    events = [event()]
    agent = ExplanationAgent()
    a = alert(events)
    a.zone = None
    state = ExplanationState(alert=a, hypothesis=hypothesis(events))
    state.evidence_ids = [events[0].event_id]
    assert "zone 'site'" in agent._fallback(state)


def test_vision_is_skipped_unless_enabled(monkeypatch, tmp_path):
    frame = tmp_path / "e.jpg"
    frame.write_bytes(b"\xff\xd8jpeg")
    events = [event()]
    agent = ExplanationAgent()
    client = install(agent, monkeypatch, draft([events[0].event_id]))
    agent.explain(alert(events, evidence=[str(frame)]), hypothesis(events))
    assert len(client.completions.calls) == 1, "no describe() request"


def test_vision_pass_describes_frames_and_feeds_the_draft(monkeypatch, tmp_path):
    frames = []
    for i in range(3):
        p = tmp_path / f"e{i}.jpg"
        p.write_bytes(b"\xff\xd8jpeg")
        frames.append(str(p))
    events = [event()]
    agent = ExplanationAgent(use_vision=True, max_evidence_frames=2)
    client = install(agent, monkeypatch, "a corridor", "a blurred person",
                     draft([events[0].event_id]))
    agent.explain(alert(events, evidence=frames), hypothesis(events))

    assert len(client.completions.calls) == 3, "2 frames capped, then 1 draft"
    image = client.completions.calls[0]["messages"][0]["content"][1]
    assert image["image_url"]["url"].startswith("data:image/jpeg;base64,")
    payload = json.loads(client.completions.calls[2]["messages"][1]["content"])
    assert payload["frame_descriptions"] == ["a corridor", "a blurred person"]
    assert agent.metrics["requests"] == 3


def test_missing_evidence_files_are_skipped(monkeypatch, tmp_path):
    present = tmp_path / "there.jpg"
    present.write_bytes(b"\xff\xd8jpeg")
    events = [event()]
    agent = ExplanationAgent(use_vision=True, max_evidence_frames=3)
    client = install(agent, monkeypatch, "a corridor",
                     draft([events[0].event_id]))
    agent.explain(alert(events, evidence=["", str(tmp_path / "gone.jpg"),
                                          str(present)]),
                  hypothesis(events))
    payload = json.loads(client.completions.calls[-1]["messages"][1]["content"])
    assert payload["frame_descriptions"] == ["a corridor"]


def test_get_client_is_lazy_so_offline_guardrail_use_needs_no_sdk(monkeypatch):
    agent = ExplanationAgent()
    assert agent._client is None
    monkeypatch.setattr(agent, "_get_client", lambda: pytest.fail(
        "guardrail checks must not touch the LLM client"))
    events = [event()]
    state = ExplanationState(alert=alert(events), hypothesis=hypothesis(events))
    agent._collect_evidence(state)
    agent._guardrail_check(state)
