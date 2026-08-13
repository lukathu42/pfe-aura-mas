"""Generate thesis result figures from results/summary.csv."""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.environ.get("FIG_OUT", "results/figures")
os.makedirs(OUT, exist_ok=True)

with open("results/summary.csv") as f:
    rows = list(csv.DictReader(f))

order = ["centralized", "mas-nocoord", "mas-rules", "mas-auction"]
rows.sort(key=lambda r: order.index(r["mode"]))
modes = [r["mode"] for r in rows]
labels = ["Centralized\nbaseline", "MAS\n(no coord.)", "MAS\n(rule sched.)",
          "MAS\n(auction)"]
colors = ["#888888", "#7fb3d5", "#5499c7", "#1f618d"]

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})


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
bar(axes[0], [float(r["f1"]) for r in rows], "Event-level F1", "F1")
bar(axes[1], [float(r["precision"]) for r in rows], "Precision", "Precision")
fig.suptitle("Detection quality by architecture (scenario demo_site_01)")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_detection_quality.png", bbox_inches="tight")

# Figure 2: system responsiveness --------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
bar(axes[0], [float(r["mean_time_to_alert_s"]) for r in rows],
    "Mean time-to-alert", "seconds", "{:.1f}s")
bar(axes[1], [float(r["false_alerts_per_hour"]) for r in rows],
    "False alerts per hour", "alerts/h", "{:.0f}")
fig.suptitle("System responsiveness and operator load")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_system_metrics.png", bbox_inches="tight")

# Figure 3: coordination overhead ---------------------------------------------
fig, ax = plt.subplots(figsize=(6, 4))
bar(ax, [int(r["coord_messages"]) for r in rows],
    "Coordination message overhead", "messages", "{:.0f}")
fig.tight_layout()
fig.savefig(f"{OUT}/fig_coordination_overhead.png", bbox_inches="tight")

print("figures written to", OUT)
