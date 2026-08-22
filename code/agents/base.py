"""Base agent: message-driven control loop with local state (belief store)."""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from aura_mas.core.bus import BaseBus, Event, TOPIC_EVENTS, new_id


class Agent:
    """Minimal stateful agent.

    Each agent has:
    - an identity (`agent_id`),
    - a belief store (`self.beliefs`) updated by messages and perception,
    - a message-driven control loop (subscriptions dispatched by the bus),
    - an optional periodic `tick()` for time-driven behavior.
    """

    def __init__(self, agent_id: str, bus: BaseBus, tick_interval: float = 0.0) -> None:
        self.agent_id = agent_id
        self.bus = bus
        self.beliefs: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        self.log = logging.getLogger(f"aura.{agent_id}")
        self._tick_interval = tick_interval
        self._stop = threading.Event()
        self._tick_thread: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        self.setup()
        if self._tick_interval > 0:
            self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
            self._tick_thread.start()
        self.log.info("agent started")

    def stop(self) -> None:
        self._stop.set()
        self.log.info("agent stopped")

    def publish_event(self, event_type: str, confidence: float, ts: float,
                      modality: str, zone: Optional[str] = None,
                      track_id: Optional[int] = None,
                      evidence_path: Optional[str] = None,
                      extra: Optional[Dict[str, Any]] = None) -> Event:
        """Build and publish a semantic Event on TOPIC_EVENTS (QoS 1),
        counting it in the agent's metrics."""
        ev = Event(event_id=new_id("ev"), sensor_id=self.agent_id,
                   timestamp=ts, event_type=event_type,
                   confidence=round(confidence, 3), modality=modality,
                   zone=zone, track_id=track_id, evidence_path=evidence_path,
                   extra=extra or {})
        self.metrics["events"] = self.metrics.get("events", 0) + 1
        self.bus.publish(TOPIC_EVENTS, ev.to_json(), qos=1)
        return ev

    def _tick_loop(self) -> None:
        while not self._stop.wait(self._tick_interval):
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                self.log.exception("tick error")

    # -- to override ----------------------------------------------------------
    def setup(self) -> None:
        """Subscribe to topics, load models."""

    def tick(self) -> None:
        """Periodic behavior (optional)."""
