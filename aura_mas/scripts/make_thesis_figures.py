"""Thesis figures for the inferential-statistics layer of the Results chapter.

Complements `aura_mas/scripts/make_figures.py` (which draws the per-mode
aggregate bars already cited by chapter 6) rather than replacing it. Every
number is read from `results/summary.csv` / `results/thesis_stats.json`; nothing
is hard-coded. Run `thesis_stats.py` first.

House style is deliberately identical to `make_figures.py` -- same palette,
font size, dpi, and hidden top/right spines -- so old and new figures do not
look like they came from two different documents.

Figures:
  1 fig_per_scenario_f1        heatmap, 9 scenarios x 4 modes, the table the
                               chapter previously reduced to a single scenario
  2 fig_paired_forest          paired mean differences with bootstrap CIs and
                               Holm-adjusted p; the visual form of "no
                               comparison survives multiplicity correction"
  3 fig_tta_per_scenario       time-to-alert by scenario, showing that the
                               large demo_site_01 latency gap does not recur
                               elsewhere
  4 fig_fa_per_hour_degeneracy false-alerts/hour against run length, showing
                               the metric is dominated by the denominator
  5 fig_power_curve            detectable effect size vs sample size, marking
                               where this campaign actually sits
  6 fig_mode_ci               per-mode mean F1 with bootstrap CIs, overlap visible
"""

from __future__ import annotations

import csv
import json
import os
import statistics as st
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.environ.get("FIG_OUT", "results/figures")
STATS = os.environ.get("STATS_JSON", "results/thesis_stats.json")
SUMMARY = os.environ.get("SUMMARY_CSV", "results/summary.csv")
os.makedirs(OUT, exist_ok=True)

MODES = ["centralized", "mas-nocoord", "mas-rules", "mas-auction"]
LABELS = [
    "Centralized\nbaseline",
    "MAS\n(no coord.)",
    "MAS\n(rule sched.)",
    "MAS\n(auction)",
]
SHORT = ["Centralized", "MAS-nocoord", "MAS-rules", "MAS-auction"]
COLORS = ["#888888", "#7fb3d5", "#5499c7", "#1f618d"]
PROBE = "loitering_01"

plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

with open(STATS) as fh:
    S = json.load(fh)
with open(SUMMARY) as fh:
    ROWS = [
        r
        for r in csv.DictReader(fh)
        if r.get("rep")
        and r.get("audio_backend") in ("auto", "")
        and r["mode"] in MODES
    ]


def scen_label(s: str) -> str:
    return s + (" †" if s == PROBE else "")


# --- Figure 1: per-scenario F1 heatmap ---------------------------------------
grid = S["f1"]["per_scenario"]
scens = sorted(grid)
mat = np.array(
    [
        [
            grid[s][m]["mean"] if grid[s][m]["mean"] is not None else np.nan
            for m in MODES
        ]
        for s in scens
    ]
)

fig, ax = plt.subplots(figsize=(7.4, 5.2))
im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(MODES)))
ax.set_xticklabels(SHORT, rotation=18, ha="right")
ax.set_yticks(range(len(scens)))
ax.set_yticklabels([scen_label(s) for s in scens], fontsize=9.5)
for i in range(len(scens)):
    for j in range(len(MODES)):
        v = mat[i, j]
        if np.isnan(v):
            ax.text(j, i, "--", ha="center", va="center", fontsize=9, color="#666666")
            continue
        sd = grid[scens[i]][MODES[j]]["sd"]
        txt = f"{v:.2f}" + (f"\n±{sd:.2f}" if sd else "")
        ax.text(
            j,
            i,
            txt,
            ha="center",
            va="center",
            fontsize=8.5,
            color="white" if v > 0.55 else "#1a1a1a",
        )
