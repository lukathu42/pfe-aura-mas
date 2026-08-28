"""Assemble the anonymized-evidence figure for the thesis Governance section.

Picks one real evidence crop per (sensor, event type) from `data/evidence/`
(1,737 files, all produced by `aura_mas/core/privacy.py` during the v2
campaign) and lays them out as a labelled 2x2 contact sheet.

Deliberately does NOT re-run the blur: these are the exact bytes the pipeline
wrote at evaluation time, so the figure is evidence about the privacy choke
point rather than an illustration of it. Panel labels record the source
filename so any frame can be traced back to its run.
"""

from __future__ import annotations

import glob
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

OUT = os.environ.get("FIG_OUT", "results/figures")
os.makedirs(OUT, exist_ok=True)

PANELS = [
    ("data/evidence/cam_01_intrusion_*.jpg", "cam\\_01 — intrusion, zone\\_A"),
    ("data/evidence/cam_02_intrusion_*.jpg", "cam\\_02 — intrusion, zone\\_B"),
    ("data/evidence/cam_01_abandoned_object_*.jpg", "cam\\_01 — abandoned object"),
    ("data/evidence/cam_01_anomaly_*.jpg", "cam\\_01 — CLIP semantic anomaly"),
]

plt.rcParams.update({"font.size": 10, "figure.dpi": 150})
fig, axes = plt.subplots(2, 2, figsize=(9.2, 5.6))

for ax, (pattern, label) in zip(axes.ravel(), PANELS):
    files = sorted(glob.glob(pattern), key=os.path.getsize, reverse=True)
    if not files:
        ax.text(0.5, 0.5, "no evidence file", ha="center", va="center")
        ax.axis("off")
        continue
    path = files[0]
    ax.imshow(Image.open(path))
    ax.set_title(label.replace("\\_", "_"), fontsize=10)
    ax.set_xlabel(os.path.basename(path), fontsize=6.5, color="#666666")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#444444")

fig.suptitle(
    "Anonymized alert evidence written by core/privacy.py during the v2 campaign",
    fontsize=11,
)
fig.tight_layout(rect=(0, 0, 1, 0.97))
out = f"{OUT}/fig_evidence_grid.png"
fig.savefig(out, bbox_inches="tight")
print("wrote", out, os.path.getsize(out) // 1024, "KB")
