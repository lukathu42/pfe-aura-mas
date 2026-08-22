"""Probe a clip with YOLO to find where people walk, to place a realistic
restricted zone polygon for the demo scenario manifest."""
import sys

from ultralytics import YOLO

from aura_mas.core.video import iter_frames, open_video


def main(path: str) -> None:
    m = YOLO("yolo11n.pt")
    cap, fps = open_video(path)
    feet = []
    for fid, frame in iter_frames(cap, 12, start=1):
        r = m.predict(frame, conf=0.4, verbose=False)[0]
        if r.boxes is None:
            continue
        for b in r.boxes:
            if r.names[int(b.cls)] == "person":
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                t = fid / fps
                feet.append((round(t, 1), int((x1 + x2) / 2), int(y2)))
    print("first/last person foot points (t, cx, cy):")
    for row in feet[:10]:
        print(row)
    print("...")
    for row in feet[-10:]:
        print(row)
    xs = [f[1] for f in feet]
    ys = [f[2] for f in feet]
    if xs:
        print(f"x range {min(xs)}-{max(xs)}, y range {min(ys)}-{max(ys)}, "
              f"t range {feet[0][0]}-{feet[-1][0]}s, n={len(feet)}")


if __name__ == "__main__":
    main(sys.argv[1])
