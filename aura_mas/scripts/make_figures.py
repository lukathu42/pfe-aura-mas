"""Generate thesis result figures from results/summary.csv.

results/summary.csv now has one row per (scenario, mode) pair across the
6-scenario pack, not a single scenario -- see results/evaluation_campaign_notes.md.
Figures 1-3 aggregate (mean) across scenarios per mode; loitering_01 is
excluded from the quantitative aggregate since it has an intentionally empty
ground truth (a true-negative probe, see scenarios/loitering_01.json), which
would otherwise drag every mode's mean toward 0 for reasons unrelated to
detection quality. Figure 4 is new: vision-only vs audio-visual F1, averaged
over the 4 scenarios that carry an audio sensor.
"""
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.environ.get("FIG_OUT", "results/figures")
os.makedirs(OUT, exist_ok=True)

with open("results/summary.csv") as f:
    all_rows = list(csv.DictReader(f))

order = ["centralized", "mas-nocoord", "mas-rules", "mas-auction"]
labels = ["Centralized\nbaseline", "MAS\n(no coord.)", "MAS\n(rule sched.)",
          "MAS\n(auction)"]
colors = ["#888888", "#7fb3d5", "#5499c7", "#1f618d"]

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


def mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


# aggregate audio-visual (non-vision-only) rows, excluding the empty-GT probe
agg_rows = [r for r in all_rows if r["mode"] in order and r["scenario"] != "loitering_01"]
by_mode = defaultdict(list)
for r in agg_rows:
    by_mode[r["mode"]].append(r)
n_scenarios = len({r["scenario"] for r in agg_rows})

means = {}
for mode in order:
    rs = by_mode[mode]
    means[mode] = {
        "f1": mean([float(r["f1"]) for r in rs]),
        "precision": mean([float(r["precision"]) for r in rs]),
        "time_to_alert": mean([float(r["mean_time_to_alert_s"]) for r in rs
                               if r["mean_time_to_alert_s"]]),
        "false_alerts_per_hour": mean([float(r["false_alerts_per_hour"]) for r in rs]),
        "coord_messages": mean([float(r["coord_messages"]) for r in rs]),
    }


def bar(ax, values, title, ylabel, fmt="{:.2f}"):
    bars = ax.bar(labels, values, color=colors, width=0.6)
    ax.set_title(title, fontsize=12)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    for b, v in zip(bars, values):
        ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, v),
                    ha="center", va="bottom", fontsize=10)


# Figure 1: detection quality -------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
bar(axes[0], [means[m]["f1"] for m in order], "Mean event-level F1", "F1")
bar(axes[1], [means[m]["precision"] for m in order], "Mean precision", "Precision")
fig.suptitle(f"Detection quality by architecture (mean over {n_scenarios} scenarios)")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_detection_quality.png", bbox_inches="tight")

# Figure 2: system responsiveness --------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
bar(axes[0], [means[m]["time_to_alert"] for m in order],
    "Mean time-to-alert", "seconds", "{:.1f}s")
bar(axes[1], [means[m]["false_alerts_per_hour"] for m in order],
    "Mean false alerts per hour", "alerts/h", "{:.0f}")
fig.suptitle(f"System responsiveness and operator load (mean over {n_scenarios} scenarios)")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_system_metrics.png", bbox_inches="tight")

# Figure 3: coordination overhead ---------------------------------------------
fig, ax = plt.subplots(figsize=(6, 4))
bar(ax, [means[m]["coord_messages"] for m in order],
    "Mean coordination message overhead", "messages", "{:.1f}")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_coordination_overhead.png", bbox_inches="tight")

# Figure 4: vision-only vs audio-visual ablation -------------------------------
audio_scenarios = {"intrusion_01", "audio_glass_break_01",
                   "combined_audio_video_01", "demo_site_01"}
vis_f1 = {m: mean([float(r["f1"]) for r in all_rows
                   if r["mode"] == f"{m}-visiononly" and r["scenario"] in audio_scenarios])
         for m in order}
av_f1 = {m: mean([float(r["f1"]) for r in all_rows
                  if r["mode"] == m and r["scenario"] in audio_scenarios])
        for m in order}

fig, ax = plt.subplots(figsize=(8, 4.5))
x = range(len(order))
w = 0.35
ax.bar([i - w / 2 for i in x], [vis_f1[m] for m in order], width=w,
      label="Vision-only", color="#aab7b8")
ax.bar([i + w / 2 for i in x], [av_f1[m] for m in order], width=w,
      label="Audio-visual", color="#1f618d")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Mean F1")
ax.set_title(f"Vision-only vs. audio-visual F1 (mean over {len(audio_scenarios)} scenarios)")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_modality_ablation.png", bbox_inches="tight")

print("figures written to", OUT)
