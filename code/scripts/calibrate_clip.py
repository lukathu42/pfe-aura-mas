"""CLIP zero-shot anomaly scorer calibration (W2.1/W2.2).

Runs ClipAnomalyScorer over a small labeled clip set (anomaly vs. normal),
computes frame-level AUC (rank-based, no sklearn dependency) and a threshold
sweep, and writes results/clip_anomaly_calibration.csv +
results/clip_anomaly_threshold_sweep.csv.

The original schedule named UCF-Crime as the anomaly source; substituted
here with the AIRTLab violence clips + existing normal CCTV-style clips
already in the repo (see data/clips_real/manifest.json for why UCF-Crime/
Avenue weren't practical to download in this environment). The evaluation
methodology (zero-shot CLIP frame scoring vs. text prompts, AUC, threshold
sweep) is unchanged from the plan.
"""
from __future__ import annotations

import argparse
from typing import List, Tuple

from aura_mas.agents.camera_agent import ClipAnomalyScorer
from aura_mas.core.utils import round_mean, write_csv
from aura_mas.core.video import iter_frames, open_video

ANOMALY_CLIPS = [
    "data/clips_real/violence/violent_1.mp4",
    "data/clips_real/violence/violent_10.mp4",
]
NORMAL_CLIPS = [
    "data/clips_real/violence/nonviolent_1.mp4",
    "data/clips/overview.mp4",
    "data/clips/street.mp4",
    "data/clips/people.mp4",
]


def sample_scores(scorer: ClipAnomalyScorer, path: str, every_n: int = 5
                   ) -> List[Tuple[float, str]]:
    cap, _ = open_video(path)
    return [scorer.score(frame) for _, frame in iter_frames(cap, every_n)]


def auc(pos: List[float], neg: List[float]) -> float:
    """Rank-based AUC (Mann-Whitney U), no sklearn dependency."""
    if not pos or not neg:
        return float("nan")
    combined = sorted((s, 0) for s in pos) + sorted((s, 1) for s in neg)
    combined.sort(key=lambda x: x[0])
    ranks: dict = {}
    i = 0
    n = len(combined)
    while i < n:
        j = i
        while j < n and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    rank_sum_pos = sum(ranks[k] for k in range(n) if combined[k][1] == 0)
    n_pos, n_neg = len(pos), len(neg)
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--every-n", type=int, default=5)
    ap.add_argument("--out-dir", default="results")
    args = ap.parse_args()

    scorer = ClipAnomalyScorer()

    per_clip_rows = []
    pos_scores: List[float] = []
    neg_scores: List[float] = []

    for label, clips, sink in (("anomaly", ANOMALY_CLIPS, pos_scores),
                               ("normal", NORMAL_CLIPS, neg_scores)):
        for path in clips:
            scores = sample_scores(scorer, path, args.every_n)
            vals = [s for s, _ in scores]
            sink.extend(vals)
            per_clip_rows.append({
                "clip": path, "label": label, "n_frames": len(vals),
                "mean_score": round_mean(vals, 4),
                "max_score": round(max(vals), 4) if vals else None,
                "top_predicted_label": max(scores, key=lambda x: x[0])[1] if scores else None,
            })

    calib_path = f"{args.out_dir}/clip_anomaly_calibration.csv"
    write_csv(per_clip_rows, calib_path)

    frame_auc = auc(pos_scores, neg_scores)

    sweep_rows = []
    for i in range(21):
        thr = i / 20.0
        tp = sum(1 for s in pos_scores if s >= thr)
        fn = len(pos_scores) - tp
        fp = sum(1 for s in neg_scores if s >= thr)
        tn = len(neg_scores) - fp
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        fpr = fp / (fp + tn) if (fp + tn) else None
        sweep_rows.append({
            "threshold": round(thr, 2), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 3) if precision is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "fpr": round(fpr, 3) if fpr is not None else None,
        })
    sweep_path = f"{args.out_dir}/clip_anomaly_threshold_sweep.csv"
    write_csv(sweep_rows, sweep_path)

    print(f"frame-level AUC = {frame_auc:.3f}  "
          f"(n_pos={len(pos_scores)}, n_neg={len(neg_scores)})")
    print(f"per-clip -> {calib_path}")
    print(f"threshold sweep -> {sweep_path}")
    print(f"default CameraAgent.anomaly_threshold=0.55 -> "
          f"{[r for r in sweep_rows if r['threshold'] == 0.55]}")


if __name__ == "__main__":
    main()
