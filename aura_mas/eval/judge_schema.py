"""Structured-output schema for the LLM-as-judge explanation-quality pilot
(docs/ai-enhancement-research.md Section 4.1; results/explanation_judge_notes.md).

Mirrors the pattern in aura_mas/agents/explanation_schema.py: validated by
`instructor` at parse time so `llm_judge.py` never has to hand-parse a raw
JSON string. Each axis is scored 1-5; `passed` is the judge's own binary
rollup (kept separate from a hardcoded score threshold so the judge can
weigh axes contextually, e.g. a severity-calibration miss on a CRITICAL
alert matters more than one on an INFO alert).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    grounding: int = Field(ge=1, le=5,
        description="Does every claim in the explanation trace to a field "
                    "actually present in the alert/events payload? 5 = fully "
                    "grounded, 1 = contains claims with no basis in the payload.")
    severity_calibration: int = Field(ge=1, le=5,
        description="Does the language match the alert's actual severity and "
                    "confidence (e.g. not describing a low-confidence gray-zone "
                    "alert with 'confirmed'/'certain' language)? 5 = well "
                    "calibrated, 1 = badly mismatched.")
    conciseness: int = Field(ge=1, le=5,
        description="Is the explanation free of redundant padding/restated "
                    "content that adds no information (verbosity-bias check)? "
                    "5 = concise, 1 = padded/repetitive.")
    actionability: int = Field(ge=1, le=5,
        description="Is the recommended action appropriate and non-speculative "
                    "(observation/verification only, no identification or "
                    "enforcement recommendation)? 5 = appropriate, 1 = not.")
    rationale: str = Field(description="1-3 sentence justification citing "
                           "specific text from the explanation, not a generic "
                           "restatement of the scores.")
    passed: bool = Field(description="Overall pass/fail judgment: would this "
                         "explanation be acceptable to hand to a human "
                         "security operator as-is?")
