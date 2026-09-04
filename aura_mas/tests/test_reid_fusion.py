import numpy as np
import pytest
from aura_mas.agents.camera_agent import ReIdFeatureExtractor
from aura_mas.agents.fusion_agent import FusionAgent, Hypothesis
from aura_mas.core.bus import Event, LocalBus


def test_reid_feature_extractor():
    # Synthetic person crop (e.g. 100x50 BGR image)
    crop = np.zeros((100, 50, 3), dtype=np.uint8)
    crop[0:30, :] = [255, 0, 0]    # Blue upper
    crop[30:70, :] = [0, 255, 0]   # Green torso
    crop[70:100, :] = [0, 0, 255]  # Red legs

    feat = ReIdFeatureExtractor.extract(crop)
    assert feat is not None
    assert isinstance(feat, list)
    assert len(feat) > 0
    # Check unit norm
    vec = np.array(feat)
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-3)


def test_fusion_contributing_types_and_reid_association():
    bus = LocalBus()
    agent = FusionAgent("fusion", bus)

    # Synthetic Re-ID feature vector
    feat_person_a = [0.1] * 96
    norm = np.linalg.norm(feat_person_a)
    feat_person_a = (np.array(feat_person_a) / norm).tolist()

    # Event 1 from Cam 1 in Zone A
    ev1 = Event(
        event_id="ev_01", sensor_id="cam_01", timestamp=10.0,
        event_type="intrusion", confidence=0.75, modality="video",
        zone="zone_A", extra={"reid_feat": feat_person_a}
    )
    # Event 2 from Mic 1 in Zone A (audio glass break)
    ev2 = Event(
        event_id="ev_02", sensor_id="mic_01", timestamp=11.0,
        event_type="audio_glass_break", confidence=0.65, modality="audio",
        zone="zone_A"
    )

    agent._on_event("site/events", ev1.to_json())
    agent._on_event("site/events", ev2.to_json())

    key = "security:zone_A"
    hyp = agent._hypotheses[key]

    # Verify composite event retention
    assert set(hyp.contributing_types) == {"intrusion", "audio_glass_break"}
    assert hyp.dominant_type() == "intrusion"
    assert hyp.global_entity_id is not None

    # Event 3 from Cam 2 in Zone B with same person appearance (Cross-camera matching)
    ev3 = Event(
        event_id="ev_03", sensor_id="cam_02", timestamp=15.0,
        event_type="loitering", confidence=0.70, modality="video",
        zone="zone_B", extra={"reid_feat": feat_person_a}
    )
    agent._on_event("site/events", ev3.to_json())

    key_b = "security:zone_B"
    hyp_b = agent._hypotheses[key_b]
    # Global entity ID should be shared across camera 1 and camera 2
    assert hyp_b.global_entity_id == hyp.global_entity_id
    assert agent.metrics["reid_matches"] >= 1
