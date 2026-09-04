import os
import tempfile
import pytest
from aura_mas.core.db import AuraDatabase


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = AuraDatabase(db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_save_and_get_alert(temp_db):
    alert_data = {
        "alert_id": "alt_test_01",
        "timestamp": 100.0,
        "severity": "CRITICAL",
        "event_type": "intrusion",
        "contributing_types": ["intrusion", "audio_glass_break"],
        "confidence": 0.88,
        "zone": "zone_A",
        "sensors": ["cam_01", "mic_01"],
        "evidence": ["data/evidence/crop1.jpg"],
        "fused_events": ["ev_01", "ev_02"],
        "explanation": "Intrusion and glass break corroborated.",
        "status": "OPEN",
    }
    temp_db.save_alert(alert_data)
    fetched = temp_db.get_alert("alt_test_01")
    assert fetched is not None
    assert fetched["alert_id"] == "alt_test_01"
    assert fetched["severity"] == "CRITICAL"
    assert fetched["contributing_types"] == ["intrusion", "audio_glass_break"]
    assert fetched["confidence"] == 0.88
    assert fetched["status"] == "OPEN"


def test_query_alerts_filtering(temp_db):
    temp_db.save_alert({
        "alert_id": "alt_1", "timestamp": 10.0, "severity": "WARNING",
        "event_type": "loitering", "confidence": 0.6, "zone": "entry_gate"
    })
    temp_db.save_alert({
        "alert_id": "alt_2", "timestamp": 20.0, "severity": "CRITICAL",
        "event_type": "intrusion", "confidence": 0.9, "zone": "vault"
    })

    vault_alerts = temp_db.query_alerts(zone="vault")
    assert len(vault_alerts) == 1
    assert vault_alerts[0]["alert_id"] == "alt_2"

    crit_alerts = temp_db.query_alerts(severity="CRITICAL")
    assert len(crit_alerts) == 1
    assert crit_alerts[0]["alert_id"] == "alt_2"


def test_record_feedback_and_status(temp_db):
    temp_db.save_alert({
        "alert_id": "alt_fb", "timestamp": 10.0, "severity": "WARNING",
        "event_type": "loitering", "confidence": 0.6, "zone": "entry_gate",
        "status": "OPEN"
    })

    reward = temp_db.record_feedback("alt_fb", action="ACKNOWLEDGE", notes="True positive confirmed")
    assert reward == 1.0
    updated = temp_db.get_alert("alt_fb")
    assert updated["status"] == "ACKNOWLEDGED"

    reward_dismiss = temp_db.record_feedback("alt_fb", action="DISMISS")
    assert reward_dismiss == -1.0
    updated_dismiss = temp_db.get_alert("alt_fb")
    assert updated_dismiss["status"] == "DISMISSED"
