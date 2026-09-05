import calendar

import pytest

from aura_mas.operations import OperationalApplication, OperationalStore


@pytest.fixture
def store(tmp_path):
    return OperationalStore(tmp_path / "operations.db")


def monitoring_policy(*rules, zone_aware_abandoned_object=False):
    return {
        "zones": {"entry": {"enabled_rules": list(rules), "thresholds": {rule: 0.5 for rule in rules}}},
        "camera_view_zones": [
            {"camera_id": camera, "physical_zone_id": "entry", "polygon": [[0, 0], [1, 0], [1, 1]]}
            for camera in ["cam_entry_pi", "cam_verifier_usb"]
        ],
        "capabilities": {"zone_aware_abandoned_object": zone_aware_abandoned_object},
    }


def live_provenance(**extra):
    return {"frame_point": [0.75, 0.25], **extra}


def live_source_config():
    return [
        {
            "camera_id": "cam_entry_pi", "transport": "RTSP",
            "endpoint_fingerprint": "sha256:pi-endpoint", "continuous": True,
        },
        {
            "camera_id": "cam_verifier_usb", "transport": "USB",
            "endpoint_fingerprint": "sha256:usb-device", "continuous": True,
        },
    ]


def start_live(store, policy):
    return store.start_session(
        "LIVE", policy["policy_version_id"], live_sources=live_source_config(),
    )


def test_session_mode_and_policy_version_are_immutable(store):
    policy = store.create_policy_version("base-safety", monitoring_policy("person_down"))
    session = start_live(store, policy)

    assert session["mode"] == "LIVE"
    assert session["policy_version_id"] == policy["policy_version_id"]
    with pytest.raises(ValueError, match="immutable"):
        store.change_session_identity(session["session_id"], mode="PREPARED_REPLAY")


def test_compatible_observations_associate_without_merging_on_zone_alone(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion", "loitering"))
    session = start_live(store, policy)

    first = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })
    compatible = store.record_observation(session["session_id"], {
        "observation_id": "obs-2", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_verifier_usb", "capture_time": 108.0, "receive_time": 108.1,
        "sequence": 1, "confidence": 0.9, "provenance": live_provenance(),
    })
    different_semantics = store.record_observation(session["session_id"], {
        "observation_id": "obs-3", "event_type": "loitering", "physical_zone_id": "entry",
        "camera_id": "cam_verifier_usb", "capture_time": 109.0, "receive_time": 109.1,
        "sequence": 2, "confidence": 0.7, "provenance": live_provenance(),
    })

    assert compatible["incident_id"] == first["incident_id"]
    assert different_semantics["incident_id"] != first["incident_id"]


def test_acknowledgement_and_verdict_are_independent(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    incident = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })

    acknowledged = store.record_action(incident["incident_id"], "ACKNOWLEDGE", "operator")
    assert acknowledged["workflow_state"] == "ACKNOWLEDGED"
    assert acknowledged["verdict"] == "UNREVIEWED"
    assert store.list_feedback(incident["incident_id"]) == []

    confirmed = store.record_action(
        incident["incident_id"], "SET_VERDICT", "operator",
        {"verdict": "CONFIRMED_ANOMALY", "note": "verified on both views"},
    )
    assert confirmed["workflow_state"] == "ACKNOWLEDGED"
    assert confirmed["verdict"] == "CONFIRMED_ANOMALY"
    assert store.list_feedback(incident["incident_id"])[0]["verdict"] == "CONFIRMED_ANOMALY"


