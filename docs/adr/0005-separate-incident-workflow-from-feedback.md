---
status: accepted
---

# Separate Incident workflow from correctness feedback

An Incident has an independent workflow state (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`) and verdict (`UNREVIEWED`, `CONFIRMED_ANOMALY`, `FALSE_ALARM`). Notes, escalation, evidence export, and Response Playbook approvals are immutable operator actions. Acknowledgement never produces a learning reward, and Feedback Records cannot change models, thresholds, auction behavior, or policy during a Live Monitoring Session.

## Considered Options

The existing combined acknowledge/dismiss status is simpler but conflates “seen,” “correct,” and “closed.” Immediate online updates make an attractive demonstration but cannot be defended from sparse, unreviewed clicks and can change system behavior during the measured run.

## Consequences

Frontend overlays and session state must be replaced by durable backend commands and an action history. Any calibration or learned update occurs offline, receives a version, and must be evaluated on recordings excluded from its calibration data before activation. Response Playbooks are deterministic policy data; generated Context Annotations cannot add or execute actions.
