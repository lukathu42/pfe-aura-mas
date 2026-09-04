# AURA-MAS Surveillance

AURA-MAS monitors configured physical areas, turns sensor observations into reviewable incidents, and keeps operator workflow separate from model feedback.

## Monitoring

**Camera Node**:
A physical camera and its nearby computer responsible for acquiring and publishing a live stream and reporting camera health.
_Avoid_: Edge AI node, when inference is not actually running there

**Physical Zone**:
A real site location that can be observed by one or more cameras and owns the operator-facing Zone Policy and Incident history.
_Avoid_: Polygon, camera zone

**Camera View Zone**:
A polygon in one camera's image that maps that view onto a Physical Zone. Similar names do not imply that two Camera View Zones observe the same place.
_Avoid_: Physical zone, area, region

**Zone Policy**:
The inherited set of enabled anomaly rules, thresholds, schedule, severity, verification requirement, and cooldown for a Monitoring Zone.
_Avoid_: Anomaly scope, zone settings

**Policy Version**:
An immutable snapshot of the Site Policy Profile and Zone Policies applied for one Monitoring Session. Incidents retain its identifier so later configuration changes cannot rewrite what the system was expected to detect.
_Avoid_: Current settings

**Live Monitoring Session**:
A bounded, attributable run that consumes ongoing camera streams and produces health records, detections, incidents, and measured latency without replaying a finite media file.
_Avoid_: Real-time mode, live replay

**Prepared Replay**:
A finite, versioned recording used to reproduce a known scenario and compare system behavior. A Prepared Replay is evidence of repeatability, not evidence of live deployment.
_Avoid_: Live demo

**Session Mode**:
The immutable declaration that a Monitoring Session is either `LIVE` or `PREPARED_REPLAY`. The mode is displayed to the operator and retained with every resulting Incident and measurement.
_Avoid_: Demo mode, automatic fallback

**Legacy Observation**:
A read-only view of an archived alert or result whose original schema lacks one or more current domain fields. Missing provenance or mappings remain unknown rather than being inferred during adaptation.
_Avoid_: Migrated incident

## Incidents

**Incident**:
A reviewable surveillance occurrence created from one or more fused sensor events and represented by an alert, evidence, context, and operator history.
_Avoid_: Anomaly, when referring to the whole operator-facing record

**Sensor Health Incident**:
A reviewable loss or degradation of sensing capability, such as a disconnected or stale camera. It is operational health evidence and is never counted as a surveillance anomaly.
_Avoid_: Anomaly alert, detection failure

**Incident Association Window**:
The bounded interval in which compatible observations of the same Physical Zone may be associated with an open Incident. Association also requires compatible event semantics; time or matching labels alone are insufficient.
_Avoid_: Fusion window, cooldown

**Incident Clip**:
The bounded video evidence retained around an Incident, including configured pre-event and post-event intervals and its provenance metadata.
_Avoid_: Recording, replay

**Context Annotation**:
An AI-generated description or searchable representation derived from incident evidence. It may aid review and retrieval but cannot create, suppress, or authorize an alert.
_Avoid_: Detection, decision

**Observed Fact**:
A detector, rule, sensor, or policy record produced by the deterministic surveillance path and retained with provenance.
_Avoid_: Generated context, ground truth

**Operator Verdict**:
The human assessment attached to an Incident, including its Incident Verdict and any notes. It is distinct from both Observed Facts and generated Context Annotations.
_Avoid_: Acknowledgement, model output

**Acknowledgement**:
An operator statement that an Incident has been seen. It is a workflow transition and says nothing about whether the detection was correct.
_Avoid_: Confirmation, positive feedback

**Incident Verdict**:
An explicit operator label with one of `UNREVIEWED`, `CONFIRMED_ANOMALY`, or `FALSE_ALARM`. It records correctness independently from workflow progress.
_Avoid_: Acknowledgement, dismissal without a reason

**Incident Workflow State**:
The operator-handling state `OPEN`, `ACKNOWLEDGED`, or `RESOLVED`. It does not indicate whether the Incident was correctly detected.
_Avoid_: Verdict, feedback label

**Resolution**:
The closure of an Incident after any necessary response or escalation has been recorded.
_Avoid_: Acknowledgement

**Response Playbook**:
A Zone Policy's operator-facing, anomaly-specific sequence of suggested actions. A Response Playbook requires operator approval and does not autonomously operate safety-critical devices.
_Avoid_: Automation, response action

**Feedback Record**:
An attributable operator verdict and note retained for later evaluation or offline calibration. It cannot modify active models, thresholds, or policies during a Monitoring Session.
_Avoid_: Online reinforcement, acknowledgement

## Evidence

**Private Staged Corpus**:
Consented home recordings retained locally for system development and defense demonstrations, with anonymized exports when needed.
_Avoid_: Public dataset

**Distributable Benchmark Corpus**:
Recorded samples whose source, license, checksum, and permitted uses are documented and allow the intended academic distribution.
_Avoid_: Downloaded clips, internet footage

## Capability

**Capability Level**:
The evidence-backed maturity attached to a feature: `OPERATIONALLY_DEMONSTRATED`, `RESEARCH_PROTOTYPE`, `EXPERIMENTAL`, or `PREPARED_REPLAY_ONLY`.
_Avoid_: Implemented, supported, production-ready

**Search Level**:
The active retrieval capability: metadata filters, deterministic lexical search, semantic text retrieval, or VLM-enriched retrieval. The operator interface states the active level explicitly.
_Avoid_: AI search, when only lexical matching is active
