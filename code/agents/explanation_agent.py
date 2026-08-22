"""ExplanationAgent: rule-guarded agentic incident summarization.

A small LangGraph-style state machine:

  collect_evidence -> describe (VLM/LLM) -> draft_report -> guardrail_check
        |                                                        |
        +----------------- fallback_template <-- (fail) ---------+

Design guarantees (thesis contribution C4):
- The agent runs strictly AFTER the PolicyAgent decision and cannot alter it.
- The report may cite ONLY evidence IDs supplied in the alert (guardrail
  rejects fabricated references).
- On any failure (API down, guardrail rejection), it degrades gracefully to
  a deterministic template.

Uses the OpenAI-compatible chat completions API (works with GPT-4o-mini,
Qwen-VL via compatible endpoints, or a local Ollama server).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger("aura.explanation")

SYSTEM_PROMPT = """You are the explanation agent of AURA-MAS, a multi-agent \
site surveillance system. You write concise, factual incident reports for a \
human security operator. STRICT RULES:
1. Use ONLY the evidence provided in the JSON payload. Never invent details.
2. Reference evidence items by their exact IDs in square brackets, e.g. [ev_ab12].
3. Do not identify or speculate about the identity of any person.
4. Do not recommend enforcement actions; only observation/verification steps.
5. Output valid JSON: {"summary": str, "reasoning": str, "cited_evidence": [ids], "recommended_action": str}."""


@dataclass
class ExplanationState:
    alert: Any
    hypothesis: Any
    evidence_ids: List[str] = field(default_factory=list)
    frame_descriptions: List[str] = field(default_factory=list)
    draft: Optional[Dict] = None
    guardrail_passed: bool = False
    final_text: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class ExplanationAgent:
    def __init__(self, model: str = "gpt-4.1-mini", use_vision: bool = False,
                 max_evidence_frames: int = 2) -> None:
        self.model = model
        self.use_vision = use_vision
        self.max_evidence_frames = max_evidence_frames
        self._client = None
        self.metrics = {"requests": 0, "guardrail_rejections": 0,
                        "fallbacks": 0, "errors": 0}

    # -------------------------------------------------------------- pipeline
    def explain(self, alert, hypothesis) -> str:
        state = ExplanationState(alert=alert, hypothesis=hypothesis)
        self._collect_evidence(state)
        try:
            self._describe(state)
            self._draft_report(state)
            self._guardrail_check(state)
        except Exception:  # noqa: BLE001
            # The template fallback is a design guarantee (C4), but an API
            # outage and a guardrail rejection are different failures and were
            # indistinguishable: both only showed up as a bumped `fallbacks`
            # count, with the traceback discarded entirely.
            self.metrics["errors"] += 1
            log.exception("explanation pipeline failed; falling back to "
                          "template for alert %s", getattr(alert, "alert_id",
                                                            "?"))
            state.guardrail_passed = False
        if not state.guardrail_passed:
            self.metrics["fallbacks"] += 1
            return self._fallback(state)
        d = state.draft
        return (f"{d['summary']}\n\nReasoning: {d['reasoning']}\n"
                f"Evidence: {', '.join(d['cited_evidence'])}\n"
                f"Recommended action: {d['recommended_action']}")

    # ---------------------------------------------------------------- nodes
    def _collect_evidence(self, state: ExplanationState) -> None:
        state.evidence_ids = [e.event_id for e in state.hypothesis.events]

    def _describe(self, state: ExplanationState) -> None:
        """Optional VLM pass over anonymized evidence keyframes."""
        if not self.use_vision:
            return
        client = self._get_client()
        for path in state.alert.evidence[: self.max_evidence_frames]:
            if not path or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "text",
                     "text": "Describe factually what is visible in this "
                             "anonymized surveillance frame in <=25 words. "
                             "Do not speculate about identities."},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]}],
                max_tokens=80,
            )
            self.metrics["requests"] += 1
            state.frame_descriptions.append(resp.choices[0].message.content)

    def _draft_report(self, state: ExplanationState) -> None:
        client = self._get_client()
        payload = {
            "alert": {"severity": state.alert.severity,
                      "event_type": state.alert.event_type,
                      "confidence": state.alert.confidence,
                      "zone": state.alert.zone,
                      "sensors": state.alert.sensors},
            "events": [{"id": e.event_id, "type": e.event_type,
                        "modality": e.modality, "confidence": e.confidence,
                        "sensor": e.sensor_id} for e in state.hypothesis.events],
            "frame_descriptions": state.frame_descriptions,
        }
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": json.dumps(payload)}],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        self.metrics["requests"] += 1
        state.draft = json.loads(resp.choices[0].message.content)

    def _guardrail_check(self, state: ExplanationState) -> None:
        """Reject drafts that cite evidence not supplied (hallucination probe)."""
        d = state.draft or {}
        required = {"summary", "reasoning", "cited_evidence", "recommended_action"}
        if not required.issubset(d):
            self.metrics["guardrail_rejections"] += 1
            return
        cited = set(d.get("cited_evidence", []))
        allowed = set(state.evidence_ids)
        # also scan free text for fabricated ev_ ids
        text_ids = set(re.findall(r"ev_[0-9a-f]{6,}",
                                  d["summary"] + " " + d["reasoning"]))
        if not cited or not cited.issubset(allowed) or not text_ids.issubset(allowed):
            self.metrics["guardrail_rejections"] += 1
            return
        state.guardrail_passed = True

    def _fallback(self, state: ExplanationState) -> str:
        a, h = state.alert, state.hypothesis
        mods = "/".join(sorted({e.modality for e in h.events}))
        return (f"[{a.severity}] {a.event_type.replace('_', ' ')} in zone "
                f"'{a.zone or 'site'}' (confidence {a.confidence:.2f}); "
                f"{len(h.events)} corroborating event(s) from "
                f"{len(a.sensors)} sensor(s) ({mods}). "
                f"Evidence: {', '.join(state.evidence_ids)}. "
                f"Recommended action: operator review of attached evidence.")

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()  # uses OPENAI_API_KEY / OPENAI_API_BASE
        return self._client
