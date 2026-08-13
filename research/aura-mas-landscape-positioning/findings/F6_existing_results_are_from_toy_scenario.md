---
name: F6_existing_results_are_from_toy_scenario
---
# F6 — The AURA-MAS thesis draft's existing "experimental results" come from a single, extremely small toy scenario

**Claim**: Per `STATE_NOTES.md`, the comparative results already written into the thesis (centralized vs. mas-nocoord vs. mas-rules vs. mas-auction: F1, time-to-alert, false-alerts/hour, coordination messages) come from exactly one scenario ("demo_site_01") using 2 real pedestrian video clips (from a public sample-video GitHub repo) and 1 synthetic (scripted, not recorded) glass-break audio event, with ground truth manually defined by the same session that ran the experiment.

**Evidence**: STATE_NOTES.md lines 19-26 (this repository); cross-checked against the much larger evaluation ambition described in the original blueprint (`pasted_content_2.txt`), which recommends UCF-Crime, XD-Violence, ShanghaiTech Campus, and DCASE benchmarks plus digital-twin simulation (Isaac Sim/Omniverse) — none of which were actually used in the results that made it into the thesis chapters.

**Implication**: The gap between the blueprint's evaluation ambition and what was actually run is large. The numeric comparisons (e.g., "MAS reduces time-to-alert ~36% vs centralized") are internally consistent demo output, not evidence that would satisfy a jury or support the thesis's own comparative claims — n=1 scenario, self-defined ground truth, no statistical testing, no public benchmark. A real Master's/Engineer submission needs either a genuinely expanded evaluation (multiple scenarios, ideally a public benchmark subset) or an explicit, honest scoping of the existing results as a feasibility demonstration rather than a validated comparative result.

**Confidence**: High (direct, unambiguous statement in the project's own internal notes).
