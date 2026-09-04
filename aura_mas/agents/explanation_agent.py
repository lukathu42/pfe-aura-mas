"""ExplanationAgent: rule-guarded agentic incident summarization.

An explicit state machine (`ExplanationFSM`, `explanation_fsm.py`):

  collecting -> [describing] -> drafting -> checking_guardrail -> emitted
       |              |              |              |
       +--------------+--- fail -----+--- fail ------+---> fallback

Design guarantees (thesis contribution C4):
- The agent runs strictly AFTER the PolicyAgent decision and cannot alter it.
- The report may cite ONLY evidence IDs supplied in the alert (guardrail
  rejects fabricated references) -- enforced in `_guardrail_check`, which
  runs regardless of how the draft was produced.
- On any failure (API down, malformed/unvalidatable response, guardrail
  rejection), it degrades gracefully to a deterministic template.
- Transient API errors (rate limit / timeout / connection) are retried with
  bounded backoff; a structurally invalid response is NOT retried -- it goes
  straight to the fallback template rather than re-prompting the model.

Uses the OpenAI-compatible chat completions API (works with GPT-4o-mini,
Qwen-VL via compatible endpoints, or a local Ollama server), patched through
`instructor` for Pydantic-validated structured output on the draft-report
call only.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from openai import APIConnectionError, APITimeoutError, RateLimitError
from opentelemetry import trace
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..telemetry import get_explanation_tracer
from .explanation_fsm import ExplanationFSM
from .explanation_schema import EVIDENCE_ID_PATTERN, DraftReport

SYSTEM_PROMPT = """You are the explanation agent of AURA-MAS, a multi-agent \
site surveillance system. You write concise, factual incident reports for a \
human security operator. STRICT RULES:
1. Use ONLY the evidence provided in the JSON payload. Never invent details.
2. Reference evidence items by their exact IDs in square brackets, e.g. [ev_ab12].
3. Do not identify or speculate about the identity of any person.
4. Do not recommend enforcement actions; only observation/verification steps.
5. Output valid JSON: {"summary": str, "reasoning": str, "cited_evidence": [ids], "recommended_action": str}."""

_RETRYABLE_OPENAI_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError)


@dataclass
class ExplanationState:
    alert: Any
    hypothesis: Any
    evidence_ids: List[str] = field(default_factory=list)
    frame_descriptions: List[str] = field(default_factory=list)
    draft: Optional[DraftReport] = None
    guardrail_passed: bool = False
    final_text: Optional[str] = None
    metrics: dict = field(default_factory=dict)


class ExplanationAgent:
    def __init__(self, model: Optional[str] = None, use_vision: bool = False,
                 max_evidence_frames: int = 2, request_timeout: float = 15.0,
                 max_retries: int = 1,
                 provider: str = "auto",
                 ollama_base_url: str = "http://localhost:11434/v1") -> None:
        self.provider = provider
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", ollama_base_url)
        # Default model selection:
        if model:
            self.model = model
        elif provider == "ollama" or (provider == "auto" and not os.environ.get("OPENAI_API_KEY")):
            self.model = os.environ.get("AURA_LOCAL_LLM", "qwen2.5-vl:3b")
        else:
            self.model = "gpt-4.1-mini"
        self.use_vision = use_vision
        self.max_evidence_frames = max_evidence_frames
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self._client = None
        self.log = logging.getLogger("aura.explanation")
        self._tracer = get_explanation_tracer()
        self.metrics = {"requests": 0, "guardrail_rejections": 0,
                        "fallbacks": 0}

    def _retrying(self) -> Retrying:
        """Bounded retry policy for transient OpenAI errors only. Validation
        failures from `instructor` are deliberately NOT in the retry set --
        they propagate immediately so a malformed response degrades to
        fallback rather than spending an extra round-trip re-prompting the
        model."""
        return Retrying(
            retry=retry_if_exception_type(_RETRYABLE_OPENAI_ERRORS),
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(multiplier=0.5, max=4),
            reraise=True,
        )

    # -------------------------------------------------------------- pipeline
    def explain(self, alert, hypothesis) -> str:
        state = ExplanationState(alert=alert, hypothesis=hypothesis)
        self._collect_evidence(state)
        fsm = ExplanationFSM(use_vision=self.use_vision)
        with self._tracer.start_as_current_span("explanation.explain") as span:
            span.set_attribute("aura.llm.model", self.model)
            try:
                fsm.collect_done()
                if fsm.current_state_value == "describing":
                    self._describe(state)
                    fsm.describe_done()
                self._draft_report(state)
                fsm.draft_done()
                self._guardrail_check(state)
                if state.guardrail_passed:
                    fsm.guardrail_passed()
                else:
                    fsm.guardrail_failed()
            except Exception:  # noqa: BLE001
                self.log.exception("explanation pipeline failed")
                fsm.fail()
            fallback_triggered = fsm.current_state_value == "fallback"
            span.set_attribute("aura.guardrail.passed", state.guardrail_passed)
            span.set_attribute("aura.explanation.fallback_triggered", fallback_triggered)
        if fallback_triggered:
            self.metrics["fallbacks"] += 1
            return self._fallback(state)
        d = state.draft
        return (f"{d.summary}\n\nReasoning: {d.reasoning}\n"
                f"Evidence: {', '.join(d.cited_evidence)}\n"
                f"Recommended action: {d.recommended_action}")

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
            start = time.perf_counter()
            resp = None
            for attempt in self._retrying():
                with attempt:
                    resp = client.chat.completions.create(
                        response_model=None,
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
                        timeout=self.request_timeout,
                    )
            latency_ms = (time.perf_counter() - start) * 1000
            self.metrics["requests"] += 1
            self._span_llm_attrs(prefix="describe", latency_ms=latency_ms, usage=getattr(resp, "usage", None))
            state.frame_descriptions.append(resp.choices[0].message.content)

    def _draft_report(self, state: ExplanationState) -> None:
        client = self._get_client()
        payload = {
            "alert": {
                "severity": state.alert.severity,
                "event_type": state.alert.event_type,
                "contributing_types": getattr(state.alert, "contributing_types", [state.alert.event_type]),
                "confidence": state.alert.confidence,
                "zone": state.alert.zone,
                "sensors": state.alert.sensors,
                "entity_id": getattr(state.hypothesis, "global_entity_id", None),
            },
            "events": [{"id": e.event_id, "type": e.event_type,
                        "modality": e.modality, "confidence": e.confidence,
                        "sensor": e.sensor_id} for e in state.hypothesis.events],
            "frame_descriptions": state.frame_descriptions,
        }
        start = time.perf_counter()
        draft = completion = None
        for attempt in self._retrying():
            with attempt:
                draft, completion = client.chat.completions.create_with_completion(
                    response_model=DraftReport,
                    max_retries=0,  # disable instructor's own reask-on-validation-failure loop
                    model=self.model,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT},
                              {"role": "user", "content": json.dumps(payload)}],
                    max_tokens=400,
                    timeout=self.request_timeout,
                )
        latency_ms = (time.perf_counter() - start) * 1000
        self.metrics["requests"] += 1
        self._span_llm_attrs(prefix="draft", latency_ms=latency_ms, usage=getattr(completion, "usage", None))
        state.draft = draft

    def _guardrail_check(self, state: ExplanationState) -> None:
        """Reject drafts that cite evidence not supplied (hallucination probe)."""
        d = state.draft
        if d is None:
            self.metrics["guardrail_rejections"] += 1
            return
        cited = set(d.cited_evidence)
        allowed = set(state.evidence_ids)
        # also scan free text for fabricated ev_ ids
        text_ids = set(EVIDENCE_ID_PATTERN.findall(d.summary + " " + d.reasoning))
        if not cited or not cited.issubset(allowed) or not text_ids.issubset(allowed):
            self.metrics["guardrail_rejections"] += 1
            return
        state.guardrail_passed = True

    def _fallback(self, state: ExplanationState) -> str:
        a, h = state.alert, state.hypothesis
        mods = "/".join(sorted({e.modality for e in h.events}))
        types = ", ".join(getattr(a, "contributing_types", [a.event_type]))
        entity_note = f" (Subject {h.global_entity_id})" if getattr(h, "global_entity_id", None) else ""
        return (f"[{a.severity}] {types.replace('_', ' ')}{entity_note} in zone "
                f"'{a.zone or 'site'}' (confidence {a.confidence:.2f}); "
                f"{len(h.events)} corroborating event(s) from "
                f"{len(a.sensors)} sensor(s) ({mods}). "
                f"Evidence: {', '.join(state.evidence_ids)}. "
                f"Recommended action: operator review of attached evidence.")

    def _get_client(self):
        if self._client is None:
            import instructor
            from openai import OpenAI
            if self.provider == "ollama" or (self.provider == "auto" and not os.environ.get("OPENAI_API_KEY")):
                raw_client = OpenAI(
                    base_url=self.ollama_base_url,
                    api_key="ollama",
                    timeout=self.request_timeout,
                )
            else:
                raw_client = OpenAI(timeout=self.request_timeout)
            self._client = instructor.from_openai(raw_client)
        return self._client

    def _span_llm_attrs(self, prefix: str, latency_ms: float, usage) -> None:
        span = trace.get_current_span()
        span.set_attribute(f"aura.llm.{prefix}.latency_ms", latency_ms)
        if usage is not None:
            span.set_attribute(f"aura.llm.{prefix}.prompt_tokens", usage.prompt_tokens)
            span.set_attribute(f"aura.llm.{prefix}.completion_tokens", usage.completion_tokens)