def test_camera_disconnect_is_a_health_incident(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    store.record_camera_health(
        session["session_id"], "cam_entry_pi", "entry", "OFFLINE", 120.0,
        reason="connection failed",
    )

    incidents = store.list_incidents(session_id=session["session_id"])
    assert incidents[0]["category"] == "SENSOR_HEALTH"
    assert incidents[0]["event_type"] == "camera_offline"
    assert incidents[0]["is_surveillance_anomaly"] is False


def test_camera_health_cannot_claim_an_unmapped_physical_zone(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    with pytest.raises(ValueError, match="not mapped"):
        store.record_camera_health(
            session["session_id"], "cam_entry_pi", "unrelated_room", "OFFLINE", 120.0,
        )


def test_search_reports_the_capability_level_used(store):
    policy = store.create_policy_version(
        "entrance", monitoring_policy("abandoned_object", zone_aware_abandoned_object=True),
    )
    session = start_live(store, policy)
    store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "abandoned_object",
        "physical_zone_id": "entry", "camera_id": "cam_entry_pi",
        "capture_time": 100.0, "receive_time": 100.1, "sequence": 1,
        "confidence": 0.8, "facts": ["bag left near entrance"],
        "provenance": live_provenance(zone_aware_evaluation=True),
    })

    result = store.search("bag entrance")
    assert result["search_level"] == "DETERMINISTIC_LEXICAL"
    assert result["results"][0]["event_type"] == "abandoned_object"


def test_operational_api_exposes_session_and_durable_workflow(store):
    application = OperationalApplication(store)
    status, policy = application.handle("POST", "/v1/policies", {
        "profile_name": "entrance", "payload": monitoring_policy("intrusion"),
    })
    assert status == 201
    status, session = application.handle("POST", "/v1/sessions", {
        "mode": "LIVE", "policy_version_id": policy["policy_version_id"],
        "live_sources": live_source_config(),
    })
    assert status == 201
    status, state = application.handle("GET", "/v1/state", None)
    assert status == 200
    assert state["active_session"]["session_id"] == session["session_id"]
    assert state["active_session"]["mode"] == "LIVE"
    assert state["search_level"] == "DETERMINISTIC_LEXICAL"


def test_policy_validation_requires_explicit_physical_zone_mapping(store):
    with pytest.raises(ValueError, match="site profile"):
        store.create_policy_version("invalid", {
            "site_profile": "Bogus", "zones": {"entry": {}},
        })

    with pytest.raises(ValueError, match="physical zone"):
        store.create_policy_version("entrance", {
            "zones": {"entry": {"profile": "Entrance"}},
            "capabilities": {"zone_aware_abandoned_object": True},
            "camera_view_zones": [{
                "camera_id": "cam_entry_pi", "physical_zone_id": "missing",
                "polygon": [[0, 0], [1, 0], [1, 1]],
            }],
        })

    with pytest.raises(ValueError, match="zone-aware"):
        store.create_policy_version("room", {
            "zones": {"room": {"enabled_rules": ["abandoned_object"]}},
        })

    policy = store.create_policy_version("entrance", {
        "zones": {"entry_overlap": {"profile": "Entrance"}},
        "capabilities": {"zone_aware_abandoned_object": True},
        "camera_view_zones": [
            {"camera_id": camera, "physical_zone_id": "entry_overlap", "polygon": [[0, 0], [1, 0], [1, 1]]}
            for camera in ["cam_entry_pi", "cam_verifier_usb"]
        ],
    })
    assert len(policy["payload"]["camera_view_zones"]) == 2
    assert "intrusion" in policy["payload"]["zones"]["entry_overlap"]["enabled_rules"]


