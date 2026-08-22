"""Explicit state machine for ExplanationAgent's evidence -> report pipeline.

Replaces the previous "four sequential method calls in one broad try/except"
control flow with an inspectable, unit-testable graph. `ExplanationAgent`
still owns *what* each step does (`_collect_evidence`, `_describe`,
`_draft_report`, `_guardrail_check`); this class only tracks *when* they run
and enforces that any failure at any stage routes to `fallback`, never
`emitted`.
"""
from __future__ import annotations

from statemachine import State, StateMachine


class ExplanationFSM(StateMachine):
    collecting = State(initial=True)
    describing = State()
    drafting = State()
    checking_guardrail = State()
    emitted = State(final=True)
    fallback = State(final=True)

    collect_done = (
        collecting.to(describing, cond="use_vision")
        | collecting.to(drafting, unless="use_vision")
    )
    describe_done = describing.to(drafting)
    draft_done = drafting.to(checking_guardrail)
    guardrail_passed = checking_guardrail.to(emitted)
    guardrail_failed = checking_guardrail.to(fallback)
    fail = (
        collecting.to(fallback)
        | describing.to(fallback)
        | drafting.to(fallback)
        | checking_guardrail.to(fallback)
    )

    def __init__(self, use_vision: bool = False, **kwargs) -> None:
        self.use_vision = use_vision
        super().__init__(**kwargs)
