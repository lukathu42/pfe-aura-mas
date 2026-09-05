---
status: accepted
---

# Use separate live and prepared-replay evidence tracks

AURA-MAS will demonstrate continuous processing with at least one physical Raspberry Pi camera while retaining versioned, licensed Prepared Replays for repeatable scenarios and evaluation. Live operation establishes deployability and measured end-to-end behavior; replays establish reproducibility. Neither evidence track will be presented as proving the claims of the other, and the project will not claim production readiness from the defense demonstration.

## Considered Options

An all-replay demonstration would remain reproducible but would not substantiate live operation. An all-live demonstration would be difficult to repeat and would weaken controlled comparison. Claiming a production-ready home-surveillance product would exceed the available reliability, security, and deployment evidence.

## Consequences

Results and UI labels must identify whether their source is a Live Monitoring Session or a Prepared Replay through an immutable Session Mode. A fallback from failed live hardware requires an explicit operator transition, retains the failure reason, and cannot relabel replay evidence as live evidence. Simultaneous multi-camera claims require simultaneous physical streams; moving one camera between rooms produces a staged corpus, not a multi-camera deployment.
