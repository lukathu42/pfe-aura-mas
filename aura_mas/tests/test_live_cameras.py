import json

import pytest

from aura_mas.streaming.live_cameras import load_camera_config, redact_url


def test_config_resolves_source_env_without_returning_env_name(tmp_path):
    path = tmp_path / "cameras.json"
    path.write_text(json.dumps({"schema_version": 1, "cameras": [
        {"id": "gate", "label": "Gate", "source_env": "SECRET_URL"}
    ]}))
    result = load_camera_config(path, {"SECRET_URL": "rtsp://alice:secret@cam.local/live?token=x"})
    assert result[0]["source"].startswith("rtsp://alice:secret@")
    assert "source_env" not in result[0]


def test_config_rejects_raw_sources_and_unsupported_schemes(tmp_path):
    path = tmp_path / "cameras.json"
    path.write_text(json.dumps({"schema_version": 1, "cameras": [
        {"id": "gate", "source": "rtsp://secret", "source_env": "MISSING"}
    ]}))
    with pytest.raises(ValueError):
        load_camera_config(path, {})


def test_url_redaction_removes_credentials_and_query():
    clean = redact_url("rtsps://alice:secret@cam.local:7441/live?token=abc")
    assert clean == "rtsps://cam.local:7441/live"
    assert "alice" not in clean and "secret" not in clean and "token" not in clean
