import numpy as np
import soundfile as sf

from aura_mas.agents.audio_agent import AudioAgent


class _Bus:
    def publish(self, *_args, **_kwargs):
        pass

    def subscribe(self, *_args, **_kwargs):
        pass


def test_audio_agent_processes_trailing_partial_chunk(tmp_path, monkeypatch):
    path = tmp_path / "partial.wav"
    sf.write(path, np.zeros(24000, dtype=np.float32), 16000)
    agent = AudioAgent("mic", _Bus(), str(path), backend="dsp", realtime=False)
    calls = []
    monkeypatch.setattr(agent, "_process_chunk",
                        lambda chunk, _sr, **kwargs: calls.append(
                            (len(chunk), kwargs["scene_time_seconds"])))
    agent.run()
    assert calls == [(16000, 0.0), (16000, 1.0)]
