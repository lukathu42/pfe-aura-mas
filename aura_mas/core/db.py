"""SQLite persistence layer for AURA-MAS.

Provides a thread-safe, lightweight relational store for:
- Alerts (status, severity, confidence, composite types, explanations)
- Audit log (actor, action, reasoning, timestamp)
- Operator feedback (for online reinforcement learning / RLOF)
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("aura.db")

DEFAULT_DB_PATH = "data/aura_surveillance.db"


class AuraDatabase:
    """Thread-safe SQLite database manager for AURA-MAS."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.executescript("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        severity TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        contributing_types TEXT,
                        confidence REAL NOT NULL,
                        zone TEXT,
                        sensors TEXT,
                        evidence TEXT,
                        fused_events TEXT,
                        explanation TEXT,
                        status TEXT DEFAULT 'OPEN',
                        created_at REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        alert_id TEXT,
                        hypothesis_id TEXT,
                        details TEXT,
                        created_at REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS operator_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        alert_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        reward REAL NOT NULL,
                        notes TEXT,
                        FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_alerts_zone ON alerts(zone);
                    CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
                    CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);
                    """)
            finally:
                conn.close()

    def save_alert(self, alert_data: Dict[str, Any]) -> None:
        """Insert or replace an alert in the database."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT OR REPLACE INTO alerts (
                        alert_id, timestamp, severity, event_type, contributing_types,
                        confidence, zone, sensors, evidence, fused_events, explanation,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        alert_data["alert_id"],
                        alert_data["timestamp"],
                        alert_data["severity"],
                        alert_data["event_type"],
                        json.dumps(alert_data.get("contributing_types", [alert_data["event_type"]])),
                        float(alert_data["confidence"]),
                        alert_data.get("zone"),
                        json.dumps(alert_data.get("sensors", [])),
                        json.dumps(alert_data.get("evidence", [])),
                        json.dumps(alert_data.get("fused_events", [])),
                        alert_data.get("explanation"),
                        alert_data.get("status", "OPEN"),
                        time.time(),
                    ))
            except Exception as e:
                log.exception("Failed to save alert %s: %s", alert_data.get("alert_id"), e)
            finally:
                conn.close()

    def update_alert_status(self, alert_id: str, status: str) -> bool:
        """Update status of an alert (OPEN, ACKNOWLEDGED, DISMISSED)."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cursor = conn.execute(
                        "UPDATE alerts SET status = ? WHERE alert_id = ?",
                        (status, alert_id)
                    )
                    return cursor.rowcount > 0
            finally:
                conn.close()

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single alert by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_alert_dict(row)
            finally:
                conn.close()

    def query_alerts(self, limit: int = 50, zone: Optional[str] = None,
                     severity: Optional[str] = None, status: Optional[str] = None,
                     since_ts: Optional[float] = None) -> List[Dict[str, Any]]:
        """Query alerts with flexible filtering."""
        query = "SELECT * FROM alerts WHERE 1=1"
        params: List[Any] = []

        if zone:
            query += " AND zone = ?"
            params.append(zone)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if status:
            query += " AND status = ?"
            params.append(status)
        if since_ts is not None:
            query += " AND timestamp >= ?"
            params.append(since_ts)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(query, params)
                return [self._row_to_alert_dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

    def log_audit(self, actor: str, action: str, alert_id: Optional[str] = None,
                  hypothesis_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Record an audit trail event."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO audit_log (timestamp, actor, action, alert_id, hypothesis_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        time.time(),
                        actor,
                        action,
                        alert_id,
                        hypothesis_id,
                        json.dumps(details or {}),
                        time.time()
                    ))
            finally:
                conn.close()

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledgement cannot serve as a learning signal."""
        return self.update_alert_status(alert_id, "ACKNOWLEDGED")

    def record_feedback(self, alert_id: str, verdict: str, notes: Optional[str] = None) -> float:
        """Only explicit verdicts may feed later offline calibration."""
        verdict = verdict.upper()
        if verdict not in {"CONFIRMED_ANOMALY", "FALSE_ALARM"}:
            raise ValueError("feedback requires an explicit operator verdict")
        reward = 1.0 if verdict == "CONFIRMED_ANOMALY" else -1.0
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                    INSERT INTO operator_feedback (timestamp, alert_id, action, reward, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """, (time.time(), alert_id, verdict, reward, notes or ""))
            finally:
                conn.close()
        return reward

    def query_feedback(self, alert_id: str) -> List[Dict[str, Any]]:
        """Acknowledgement is deliberately absent from this history."""
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute("""
                    SELECT id, timestamp, alert_id, action AS verdict, reward, notes
                    FROM operator_feedback WHERE alert_id = ? ORDER BY timestamp
                """, (alert_id,)).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def _row_to_alert_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "alert_id": row["alert_id"],
            "timestamp": row["timestamp"],
            "severity": row["severity"],
            "event_type": row["event_type"],
            "contributing_types": json.loads(row["contributing_types"] or "[]"),
            "confidence": row["confidence"],
            "zone": row["zone"],
            "sensors": json.loads(row["sensors"] or "[]"),
            "evidence": json.loads(row["evidence"] or "[]"),
            "fused_events": json.loads(row["fused_events"] or "[]"),
            "explanation": row["explanation"],
            "status": row["status"],
        }
