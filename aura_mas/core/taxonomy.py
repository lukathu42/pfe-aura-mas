"""Single source of truth for event-type -> incident-family mapping.

Previously duplicated between `fusion_agent.py` and `eval/metrics.py`, and the
two copies had drifted out of sync: `metrics.FAMILY` was missing
`audio_explosion` and `audio_breaking`, so any alert of those types fell
through to its own event-type-as-family and could only ever score as a false
positive, even though FusionAgent already treated them as corroborating
evidence. See `results/methodology_changes.md` for the measured effect of
unifying them.
"""
from __future__ import annotations

# events considered mutually corroborating (same incident family)
EVENT_FAMILIES = {
    "intrusion": "security", "loitering": "security",
    "abandoned_object": "security", "anomaly": "violence_or_hazard",
    "audio_scream": "violence_or_hazard", "audio_glass_break": "security",
    "audio_gunshot": "violence_or_hazard", "audio_alarm": "hazard",
    "audio_explosion": "hazard", "audio_breaking": "security",
    "audio_anomaly": "violence_or_hazard",
    # `zone_occupancy` is deliberately NOT `security`: FusionAgent keys
    # hypotheses on (family, zone), so filing overcrowding under `security`
    # would merge it with an `intrusion` in the same zone and let
    # `dominant_type()` discard whichever scored lower.
    "zone_occupancy": "hazard", "wrong_direction": "security",
    "person_down": "violence_or_hazard", "rapid_movement": "security",
}
