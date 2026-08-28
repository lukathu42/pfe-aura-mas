"""Create the missing versioned scenario manifests for the 36-replay catalogue.

This command never overwrites an existing calibrated manifest unless --force
is supplied. Generated time windows are candidate windows from official
annotations/media inspection and must still pass validate_demo_catalog after
real pipeline execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

FULL = [[0, 0], [384, 0], [384, 288], [0, 288]]


def camera(sensor_id: str, source: str, zones: list[dict[str, Any]], **options: Any) -> dict[str, Any]:
    return {"type": "camera", "id": sensor_id, "source": source, **options, "zones": zones}


def paired(name: str, stems: tuple[str, str], duration: int, event: str,
           zone: dict[str, Any], window: tuple[float, float], **options: Any) -> dict[str, Any]:
    zone_name = zone["name"]
    return {"name": name, "duration_seconds": duration,
            "fov_overlap": {zone_name: {"cam_01": 0.9, "cam_02": 0.9}},
            "sensors": [
                camera("cam_01", f"data/clips_real/caviar/{stems[0]}.mp4", [zone], **options),
                camera("cam_02", f"data/clips_real/caviar/{stems[1]}.mp4", [zone],
                       detection_conf=0.15, **options),
            ], "ground_truth": [{"event_type": event, "zone": zone_name,
                                  "t_start": window[0], "t_end": window[1]}],
            "notes": "Official synchronized CAVIAR views and XML annotations; candidate thresholds are accepted only after an exact pipeline probe produces the declared event."}


def audio(name: str, source: str, event: str, end: float, notes: str) -> dict[str, Any]:
    return {"name": name, "duration_seconds": int(end + 2),
            "sensors": [{"type": "audio", "id": "mic_01", "source": source}],
            "ground_truth": [{"event_type": event, "zone": None,
                              "t_start": 15.0, "t_end": end}], "notes": notes}


def manifests() -> Dict[str, Dict[str, Any]]:
    entry = {"name": "shop_forecourt", "type": "entry", "polygon": FULL}
    occupancy = {"name": "retail_corridor", "type": "entry", "polygon": FULL,
                 "max_occupancy": 2}
    values: Dict[str, Dict[str, Any]] = {
        "perimeter_chain_02": paired("perimeter_chain_02", ("EnterExitCrossingPaths2cor", "EnterExitCrossingPaths2front"), 20, "intrusion", {"name": "restricted_shop_boundary", "type": "restricted", "polygon": FULL}, (1.0, 19.0), loiter_seconds=999.0),
        "perimeter_chain_03": paired("perimeter_chain_03", ("TwoEnterShop1cor", "TwoEnterShop1front"), 66, "intrusion", {"name": "restricted_shop_boundary", "type": "restricted", "polygon": FULL}, (1.0, 65.0), loiter_seconds=999.0),
        "loitering_multizone_02": paired("loitering_multizone_02", ("OneShopOneWait2cor", "OneShopOneWait2front"), 59, "loitering", entry, (12.0, 58.0), loiter_seconds=8.0),
        "loitering_multizone_03": paired("loitering_multizone_03", ("OneStopMoveNoEnter1cor", "OneStopMoveNoEnter1front"), 67, "loitering", entry, (12.0, 66.0), loiter_seconds=8.0),
        "zone_occupancy_02": paired("zone_occupancy_02", ("ThreePastShop2cor", "ThreePastShop2front"), 61, "zone_occupancy", occupancy, (1.0, 60.0), loiter_seconds=999.0),
        "zone_occupancy_03": paired("zone_occupancy_03", ("OneStopMoveEnter2cor", "OneStopMoveEnter2front"), 90, "zone_occupancy", occupancy, (1.0, 89.0), loiter_seconds=999.0),
        "wrong_direction_02": paired("wrong_direction_02", ("OneLeaveShopReenter2cor", "OneLeaveShopReenter2front"), 23, "wrong_direction", {**entry, "name": "one_way_shop_exit", "flow_direction": [-1, 0]}, (1.0, 22.0), loiter_seconds=999.0, min_flow_px=30.0),
        "wrong_direction_03": paired("wrong_direction_03", ("OneStopMoveEnter2cor", "OneStopMoveEnter2front"), 90, "wrong_direction", {**entry, "name": "one_way_shop_exit", "flow_direction": [-1, 0]}, (1.0, 89.0), loiter_seconds=999.0, min_flow_px=30.0),
    }
    # Perspective reverses the horizontal image axis in this synchronized
    # front view; its projected displacement is also shorter.
    values["wrong_direction_02"]["sensors"][1]["zones"][0]["flow_direction"] = [1, 0]
    values["wrong_direction_02"]["sensors"][1]["min_flow_px"] = 10.0
    values["wrong_direction_02"]["verification_gray_zone"] = [0.35, 0.8]
    singles = {
        "abandoned_object_02": ("data/clips_real/abandoned_object/video3.avi", 88, "abandoned_object", {"abandoned_seconds": 0.5, "detection_conf": 0.15}, (10.0, 87.0)),
        "abandoned_object_03": ("data/clips_real/caviar/LeftBag.mp4", 58, "abandoned_object", {"abandoned_seconds": 0.5, "detection_conf": 0.15}, (5.0, 57.0)),
        "fight_02": ("data/clips_real/violence/violent_10.mp4", 7, "anomaly", {"enable_clip": True}, (0.0, 6.2)),
        "fight_03": ("data/clips_real/caviar/Fight_Chase.mp4", 18, "anomaly", {"enable_clip": True}, (0.0, 17.5)),
        "person_down_01": ("data/clips_real/caviar/Rest_FallOnFloor.mp4", 41, "person_down", {"person_down_seconds": 0.6, "detection_conf": 0.15}, (1.0, 40.0)),
        "person_down_02": ("data/clips_real/caviar/Rest_SlumpOnFloor.mp4", 37, "person_down", {"person_down_seconds": 0.6, "detection_conf": 0.15}, (1.0, 36.0)),
        "person_down_03": ("data/clips_real/caviar/Fight_OneManDown.mp4", 39, "person_down", {"person_down_seconds": 0.6, "detection_conf": 0.15}, (1.0, 38.0)),
        "rapid_movement_01": ("data/clips_real/caviar/Fight_RunAway1.mp4", 23, "rapid_movement", {"rapid_window_seconds": 1.2, "rapid_min_duration": 0.0, "detection_conf": 0.15}, (1.0, 22.0)),
        "rapid_movement_02": ("data/clips_real/caviar/Fight_RunAway2.mp4", 23, "rapid_movement", {"rapid_window_seconds": 1.2, "rapid_min_duration": 0.0, "detection_conf": 0.15}, (1.0, 22.0)),
        "rapid_movement_03": ("data/clips_real/caviar/Fight_Chase.mp4", 18, "rapid_movement", {"rapid_window_seconds": 1.2, "rapid_min_duration": 0.0, "detection_conf": 0.15}, (1.0, 17.0)),
    }
    for name, (source, duration, event, options, window) in singles.items():
        zone = {"name": "monitored_area", "type": "entry", "polygon": FULL}
        if event == "person_down": zone["down_aspect_ratio"] = 1.05
        if event == "rapid_movement": zone["max_speed_zone_lengths_per_second"] = 0.02
        values[name] = {"name": name, "duration_seconds": duration,
                        "sensors": [camera("cam_01", source, [zone] if event in {"person_down", "rapid_movement"} else [], **options)],
                        "ground_truth": [{"event_type": event, "zone": "monitored_area" if event in {"person_down", "rapid_movement"} else None,
                                          "t_start": window[0], "t_end": window[1]}],
                        "notes": "Real research footage; declared detector settings and event window must be confirmed by the exact pipeline before defence use."}
    values.update({
        "audio_glass_break_02": audio("audio_glass_break_02", "data/clips_real/audio/2-141563-A-39_with_baseline.wav", "audio_glass_break", 20.0, "ESC-50 fold 2, CC BY-NC 3.0; selected after exact YAMNet probe; 15-second measured baseline prefix."),
        "audio_glass_break_03": audio("audio_glass_break_03", "data/clips_real/audio/3-216280-A-39_with_baseline.wav", "audio_glass_break", 20.0, "ESC-50 fold 3, CC BY-NC 3.0; selected after exact YAMNet probe; 15-second measured baseline prefix."),
        "audio_alarm_siren_02": audio("audio_alarm_siren_02", "data/clips_real/audio/3-51376-A-42_with_baseline.wav", "audio_alarm", 20.0, "ESC-50 fold 3 siren, CC BY-NC 3.0; selected after exact YAMNet probe; 15-second measured baseline prefix."),
        "audio_distress_01": audio("audio_distress_01", "data/clips_real/audio/distress/fsd50k_9429_with_baseline.wav", "audio_scream", 20.0, "FSD50K 9429 by thanvannispen, CC BY 3.0; observable scream only, no cause inferred."),
        "audio_distress_02": audio("audio_distress_02", "data/clips_real/audio/distress/fsd50k_169628_with_baseline.wav", "audio_scream", 25.0, "FSD50K 169628 by Dinsfire, CC0; observable class scream only."),
        "audio_distress_03": audio("audio_distress_03", "data/clips_real/audio/distress/fsd50k_48052_with_baseline.wav", "audio_scream", 23.9, "FSD50K 48052 by JohnnyDiamond, CC BY 3.0; observable scream only."),
        "audio_gunshot_01": audio("audio_gunshot_01", "data/clips_real/audio/gunshot/urbansound8k_fold6_111048-6-0-0_with_baseline.wav", "audio_gunshot", 16.6, "UrbanSound8K fold 6 / Freesound 111048 by GaryQ, CC0; audio-class label only."),
        "audio_gunshot_02": audio("audio_gunshot_02", "data/clips_real/audio/gunshot/urbansound8k_fold7_147317-6-0-0_with_baseline.wav", "audio_gunshot", 16.4, "UrbanSound8K fold 7 / Freesound 147317 by udikagan, CC0; audio-class label only."),
        "audio_gunshot_03": audio("audio_gunshot_03", "data/clips_real/audio/gunshot/urbansound8k_fold8_131571-6-0-0_with_baseline.wav", "audio_gunshot", 17.0, "UrbanSound8K fold 8 / Freesound 131571 by deleted_user_389799, CC BY 3.0; audio-class label only."),
    })
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("scenarios"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, value in manifests().items():
        path = args.out / f"{name}.json"
        if path.exists() and not args.force:
            continue
        path.write_text(json.dumps(value, indent=2) + "\n")
        print(path)


if __name__ == "__main__":
    main()
