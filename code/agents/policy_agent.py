"""PolicyAgent: deterministic, auditable alert decision logic.

The PolicyAgent is the ONLY component allowed to create alerts. It applies:
1. Severity mapping per event family/type.
2. Confidence thresholds with hysteresis (per-zone cooldown to prevent
   alert storms / operator fatigue).
3. Optional coordination: gray-zone hypotheses are sent for cross-camera
   verification before deciding; verification outcome adjusts confidence.
4. Every decision (alert OR suppression) is written to the audit log.

The agentic ExplanationAgent runs strictly *after* this decision and can
never change it (rule-guarded agentic AI).
"""
from __future__ import annotations

import time
from typing import Dict, Optional

from aura_mas.agents.base import Agent
from aura_mas.core.bus import Alert, AlertStore, new_id, now_ts

SEVERITY_MAP = {
    "audio_gunshot": "CRITICAL", "audio_explosion": "CRITICAL",
    "intrusion": "CRITICAL", "anomaly": "WARNING",
    "audio_scream": "WARNING", "audio_glass_break": "WARNING",
    "abandoned_object": "WARNING", "loitering": "INFO",
    "audio_alarm": "WARNING", "audio_breaking": "WARNING",
    "audio_anomaly": "INFO",
}

ALERT_THRESHOLDS = {"CRITICAL": 0.45, "WARNING": 0.55, "INFO": 0.70}


class PolicyAgent(Agent):
    def __init__(self, agent_id: str, bus, store: AlertStore,
                 coordinator=None, explainer=None,
                 cooldown_seconds: float = 20.0) -> None:
        super().__init__(agent_id, bus)
        self.store = store
        self.coordinator = coordinator
        self.explainer = explainer
        self.cooldown_seconds = cooldown_seconds
        self._last_alert: Dict[str, float] = {}   # (zone,event_type) -> ts
        self.metrics = {"hypotheses": 0, "alerts": 0, "suppressed": 0,
                        "verified_up": 0, "verified_down": 0,
                        "explanation_failures": 0,
                        "decision_ms": []}

    # entry point wired as FusionAgent.on_hypothesis callback ---------------
    def on_hypothesis(self, hyp) -> Optional[Alert]:
        t0 = time.time()
        self.metrics["hypotheses"] += 1
        event_type = hyp.dominant_type()
        severity = SEVERITY_MAP.get(event_type, "INFO")
        confidence = hyp.confidence

        # 1. coordination: verify gray-zone hypotheses ------------------------
        if self.coordinator and self.coordinator.needs_verification(confidence):
            result = self.coordinator.request_verification(hyp)
            if result:
                if result["verified"]:
                    confidence = min(1.0, confidence + 0.15)
                    self.metrics["verified_up"] += 1
                else:
                    confidence = max(0.0, confidence - 0.20)
                    self.metrics["verified_down"] += 1

        # 2. threshold decision ------------------------------------------------
        threshold = ALERT_THRESHOLDS[severity]
        decision = confidence >= threshold

        # 3. hysteresis / cooldown ---------------------------------------------
        key = f"{hyp.zone}:{event_type}"
        if decision and now_ts() - self._last_alert.get(key, 0) < self.cooldown_seconds:
            decision = False
            reason = "cooldown"
        else:
            reason = "threshold" if not decision else "accepted"

        self.metrics["decision_ms"].append((time.time() - t0) * 1000)

        # 4. audit every decision ---------------------------------------------
        self.store.audit({
            "actor": self.agent_id, "action": "decision",
            "hypothesis_id": hyp.hypothesis_id, "event_type": event_type,
            "confidence": confidence, "severity": severity,
            "decision": "ALERT" if decision else "SUPPRESS", "reason": reason,
        })

        if not decision:
            self.metrics["suppressed"] += 1
            return None

        # 5. emit alert ----------------------------------------------------------
        self._last_alert[key] = now_ts()
        alert = Alert(
            alert_id=new_id("alt"), timestamp=now_ts(), severity=severity,
            event_type=event_type, confidence=round(confidence, 3),
            zone=hyp.zone, sensors=sorted(hyp.sensors),
            evidence=[e.evidence_path for e in hyp.events if e.evidence_path],
            fused_events=[e.event_id for e in hyp.events],
        )

        # 6. agentic explanation (downstream, non-blocking for the decision) --
        if self.explainer:
            try:
                alert.explanation = self.explainer.explain(alert, hyp)
            except Exception:  # noqa: BLE001
                self.metrics["explanation_failures"] += 1
                self.log.exception("explanation failed; using template")
                alert.explanation = self._template_explanation(alert, hyp)
        else:
            alert.explanation = self._template_explanation(alert, hyp)

        self.store.append(alert)
        self.metrics["alerts"] += 1
        self.log.warning("ALERT %s %s conf=%.2f zone=%s sensors=%s",
                         alert.severity, alert.event_type, alert.confidence,
                         alert.zone, alert.sensors)
        return alert

    @staticmethod
    def _template_explanation(alert: Alert, hyp) -> str:
        mods = "/".join(sorted({e.modality for e in hyp.events}))
        return (f"[{alert.severity}] {alert.event_type.replace('_', ' ')} "
                f"detected in zone '{alert.zone or 'site'}' with fused "
                f"confidence {alert.confidence:.2f}, corroborated by "
                f"{len(hyp.events)} event(s) from {len(alert.sensors)} "
                f"sensor(s) ({mods}). Evidence attached; awaiting operator "
                f"acknowledgment.")
