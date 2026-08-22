"""AudioAgent tests: DSP scorer, backend selection, and event emission.

No TensorFlow required — the YAMNet path is exercised with a stub model so
the class-collapsing / top_k logic documented in `_process_chunk` is covered
on machines without `tensorflow-cpu` installed.
"""
from __future__ import annotations

import json
import wave

import numpy as np
import pytest

from aura_mas.agents.audio_agent import AudioAgent, DspAnomalyScorer
from aura_mas.core.bus import Event, LocalBus, TOPIC_EVENTS

SR = 16000


@pytest.fixture
def collected_events():
    bus = LocalBus()
    events = []
    bus.subscribe(TOPIC_EVENTS, lambda t, p: events.append(Event.from_json(p)))
    return bus, events


def tone(n: int, amplitude: float = 0.1, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(n) * amplitude).astype(np.float32)


def test_dsp_scorer_stays_silent_until_baseline_is_established():
    scorer = DspAnomalyScorer()
    for _ in range(9):
        assert scorer.score(tone(SR), SR) == 0.0
    assert len(scorer.energy_hist) == 9


def test_dsp_scorer_flags_a_transient_above_its_baseline():
    scorer = DspAnomalyScorer()
    for i in range(20):
        scorer.score(tone(SR, 0.01, seed=i), SR)
    quiet = scorer.score(tone(SR, 0.01, seed=99), SR)
    spike = scorer.score(tone(SR, 5.0, seed=100), SR)
    assert spike > quiet
    assert 0.0 <= spike <= 1.0


def test_dsp_scorer_history_is_bounded():
    scorer = DspAnomalyScorer(history=5)
    for i in range(20):
        scorer.score(tone(1024, seed=i), SR)
    assert len(scorer.energy_hist) == 5 and len(scorer.flatness_hist) == 5


def test_dsp_backend_skips_yamnet_load(collected_events, monkeypatch):
    bus, _ = collected_events

    def fail():
        raise AssertionError("backend='dsp' must not try to load YAMNet")

    agent = AudioAgent("mic_01", bus, source="x.wav", backend="dsp")
    monkeypatch.setattr(agent, "_load_yamnet", fail)
    agent.setup()
    assert agent.backend_used == "dsp" and agent.metrics["backend"] == "dsp"


def test_auto_backend_falls_back_to_dsp(collected_events, monkeypatch):
    bus, _ = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="auto")
    monkeypatch.setattr(agent, "_load_yamnet",
                        lambda: (_ for _ in ()).throw(ImportError("no tf")))
    agent.setup()
    assert agent.backend_used == "dsp"


def test_requested_yamnet_backend_never_degrades_silently(collected_events,
                                                          monkeypatch):
    bus, _ = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="yamnet")
    monkeypatch.setattr(agent, "_load_yamnet",
                        lambda: (_ for _ in ()).throw(ImportError("no tf")))
    with pytest.raises(ImportError):
        agent.setup()


def test_auto_backend_records_yamnet_when_it_loads(collected_events, monkeypatch):
    bus, _ = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="auto")
    monkeypatch.setattr(agent, "_load_yamnet",
                        lambda: agent._class_names.extend(["Screaming"]))
    agent.setup()
    assert agent.backend_used == "yamnet" and agent.metrics["backend"] == "yamnet"


def test_warmup_is_a_noop_for_dsp(collected_events):
    bus, _ = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="dsp")
    agent.warmup()
    assert not agent._dsp.energy_hist, "warmup must not poison the DSP baseline"


def test_warmup_runs_one_yamnet_inference(collected_events, monkeypatch):
    bus, _ = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="yamnet")
    agent.backend_used = "yamnet"
    seen = []
    monkeypatch.setattr(agent, "_infer", lambda chunk: seen.append(len(chunk)))
    agent.warmup()
    assert seen == [SR + SR // 2]


def test_dsp_chunk_emits_zoned_audio_anomaly_event(collected_events):
    bus, events = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="dsp",
                       anomaly_threshold=0.0, zone="zone_A")
    agent.setup()
    agent._process_chunk(tone(SR), SR)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "audio_anomaly" and ev.modality == "audio"
    assert ev.zone == "zone_A" and ev.sensor_id == "mic_01"
    assert ev.extra == {"method": "dsp_zscore"}
    assert agent.metrics["events"] == 1


def test_dsp_chunk_below_threshold_emits_nothing(collected_events):
    bus, events = collected_events
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="dsp",
                       anomaly_threshold=1.0)
    agent.setup()
    agent._process_chunk(tone(SR), SR)
    assert events == [] and agent.metrics["events"] == 0


class FakeScores:
    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = matrix

    def numpy(self) -> np.ndarray:
        return self.matrix


