"""AURA-MAS operator dashboard (Streamlit).

Run: streamlit run aura_mas/dashboard/app.py

Shows the live alert feed (Redis Streams or JSONL fallback), anonymized
evidence, agentic explanations, and lets the operator acknowledge/dismiss
alerts — every action is written to the audit log (human-in-the-loop).
"""
from __future__ import annotations

import glob
import json
import logging
import os
import time

import streamlit as st

from aura_mas.core.bus import Alert, AlertStore

st.set_page_config(page_title="AURA-MAS Operator Console", layout="wide",
                   page_icon="🛰️")

SEVERITY_COLOR = {"CRITICAL": "#d62728", "WARNING": "#ff7f0e", "INFO": "#1f77b4"}

log = logging.getLogger("aura.dashboard")


@st.cache_resource
def get_store() -> AlertStore:
    return AlertStore(redis_url=os.getenv("AURA_REDIS_URL",
                                          "redis://localhost:6379"))


def load_alerts(store: AlertStore) -> tuple[list[Alert], list[str]]:
    """Returns (alerts, problems); an operator console must not hide data loss."""
    alerts = store.read_alerts(200)
    problems: list[str] = []
    if store.read_skipped:
        problems.append(f"{store.read_skipped} unreadable alert record(s) in "
                        "the alert store were skipped")
    if not alerts:  # fallback: aggregate all replay JSONL logs
        for path in glob.glob("data/alerts_*.jsonl"):
            skipped = 0
            try:
                with open(path) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            alerts.append(Alert.from_json(line))
                        except Exception:  # noqa: BLE001
                            skipped += 1
                            log.exception("unparsable alert line in %s", path)
            except OSError as exc:
                log.exception("cannot read %s", path)
                problems.append(f"{path}: {exc.strerror or exc}")
                continue
            if skipped:
                problems.append(f"{path}: {skipped} unparsable record(s) "
                                "skipped")
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
    return alerts, problems


def main() -> None:
    store = get_store()
    st.title("AURA-MAS — Operator Console")
    st.caption("Privacy-aware hierarchical multi-agent surveillance · "
               "human-in-the-loop escalation")

    col_feed, col_detail = st.columns([1, 1.4])
    alerts, problems = load_alerts(store)
    for problem in problems:
        st.warning(f"Alert feed is incomplete — {problem}", icon="⚠️")

    if "ack" not in st.session_state:
        st.session_state.ack = {}

    with col_feed:
        st.subheader(f"Alert feed ({len(alerts)})")
        sev_filter = st.multiselect("Severity",
                                    ["CRITICAL", "WARNING", "INFO"],
                                    default=["CRITICAL", "WARNING", "INFO"])
        selected = None
        for a in alerts:
            if a.severity not in sev_filter:
                continue
            status = st.session_state.ack.get(a.alert_id, a.status)
            color = SEVERITY_COLOR.get(a.severity, "#7f7f7f")
            label = (f"{time.strftime('%H:%M:%S', time.localtime(a.timestamp))} "
                     f"· {a.severity} · {a.event_type} · zone={a.zone or 'site'}"
                     f" · {status}")
            if st.button(label, key=a.alert_id, use_container_width=True):
                st.session_state.selected = a.alert_id
        selected_id = st.session_state.get("selected")
        selected = next((a for a in alerts if a.alert_id == selected_id), None)

    with col_detail:
        st.subheader("Incident detail")
        if selected is None:
            st.info("Select an alert from the feed.")
            return
        a = selected
        st.markdown(
            f"**{a.event_type.replace('_',' ').title()}** — "
            f"<span style='color:{SEVERITY_COLOR[a.severity]}'>"
            f"{a.severity}</span> · confidence **{a.confidence:.2f}** · "
            f"zone **{a.zone or 'site'}** · sensors: `{', '.join(a.sensors)}`",
            unsafe_allow_html=True)

        st.markdown("##### Agentic incident report")
        st.write(a.explanation or "—")

        st.markdown("##### Anonymized evidence")
        cols = st.columns(3)
        shown = 0
        for path in a.evidence:
            if path and os.path.exists(path):
                cols[shown % 3].image(path, use_container_width=True)
                shown += 1
        if not shown:
            st.caption("no visual evidence attached (audio-only incident)")

        c1, c2 = st.columns(2)
        if c1.button("Acknowledge", type="primary"):
            st.session_state.ack[a.alert_id] = "ACKNOWLEDGED"
            store.audit({"actor": "operator", "action": "acknowledge",
                         "alert_id": a.alert_id})
            st.rerun()
        if c2.button("Dismiss (false alarm)"):
            st.session_state.ack[a.alert_id] = "DISMISSED"
            store.audit({"actor": "operator", "action": "dismiss",
                         "alert_id": a.alert_id})
            st.rerun()


main()
