"""AURA-MAS operator dashboard (Streamlit).

Run: streamlit run aura_mas/dashboard/app.py

Shows the live alert feed (Redis Streams or JSONL fallback), anonymized
evidence, agentic explanations, and lets the operator acknowledge/dismiss
alerts — every action is written to the audit log (human-in-the-loop).
"""
from __future__ import annotations

import glob
import hmac
import html
import json
import os
import time

import streamlit as st

from aura_mas.core.bus import Alert, AlertStore

st.set_page_config(page_title="AURA-MAS Operator Console", layout="wide",
                   page_icon="🛰️")

SEVERITY_COLOR = {"CRITICAL": "#d62728", "WARNING": "#ff7f0e", "INFO": "#1f77b4"}
DEFAULT_COLOR = "#7f7f7f"
EVIDENCE_ROOT = os.path.realpath(os.getenv("AURA_EVIDENCE_DIR", "data/evidence"))


@st.cache_resource
def get_store() -> AlertStore:
    return AlertStore()


def authenticated() -> bool:
    """Shared-secret gate on the console.

    The console exposes surveillance alerts and evidence imagery and lets the
    operator acknowledge/dismiss incidents (written to the audit log), so it is
    fail-closed: without `AURA_DASHBOARD_PASSWORD` it refuses to render unless
    the deployment explicitly opts out with `AURA_DASHBOARD_ALLOW_ANONYMOUS=1`.
    """
    if st.session_state.get("authenticated"):
        return True
    expected = os.getenv("AURA_DASHBOARD_PASSWORD", "")
    if not expected:
        if os.getenv("AURA_DASHBOARD_ALLOW_ANONYMOUS", "") in ("1", "true", "yes"):
            return True
        st.error("Console locked: set AURA_DASHBOARD_PASSWORD before starting "
                 "Streamlit (or AURA_DASHBOARD_ALLOW_ANONYMOUS=1 for an "
                 "isolated offline demo).")
        return False
    with st.form("login"):
        entered = st.text_input("Operator password", type="password")
        if st.form_submit_button("Sign in"):
            if hmac.compare_digest(entered, expected):
                st.session_state.authenticated = True
                return True
            st.error("Incorrect password.")
    return False


def under_evidence_root(path: str) -> bool:
    """Evidence paths arrive over the bus, so they are treated as untrusted."""
    real = os.path.realpath(path)
    return (os.path.commonpath([real, EVIDENCE_ROOT]) == EVIDENCE_ROOT
            and os.path.isfile(real))


def load_alerts(store: AlertStore) -> list[Alert]:
    alerts = store.read_alerts(200)
    if not alerts:  # fallback: aggregate all replay JSONL logs
        for path in glob.glob("data/alerts_*.jsonl"):
            with open(path) as f:
                for line in f:
                    try:
                        alerts.append(Alert.from_json(line))
                    except Exception:  # noqa: BLE001
                        pass
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
    return alerts


def main() -> None:
    if not authenticated():
        return
    store = get_store()
    st.title("AURA-MAS — Operator Console")
    st.caption("Privacy-aware hierarchical multi-agent surveillance · "
               "human-in-the-loop escalation")

    col_feed, col_detail = st.columns([1, 1.4])
    alerts = load_alerts(store)

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
        # every interpolated field originates from the bus / alert log, so it is
        # escaped before being rendered with unsafe_allow_html
        st.markdown(
            f"**{html.escape(a.event_type.replace('_',' ').title())}** — "
            f"<span style='color:{SEVERITY_COLOR.get(a.severity, DEFAULT_COLOR)}'>"
            f"{html.escape(a.severity)}</span> · confidence "
            f"**{a.confidence:.2f}** · zone **{html.escape(a.zone or 'site')}** · "
            f"sensors: `{html.escape(', '.join(a.sensors))}`",
            unsafe_allow_html=True)

        st.markdown("##### Agentic incident report")
        st.write(a.explanation or "—")

        st.markdown("##### Anonymized evidence")
        cols = st.columns(3)
        shown = 0
        for path in a.evidence:
            if path and under_evidence_root(path):
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
