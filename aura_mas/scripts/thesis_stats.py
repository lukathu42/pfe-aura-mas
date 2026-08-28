"""Inferential statistics over the v2 campaign, for the thesis Results chapter.

`results/summary_agg.csv` reports mean+/-std per (scenario, mode, backend) cell
and nothing else -- no interval, no test, no effect size. Several of those
cells are Bernoulli outcomes over n=5 reps, where a "std" of 0.447 just means
the per-run F1 flipped between 1.0 and 0.0; reporting that as a dispersion
estimate invites over-reading. This module supplies the missing inferential
layer that `research/reports/research-report-v1/02-gaps-and-recommendations.md`
A6 asks for, and writes both a machine-readable JSON and ready-to-input LaTeX
tables so no number is ever retyped by hand into a chapter.

Design choices worth knowing before citing anything this produces:

* The campaign grid is a **paired** design: every (scenario, rep) cell is
  observed under all four modes on identical inputs. Paired tests are
  therefore the correct family, and the unit of analysis is the paired
  difference -- not the marginal per-mode mean, which ignores that pairing.
* Wilcoxon signed-rank rather than a paired t-test, because per-run F1 on a
  1-3 event scenario is discrete and bounded, nowhere near normal.
* Holm-Bonferroni across the 6 pairwise mode comparisons. Reporting 6
  uncorrected p-values and quoting whichever falls below 0.05 is exactly the
  multiplicity error that makes a single "significant" result meaningless.
* Cliff's delta as the effect size, since it is the non-parametric companion
  to the rank test and is not distorted by the F1 distribution's shape.
* Bootstrap percentile CIs (10k resamples, fixed seed) instead of normal-theory
  intervals, for the same non-normality reason.

`loitering_01` is a deliberate empty-ground-truth true-negative probe
(`scenarios/loitering_01.json`), so its F1 is 0.0 for every mode by
construction. It is retained in the primary paired analysis -- excluding a
cell *because* every mode scores identically on it would bias the comparison
toward whichever mode the remaining scenarios happen to favour -- and reported
separately as a sensitivity check.
"""

from __future__ import annotations

import csv
import itertools
import json
import os
import statistics as st
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.stats import fligner, levene, wilcoxon

SUMMARY = os.environ.get("SUMMARY_CSV", "results/summary.csv")
OUT_JSON = os.environ.get("STATS_JSON", "results/thesis_stats.json")
TEX_OUT = os.environ.get("STATS_TEX_DIR", "thesis/Assets/generated")

MODES = ["centralized", "mas-nocoord", "mas-rules", "mas-auction"]
MODE_TEX = {
    "centralized": "Centralized",
    "mas-nocoord": "MAS-nocoord",
    "mas-rules": "MAS-rules",
    "mas-auction": "MAS-auction",
}
PROBE_SCENARIO = "loitering_01"
BOOT = 10000
SEED = 20260826


def load_rows() -> List[Dict[str, str]]:
    """v2 headline rows only: real reps, YAMNet/auto backend, the 4 core modes.

    `rep=""` rows are the 44 v1 pre-YAMNet single-pass runs; pooling them with
    5 real v2 repetitions corrupts every statistic downstream. Same exclusion
    as `aura_mas.eval.metrics.aggregate()` and `make_figures.py`.
    """
    with open(SUMMARY) as fh:
        rows = list(csv.DictReader(fh))
    return [
        r
        for r in rows
        if r.get("rep")
        and r.get("audio_backend") in ("auto", "")
        and r["mode"] in MODES
    ]


def paired_cells(
    rows: Sequence[Dict[str, str]], metric: str
) -> Dict[Tuple[str, str], Dict[str, float]]:
    """(scenario, rep) -> {mode: value}, keeping only fully-observed cells."""
    cells: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
    for r in rows:
        raw = r.get(metric)
        if raw in (None, ""):
            continue
        cells[(r["scenario"], r["rep"])][r["mode"]] = float(raw)
    return {k: v for k, v in cells.items() if len(v) == len(MODES)}


def cliffs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    """P(a>b) - P(a<b) over all pairs. +1 = a always larger, 0 = no dominance."""
    gt = lt = 0
    for x in a:
        for y in b:
            if x > y:
                gt += 1
            elif x < y:
                lt += 1
    total = len(a) * len(b)
    return (gt - lt) / total if total else 0.0


def bootstrap_ci(
    values: Sequence[float], conf: float = 95.0, n_boot: int = BOOT, seed: int = SEED
) -> Tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    means = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    lo = float(np.percentile(means, (100.0 - conf) / 2.0))
    hi = float(np.percentile(means, 100.0 - (100.0 - conf) / 2.0))
    return lo, hi


