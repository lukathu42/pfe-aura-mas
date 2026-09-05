import json

import pytest

from aura_mas.streaming.live_cameras import FrameRingBuffer, load_camera_config, redact_url


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


def test_ring_buffer_is_bounded_and_extracts_incident_window():
    buffer = FrameRingBuffer(retention_seconds=30, max_frames=4)
    for sequence, captured_at in enumerate([60.0, 75.0, 90.0, 105.0, 120.0]):
        buffer.append(sequence, captured_at, f"frame-{sequence}".encode())

    assert [frame.sequence for frame in buffer.snapshot()] == [2, 3, 4]
    assert [frame.sequence for frame in buffer.incident_clip(105.0, 105.0)] == [2, 3, 4]
