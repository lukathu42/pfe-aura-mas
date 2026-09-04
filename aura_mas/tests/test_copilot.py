import os
import tempfile
import pytest
from aura_mas.copilot.copilot_agent import OperatorCopilot
from aura_mas.core.db import AuraDatabase


@pytest.fixture
def copilot_with_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = AuraDatabase(db_path)
    # Seed test alert
    db.save_alert({
        "alert_id": "alt_test_copilot",
        "timestamp": 1000.0,
        "severity": "CRITICAL",
        "event_type": "intrusion",
        "contributing_types": ["intrusion", "audio_glass_break"],
        "confidence": 0.92,
        "zone": "vault_room",
        "sensors": ["cam_01", "mic_01"],
        "evidence": ["data/evidence/crop.jpg"],
        "fused_events": ["ev_1"],
        "explanation": "Critical security breach in vault room.",
        "status": "OPEN",
    })
    copilot = OperatorCopilot(db=db)
    yield copilot, db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_copilot_summary_and_queries(copilot_with_db):
    copilot, db = copilot_with_db
    summary = copilot.get_system_summary()
    assert summary["open_alerts"] == 1
    assert summary["critical_count"] == 1

    alerts = copilot.query_recent_alerts(limit=5)
    assert len(alerts) == 1
    assert alerts[0]["alert_id"] == "alt_test_copilot"


def test_copilot_fallback_chat(copilot_with_db):
    copilot, db = copilot_with_db
    # Test status query in offline fallback
    reply_status = copilot._fallback_chat("Give me a site status summary", {
        "summary": copilot.get_system_summary(),
        "recent_alerts": copilot.query_recent_alerts(limit=5),
    })
    assert "Site Status Overview" in reply_status
    assert "Critical Alerts" in reply_status

    # Test alert detail query in offline fallback
    reply_alert = copilot._fallback_chat("What is the latest alert?", {
        "summary": copilot.get_system_summary(),
        "recent_alerts": copilot.query_recent_alerts(limit=5),
    })
    assert "alt_test_copilot" in reply_alert
    assert "vault_room" in reply_alert
