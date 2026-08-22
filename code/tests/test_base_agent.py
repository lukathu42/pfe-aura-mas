"""Agent lifecycle tests: setup hook, tick thread and stop semantics."""
from __future__ import annotations

import threading

from aura_mas.agents.base import Agent
from aura_mas.core.bus import LocalBus


class Recorder(Agent):
    def __init__(self, bus, tick_interval=0.0, raise_on_tick=False):
        super().__init__("agent_x", bus, tick_interval=tick_interval)
        self.setup_calls = 0
        self.ticks = threading.Semaphore(0)
        self.tick_count = 0
        self.raise_on_tick = raise_on_tick

    def setup(self) -> None:
        self.setup_calls += 1

    def tick(self) -> None:
        self.tick_count += 1
        self.ticks.release()
        if self.raise_on_tick:
            raise RuntimeError("tick blew up")


def test_new_agent_has_an_identity_and_an_empty_belief_store():
    bus = LocalBus()
    agent = Agent("agent_x", bus)
    assert agent.agent_id == "agent_x" and agent.bus is bus
    assert agent.beliefs == {}
    assert agent.log.name == "aura.agent_x"


def test_default_hooks_are_inert():
    agent = Agent("agent_x", LocalBus())
    assert agent.setup() is None and agent.tick() is None


def test_start_runs_setup_without_a_tick_thread():
    agent = Recorder(LocalBus())
    agent.start()
    assert agent.setup_calls == 1
    assert agent._tick_thread is None
    agent.stop()


def test_tick_interval_spawns_a_daemon_thread_that_ticks():
    agent = Recorder(LocalBus(), tick_interval=0.01)
    agent.start()
    try:
        assert agent.ticks.acquire(timeout=5.0)
        assert agent._tick_thread is not None
        assert agent._tick_thread.daemon is True
    finally:
        agent.stop()
    agent._tick_thread.join(timeout=5.0)
    assert not agent._tick_thread.is_alive()


def test_a_raising_tick_does_not_kill_the_loop():
    agent = Recorder(LocalBus(), tick_interval=0.01, raise_on_tick=True)
    agent.start()
    try:
        assert agent.ticks.acquire(timeout=5.0)
        assert agent.ticks.acquire(timeout=5.0)
    finally:
        agent.stop()


def test_stop_is_idempotent():
    agent = Recorder(LocalBus())
    agent.stop()
    agent.stop()
    assert agent._stop.is_set()
