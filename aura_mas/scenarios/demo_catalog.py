"""Stable presentation metadata for the prepared defence replay catalogue."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


def _entry(title: str, anomaly_key: str, sample_id: str, sample_label: str,
           description: str, dataset: str, attribution: str,
           detected: Iterable[str], camera_count: int,
           display_sources: Optional[Dict[str, str]] = None,
           tags: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    detected_types = list(detected)
    value: Dict[str, Any] = {
        "title": title, "anomaly_type": detected_types[0],
        "anomaly_key": anomaly_key, "sample_id": sample_id,
        "sample_label": sample_label, "site_context": "semi-closed site",
        "tags": list(tags or (anomaly_key, "prepared replay")),
        "camera_count": camera_count, "has_context": True,
        "detected_event_types": detected_types, "description": description,
        "dataset": dataset, "attribution": attribution,
    }
    if display_sources:
        value["display_sources"] = display_sources
    return value


CAVIAR = "EC-funded CAVIAR project / IST 2001 37540 (CC BY-SA)"
AIRTLAB = "Bianculli et al., Data in Brief 33 (2020), doi:10.1016/j.dib.2020.106587"
ABODA = "ABODA public research dataset (non-commercial academic evaluation)"
ESC50 = "Piczak, ESC-50 (2015), CC BY-NC 3.0; non-commercial thesis use"
FSD50K = "Fonseca et al., FSD50K (2022), per-clip Creative Commons; non-commercial thesis use"
URBANSOUND8K = "Salamon et al., UrbanSound8K (2014), CC BY-NC 4.0; non-commercial thesis use"


DEMO_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "perimeter_chain_01": _entry("Perimeter Intrusion", "perimeter_intrusion", "01", "Crossing paths 1", "A person crosses a restricted shop boundary observed by two synchronized cameras.", "CAVIAR — EnterExitCrossingPaths1", CAVIAR, ["intrusion"], 2),
    "perimeter_chain_02": _entry("Perimeter Intrusion", "perimeter_intrusion", "02", "Crossing paths 2", "A second synchronized crossing tests the same rule with different trajectories.", "CAVIAR — EnterExitCrossingPaths2", CAVIAR, ["intrusion"], 2),
    "perimeter_chain_03": _entry("Perimeter Intrusion", "perimeter_intrusion", "03", "Two enter shop", "Two people cross a restricted shop threshold in synchronized views.", "CAVIAR — TwoEnterShop1", CAVIAR, ["intrusion"], 2),
    "loitering_multizone_01": _entry("Multi-camera Loitering", "loitering", "01", "One waits 1", "A person remains outside a shop while a second view corroborates dwell.", "CAVIAR — OneShopOneWait1", CAVIAR, ["loitering"], 2),
    "loitering_multizone_02": _entry("Multi-camera Loitering", "loitering", "02", "One waits 2", "A second waiting sequence exercises dwell tracking amid passing groups.", "CAVIAR — OneShopOneWait2", CAVIAR, ["loitering"], 2),
    "loitering_multizone_03": _entry("Multi-camera Loitering", "loitering", "03", "Stops outside shop", "A person repeatedly stops outside a shop in synchronized views.", "CAVIAR — OneStopMoveNoEnter1", CAVIAR, ["loitering"], 2),
    "zone_occupancy_01": _entry("Zone Occupancy Violation", "zone_occupancy", "01", "Three pass shop 1", "Three pedestrians enter a zone whose safe occupancy is two.", "CAVIAR — ThreePastShop1", CAVIAR, ["zone_occupancy"], 2),
    "zone_occupancy_02": _entry("Zone Occupancy Violation", "zone_occupancy", "02", "Three pass shop 2", "A second three-person corridor sequence exceeds the declared limit.", "CAVIAR — ThreePastShop2", CAVIAR, ["zone_occupancy"], 2),
    "zone_occupancy_03": _entry("Zone Occupancy Violation", "zone_occupancy", "03", "Four-person corridor", "A four-person group violates the corridor occupancy policy.", "CAVIAR — OneStopMoveEnter2", CAVIAR, ["zone_occupancy"], 2),
    "wrong_direction_01": _entry("Wrong-direction Movement", "wrong_direction", "01", "Leave and re-enter 1", "A shopper reverses through a declared one-way boundary.", "CAVIAR — OneLeaveShopReenter1", CAVIAR, ["wrong_direction"], 2),
    "wrong_direction_02": _entry("Wrong-direction Movement", "wrong_direction", "02", "Leave and re-enter 2", "A second re-entry is measured against camera-specific flow axes.", "CAVIAR — OneLeaveShopReenter2", CAVIAR, ["wrong_direction"], 2),
    "wrong_direction_03": _entry("Wrong-direction Movement", "wrong_direction", "03", "Repeated shop movement", "Repeated entries and exits produce a distinct counter-flow window.", "CAVIAR — OneStopMoveEnter2", CAVIAR, ["wrong_direction"], 2),
    "abandoned_object_01": _entry("Abandoned Object", "abandoned_object", "01", "ABODA hallway 1", "A stationary unattended item persists after its owner leaves.", "ABODA — video1", ABODA, ["abandoned_object"], 1, {"cam_01": "data/clips_real/abandoned_object/video1_demo.mp4"}),
    "abandoned_object_02": _entry("Abandoned Object", "abandoned_object", "02", "ABODA hallway 3", "A second hallway sequence tests stationary-object persistence.", "ABODA — video3", ABODA, ["abandoned_object"], 1, {"cam_01": "data/clips_real/abandoned_object/video3_demo.mp4"}),
    "abandoned_object_03": _entry("Abandoned Object", "abandoned_object", "03", "CAVIAR left bag", "A person leaves a bag in a public indoor lobby.", "CAVIAR — LeftBag", CAVIAR, ["abandoned_object"], 1),
    "fight_01": _entry("Violence / Fighting", "violence", "01", "AIRTLab fight 1", "Semantic scoring identifies a staged physical fight.", "AIRTLab — violent/cam1/1", AIRTLAB, ["anomaly"], 1, {"cam_01": "data/clips_real/violence/violent_1_demo.mp4"}),
    "fight_02": _entry("Violence / Fighting", "violence", "02", "AIRTLab fight 10", "A distinct staged fight varies actors and motion.", "AIRTLab — violent/cam1/10", AIRTLAB, ["anomaly"], 1, {"cam_01": "data/clips_real/violence/violent_10_demo.mp4"}),
    "fight_03": _entry("Violence / Fighting", "violence", "03", "CAVIAR fight and chase", "Two people fight and then chase in an indoor lobby.", "CAVIAR — Fight_Chase", CAVIAR, ["anomaly"], 1),
    "person_down_01": _entry("Person Down", "person_down", "01", "Fall on floor", "Tracked posture remains horizontal after a staged fall.", "CAVIAR — Rest_FallOnFloor", CAVIAR, ["person_down"], 1),
    "person_down_02": _entry("Person Down", "person_down", "02", "Slump on floor", "A person slumps and remains down in the monitored zone.", "CAVIAR — Rest_SlumpOnFloor", CAVIAR, ["person_down"], 1),
    "person_down_03": _entry("Person Down", "person_down", "03", "Fight victim down", "A fight concludes with one tracked person remaining down.", "CAVIAR — Fight_OneManDown", CAVIAR, ["person_down"], 1),
    "rapid_movement_01": _entry("Rapid Movement", "rapid_movement", "01", "Run away 1", "A tracked person exceeds the declared indoor speed policy.", "CAVIAR — Fight_RunAway1", CAVIAR, ["rapid_movement"], 1),
    "rapid_movement_02": _entry("Rapid Movement", "rapid_movement", "02", "Run away 2", "A second running sequence tests normalized trajectory speed.", "CAVIAR — Fight_RunAway2", CAVIAR, ["rapid_movement"], 1),
    "rapid_movement_03": _entry("Rapid Movement", "rapid_movement", "03", "Fight chase", "A chase creates a sustained rapid-movement window.", "CAVIAR — Fight_Chase", CAVIAR, ["rapid_movement"], 1),
    "audio_glass_break_01": _entry("Glass Break", "glass_break", "01", "ESC-50 glass 1", "A glass-breaking transient is classified after a quiet baseline.", "ESC-50 — glass_breaking", ESC50, ["audio_glass_break"], 0),
    "audio_glass_break_02": _entry("Glass Break", "glass_break", "02", "ESC-50 glass 2", "A second fold supplies a distinct glass-breaking recording.", "ESC-50 — 2-141563-A-39", ESC50, ["audio_glass_break"], 0),
    "audio_glass_break_03": _entry("Glass Break", "glass_break", "03", "ESC-50 glass 3", "A third fold supplies a distinct glass-breaking recording.", "ESC-50 — 3-216280-A-39", ESC50, ["audio_glass_break"], 0),
    "audio_alarm_clock_01": _entry("Alarm / Siren", "alarm_siren", "01", "Clock alarm", "A clock alarm is classified as a site hazard.", "ESC-50 — clock_alarm", ESC50, ["audio_alarm"], 0),
    "audio_alarm_siren_01": _entry("Alarm / Siren", "alarm_siren", "02", "Siren 1", "A real siren recording is classified as an alarm.", "ESC-50 — siren", ESC50, ["audio_alarm"], 0),
    "audio_alarm_siren_02": _entry("Alarm / Siren", "alarm_siren", "03", "Siren 2", "A distinct siren recording tests class consistency.", "ESC-50 — 3-51376-A-42", ESC50, ["audio_alarm"], 0),
    "audio_distress_01": _entry("Distress Vocalization", "distress_vocalization", "01", "Woman scream", "A human scream is classified as an audible distress signal; no cause or victim is inferred.", "FSD50K — 9429", FSD50K, ["audio_scream"], 0, tags=["scream", "yell", "distress", "cry for help", "prepared replay"]),
    "audio_distress_02": _entry("Distress Vocalization", "distress_vocalization", "02", "Male scream", "A second contributor and recording condition tests audible-distress classification.", "FSD50K — 169628", FSD50K, ["audio_scream"], 0, tags=["scream", "yell", "distress", "cry for help", "prepared replay"]),
    "audio_distress_03": _entry("Distress Vocalization", "distress_vocalization", "03", "Fall-down scream", "A distinct staged scream tests the conservative audible-distress label.", "FSD50K — 48052", FSD50K, ["audio_scream"], 0, tags=["scream", "yell", "distress", "cry for help", "prepared replay"]),
    "audio_gunshot_01": _entry("Gunshot-like Impulse", "gunshot_impulse", "01", "Gunshot fold 6", "A sharp impulsive recording is classified by the declared gunshot audio class; visual weapon presence is not inferred.", "UrbanSound8K — 111048 fold 6", URBANSOUND8K, ["audio_gunshot"], 0, tags=["gunshot", "gun fire", "weapon discharge", "impulse", "prepared replay"]),
    "audio_gunshot_02": _entry("Gunshot-like Impulse", "gunshot_impulse", "02", "Gunshot fold 7", "A second official fold tests gunshot-class consistency under different acoustics.", "UrbanSound8K — 147317 fold 7", URBANSOUND8K, ["audio_gunshot"], 0, tags=["gunshot", "gun fire", "weapon discharge", "impulse", "prepared replay"]),
    "audio_gunshot_03": _entry("Gunshot-like Impulse", "gunshot_impulse", "03", "Gunshot fold 8", "A third official fold supplies an independent gunshot-like impulse example.", "UrbanSound8K — 131571 fold 8", URBANSOUND8K, ["audio_gunshot"], 0, tags=["gunshot", "gun fire", "weapon discharge", "impulse", "prepared replay"]),
}


def metadata_for(name: str) -> Dict[str, Any]:
    """Return a defensive copy so artifact generation cannot mutate the catalogue."""
    return dict(DEMO_SCENARIOS.get(name, {
        "title": name.replace("_", " ").title(), "anomaly_type": "unknown",
        "anomaly_key": "unknown", "sample_id": "00", "sample_label": name,
        "site_context": "semi-closed site", "tags": ["prepared replay"],
        "camera_count": 0, "has_context": False, "detected_event_types": [],
        "description": "Prepared AURA-MAS scenario replay.",
        "dataset": "See scenario manifest",
        "attribution": "See repository provenance manifest",
    }))