def holm(pvals: Sequence[float]) -> List[float]:
    """Holm-Bonferroni step-down adjusted p-values, order preserved."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = min(1.0, pvals[idx] * (m - rank))
        running = max(running, val)  # enforce monotonicity
        adj[idx] = running
    return adj


def required_n(
    diffs: Sequence[float], power: float = 0.80, alpha: float = 0.05
) -> Dict[str, float]:
    """Paired-design sample size for the observed standardized effect.

    Normal approximation (z_{1-a/2}+z_{1-b})^2 / dz^2. Deliberately the
    optimistic parametric estimate: the actual Wilcoxon requirement is
    higher still, so this is a lower bound on what would be needed.
    """
    sd = st.stdev(diffs) if len(diffs) >= 2 else 0.0
    mean = st.mean(diffs) if diffs else 0.0
    if sd == 0 or mean == 0:
        return {"cohen_dz": 0.0, "n_required": float("inf")}
    dz = mean / sd
    z_a, z_b = 1.959964, 0.841621  # alpha=.05 two-sided, power=.80
    return {"cohen_dz": dz, "n_required": ((z_a + z_b) ** 2) / (dz**2)}


def pairwise(cells: Dict[Tuple[str, str], Dict[str, float]]) -> List[Dict]:
    """All 6 mode pairs: paired Wilcoxon + Cliff's delta + bootstrap CI."""
    results = []
    for a, b in itertools.combinations(MODES, 2):
        xa = [v[a] for v in cells.values()]
        xb = [v[b] for v in cells.values()]
        diffs = [x - y for x, y in zip(xa, xb)]
        nonzero = [d for d in diffs if d != 0]
        if nonzero:
            stat, p = wilcoxon(xa, xb, zero_method="wilcox")
            stat, p = float(stat), float(p)
        else:
            stat, p = float("nan"), 1.0
        lo, hi = bootstrap_ci(diffs)
        results.append(
            {
                "mode_a": a,
                "mode_b": b,
                "n_pairs": len(diffs),
                "n_nonzero_pairs": len(nonzero),
                "mean_diff": st.mean(diffs),
                "median_diff": st.median(diffs),
                "ci_lo": lo,
                "ci_hi": hi,
                "wilcoxon_W": stat,
                "p_raw": p,
                "cliffs_delta": cliffs_delta(xa, xb),
                **required_n(diffs),
            }
        )
    for row, adj in zip(results, holm([r["p_raw"] for r in results])):
        row["p_holm"] = adj
        row["significant_holm"] = bool(adj < 0.05)
    return results


def marginals(cells: Dict[Tuple[str, str], Dict[str, float]]) -> Dict[str, Dict]:
    out = {}
    for m in MODES:
        vals = [v[m] for v in cells.values()]
        lo, hi = bootstrap_ci(vals)
        out[m] = {
            "n": len(vals),
            "mean": st.mean(vals),
            "median": st.median(vals),
            "sd": st.stdev(vals) if len(vals) > 1 else 0.0,
            "ci_lo": lo,
            "ci_hi": hi,
        }
    return out


def variance_tests(
    rows: Sequence[Dict[str, str]], metric: str, scenario: str | None = None
) -> Dict:
    """Levene + Fligner-Killeen on `metric` dispersion across modes.

    Tests THESIS_REPATCH.md's proposed fallback claim that auction
    coordination, while not better on the mean, is more *stable* run to run.
    """
    groups: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        if scenario and r["scenario"] != scenario:
            continue
        raw = r.get(metric)
        if raw in (None, ""):
            continue
        groups[r["mode"]].append(float(raw))
    present = [m for m in MODES if len(groups.get(m, [])) >= 2]
    out = {
        "scenario": scenario or "ALL",
        "metric": metric,
        "per_mode": {
            m: {
                "n": len(groups[m]),
                "mean": st.mean(groups[m]),
                "variance": float(np.var(groups[m], ddof=1)),
                "values": groups[m],
            }
            for m in present
        },
    }
    if len(present) >= 2:
        arrays = [groups[m] for m in present]
        try:
            w, p = levene(*arrays)
            out["levene"] = {"stat": float(w), "p": float(p)}
        except Exception as exc:  # degenerate (all-constant) groups
            out["levene"] = {"error": str(exc)}
        try:
            x2, p2 = fligner(*arrays)
            out["fligner"] = {"stat": float(x2), "p": float(p2)}
        except Exception as exc:
            out["fligner"] = {"error": str(exc)}
    return out


