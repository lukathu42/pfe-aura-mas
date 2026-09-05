---
status: accepted
---

# Make Next.js the authoritative operator console

The Next.js console will be the defense and operational interface, backed by shared APIs and durable stores. Streamlit remains an engineering diagnostic and contingency interface, not a second owner of alert status, feedback, policy, or session state.

## Considered Options

Keeping both interfaces equally authoritative would duplicate workflow behavior and preserve their current inconsistent status handling. Using Streamlit alone would reduce implementation work but would discard the more polished multi-camera and search presentation already present in the Next.js application.

## Consequences

In-memory and session-only alert overlays must be replaced by backend-owned durable transitions. The Next.js console must display Session Mode prominently. A hardware failure may trigger an operator-selected Prepared Replay, but the UI must identify the failed live component and must never relabel replay evidence as live evidence.
