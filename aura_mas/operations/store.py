"""WAL persistence keeps every client on one recoverable operational history."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

SESSION_MODES = {"LIVE", "PREPARED_REPLAY"}
WORKFLOW_STATES = {"OPEN", "ACKNOWLEDGED", "RESOLVED"}
VERDICTS = {"UNREVIEWED", "CONFIRMED_ANOMALY", "FALSE_ALARM"}
HEALTH_STATES = {"CONNECTING", "ONLINE", "DEGRADED", "OFFLINE"}
ASSOCIATION_WINDOW_SECONDS = 10.0
ACCEPTED_PROFILES = {
    "Base safety", "Entrance", "Corridor", "Room", "Normal observation",
}
PROFILE_RULES = {
    "Base safety": ["person_down", "rapid_movement"],
    "Entrance": ["person_down", "rapid_movement", "intrusion", "loitering", "abandoned_object"],
    "Corridor": ["person_down", "rapid_movement", "wrong_direction", "loitering"],
    "Room": ["person_down", "rapid_movement", "occupancy_violation", "loitering", "abandoned_object"],
    "Normal observation": [],
}


class IncidentAction(str, Enum):
    ACKNOWLEDGE = "ACKNOWLEDGE"
    RESOLVE = "RESOLVE"
    SET_VERDICT = "SET_VERDICT"
    ADD_NOTE = "ADD_NOTE"
    APPROVE_PLAYBOOK = "APPROVE_PLAYBOOK"
    ESCALATE = "ESCALATE"
    EXPORT_EVIDENCE = "EXPORT_EVIDENCE"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _identifier(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class OperationalStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS policy_versions (
                    policy_version_id TEXT PRIMARY KEY,
                    profile_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    checksum TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS monitoring_sessions (
                    session_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL CHECK(mode IN ('LIVE', 'PREPARED_REPLAY')),
                    policy_version_id TEXT NOT NULL REFERENCES policy_versions(policy_version_id),
                    failure_reason TEXT,
                    started_at REAL NOT NULL,
                    ended_at REAL,
                    ended_reason TEXT
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES monitoring_sessions(session_id),
                    policy_version_id TEXT NOT NULL REFERENCES policy_versions(policy_version_id),
                    category TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    physical_zone_id TEXT,
                    affected_camera_id TEXT,
                    workflow_state TEXT NOT NULL DEFAULT 'OPEN',
                    verdict TEXT NOT NULL DEFAULT 'UNREVIEWED',
                    severity TEXT NOT NULL,
                    is_surveillance_anomaly INTEGER NOT NULL,
                    confidence REAL,
                    first_event_at REAL NOT NULL,
                    last_evidence_at REAL NOT NULL,
                    evidence_closed_at REAL,
                    facts TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    camera_id TEXT,
                    event_type TEXT NOT NULL,
                    physical_zone_id TEXT,
                    capture_time REAL,
                    receive_time REAL NOT NULL,
                    sequence INTEGER NOT NULL,
                    clock_offset REAL,
                    processing_started_at REAL,
                    processing_finished_at REAL,
                    alert_emitted_at REAL,
                    confidence REAL,
                    facts TEXT NOT NULL DEFAULT '[]',
                    provenance TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS session_sources (
                    source_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES monitoring_sessions(session_id),
                    camera_id TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    transport TEXT,
                    endpoint_fingerprint TEXT,
                    continuous INTEGER NOT NULL DEFAULT 0,
                    recording_id TEXT,
                    recording_checksum TEXT,
                    registered_at REAL NOT NULL,
                    UNIQUE(session_id, camera_id)
                );
                CREATE TABLE IF NOT EXISTS verification_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES monitoring_sessions(session_id),
                    camera_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    physical_zone_id TEXT NOT NULL,
                    observed_at REAL NOT NULL,
                    confidence REAL NOT NULL,
                    provenance TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incident_actions (
                    action_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback_records (
                    feedback_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    verdict TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    note TEXT,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS camera_health (
                    health_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES monitoring_sessions(session_id),
                    camera_id TEXT NOT NULL,
                    physical_zone_id TEXT,
                    state TEXT NOT NULL,
                    reason TEXT,
                    recorded_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_measurements (
                    measurement_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES monitoring_sessions(session_id),
                    camera_id TEXT,
                    recorded_at REAL NOT NULL,
                    inference_fps REAL,
                    dropped_frames INTEGER,
                    stale_frames INTEGER,
                    cpu_percent REAL,
                    ram_percent REAL,
                    network_kbps REAL,
                    camera_uptime_seconds REAL,
                    reconnects INTEGER,
                    alert_latency_ms REAL
                );
                CREATE INDEX IF NOT EXISTS idx_incident_association
                    ON incidents(session_id, physical_zone_id, event_type, last_evidence_at);
                CREATE INDEX IF NOT EXISTS idx_incident_session ON incidents(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_observation_incident ON observations(incident_id);
            """)
            session_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(monitoring_sessions)")
            }
            if "ended_reason" not in session_columns:
                connection.execute("ALTER TABLE monitoring_sessions ADD COLUMN ended_reason TEXT")
            incident_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(incidents)")
            }
            if "affected_camera_id" not in incident_columns:
                connection.execute("ALTER TABLE incidents ADD COLUMN affected_camera_id TEXT")
                if "subject_id" in incident_columns:
                    connection.execute(
                        "UPDATE incidents SET affected_camera_id = subject_id WHERE subject_id IS NOT NULL",
                    )
            source_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(session_sources)")
            }
            for column, declaration in {
                "transport": "TEXT", "endpoint_fingerprint": "TEXT",
                "continuous": "INTEGER NOT NULL DEFAULT 0",
            }.items():
                if column not in source_columns:
                    connection.execute(f"ALTER TABLE session_sources ADD COLUMN {column} {declaration}")

    def create_policy_version(self, profile_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not profile_name.strip() or not isinstance(payload.get("zones"), dict):
            raise ValueError("policy requires a profile name and zones object")
        normalized = json.loads(json.dumps(payload))
        site_profile = normalized.get("site_profile")
        for zone in normalized["zones"].values():
            inherited_profile = zone.get("profile") or site_profile
            if inherited_profile and "enabled_rules" not in zone:
                zone["enabled_rules"] = list(PROFILE_RULES.get(inherited_profile, []))
        self._validate_policy(normalized)
        serialized = _canonical_json(normalized)
        version_material = _canonical_json({"profile_name": profile_name, "payload": normalized})
        checksum = hashlib.sha256(version_material.encode()).hexdigest()
        with self._lock, self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM policy_versions WHERE checksum = ?", (checksum,),
            ).fetchone()
            if existing:
                return self._policy(existing)
            policy_id = f"policy_{checksum[:16]}"
            created_at = time.time()
            connection.execute(
                "INSERT INTO policy_versions VALUES (?, ?, ?, ?, ?)",
                (policy_id, profile_name, serialized, checksum, created_at),
            )
            return {
                "policy_version_id": policy_id,
                "profile_name": profile_name,
                "payload": normalized,
                "checksum": checksum,
                "created_at": created_at,
            }

    @staticmethod
    def _validate_policy(payload: Mapping[str, Any]) -> None:
        zones = payload["zones"]
        site_profile = payload.get("site_profile")
        if site_profile is not None and site_profile not in ACCEPTED_PROFILES:
            raise ValueError(f"unsupported site profile: {site_profile}")
        for zone_id, zone in zones.items():
            if not isinstance(zone_id, str) or not zone_id or not isinstance(zone, Mapping):
                raise ValueError("each physical zone requires an identifier and configuration")
            profile = zone.get("profile")
            if profile is not None and profile not in ACCEPTED_PROFILES:
                raise ValueError(f"unsupported zone profile: {profile}")
            if profile == "Normal observation" and zone.get("enabled_rules"):
                raise ValueError("Normal observation cannot enable anomaly rules")
            if zone.get("severity") not in {None, "CRITICAL", "WARNING", "INFO"}:
                raise ValueError("zone severity must be CRITICAL, WARNING, or INFO")
            schedule = zone.get("schedule")
            if schedule:
                try:
                    start_hour = int(schedule["start_hour_utc"])
                    end_hour = int(schedule["end_hour_utc"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError("schedule requires integer UTC start and end hours") from error
                if not 0 <= start_hour <= 23 or not 0 <= end_hour <= 24:
                    raise ValueError("schedule UTC hours are out of range")
            if (
                "abandoned_object" in (zone.get("enabled_rules") or [])
                and not (payload.get("capabilities") or {}).get("zone_aware_abandoned_object")
            ):
                raise ValueError("abandoned_object requires zone-aware evaluation capability")
        views = payload.get("camera_view_zones", [])
        if not isinstance(views, list):
            raise ValueError("camera_view_zones must be a list")
        for view in views:
            if not isinstance(view, Mapping) or view.get("physical_zone_id") not in zones:
                raise ValueError("camera view must map to an existing physical zone")
            polygon = view.get("polygon")
            if not isinstance(polygon, list) or len(polygon) < 3:
                raise ValueError("camera view polygon requires at least three points")

    def start_session(
        self, mode: str, policy_version_id: str, *, failure_reason: Optional[str] = None,
        recording_id: Optional[str] = None, recording_checksum: Optional[str] = None,
        live_sources: Optional[list[Mapping[str, Any]]] = None,
    ) -> dict[str, Any]:
        if mode not in SESSION_MODES:
            raise ValueError(f"mode must be one of {sorted(SESSION_MODES)}")
        if mode == "PREPARED_REPLAY" and failure_reason is not None and not failure_reason.strip():
            raise ValueError("failure reason cannot be blank")
        if mode == "PREPARED_REPLAY" and (not recording_id or not recording_checksum):
            raise ValueError("Prepared Replay requires a recording identifier and checksum")
        session_id = _identifier("session")
        started_at = time.time()
        with self._lock, self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM monitoring_sessions WHERE ended_at IS NULL LIMIT 1",
            ).fetchone():
                raise ValueError("a monitoring session is already active")
            policy_row = connection.execute(
                "SELECT payload FROM policy_versions WHERE policy_version_id = ?", (policy_version_id,),
            ).fetchone()
            if not policy_row:
                raise ValueError("unknown policy version")
            connection.execute(
                """INSERT INTO monitoring_sessions (
                    session_id, mode, policy_version_id, failure_reason, started_at, ended_at, ended_reason
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL)""",
                (session_id, mode, policy_version_id, failure_reason, started_at),
            )
            source_kind = "LIVE_STREAM" if mode == "LIVE" else "VERSIONED_RECORDING"
            camera_ids = {
                view["camera_id"] for view in json.loads(policy_row["payload"]).get("camera_view_zones", [])
            }
            sources_by_camera = {
                source.get("camera_id"): source for source in (live_sources or [])
            }
            if mode == "LIVE":
                if len(camera_ids) < 2:
                    raise ValueError("LIVE session requires at least two configured physical camera views")
                if set(sources_by_camera) != camera_ids:
                    raise ValueError("LIVE session sources must match the Policy Version camera mappings")
                for source in sources_by_camera.values():
                    if (
                        source.get("transport") not in {"RTSP", "USB", "HTTP_MJPEG"}
                        or not source.get("endpoint_fingerprint")
                        or source.get("continuous") is not True
                    ):
                        raise ValueError("LIVE sources require transport, endpoint fingerprint, and continuity")
            for camera_id in camera_ids:
                connection.execute("""
                    INSERT INTO session_sources (
                        source_id, session_id, camera_id, source_kind, transport,
                        endpoint_fingerprint, continuous, recording_id, recording_checksum, registered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    _identifier("source"), session_id, camera_id, source_kind,
                    sources_by_camera.get(camera_id, {}).get("transport"),
                    sources_by_camera.get(camera_id, {}).get("endpoint_fingerprint"),
                    int(mode == "LIVE"),
                    recording_id, recording_checksum, started_at,
                ))
        return self.get_session(session_id)

    def end_session(self, session_id: str, *, reason: str) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("session end reason is required")
        with self._lock, self._connect() as connection:
            connection.execute("""
                UPDATE incidents SET evidence_closed_at = last_evidence_at + ?
                WHERE session_id = ? AND category = 'SURVEILLANCE' AND evidence_closed_at IS NULL
            """, (ASSOCIATION_WINDOW_SECONDS, session_id))
            cursor = connection.execute("""
                UPDATE monitoring_sessions SET ended_at = ?, ended_reason = ?
                WHERE session_id = ? AND ended_at IS NULL
            """, (time.time(), reason, session_id))
            if cursor.rowcount != 1:
                raise ValueError("unknown or already ended monitoring session")
        return self.get_session(session_id)

    def change_session_identity(self, session_id: str, **changes: Any) -> None:
        if {"mode", "policy_version_id"}.intersection(changes):
            raise ValueError("session mode and policy version are immutable")
        raise ValueError("session identity is immutable")

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM monitoring_sessions WHERE session_id = ?", (session_id,),
            ).fetchone()
        if not row:
            raise KeyError(session_id)
        return dict(row)

    def snapshot(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            session = connection.execute(
                "SELECT * FROM monitoring_sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            ).fetchone()
            cameras: list[dict[str, Any]] = []
            measurements: list[dict[str, Any]] = []
            policy = None
            if session:
                policy_row = connection.execute(
                    "SELECT * FROM policy_versions WHERE policy_version_id = ?",
                    (session["policy_version_id"],),
                ).fetchone()
                policy = self._policy(policy_row) if policy_row else None
                cameras = [dict(row) for row in connection.execute("""
                    SELECT health_id, session_id, camera_id, physical_zone_id, state, reason, recorded_at
                    FROM camera_health WHERE health_id IN (
                        SELECT health_id FROM camera_health AS newest
                        WHERE newest.session_id = ? AND newest.recorded_at = (
                            SELECT MAX(recorded_at) FROM camera_health
                            WHERE session_id = newest.session_id AND camera_id = newest.camera_id
                        )
                    ) ORDER BY camera_id
                """, (session["session_id"],)).fetchall()]
                measurements = [dict(row) for row in connection.execute("""
                    SELECT * FROM session_measurements WHERE measurement_id IN (
                        SELECT measurement_id FROM session_measurements AS newest
                        WHERE newest.session_id = ? AND newest.recorded_at = (
                            SELECT MAX(recorded_at) FROM session_measurements
                            WHERE session_id = newest.session_id
                              AND camera_id IS newest.camera_id
                        )
                    ) ORDER BY camera_id
                """, (session["session_id"],)).fetchall()]
        active_session = dict(session) if session else None
        return {
            "active_session": active_session,
            "active_policy": policy,
            "camera_health": cameras,
            "measurements": measurements,
            "incidents": self.list_incidents(session_id=session["session_id"]) if session else [],
            "search_level": "DETERMINISTIC_LEXICAL",
        }

    def list_sources(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM session_sources WHERE session_id = ? ORDER BY camera_id", (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_verification_evidence(
        self, session_id: str, evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        required = {"camera_id", "event_type", "physical_zone_id", "observed_at", "confidence"}
        missing = required.difference(evidence)
        if missing:
            raise ValueError(f"verification evidence missing: {', '.join(sorted(missing))}")
        evidence_id = _identifier("verification")
        with self._lock, self._connect() as connection:
            source = connection.execute("""
                SELECT s.*, p.payload FROM session_sources s
                JOIN monitoring_sessions m ON m.session_id = s.session_id
                JOIN policy_versions p ON p.policy_version_id = m.policy_version_id
                WHERE s.session_id = ? AND s.camera_id = ? AND m.ended_at IS NULL
            """, (session_id, evidence["camera_id"])).fetchone()
            if not source:
                raise ValueError("verification camera is not a registered active source")
            policy = json.loads(source["payload"])
            view = next((
                candidate for candidate in policy.get("camera_view_zones", [])
                if candidate.get("camera_id") == evidence["camera_id"]
                and candidate.get("physical_zone_id") == evidence["physical_zone_id"]
            ), None)
            provenance = evidence.get("provenance") or {}
            if not view or not self._point_in_polygon(provenance.get("frame_point"), view["polygon"]):
                raise ValueError("verification evidence is outside the mapped Camera View Zone")
            connection.execute("""
                INSERT INTO verification_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence_id, session_id, evidence["camera_id"], evidence["event_type"],
                evidence["physical_zone_id"], evidence["observed_at"], evidence["confidence"],
                _canonical_json({**provenance, "registered_source_id": source["source_id"]}),
            ))
        return {"evidence_id": evidence_id, **dict(evidence)}

    def record_observation(self, session_id: str, observation: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "observation_id", "event_type", "physical_zone_id", "receive_time", "sequence",
        }
        missing = required.difference(observation)
        if missing:
            raise ValueError(f"observation missing: {', '.join(sorted(missing))}")
        event_time = float(observation.get("capture_time") or observation["receive_time"])
        with self._lock, self._connect() as connection:
            session = connection.execute(
                "SELECT * FROM monitoring_sessions WHERE session_id = ? AND ended_at IS NULL", (session_id,),
            ).fetchone()
            if not session:
                raise ValueError("unknown or ended monitoring session")
            policy_row = connection.execute(
                "SELECT payload FROM policy_versions WHERE policy_version_id = ?",
                (session["policy_version_id"],),
            ).fetchone()
            policy = json.loads(policy_row["payload"])
            source = connection.execute("""
                SELECT * FROM session_sources WHERE session_id = ? AND camera_id = ?
            """, (session_id, observation.get("camera_id"))).fetchone()
            if not source:
                raise ValueError("observation camera is not a registered session source")
            provenance = {
                **(observation.get("provenance") or {}),
                "registered_source_id": source["source_id"],
                "source_kind": source["source_kind"],
                "recording_id": source["recording_id"],
                "recording_checksum": source["recording_checksum"],
            }
            zone_id = observation["physical_zone_id"]
            zone_policy = policy["zones"].get(zone_id)
            if not zone_policy:
                raise ValueError("observation physical zone is not in the active policy")
            event_type = observation["event_type"]
            if event_type not in (zone_policy.get("enabled_rules") or []):
                raise ValueError(f"event type is disabled by the active policy: {event_type}")
            threshold = float((zone_policy.get("thresholds") or {}).get(event_type, 0))
            if float(observation.get("confidence") or 0) < threshold:
                raise ValueError("observation confidence is below the active policy threshold")
            view = next((
                candidate for candidate in policy.get("camera_view_zones", [])
                if candidate.get("camera_id") == observation.get("camera_id")
                and candidate.get("physical_zone_id") == zone_id
            ), None)
            point = provenance.get("frame_point")
            if not view or not self._point_in_polygon(point, view["polygon"]):
                raise ValueError("observation coordinates are not inside the mapped Camera View Zone")
            if event_type == "abandoned_object" and not (
                (policy.get("capabilities") or {}).get("zone_aware_abandoned_object")
                and provenance.get("zone_aware_evaluation")
            ):
                raise ValueError("abandoned_object observation lacks zone-aware evaluation provenance")
            schedule = zone_policy.get("schedule")
            if schedule:
                hour = time.gmtime(event_time).tm_hour
                start_hour = int(schedule["start_hour_utc"])
                end_hour = int(schedule["end_hour_utc"])
                schedule_active = (
                    start_hour <= hour < end_hour if start_hour < end_hour
                    else hour >= start_hour or hour < end_hour
                )
                if not schedule_active:
                    raise ValueError("observation occurred outside the active policy schedule")
            if zone_policy.get("verification_required"):
                evidence_ids = (observation.get("verification") or {}).get("evidence_ids") or []
                placeholders = ",".join("?" for _ in evidence_ids)
                verifier = None
                if placeholders:
                    verifier = connection.execute(f"""
                        SELECT 1 FROM verification_evidence
                        WHERE evidence_id IN ({placeholders}) AND session_id = ?
                          AND physical_zone_id = ? AND event_type = ? AND camera_id != ?
                          AND ABS(observed_at - ?) <= ? LIMIT 1
                    """, (
                        *evidence_ids, session_id, zone_id, event_type, observation.get("camera_id"),
                        event_time, ASSOCIATION_WINDOW_SECONDS,
                    )).fetchone()
                if not verifier:
                    raise ValueError("observation requires simultaneous evidence from another mapped camera")
            connection.execute("""
                UPDATE incidents SET evidence_closed_at = last_evidence_at + ?
                WHERE session_id = ? AND category = 'SURVEILLANCE'
                  AND evidence_closed_at IS NULL AND ? - last_evidence_at > ?
            """, (
                ASSOCIATION_WINDOW_SECONDS, session_id, event_time, ASSOCIATION_WINDOW_SECONDS,
            ))
            incident = connection.execute("""
                SELECT * FROM incidents
                WHERE session_id = ? AND category = 'SURVEILLANCE'
                  AND physical_zone_id = ? AND event_type = ?
                  AND evidence_closed_at IS NULL AND ? - last_evidence_at <= ?
                  AND ? >= last_evidence_at
                ORDER BY last_evidence_at DESC LIMIT 1
            """, (
                session_id, observation["physical_zone_id"], observation["event_type"],
                event_time, ASSOCIATION_WINDOW_SECONDS, event_time,
            )).fetchone()
            facts = list(observation.get("facts") or [])
            if incident:
                incident_id = incident["incident_id"]
                combined_facts = list(dict.fromkeys(json.loads(incident["facts"]) + facts))
                connection.execute("""
                    UPDATE incidents SET last_evidence_at = ?, confidence = MAX(confidence, ?), facts = ?
                    WHERE incident_id = ?
                """, (
                    event_time, float(observation.get("confidence") or 0),
                    _canonical_json(combined_facts), incident_id,
                ))
            else:
                cooldown = float(zone_policy.get("cooldown_seconds") or 0)
                last_incident = connection.execute("""
                    SELECT last_evidence_at FROM incidents
                    WHERE session_id = ? AND category = 'SURVEILLANCE'
                      AND physical_zone_id = ? AND event_type = ?
                    ORDER BY last_evidence_at DESC LIMIT 1
                """, (session_id, zone_id, event_type)).fetchone()
                if last_incident and event_time - last_incident["last_evidence_at"] <= cooldown:
                    raise ValueError("observation is inside the active policy cooldown")
                incident_id = _identifier("incident")
                connection.execute("""
                    INSERT INTO incidents (
                        incident_id, session_id, policy_version_id, category, event_type,
                        physical_zone_id, workflow_state, verdict, severity,
                        is_surveillance_anomaly, confidence, first_event_at, last_evidence_at,
                        facts, created_at
                    ) VALUES (?, ?, ?, 'SURVEILLANCE', ?, ?, 'OPEN', 'UNREVIEWED', ?, 1, ?, ?, ?, ?, ?)
                """, (
                    incident_id, session_id, session["policy_version_id"], observation["event_type"],
                    observation["physical_zone_id"], zone_policy.get("severity", "WARNING"),
                    float(observation.get("confidence") or 0), event_time, event_time,
                    _canonical_json(facts), time.time(),
                ))
            connection.execute("""
                INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                observation["observation_id"], incident_id, observation.get("camera_id"),
                observation["event_type"], observation["physical_zone_id"],
                observation.get("capture_time"), observation["receive_time"], observation["sequence"],
                observation.get("clock_offset"), observation.get("processing_started_at"),
                observation.get("processing_finished_at"), observation.get("alert_emitted_at"),
                observation.get("confidence"), _canonical_json(facts),
                _canonical_json(provenance),
            ))
        return self.get_incident(incident_id)

    def record_action(
        self, incident_id: str, action: str, actor: str, details: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        try:
            command = IncidentAction(action)
        except ValueError as error:
            raise ValueError("unsupported incident action") from error
        details = dict(details or {})
        now = time.time()
        with self._lock, self._connect() as connection:
            incident = connection.execute(
                "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,),
            ).fetchone()
            if not incident:
                raise ValueError("unknown incident")
            if command is IncidentAction.ACKNOWLEDGE:
                if incident["workflow_state"] != "OPEN":
                    raise ValueError("only open incidents can be acknowledged")
                connection.execute(
                    "UPDATE incidents SET workflow_state = 'ACKNOWLEDGED' WHERE incident_id = ?",
                    (incident_id,),
                )
            elif command is IncidentAction.RESOLVE:
                if incident["workflow_state"] == "OPEN":
                    raise ValueError("incident must be acknowledged before resolution")
                connection.execute(
                    "UPDATE incidents SET workflow_state = 'RESOLVED' WHERE incident_id = ?",
                    (incident_id,),
                )
            elif command is IncidentAction.SET_VERDICT:
                verdict = details.get("verdict")
                if verdict not in VERDICTS - {"UNREVIEWED"}:
                    raise ValueError("verdict must be CONFIRMED_ANOMALY or FALSE_ALARM")
                connection.execute(
                    "UPDATE incidents SET verdict = ? WHERE incident_id = ?", (verdict, incident_id),
                )
                connection.execute(
                    "INSERT INTO feedback_records VALUES (?, ?, ?, ?, ?, ?)",
                    (_identifier("feedback"), incident_id, verdict, actor, details.get("note"), now),
                )
            elif command is IncidentAction.APPROVE_PLAYBOOK:
                if actor != "operator":
                    raise ValueError("Response Playbook approval requires an operator")
                policy_row = connection.execute(
                    "SELECT payload FROM policy_versions WHERE policy_version_id = ?",
                    (incident["policy_version_id"],),
                ).fetchone()
                policy = json.loads(policy_row["payload"])
                zone = (policy.get("zones") or {}).get(incident["physical_zone_id"], {})
                allowed = (zone.get("response_playbooks") or {}).get(incident["event_type"], [])
                if details.get("playbook_action") not in allowed:
                    raise ValueError("approved response is not in the Incident Policy Version")
            connection.execute(
                "INSERT INTO incident_actions VALUES (?, ?, ?, ?, ?, ?)",
                (_identifier("action"), incident_id, actor, command.value, _canonical_json(details), now),
            )
        return self.get_incident(incident_id)

    def record_camera_health(
        self, session_id: str, camera_id: str, physical_zone_id: Optional[str], state: str,
        recorded_at: float, *, reason: Optional[str] = None,
    ) -> dict[str, Any]:
        if state not in HEALTH_STATES:
            raise ValueError("invalid camera health state")
        with self._lock, self._connect() as connection:
            session = connection.execute(
                "SELECT * FROM monitoring_sessions WHERE session_id = ? AND ended_at IS NULL", (session_id,),
            ).fetchone()
            if not session:
                raise ValueError("unknown monitoring session")
            if not connection.execute(
                "SELECT 1 FROM session_sources WHERE session_id = ? AND camera_id = ?",
                (session_id, camera_id),
            ).fetchone():
                raise ValueError("camera health requires a registered session source")
            policy_row = connection.execute(
                "SELECT payload FROM policy_versions WHERE policy_version_id = ?",
                (session["policy_version_id"],),
            ).fetchone()
            policy = json.loads(policy_row["payload"])
            mapped_zones = {
                view["physical_zone_id"] for view in policy.get("camera_view_zones", [])
                if view.get("camera_id") == camera_id
            }
            if physical_zone_id is None and len(mapped_zones) == 1:
                physical_zone_id = next(iter(mapped_zones))
            if physical_zone_id not in mapped_zones:
                raise ValueError("camera health physical zone is not mapped by the Policy Version")
            connection.execute(
                "INSERT INTO camera_health VALUES (?, ?, ?, ?, ?, ?, ?)",
                (_identifier("health"), session_id, camera_id, physical_zone_id, state, reason, recorded_at),
            )
            if state == "ONLINE":
                active_outage = connection.execute("""
                    SELECT incident_id, facts FROM incidents
                    WHERE session_id = ? AND category = 'SENSOR_HEALTH'
                      AND event_type = 'camera_offline' AND affected_camera_id = ?
                      AND evidence_closed_at IS NULL ORDER BY created_at DESC LIMIT 1
                """, (session_id, camera_id)).fetchone()
                if active_outage:
                    recovered_facts = list(dict.fromkeys(
                        json.loads(active_outage["facts"]) + [f"{camera_id} recovered"],
                    ))
                    connection.execute("""
                        UPDATE incidents SET evidence_closed_at = ?, last_evidence_at = ?, facts = ?
                        WHERE incident_id = ?
                    """, (
                        recorded_at, recorded_at, _canonical_json(recovered_facts),
                        active_outage["incident_id"],
                    ))
            if state == "OFFLINE":
                existing = connection.execute("""
                    SELECT incident_id FROM incidents WHERE session_id = ? AND category = 'SENSOR_HEALTH'
                    AND event_type = 'camera_offline' AND physical_zone_id IS ?
                    AND affected_camera_id = ?
                    AND evidence_closed_at IS NULL ORDER BY created_at DESC LIMIT 1
                """, (session_id, physical_zone_id, camera_id)).fetchone()
                if not existing:
                    incident_id = _identifier("incident")
                    connection.execute("""
                        INSERT INTO incidents (
                            incident_id, session_id, policy_version_id, category, event_type,
                            physical_zone_id, affected_camera_id, workflow_state, verdict, severity,
                            is_surveillance_anomaly, first_event_at, last_evidence_at, facts, created_at
                        ) VALUES (?, ?, ?, 'SENSOR_HEALTH', 'camera_offline', ?, ?, 'OPEN',
                                  'UNREVIEWED', 'WARNING', 0, ?, ?, ?, ?)
                    """, (
                        incident_id, session_id, session["policy_version_id"], physical_zone_id, camera_id,
                        recorded_at, recorded_at,
                        _canonical_json([f"{camera_id} offline", reason] if reason else [f"{camera_id} offline"]),
                        time.time(),
                    ))
        return {"camera_id": camera_id, "state": state, "recorded_at": recorded_at}

    def close_stale_evidence(self, now: float) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("""
                UPDATE incidents SET evidence_closed_at = last_evidence_at + ?
                WHERE category = 'SURVEILLANCE' AND evidence_closed_at IS NULL
                  AND session_id IN (SELECT session_id FROM monitoring_sessions WHERE mode = 'LIVE')
                  AND ? - last_evidence_at > ?
            """, (ASSOCIATION_WINDOW_SECONDS, now, ASSOCIATION_WINDOW_SECONDS))
            return cursor.rowcount

    def record_measurement(self, session_id: str, measurement: Mapping[str, Any]) -> dict[str, Any]:
        recorded_at = float(measurement.get("recorded_at", time.time()))
        measurement_id = _identifier("measurement")
        fields = (
            "inference_fps", "dropped_frames", "stale_frames", "cpu_percent", "ram_percent",
            "network_kbps", "camera_uptime_seconds", "reconnects", "alert_latency_ms",
        )
        with self._lock, self._connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM monitoring_sessions WHERE session_id = ? AND ended_at IS NULL", (session_id,),
            ).fetchone():
                raise ValueError("unknown monitoring session")
            connection.execute("""
                INSERT INTO session_measurements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                measurement_id, session_id, measurement.get("camera_id"), recorded_at,
                *(measurement.get(field) for field in fields),
            ))
        return {
            "measurement_id": measurement_id, "session_id": session_id,
            "camera_id": measurement.get("camera_id"), "recorded_at": recorded_at,
            **{field: measurement.get(field) for field in fields},
        }

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,),
            ).fetchone()
        if not row:
            raise KeyError(incident_id)
        return self._incident(row)

    def list_incidents(self, *, session_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM incidents"
        parameters: tuple[Any, ...] = ()
        if session_id:
            query += " WHERE session_id = ?"
            parameters = (session_id,)
        query += " ORDER BY created_at DESC"
        with self._lock, self._connect() as connection:
            return [self._incident(row) for row in connection.execute(query, parameters).fetchall()]

    def list_feedback(self, incident_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM feedback_records WHERE incident_id = ? ORDER BY created_at", (incident_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, *, zone: Optional[str] = None, verdict: Optional[str] = None) -> dict[str, Any]:
        tokens = {token.lower() for token in query.split() if token.strip()}
        candidates = self.list_incidents()
        if zone:
            candidates = [item for item in candidates if item["physical_zone_id"] == zone]
        if verdict:
            candidates = [item for item in candidates if item["verdict"] == verdict]
        results = []
        for incident in candidates:
            searchable = " ".join([
                incident["event_type"].replace("_", " "), incident["physical_zone_id"] or "",
                *incident["facts"],
            ]).lower()
            score = sum(token in searchable for token in tokens)
            if not tokens or score:
                results.append({**incident, "score": score})
        results.sort(key=lambda item: (item["score"], item["created_at"]), reverse=True)
        return {"search_level": "DETERMINISTIC_LEXICAL", "results": results}

    @staticmethod
    def _policy(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["payload"] = json.loads(value["payload"])
        return value

    @staticmethod
    def _incident(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["facts"] = json.loads(value["facts"])
        value["is_surveillance_anomaly"] = bool(value["is_surveillance_anomaly"])
        return value

    @staticmethod
    def _point_in_polygon(point: Any, polygon: list[list[float]]) -> bool:
        if not isinstance(point, list) or len(point) != 2:
            return False
        x, y = float(point[0]), float(point[1])
        inside = False
        previous = polygon[-1]
        for current in polygon:
            x1, y1 = float(previous[0]), float(previous[1])
            x2, y2 = float(current[0]), float(current[1])
            crosses = (y1 > y) != (y2 > y)
            if crosses and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
            previous = current
        return inside