def yamnet_agent(bus, class_scores: dict, top_k: int = 1,
                 zone: str | None = None) -> AudioAgent:
    """Wire an AudioAgent to a stub YAMNet returning fixed per-class scores."""
    agent = AudioAgent("mic_01", bus, source="x.wav", backend="yamnet",
                       top_k=top_k, zone=zone)
    names = list(class_scores)
    agent._class_names = names
    agent._class_idx = {name: i for i, name in enumerate(names)}
    row = np.array([[class_scores[n] for n in names]], dtype=np.float32)
    agent._yamnet = object()
    agent._infer = lambda chunk: (FakeScores(row), None, None)
    return agent


def test_yamnet_chunk_emits_class_specific_event(collected_events):
    bus, events = collected_events
    agent = yamnet_agent(bus, {"Screaming": 0.8, "Glass": 0.0}, zone="zone_B")
    agent._process_chunk(tone(SR), SR)
    assert [e.event_type for e in events] == ["audio_scream"]
    assert events[0].confidence == 0.8 and events[0].zone == "zone_B"
    assert events[0].extra["yamnet_class"] == "Screaming"
    assert events[0].extra["yamnet_rank"] == 0


def test_yamnet_scores_below_class_minimum_are_ignored(collected_events):
    bus, events = collected_events
    # "Screaming" needs >= 0.25, "Yell" >= 0.3
    agent = yamnet_agent(bus, {"Screaming": 0.2, "Yell": 0.25})
    agent._process_chunk(tone(SR), SR)
    assert events == []


def test_yamnet_collapses_classes_of_the_same_event_type(collected_events):
    bus, events = collected_events
    agent = yamnet_agent(bus, {"Glass": 0.4, "Shatter": 0.9})
    agent._process_chunk(tone(SR), SR)
    assert [e.event_type for e in events] == ["audio_glass_break"]
    assert events[0].extra["yamnet_class"] == "Shatter"
    assert events[0].extra["n_candidates"] == 2
    assert agent.metrics["suppressed_dupes"] == 1


def test_top_k_limits_distinct_event_types_per_chunk(collected_events):
    bus, events = collected_events
    scores = {"Screaming": 0.9, "Alarm": 0.8, "Glass": 0.7}
    agent = yamnet_agent(bus, scores, top_k=2)
    agent._process_chunk(tone(SR), SR)
    assert [e.event_type for e in events] == ["audio_scream", "audio_alarm"]
    assert agent.metrics["suppressed_dupes"] == 1


def test_yamnet_max_pools_over_frames(collected_events):
    bus, events = collected_events
    agent = yamnet_agent(bus, {"Screaming": 0.0})
    frames = np.array([[0.0], [0.9], [0.1]], dtype=np.float32)
    agent._infer = lambda chunk: (FakeScores(frames), None, None)
    agent._process_chunk(tone(SR), SR)
    assert [e.confidence for e in events] == [0.9], "max, not mean, over frames"


def test_unknown_yamnet_classes_are_skipped(collected_events):
    bus, events = collected_events
    agent = yamnet_agent(bus, {"Speech": 0.99})
    agent._process_chunk(tone(SR), SR)
    assert events == []


def write_wav(path, seconds: float = 3.0) -> str:
    samples = (tone(int(SR * seconds), 0.2) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(samples.tobytes())
    return str(path)


def test_run_chunks_a_wav_file_and_reports_metrics(tmp_path, collected_events):
    bus, _ = collected_events
    source = write_wav(tmp_path / "clip.wav", seconds=4.0)
    agent = AudioAgent("mic_01", bus, source, backend="dsp", realtime=False,
                       anomaly_threshold=1.1)
    agent.setup()
    metrics = agent.run()
    assert metrics["chunks"] == 3, "one chunk per full second, last partial dropped"
    assert metrics["backend"] == "dsp"


def test_run_honours_max_chunks(tmp_path, collected_events):
    bus, _ = collected_events
    source = write_wav(tmp_path / "clip.wav", seconds=6.0)
    agent = AudioAgent("mic_01", bus, source, backend="dsp", realtime=False)
    agent.setup()
    assert agent.run(max_chunks=2)["chunks"] == 2


def test_emitted_events_are_json_serializable(collected_events):
    bus, events = collected_events
    payloads = []
    bus.subscribe(TOPIC_EVENTS, lambda t, p: payloads.append(json.loads(p)))
    agent = yamnet_agent(bus, {"Gunshot, gunfire": 0.9})
    agent._process_chunk(tone(SR), SR)
    assert payloads[0]["event_type"] == "audio_gunshot"
    assert payloads[0]["modality"] == "audio"
