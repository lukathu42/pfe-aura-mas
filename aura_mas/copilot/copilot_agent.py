"""Operator AI Copilot for AURA-MAS.

Provides an interactive natural language assistant for security operators:
- Investigating incidents by zone, time, or severity
- Querying active sensor statuses & tracking
- Explaining automated coordinator decisions & verification bids
- Generating shift summary reports
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from ..core.db import AuraDatabase

log = logging.getLogger("aura.copilot")


COPILOT_SYSTEM_PROMPT = """You are AURA-Copilot, the intelligent conversational assistant for the AURA-MAS multi-agent surveillance system.
You assist human security operators by querying site sensors, analyzing alerts, explaining auction coordination, and summarizing incidents.

You have access to the following system context:
- System Mode: Edge-first Multi-Agent System (YOLO11n + ByteTrack + YAMNet + LinUCB Auction Coordinator)
- Active Incident Families: security (intrusion, loitering, abandoned_object, wrong_direction), violence_or_hazard (anomaly, audio_scream, audio_gunshot), hazard (audio_alarm, audio_explosion, zone_occupancy)

Rules:
1. Provide concise, clear, professional tactical answers suitable for security control rooms.
2. When referencing alerts, mention their exact IDs (e.g. alt_xxxx), severity levels, and timestamps.
3. Be factual: rely strictly on the queried database evidence and system metrics.
4. Format responses cleanly with Markdown bullet points and bold highlights.
"""


class OperatorCopilot:
    """Security Control Room AI Copilot."""

    def __init__(self, db: Optional[AuraDatabase] = None,
                 model: Optional[str] = None,
                 provider: str = "auto",
                 ollama_base_url: str = "http://localhost:11434/v1") -> None:
        self.db = db or AuraDatabase()
        self.provider = provider
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", ollama_base_url)
        if model:
            self.model = model
        elif provider == "ollama" or (provider == "auto" and not os.environ.get("OPENAI_API_KEY")):
            self.model = os.environ.get("AURA_LOCAL_LLM", "qwen2.5-vl:3b")
        else:
            self.model = "gpt-4.1-mini"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            if self.provider == "ollama" or (self.provider == "auto" and not os.environ.get("OPENAI_API_KEY")):
                self._client = OpenAI(base_url=self.ollama_base_url, api_key="ollama")
            else:
                self._client = OpenAI()
        return self._client

    # ------------------------------------------------------------- Tool Actions
    def query_recent_alerts(self, limit: int = 5, zone: Optional[str] = None,
                            severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch latest alerts from database."""
        return self.db.query_alerts(limit=limit, zone=zone, severity=severity)

    def explain_alert_decision(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details and audit trail for a specific alert."""
        alert = self.db.get_alert(alert_id)
        if not alert:
            return None
        return alert

    def get_system_summary(self) -> Dict[str, Any]:
        """Aggregate site surveillance statistics."""
        alerts = self.db.query_alerts(limit=100)
        total_open = sum(1 for a in alerts if a.get("status") == "OPEN")
        total_critical = sum(1 for a in alerts if a.get("severity") == "CRITICAL")
        total_warning = sum(1 for a in alerts if a.get("severity") == "WARNING")
        return {
            "total_recent_alerts": len(alerts),
            "open_alerts": total_open,
            "critical_count": total_critical,
            "warning_count": total_warning,
            "recent_incidents": [f"[{a['severity']}] {a['event_type']} in {a.get('zone') or 'site'}" for a in alerts[:5]],
        }

    # ----------------------------------------------------------- Chat Interface
    def chat(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process operator inquiry and return intelligent response."""
        # 1. Fetch live contextual data to inject
        summary = self.get_system_summary()
        recent_alerts = self.query_recent_alerts(limit=6)

        context_payload = {
            "summary": summary,
            "recent_alerts": recent_alerts,
        }

        # 2. Try LLM response
        try:
            client = self._get_client()
            messages = [{"role": "system", "content": COPILOT_SYSTEM_PROMPT}]
            if history:
                messages.extend(history[-6:])
            
            user_prompt = (
                f"CURRENT SYSTEM STATUS:\n{json.dumps(context_payload, indent=2)}\n\n"
                f"OPERATOR QUERY: {user_message}"
            )
            messages.append({"role": "user", "content": user_prompt})

            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=450,
                timeout=12.0,
            )
            return resp.choices[0].message.content or "No response received."
        except Exception as e:
            log.warning("Copilot LLM unavailable (%s); using heuristic fallback", e)
            return self._fallback_chat(user_message, context_payload)

    def _fallback_chat(self, message: str, context: Dict[str, Any]) -> str:
        """Heuristic rule-based fallback when LLMs/Ollama are offline."""
        msg = message.lower()
        summary = context["summary"]
        recent = context["recent_alerts"]

        if "status" in msg or "summary" in msg or "health" in msg:
            return (
                f"**Site Status Overview**:\n"
                f"- **Open Incidents**: {summary['open_alerts']}\n"
                f"- **Critical Alerts**: {summary['critical_count']}\n"
                f"- **Warning Alerts**: {summary['warning_count']}\n"
                f"- **Latest Events**: {', '.join(summary['recent_incidents'][:3]) or 'None'}"
            )
        if "alert" in msg or "incident" in msg or "intrusion" in msg:
            if not recent:
                return "No alerts currently logged in the active database."
            top = recent[0]
            types = ", ".join(top.get("contributing_types", [top["event_type"]]))
            return (
                f"**Latest Alert ({top['alert_id']})**:\n"
                f"- **Type**: {types.replace('_', ' ')}\n"
                f"- **Severity**: {top['severity']} (Confidence: {top['confidence']:.2f})\n"
                f"- **Zone**: {top.get('zone') or 'site'}\n"
                f"- **Status**: {top.get('status')}\n"
                f"- **Report**: {top.get('explanation') or 'No report text available.'}"
            )
        return (
            f"**AURA Copilot (Offline Mode)**: Monitoring active site. "
            f"{summary['open_alerts']} incident(s) currently require operator review. "
            f"You can ask about site status, recent alerts, or specific zones."
        )
