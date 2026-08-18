"""Generate thesis result figures from results/summary.csv.

results/summary.csv now has one row per (scenario, mode, rep) combination
across the scenario pack, not a single scenario -- see
results/evaluation_campaign_notes.md and results/evaluation_campaign_v2_notes.md.
Figures 1-3 aggregate (mean +/- std, pooled across scenarios AND reps) per
mode; loitering_01 is excluded from the quantitative aggregate since it has
an intentionally empty ground truth (a true-negative probe, see
scenarios/loitering_01.json), which would otherwise drag every mode's mean
toward 0 for reasons unrelated to detection quality. Figure 4: vision-only
vs audio-visual F1, averaged over the audio-capable scenarios. Figure 5 is
new: DSP vs YAMNet audio backend ablation, per audio scenario (only
populated if results/run_*_dsp.json files exist from a --audio-backend dsp
campaign pass).

Error bars are the pooled sample stdev across every contributing run
(scenario x rep together, not a proper mixed-effects decomposition) --
adequate for a thesis-level "how noisy is this" figure, not a substitute for
results/summary_agg.csv's per-(scenario,mode) grouping if that finer
breakdown is needed.
"""
import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.environ.get("FIG_OUT", "results/figures")
os.makedirs(OUT, exist_ok=True)

with open("results/summary.csv") as f:
    all_rows = list(csv.DictReader(f))

# Exclude rep="" (no --rep passed) rows: those are single, ad-hoc runs from
# before the --rep campaign infrastructure existed (the v1 pre-YAMNet
# campaign, or a one-off manual run). Pooling them in with N real
# repetitions of a v2 run would silently corrupt every mean/std figure below
# -- same fix as aura_mas.eval.metrics.aggregate(), applied here too since
# this script pools summary.csv rows independently rather than reading
# summary_agg.csv.
all_rows = [r for r in all_rows if r.get("rep")]


def mean_std(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0.0, 0.0
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) >= 2 else 0.0
    return m, s

order = ["centralized", "mas-nocoord", "mas-rules", "mas-auction"]
labels = ["Centralized\nbaseline", "MAS\n(no coord.)", "MAS\n(rule sched.)",
          "MAS\n(auction)"]
colors = ["#888888", "#7fb3d5", "#5499c7", "#1f618d"]

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

# aggregate audio-visual (non-vision-only) rows, excluding the empty-GT probe
agg_rows = [r for r in all_rows if r["mode"] in order and r["scenario"] != "loitering_01"]
by_mode = defaultdict(list)
for r in agg_rows:
    by_mode[r["mode"]].append(r)
n_scenarios = len({r["scenario"] for r in agg_rows})
n_reps = len({r.get("rep") for r in agg_rows})

stats = {}
for mode in order:
    rs = by_mode[mode]
    stats[mode] = {
        "f1": mean_std([float(r["f1"]) for r in rs]),
        "precision": mean_std([float(r["precision"]) for r in rs]),
        "time_to_alert": mean_std([float(r["mean_time_to_alert_s"]) for r in rs
                                   if r["mean_time_to_alert_s"]]),
        "false_alerts_per_hour": mean_std([float(r["false_alerts_per_hour"]) for r in rs]),
        "coord_messages": mean_std([float(r["coord_messages"]) for r in rs]),
    }


def bar(ax, stat_pairs, title, ylabel, fmt="{:.2f}"):
    values = [v for v, _ in stat_pairs]
    errs = [s for _, s in stat_pairs]
    bars = ax.bar(labels, values, yerr=errs, capsize=4, ecolor="#444444",
                  color=colors, width=0.6)
    ax.set_title(title, fontsize=12)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    for b, v, s in zip(bars, values, errs):
        label = f"{fmt.format(v)}±{fmt.format(s)}" if s else fmt.format(v)
        ax.annotate(label, (b.get_x() + b.get_width() / 2, v + s),
                    ha="center", va="bottom", fontsize=9)


rep_note = f", n={n_reps} reps" if n_reps > 1 else ""

# Figure 1: detection quality -------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
bar(axes[0], [stats[m]["f1"] for m in order], "Mean event-level F1", "F1")
bar(axes[1], [stats[m]["precision"] for m in order], "Mean precision", "Precision")
fig.suptitle(f"Detection quality by architecture (mean over {n_scenarios} scenarios{rep_note})")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_detection_quality.png", bbox_inches="tight")