def per_scenario(
    rows: Sequence[Dict[str, str]], metric: str
) -> Dict[str, Dict[str, Dict]]:
    grid: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        raw = r.get(metric)
        if raw in (None, ""):
            continue
        grid[r["scenario"]][r["mode"]].append(float(raw))
    out: Dict[str, Dict[str, Dict]] = {}
    for scen in sorted(grid):
        out[scen] = {}
        for m in MODES:
            vals = grid[scen].get(m, [])
            out[scen][m] = {
                "n": len(vals),
                "mean": st.mean(vals) if vals else None,
                "sd": st.stdev(vals) if len(vals) > 1 else (0.0 if vals else None),
            }
    return out


# ---------------------------------------------------------------- LaTeX output


def _f(x, nd=3, dash="--"):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return dash
    return f"{x:.{nd}f}"


def tex_pairwise(res: Sequence[Dict], metric_label: str) -> str:
    lines = [
        "% GENERATED by aura_mas/scripts/thesis_stats.py -- do not edit by hand.",
        "\\begin{tabular}{llrr@{\\,}c@{\\,}lrrr}",
        "\\toprule",
        "\\textbf{Mode A} & \\textbf{Mode B} & \\textbf{$\\Delta$ mean} & "
        "\\multicolumn{3}{c}{\\textbf{95\\% CI}} & \\textbf{$p$} & "
        "\\textbf{$p_{\\text{Holm}}$} & \\textbf{$\\delta$} \\\\",
        "\\midrule",
    ]
    for r in sorted(res, key=lambda x: x["p_raw"]):
        star = "$^{*}$" if r["significant_holm"] else ""
        lines.append(
            f"{MODE_TEX[r['mode_a']]} & {MODE_TEX[r['mode_b']]} & "
            f"{r['mean_diff']:+.3f} & [{_f(r['ci_lo'])} & , & {_f(r['ci_hi'])}] & "
            f"{_f(r['p_raw'])} & {_f(r['p_holm'])}{star} & {r['cliffs_delta']:+.3f} \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def tex_marginals(marg: Dict[str, Dict]) -> str:
    lines = [
        "% GENERATED by aura_mas/scripts/thesis_stats.py -- do not edit by hand.",
        "\\begin{tabular}{lrrrr@{\\,}c@{\\,}l}",
        "\\toprule",
        "\\textbf{Mode} & \\textbf{$n$} & \\textbf{Mean} & \\textbf{Median} & "
        "\\multicolumn{3}{c}{\\textbf{95\\% CI (bootstrap)}} \\\\",
        "\\midrule",
    ]
    for m in MODES:
        d = marg[m]
        lines.append(
            f"{MODE_TEX[m]} & {d['n']} & {_f(d['mean'])} & {_f(d['median'])} & "
            f"[{_f(d['ci_lo'])} & , & {_f(d['ci_hi'])}] \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def tex_per_scenario(grid: Dict[str, Dict[str, Dict]]) -> str:
    lines = [
        "% GENERATED by aura_mas/scripts/thesis_stats.py -- do not edit by hand.",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "\\textbf{Scenario} & \\textbf{Centralized} & \\textbf{MAS-nocoord} & "
        "\\textbf{MAS-rules} & \\textbf{MAS-auction} \\\\",
        "\\midrule",
    ]
    for scen in sorted(grid):
        cells = []
        best = max((grid[scen][m]["mean"] or -1) for m in MODES)
        for m in MODES:
            d = grid[scen][m]
            if d["mean"] is None:
                cells.append("--")
                continue
            txt = f"{d['mean']:.3f}"
            if d["sd"] is not None:
                txt += f"$\\pm${d['sd']:.3f}"
            if abs(d["mean"] - best) < 1e-9 and best >= 0:
                txt = f"\\textbf{{{txt}}}"
            cells.append(txt)
        label = scen.replace("_", "\\_")
        if scen == PROBE_SCENARIO:
            label += "$^{\\dagger}$"
        lines.append(f"\\texttt{{{label}}} & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def tex_variance(v: Dict) -> str:
    lines = [
        "% GENERATED by aura_mas/scripts/thesis_stats.py -- do not edit by hand.",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "\\textbf{Mode} & \\textbf{$n$} & \\textbf{Mean precision} & "
        "\\textbf{Variance} \\\\",
        "\\midrule",
    ]
    for m in MODES:
        d = v["per_mode"].get(m)
        if not d:
            continue
        lines.append(
            f"{MODE_TEX[m]} & {d['n']} & {_f(d['mean'])} & {_f(d['variance'], 5)} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    os.makedirs(TEX_OUT, exist_ok=True)
    rows = load_rows()
    report: Dict = {
        "provenance": {
            "source_csv": SUMMARY,
            "n_rows_used": len(rows),
            "filters": "rep is set (v2 only); audio_backend in {auto,''}; mode in 4 core modes",
            "bootstrap_resamples": BOOT,
            "seed": SEED,
            "multiplicity_correction": "Holm-Bonferroni over 6 pairwise mode comparisons",
            "test": "Wilcoxon signed-rank, paired on (scenario, rep)",
            "effect_size": "Cliff's delta",
        }
    }

    for metric in ("f1", "precision", "recall", "mean_time_to_alert_s"):
        cells = paired_cells(rows, metric)
        if not cells:
            continue
        block = {
            "n_paired_cells": len(cells),
            "scenarios": sorted({s for s, _ in cells}),
            "marginals": marginals(cells),
            "pairwise": pairwise(cells),
            "per_scenario": per_scenario(rows, metric),
        }
        # sensitivity: drop the empty-GT probe
        sens = {k: v for k, v in cells.items() if k[0] != PROBE_SCENARIO}
        if sens:
            block["sensitivity_excluding_probe"] = {
                "n_paired_cells": len(sens),
                "marginals": marginals(sens),
                "pairwise": pairwise(sens),
            }
        report[metric] = block

    report["variance_tests"] = {
        "precision_demo_site_01": variance_tests(rows, "precision", "demo_site_01"),
        "precision_all": variance_tests(rows, "precision"),
        "f1_all": variance_tests(rows, "f1"),
    }

    # false_alerts_per_hour degeneracy evidence: fp count vs run length
    deg = []
    for r in rows:
        try:
            deg.append(
                {
                    "scenario": r["scenario"],
                    "mode": r["mode"],
                    "fp": int(r["fp"]),
                    "wall_seconds": float(r["wall_seconds"]),
                    "fa_per_hour": float(r["false_alerts_per_hour"]),
                }
            )
        except (KeyError, ValueError):
            continue
    report["fa_per_hour_degeneracy"] = {
        "note": (
            "false_alerts_per_hour = fp / (wall_seconds/3600). At the run "
            "lengths in this campaign a single false positive extrapolates "
            "to a very large hourly rate, so the metric reports run "
            "duration as much as alert quality."
        ),
        "min_wall_seconds": min((d["wall_seconds"] for d in deg), default=None),
        "max_fa_per_hour": max((d["fa_per_hour"] for d in deg), default=None),
        "distinct_fp_counts": sorted({d["fp"] for d in deg}),
        "rows": deg,
    }

    with open(OUT_JSON, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=False)

    f1 = report["f1"]
    writes = {
        "tab_pairwise_f1.tex": tex_pairwise(f1["pairwise"], "F1"),
        "tab_marginal_f1.tex": tex_marginals(f1["marginals"]),
        "tab_per_scenario_f1.tex": tex_per_scenario(f1["per_scenario"]),
        "tab_variance_precision.tex": tex_variance(
            report["variance_tests"]["precision_demo_site_01"]
        ),
    }
    if "mean_time_to_alert_s" in report:
        writes["tab_per_scenario_tta.tex"] = tex_per_scenario(
            report["mean_time_to_alert_s"]["per_scenario"]
        )
        writes["tab_pairwise_tta.tex"] = tex_pairwise(
            report["mean_time_to_alert_s"]["pairwise"], "TTA"
        )
    for name, body in writes.items():
        with open(os.path.join(TEX_OUT, name), "w") as fh:
            fh.write(body)

    print(
        f"wrote {OUT_JSON} ({len(rows)} runs) and {len(writes)} LaTeX tables to {TEX_OUT}"
    )
    print(f"\nF1 paired cells: {f1['n_paired_cells']}")
    for m in MODES:
        d = f1["marginals"][m]
        print(f"  {m:14s} mean={d['mean']:.4f} CI=[{d['ci_lo']:.3f},{d['ci_hi']:.3f}]")
    print("\nPairwise (Holm-adjusted):")
    for r in sorted(f1["pairwise"], key=lambda x: x["p_raw"]):
        flag = " SIGNIFICANT" if r["significant_holm"] else ""
        print(
            f"  {r['mode_a']:13s} vs {r['mode_b']:13s} "
            f"d={r['mean_diff']:+.4f} p={r['p_raw']:.4f} "
            f"p_holm={r['p_holm']:.4f} delta={r['cliffs_delta']:+.3f}{flag}"
        )
    n_sig = sum(1 for r in f1["pairwise"] if r["significant_holm"])
    print(
        f"\n=> {n_sig} of {len(f1['pairwise'])} pairwise F1 comparisons significant after Holm."
    )


if __name__ == "__main__":
    main()
