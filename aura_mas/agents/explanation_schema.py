"""Structured-output schema for ExplanationAgent's drafted incident report.

`DraftReport` is validated by `instructor` at parse time, so any draft that
reaches `ExplanationAgent._guardrail_check` is already structurally well-formed
(all four fields present, correctly typed). The guardrail step therefore only
needs to check the *semantic* hallucination invariant (cited evidence IDs must
be real) -- it does not need to re-check field presence.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

EVIDENCE_ID_PATTERN = re.compile(r"ev_[0-9a-f]{6,}")


class DraftReport(BaseModel):
    summary: str
    reasoning: str
    cited_evidence: list[str] = Field(default_factory=list)
    recommended_action: str