# Figure 2: system responsiveness --------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
bar(axes[0], [stats[m]["time_to_alert"] for m in order],
    "Mean time-to-alert", "seconds", "{:.1f}s")
bar(axes[1], [stats[m]["false_alerts_per_hour"] for m in order],
    "Mean false alerts per hour", "alerts/h", "{:.0f}")
fig.suptitle(f"System responsiveness and operator load (mean over {n_scenarios} scenarios{rep_note})")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_system_metrics.png", bbox_inches="tight")

# Figure 3: coordination overhead ---------------------------------------------
fig, ax = plt.subplots(figsize=(6, 4))
bar(ax, [stats[m]["coord_messages"] for m in order],
    "Mean coordination message overhead", "messages", "{:.1f}")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_coordination_overhead.png", bbox_inches="tight")

# Figure 4: vision-only vs audio-visual ablation -------------------------------
audio_scenarios = {"intrusion_01", "audio_glass_break_01",
                   "combined_audio_video_01", "demo_site_01",
                   "audio_alarm_siren_01", "audio_alarm_clock_01"}
vis_f1 = {m: mean_std([float(r["f1"]) for r in all_rows
                       if r["mode"] == f"{m}-visiononly" and r["scenario"] in audio_scenarios])
         for m in order}
av_f1 = {m: mean_std([float(r["f1"]) for r in all_rows
                      if r["mode"] == m and r["audio_backend"] in ("auto", "")
                      and r["scenario"] in audio_scenarios])
        for m in order}

fig, ax = plt.subplots(figsize=(8, 4.5))
x = range(len(order))
w = 0.35
ax.bar([i - w / 2 for i in x], [vis_f1[m][0] for m in order],
      yerr=[vis_f1[m][1] for m in order], capsize=4, ecolor="#444444",
      width=w, label="Vision-only", color="#aab7b8")
ax.bar([i + w / 2 for i in x], [av_f1[m][0] for m in order],
      yerr=[av_f1[m][1] for m in order], capsize=4, ecolor="#444444",
      width=w, label="Audio-visual", color="#1f618d")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.set_ylabel("Mean F1")
ax.set_title(f"Vision-only vs. audio-visual F1 (mean over {len(audio_scenarios)} scenarios{rep_note})")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_modality_ablation.png", bbox_inches="tight")

# Figure 5: DSP vs YAMNet audio backend ablation -------------------------------
dsp_rows = [r for r in all_rows if r.get("audio_backend") == "dsp"
           and r["scenario"] in audio_scenarios]
if dsp_rows:
    dsp_scenarios = sorted({r["scenario"] for r in dsp_rows})
    dsp_f1 = {s: mean_std([float(r["f1"]) for r in dsp_rows if r["scenario"] == s])
             for s in dsp_scenarios}
    yamnet_f1 = {s: mean_std([float(r["f1"]) for r in all_rows
                              if r["scenario"] == s and r["mode"] in order
                              and r.get("audio_backend") in ("auto", "")])
                for s in dsp_scenarios}

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(dsp_scenarios))
    w = 0.35
    ax.bar([i - w / 2 for i in x], [dsp_f1[s][0] for s in dsp_scenarios],
          yerr=[dsp_f1[s][1] for s in dsp_scenarios], capsize=4, ecolor="#444444",
          width=w, label="DSP fallback", color="#aab7b8")
    ax.bar([i + w / 2 for i in x], [yamnet_f1[s][0] for s in dsp_scenarios],
          yerr=[yamnet_f1[s][1] for s in dsp_scenarios], capsize=4, ecolor="#444444",
          width=w, label="YAMNet", color="#1f618d")
    ax.set_xticks(list(x))
    ax.set_xticklabels(dsp_scenarios, rotation=20, ha="right")
    ax.set_ylabel("Mean F1 (pooled across coordination modes)")
    ax.set_title("Audio backend ablation: DSP fallback vs. YAMNet")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_audio_backend_ablation.png", bbox_inches="tight")
else:
    print("Figure 5 skipped: no --audio-backend dsp runs found in results/summary.csv")

print("figures written to", OUT)