row_best = np.nanmax(mat, axis=1)
for i, b in enumerate(row_best):
    for j in range(len(MODES)):
        if not np.isnan(mat[i, j]) and abs(mat[i, j] - b) < 1e-9 and b > 0:
            ax.add_patch(
                plt.Rectangle(
                    (j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="#c0392b", lw=2.0
                )
            )
ax.set_title(
    "Event-level F1 per scenario and architecture\n"
    "(mean±sd over N=5 repetitions; red outline = best in row)",
    fontsize=11,
)
fig.colorbar(im, ax=ax, label="Mean F1", fraction=0.046, pad=0.03)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_per_scenario_f1.png", bbox_inches="tight")
plt.close(fig)

# --- Figure 2: paired forest plot --------------------------------------------
pw = sorted(S["f1"]["pairwise"], key=lambda r: r["mean_diff"])
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ys = range(len(pw))
for y, r in zip(ys, pw):
    sig = r["significant_holm"]
    col = "#c0392b" if sig else "#1f618d"
    ax.plot([r["ci_lo"], r["ci_hi"]], [y, y], color=col, lw=2.2, solid_capstyle="round")
    ax.plot(r["mean_diff"], y, "o", color=col, ms=7, zorder=3)
ax.axvline(0.0, color="#444444", ls="--", lw=1.2, zorder=1)
ax.set_yticks(list(ys))
ax.set_yticklabels([f"{r['mode_a']}  −  {r['mode_b']}" for r in pw], fontsize=9.5)
ax.set_xlabel("Paired difference in mean F1  (95% bootstrap CI)")
ax.set_title(
    "Pairwise architecture comparisons, paired on (scenario, repetition)\n"
    "No comparison remains significant after Holm–Bonferroni correction",
    fontsize=11,
)
for y, r in zip(ys, pw):
    ax.annotate(
        f"$p$={r['p_raw']:.3f}, $p_{{Holm}}$={r['p_holm']:.3f}, δ={r['cliffs_delta']:+.2f}",
        (max(r["ci_hi"], 0.0) + 0.012, y),
        va="center",
        fontsize=8.2,
        color="#333333",
    )
ax.set_xlim(min(r["ci_lo"] for r in pw) - 0.05, max(r["ci_hi"] for r in pw) + 0.30)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_paired_forest.png", bbox_inches="tight")
plt.close(fig)

# --- Figure 3: TTA per scenario ----------------------------------------------
# metrics.py writes mean_time_to_alert_s=None when a mode produced no true
# positive at all, and 0.0 when it alerted at or before ground-truth onset
# (the value is clamped at 0). Those are different facts and must not both
# render as an empty slot: "no TP" is annotated n/a, 0.0 stays a real bar.
tta = defaultdict(lambda: defaultdict(list))
for r in ROWS:
    raw = r.get("mean_time_to_alert_s")
    if raw not in (None, ""):
        tta[r["scenario"]][r["mode"]].append(float(raw))
tscens = [s for s in sorted(tta) if any(tta[s][m] for m in MODES)]
fig, ax = plt.subplots(figsize=(10, 4.8))
x = np.arange(len(tscens))
w = 0.2
for k, (m, c) in enumerate(zip(MODES, COLORS)):
    means, err_lo, err_hi = [], [], []
    for s in tscens:
        vals = tta[s][m]
        if not vals:
            means.append(np.nan)
            err_lo.append(0.0)
            err_hi.append(0.0)
            continue
        mu = st.mean(vals)
        sd = st.stdev(vals) if len(vals) > 1 else 0.0
        means.append(mu)
        # latency cannot be negative: clip the lower whisker at 0 rather than
        # drawing a physically impossible bound
        err_lo.append(min(sd, mu))
        err_hi.append(sd)
    pos = x + (k - 1.5) * w
    ax.bar(
        pos,
        means,
        yerr=[err_lo, err_hi],
        capsize=3,
        ecolor="#555555",
        width=w,
        label=SHORT[k],
        color=c,
    )
    for xi, s in zip(pos, tscens):
        if not tta[s][m]:
            ax.annotate(
                "n/a",
                (xi, 0.35),
                ha="center",
                va="bottom",
                fontsize=7,
                color="#999999",
                rotation=90,
            )
ax.set_xticks(x)
ax.set_xticklabels([s.replace("_", "\n") for s in tscens], fontsize=8.5)
ax.set_ylabel("Mean time-to-alert (s)")
ax.set_ylim(0, None)
ax.set_title(
    "Time-to-alert by scenario: the large centralized/MAS gap is specific to "
    "demo_site_01",
    fontsize=11,
)
ax.legend(frameon=False, ncol=4, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
i_demo = tscens.index("demo_site_01") if "demo_site_01" in tscens else None
if i_demo is not None:
    ax.axvspan(i_demo - 0.45, i_demo + 0.45, color="#c0392b", alpha=0.08, zorder=0)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_tta_per_scenario.png", bbox_inches="tight")
plt.close(fig)

# --- Figure 4: FA/h degeneracy ----------------------------------------------
deg = S["fa_per_hour_degeneracy"]["rows"]
fig, ax = plt.subplots(figsize=(7.6, 4.4))
fps = sorted({d["fp"] for d in deg})
cmap = plt.get_cmap("viridis", max(len(fps), 2))
for i, fp in enumerate(fps):
    pts = [(d["wall_seconds"], d["fa_per_hour"]) for d in deg if d["fp"] == fp]
    if not pts:
        continue
    ax.scatter(
        [p[0] for p in pts],
        [p[1] for p in pts],
        s=26,
        alpha=0.75,
        color=cmap(i),
        label=f"{fp} false positive" + ("s" if fp != 1 else ""),
    )
ws = np.linspace(
    min(d["wall_seconds"] for d in deg), max(d["wall_seconds"] for d in deg), 200
)
for fp in fps:
    if fp:
        ax.plot(ws, fp * 3600.0 / ws, color="#999999", lw=0.9, ls=":", zorder=0)
ax.set_xlabel("Run wall-clock duration (s)")
ax.set_ylabel("False alerts per hour")
ax.set_title(
    "false_alerts_per_hour is governed by run length, not alert quality\n"
    "(dotted lines: exact $fp\\times3600/\\mathrm{duration}$ hyperbolae)",
    fontsize=10.5,
)
ax.set_ylim(-20, max(d["fa_per_hour"] for d in deg) * 1.12)
ax.legend(frameon=False, fontsize=8.6)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_fa_per_hour_degeneracy.png", bbox_inches="tight")
plt.close(fig)

# --- Figure 5: power curve ---------------------------------------------------
za, zb = 1.959964, 0.841621
dz = np.linspace(0.15, 1.2, 300)
n_req = ((za + zb) ** 2) / dz**2
fig, ax = plt.subplots(figsize=(7.4, 4.4))
ax.plot(dz, n_req, color="#1f618d", lw=2)
target = next(
    (
        r
        for r in S["f1"]["pairwise"]
        if r["mode_a"] == "mas-nocoord" and r["mode_b"] == "mas-auction"
    ),
    None,
)
if target:
    d0, n0, have = target["cohen_dz"], target["n_required"], target["n_pairs"]
    ax.axvline(d0, color="#c0392b", ls="--", lw=1.3)
    ax.axhline(have, color="#444444", ls=":", lw=1.3)
    ax.plot([d0], [n0], "o", color="#c0392b", ms=8, zorder=3)
    ax.annotate(
        f"observed effect $d_z$={d0:.2f}\nneeds n≈{n0:.0f} paired obs.",
        (d0 + 0.03, n0),
        fontsize=9,
        color="#c0392b",
        va="bottom",
    )
    ax.annotate(
        f"this campaign: n={have}\n(9 scenarios × 5 reps)",
        (0.72, have + 6),
        fontsize=9,
        color="#333333",
    )
ax.set_xlabel("Standardized paired effect size $d_z$")
ax.set_ylabel("Paired observations for 80% power")
ax.set_title(
    "Sample size required to detect the observed architecture effect\n"
    r"($\alpha=0.05$ two-sided, power $=0.80$)",
    fontsize=11,
)
ax.set_ylim(0, 260)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_power_curve.png", bbox_inches="tight")
plt.close(fig)

# --- Figure 6: per-mode mean with bootstrap CI --------------------------------
marg = S["f1"]["marginals"]
fig, ax = plt.subplots(figsize=(7.2, 4.3))
xs = np.arange(len(MODES))
means = [marg[m]["mean"] for m in MODES]
lo = [marg[m]["mean"] - marg[m]["ci_lo"] for m in MODES]
hi = [marg[m]["ci_hi"] - marg[m]["mean"] for m in MODES]
ax.bar(xs, means, yerr=[lo, hi], capsize=6, ecolor="#333333", color=COLORS, width=0.6)
band_lo = max(marg[m]["ci_lo"] for m in MODES)
band_hi = min(marg[m]["ci_hi"] for m in MODES)
if band_hi > band_lo:
    ax.axhspan(band_lo, band_hi, color="#c0392b", alpha=0.10, zorder=0)
    ax.annotate(
        "all four 95% CIs overlap in this band",
        (-0.44, (band_lo + band_hi) / 2.0),
        ha="left",
        va="center",
        fontsize=8.8,
        style="italic",
        color="#c0392b",
    )
for xi, m in zip(xs, MODES):
    d = marg[m]
    ax.annotate(
        f"{d['mean']:.3f}\n[{d['ci_lo']:.2f}, {d['ci_hi']:.2f}]",
        (xi, d["ci_hi"] + 0.015),
        ha="center",
        va="bottom",
        fontsize=8.6,
    )
ax.set_xticks(xs)
ax.set_xticklabels(LABELS)
ax.set_ylabel("Mean event-level F1")
ax.set_ylim(0, 0.85)
ax.set_title(
    f"Mean F1 with 95% bootstrap confidence intervals\n"
    f"(n={marg[MODES[0]]['n']} paired observations per mode)",
    fontsize=11,
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_mode_ci.png", bbox_inches="tight")
plt.close(fig)

print("wrote 6 figures to", OUT)
for f in [
    "fig_per_scenario_f1",
    "fig_paired_forest",
    "fig_tta_per_scenario",
    "fig_fa_per_hour_degeneracy",
    "fig_power_curve",
    "fig_mode_ci",
]:
    p = f"{OUT}/{f}.png"
    print(f"  {f:32s} {os.path.getsize(p) // 1024:4d} KB")