def test_session_measurements_are_attributable_and_visible(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    store.record_measurement(session["session_id"], {
        "recorded_at": 150.0, "camera_id": "cam_entry_pi", "inference_fps": 4.8,
        "dropped_frames": 3, "cpu_percent": 62.0, "ram_percent": 41.0,
        "network_kbps": 1900.0, "alert_latency_ms": 820.0,
    })

    snapshot = store.snapshot()
    assert snapshot["measurements"][0]["session_id"] == session["session_id"]
    assert snapshot["measurements"][0]["inference_fps"] == 4.8


def test_observation_must_be_policy_qualified_and_camera_mapped(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    base = {
        "observation_id": "obs-1", "physical_zone_id": "entry", "capture_time": 100.0,
        "receive_time": 100.1, "sequence": 1, "confidence": 0.8,
        "provenance": live_provenance(),
    }
    with pytest.raises(ValueError, match="disabled"):
        store.record_observation(session["session_id"], {
            **base, "event_type": "fire_smoke", "camera_id": "cam_entry_pi",
        })
    with pytest.raises(ValueError, match="registered session source"):
        store.record_observation(session["session_id"], {
            **base, "event_type": "intrusion", "camera_id": "unrelated_cam",
        })


def test_stale_evidence_closes_and_new_observation_opens_new_incident(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    first = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })
    second = store.record_observation(session["session_id"], {
        "observation_id": "obs-2", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 111.0, "receive_time": 111.1,
        "sequence": 2, "confidence": 0.8, "provenance": live_provenance(),
    })

    assert second["incident_id"] != first["incident_id"]
    assert store.get_incident(first["incident_id"])["evidence_closed_at"] == 110.0


def test_only_one_monitoring_session_can_be_active(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    live = start_live(store, policy)
    with pytest.raises(ValueError, match="already active"):
        store.start_session(
            "PREPARED_REPLAY", policy["policy_version_id"], failure_reason="Pi offline",
            recording_id="clip-1", recording_checksum="sha256:abc",
        )

    ended = store.end_session(live["session_id"], reason="Pi offline")
    replay = store.start_session(
        "PREPARED_REPLAY", policy["policy_version_id"], failure_reason="Pi offline",
        recording_id="clip-1", recording_checksum="sha256:abc",
    )
    assert ended["ended_at"] is not None
    assert replay["failure_reason"] == "Pi offline"


def test_session_mode_enforces_source_provenance(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    with pytest.raises(ValueError, match="sources must match"):
        store.start_session("LIVE", policy["policy_version_id"])
    live = start_live(store, policy)
    sources = store.list_sources(live["session_id"])
    assert {source["source_kind"] for source in sources} == {"LIVE_STREAM"}
    assert {source["transport"] for source in sources} == {"RTSP", "USB"}
    assert all(source["endpoint_fingerprint"] for source in sources)

    store.end_session(live["session_id"], reason="operator selected replay")
    with pytest.raises(ValueError, match="recording identifier"):
        store.start_session("PREPARED_REPLAY", policy["policy_version_id"])
    replay = store.start_session(
        "PREPARED_REPLAY", policy["policy_version_id"],
        recording_id="clip-1", recording_checksum="sha256:abc",
    )
    sources = store.list_sources(replay["session_id"])
    assert {source["source_kind"] for source in sources} == {"VERSIONED_RECORDING"}
    assert {source["recording_checksum"] for source in sources} == {"sha256:abc"}


def test_policy_controls_verification_and_severity(store):
    payload = monitoring_policy("intrusion")
    payload["zones"]["entry"].update({"verification_required": True, "severity": "CRITICAL"})
    policy = store.create_policy_version("entrance", payload)
    session = start_live(store, policy)
    observation = {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    }
    with pytest.raises(ValueError, match="simultaneous evidence"):
        store.record_observation(session["session_id"], observation)

    evidence = store.record_verification_evidence(session["session_id"], {
        "camera_id": "cam_verifier_usb", "event_type": "intrusion",
        "physical_zone_id": "entry", "observed_at": 100.2, "confidence": 0.75,
        "provenance": live_provenance(),
    })
    incident = store.record_observation(session["session_id"], {
        **observation, "verification": {"evidence_ids": [evidence["evidence_id"]]},
    })
    assert incident["severity"] == "CRITICAL"


def test_evidence_closes_without_a_later_observation(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    incident = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })

    assert store.close_stale_evidence(111.0) == 1
    assert store.get_incident(incident["incident_id"])["evidence_closed_at"] == 110.0


def test_each_offline_camera_gets_its_own_health_incident(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    for camera in ["cam_entry_pi", "cam_verifier_usb"]:
        store.record_camera_health(session["session_id"], camera, "entry", "OFFLINE", 120.0)

    incidents = store.list_incidents(session_id=session["session_id"])
    assert {incident["affected_camera_id"] for incident in incidents} == {
        "cam_entry_pi", "cam_verifier_usb",
    }


def test_camera_recovery_allows_a_later_outage_incident(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    store.record_camera_health(session["session_id"], "cam_entry_pi", "entry", "OFFLINE", 100.0)
    store.record_camera_health(session["session_id"], "cam_entry_pi", "entry", "ONLINE", 105.0)
    store.record_camera_health(session["session_id"], "cam_entry_pi", "entry", "OFFLINE", 110.0)

    incidents = store.list_incidents(session_id=session["session_id"])
    assert len(incidents) == 2
    assert sum(incident["evidence_closed_at"] is None for incident in incidents) == 1


def test_degraded_camera_does_not_close_offline_incident(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = start_live(store, policy)
    store.record_camera_health(session["session_id"], "cam_entry_pi", "entry", "OFFLINE", 100.0)
    store.record_camera_health(session["session_id"], "cam_entry_pi", "entry", "DEGRADED", 105.0)

    incident = store.list_incidents(session_id=session["session_id"])[0]
    assert incident["evidence_closed_at"] is None


def test_wall_clock_closure_does_not_close_prepared_replay_evidence(store):
    policy = store.create_policy_version("entrance", monitoring_policy("intrusion"))
    session = store.start_session(
        "PREPARED_REPLAY", policy["policy_version_id"],
        recording_id="clip-1", recording_checksum="sha256:abc",
    )
    incident = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })

    assert store.close_stale_evidence(1_000_000.0) == 0
    assert store.get_incident(incident["incident_id"])["evidence_closed_at"] is None
    store.end_session(session["session_id"], reason="recording EOF")
    assert store.get_incident(incident["incident_id"])["evidence_closed_at"] == 110.0


def test_playbook_approval_is_operator_only_and_policy_owned(store):
    payload = monitoring_policy("intrusion")
    payload["zones"]["entry"]["response_playbooks"] = {
        "intrusion": ["Inspect second view"],
    }
    policy = store.create_policy_version("entrance", payload)
    session = start_live(store, policy)
    incident = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": 100.0, "receive_time": 100.1,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })
    with pytest.raises(ValueError, match="operator"):
        store.record_action(
            incident["incident_id"], "APPROVE_PLAYBOOK", "context_model",
            {"playbook_action": "Inspect second view"},
        )
    with pytest.raises(ValueError, match="Policy Version"):
        store.record_action(
            incident["incident_id"], "APPROVE_PLAYBOOK", "operator",
            {"playbook_action": "Unlock door"},
        )
    approved = store.record_action(
        incident["incident_id"], "APPROVE_PLAYBOOK", "operator",
        {"playbook_action": "Inspect second view"},
    )
    assert approved["incident_id"] == incident["incident_id"]


def test_overnight_policy_schedule_wraps_midnight(store):
    payload = monitoring_policy("intrusion")
    payload["zones"]["entry"]["schedule"] = {"start_hour_utc": 22, "end_hour_utc": 6}
    policy = store.create_policy_version("entrance", payload)
    session = start_live(store, policy)
    at_23h = calendar.timegm((2026, 1, 1, 23, 0, 0))
    incident = store.record_observation(session["session_id"], {
        "observation_id": "obs-1", "event_type": "intrusion", "physical_zone_id": "entry",
        "camera_id": "cam_entry_pi", "capture_time": at_23h, "receive_time": at_23h,
        "sequence": 1, "confidence": 0.8, "provenance": live_provenance(),
    })
    assert incident["event_type"] == "intrusion"

    at_noon = calendar.timegm((2026, 1, 2, 12, 0, 0))
    with pytest.raises(ValueError, match="outside"):
        store.record_observation(session["session_id"], {
            "observation_id": "obs-2", "event_type": "intrusion", "physical_zone_id": "entry",
            "camera_id": "cam_entry_pi", "capture_time": at_noon, "receive_time": at_noon,
            "sequence": 2, "confidence": 0.8, "provenance": live_provenance(),
        })
