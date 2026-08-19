# 02 — Gaps and Recommendations

Every item carries a **Priority** (Critical / High / Nice-to-have) and an **Effort** estimate (Low ≈ hours, Medium ≈ days, High ≈ weeks). Every claim about the project is grounded in a file path. Terms are defined in `03-concepts-explained.md`.

**Reading order if you are short on time:** do everything marked Critical in §A and §B, in the order listed. That is roughly 8–12 days of work and it is the difference between a thesis that survives a defence and one that does not.

---

## A. Thesis gaps — what must be added to the written work

### A1. Rewrite chapter 6 from the v2 campaign data, including the negative result
**Priority: Critical · Effort: Medium**

`chapter6.tex:41-95` reports a single run of a single scenario. `results/summary_agg.csv` now holds 84 mean-and-standard-deviation groups over 373 runs, and it **contradicts the chapter's conclusions** (see `01-project-summary.md` §4): mean F1 is nocoord 0.577 > centralized 0.519 > rules 0.490 > auction 0.452.

Do not find-and-replace numbers. Rewrite the argument:

- State the ablation result as it is, including that auction ranks last on mean F1 across 9 scenarios.
- Present the defensible secondary finding: `mas-auction` on `demo_site_01` has precision `0.667 ± 0.000` across 5 repetitions while `mas-nocoord` has `0.767 ± 0.224`. Argue **variance reduction**, not mean improvement — and back it with a variance test, not an eyeball comparison.
- Report per-scenario results in a table, not a single aggregate. The aggregate hides that the audio-only scenarios strongly favour the MAS modes while the video scenarios favour centralized.
- `THESIS_REPATCH.md` already contains a row-by-row worklist for this. Apply it.

A thesis that reports a negative result cleanly is stronger than one that reports a positive result nobody can reproduce. Examiners reward this. State it in the abstract.

### A2. Declare the pacing confound and fix or bound it
**Priority: Critical · Effort: Low (to declare) / Medium (to fix)**

`replay.py:108` makes MAS modes real-time-paced and the centralized baseline unpaced and sequential, while `FusionAgent.window_seconds` and `PolicyAgent.cooldown_seconds` are wall-clock quantities. RQ1's latency comparison therefore measures pacing policy, not architecture (`01-project-summary.md` §5.1).

Minimum: a paragraph in §"Threats to Validity" naming this as an **internal validity** threat, stating that the RQ1 latency result is not attributable to architecture alone.

Better: add a `centralized-paced` mode that keeps sequential single-process processing but paces to source frame rate, re-run, and report both. That converts a confound into an extra ablation cell — and it is a genuinely interesting one, because it separates *concurrency* from *time compression*.

### A3. Fix or disclose the `demo_site_01` loitering ground truth
**Priority: Critical · Effort: Low**

`scenarios/loitering_01.json` documents that no clip in the corpus contains a person stationary for ≥ 8 s, so the loitering entry in `scenarios/demo_site_01.json` (`t = 16–46 s`) is unsatisfiable. 48 of 60 `demo_site_01` runs carry `fn = 1` as a direct consequence.

Either remove the annotation and regenerate all `demo_site_01` numbers, or keep it and state explicitly in chapter 6 that one of three ground-truth events is known to be undetectable by the current rule set, so recall is capped at 0.667 by construction. Publishing an F1 built on a known-false annotation without saying so is not survivable if a jury member reads the scenario file.

### A4. Replace or supplement the matching metric
**Priority: Critical · Effort: Medium**

`metrics.py:41-52` matches on **incident family** with a ±5 s tolerance and a greedy first-fit loop. On `demo_site_01` all three ground-truth entries are family `security`, so the metric cannot distinguish event types at all, and the intrusion entry's acceptance window covers 73 % of the run (`01-project-summary.md` §5.2).

Required changes:
- Add an **exact-event-type** matching mode alongside the family mode and report both. Family-level matching is defensible for measuring "an incident was flagged"; it is not defensible for claiming the system detects intrusion versus loitering.
- Replace greedy first-fit with **optimal one-to-one assignment** (Hungarian algorithm on a cost matrix of temporal distance), which removes the ground-truth-ordering dependence the team already documented.
- Make the tolerance a function of the event's duration rather than a fixed ±5 s, or report onset-only matching.
- Report raw counts (true positives, false positives, false negatives) alongside every ratio.

### A5. Replace `false_alerts_per_hour` with something meaningful
**Priority: High · Effort: Low**

Dividing 1 false positive by a 10-second run yields 360/h (`results/summary_agg.csv` contains 377.3, 358.8). Report **false positives per run** and **false positives per ground-truth-negative minute**, and only report a per-hour rate over a corpus of at least an hour of aggregate footage. Regenerate `fig_system_metrics.png`.

### A6. Add real statistical treatment
**Priority: Critical · Effort: Medium**

There is currently no confidence interval, significance test, or effect size anywhere in `results/` or the chapters, and several cells are Bernoulli outcomes reported as mean ± standard deviation over n = 5.

Add:
- **Paired non-parametric tests** across modes on matched `(scenario, repetition)` pairs — Wilcoxon signed-rank is the right default for this design.
- **Bootstrap confidence intervals** on per-mode mean F1 and on paired differences.
- **Effect size** (Cliff's delta) alongside any p-value.
- A correction for multiple comparisons (Holm–Bonferroni) since 4 modes × 9 scenarios generates many tests.
- Report **n, mean, confidence interval** — and stop reporting standard deviation on binary outcomes.

### A7. Disclose the CLIP result
**Priority: Critical · Effort: Low**

`results/clip_anomaly_calibration_notes.md` reports AUC = 0.308 — worse than random — root-caused to prompt/scene domain mismatch. No chapter mentions it (`THESIS_REPATCH.md` §Priority 4 confirms zero `AUC`/`calibrat` hits in `Chapters/*.tex`), yet `chapter5.tex:67` and `chapter7.tex:6` describe the scorer as a working component. Add the number, the root cause, and the prompt-engineering fix as future work. This is the highest-integrity-risk omission in the manuscript.

### A8. Verify the bibliography
**Priority: Critical · Effort: Medium**

88 of 94 entries in `Bibliography/bibliography.bib` are unverified (`research/.../findings/F5`), the 6 checked contained corrupted author fields and a wrong year, and 16 entries carry neither DOI nor URL — including `smith1980contract`, `zhang2022bytetrack`, `radford2021clip`, `sultani2018ucfcrime`, `euaiact2024` and `gdpr2016`, which are the load-bearing citations for the core claims.

Re-derive every entry from the publisher or arXiv record. Add a DOI or a stable URL to all 94. This is tedious and non-negotiable: a jury member who spot-checks two citations and finds one wrong will discount the entire related-work chapter.

### A9. Fix authorship and institutional metadata
**Priority: Critical · Effort: Low**

`EXECUTION_PLAN.md §0`: the compiled thesis carries "BELMANA Soufyane" and supervisor "Pr. AMAR BENSABER Djamel" from the template. Fix `AURA-MAS_Thesis_LaTeX/main.tex` and remove `Master_BELMANA_Soufyane.pdf` from the delivery bundle.

### A10. Update the related-work chapter to the 2026 agentic-anomaly-detection literature
**Priority: High · Effort: Medium**

`chapter_sota.tex` does not cite the current agentic-anomaly-detection taxonomy (detection-only / reasoning / tool-using / planner agents) or the systems in it (ARGOS, AD-AGENT, SentinelAgent, AnomalyRuler, Audit-LLM), nor the explainable-VAD line (Holmes-VAD, Holmes-VAU) that occupies contribution C4's territory, nor agentic VAD ("Glance, Scrutinize, and Think", 2026). The gap table `tab:sota_gap` claims "no surveyed system architecturally decouples the generative component from the alert decision" — that claim needs re-checking against the oversight-architecture family (critic agents) named in the 2026 survey before it can stand.

Also retire the claim at `chapter3.tex:40` that no system-level multi-sensor benchmark exists, or restrict it precisely: MTMMC, AI City Challenge Track 1, and the collaborative-perception benchmarks all exist and report communication-cost-versus-accuracy trade-offs.

### A11. Add a proper ethics, privacy, and data-governance section
**Priority: High · Effort: Medium**

Currently `chapter4.tex` Table `tab:privacy` maps requirements to mechanisms, which is good, but the manuscript lacks:
- A **Data Protection Impact Assessment** sketch — the EU AI Act and GDPR analysis is descriptive, not applied to this system.
- A **dataset licence and provenance table** in the manuscript. `data/clips_real/manifest.json` exists on disk but no chapter cites it. Using AIRTLab, ABODA and ESC-50 requires stating their licences and the terms under which redistribution is or is not permitted.
- A **threat model**: `docker-compose.yml` runs Mosquitto with `mosquitto-no-auth.conf` and Redis with no password. A surveillance system whose thesis argues about governance should state its adversary model and admit the prototype's transport is unauthenticated.
- **Anonymisation efficacy**: the privacy claim is that person regions are blurred (`core/privacy.py`). No measurement of whether the blur defeats re-identification is reported. At minimum, state that efficacy is asserted by construction and not measured.
- **Dual-use discussion**: a system that detects "loitering" and "intrusion" has obvious potential for discriminatory deployment. One honest paragraph is expected in 2026 and its absence is conspicuous.

### A12. Add a threats-to-validity section that names the real threats
**Priority: High · Effort: Low**

`chapter6.tex:103-111` lists scale, perception ceiling, single topology, explanation evaluation. It omits the ones that actually matter: the pacing confound (A2), the family-level metric (A4), the false-alert-rate artefact (A5), the unwired bid function (B3), the never-executed LLM path (B5), the absent seed control (B6), and construct validity of "time-to-alert" measured on a self-authored annotation.

Structure the section as **internal / external / construct / conclusion** validity, which is the standard framing and makes omissions visible.

### A13. Add the ablations the thesis promises but does not run
**Priority: High · Effort: Medium**

`README.md` advertises four comparison axes; the manuscript evaluates coordination mode and vision-only. Missing, and cheap to add with the existing harness:
- **Fusion ablation**: noisy-OR versus max-confidence versus mean. This directly tests C3's mechanism rather than assuming it.
- **Corroboration-bonus ablation**: `β = 0` versus `β = 0.05`. The bonus is a free parameter presented as a contribution.
- **Threshold sensitivity**: sweep `ALERT_THRESHOLDS` and the gray zone, and report a precision–recall curve rather than a single operating point. This is the single highest-value-per-hour experiment available, and it converts twenty magic numbers from a weakness into an analysis.
- **CLIP on/off**: currently never varied in the campaign.
- **Template versus LLM explanation** (`--llm`): promised in `README.md`'s table, never run.

### A14. Reposition the novelty claim
**Priority: High · Effort: Low**

`research/.../findings/F4` establishes that multi-agent surveillance dates to at least 2000 (Monitorix, FIPA-ACL, cross-camera re-identification), and F3 that "multi-agent system + X detection" is an established local thesis pattern. Auctions date to 1980. Noisy-OR late fusion is textbook.

Novelty must rest on the two things that are actually unusual (`01-project-summary.md` §7.4):
1. **Decision/generation decoupling with a mechanical evidence-citation guardrail** in a safety-critical alerting loop.
2. **A reproducible system-level ablation methodology** for multi-agent surveillance architectures, with a documented methodology-change log.

Rewrite C1–C5 so the contribution claims match what the evidence can support. C1 (architecture) and C2 (auction) should be demoted to "system realisation" rather than research contributions unless B3 is fixed and re-run.

### A15. Add a reproducibility appendix
**Priority: Nice-to-have · Effort: Low**

Hardware, operating system, Python version, exact library versions, seeds, total compute time, the exact command lines, and a pointer to the archived run artefacts. `results/env/pip-freeze-post-tf.txt` gets you most of the way.

---

## B. Implementation gaps — what must be built for the thesis claims to hold

### B1. Wire up seed control and determinism
**Priority: Critical · Effort: Low**

`CLAUDE.md` acknowledges "real run-to-run non-determinism" and prescribes N ≥ 3 repetitions as a workaround. Fix the cause instead:

- In `replay.py`, set `random.seed`, `numpy.random.seed`, `torch.manual_seed`, `PYTHONHASHSEED`, and `torch.set_num_threads(1)` from a `--seed` flag; record the seed in the run JSON.
- Set `cv2.setNumThreads(1)` — OpenCV thread pools are a common source of float non-determinism.
- Record library versions, git commit hash, and hostname in every run JSON.

Then re-run a small grid to confirm bit-identical repeats. Repetitions remain valuable for measuring genuine stochasticity (thread scheduling in the auction), but they should not be compensating for uncontrolled randomness.

### B2. Add a paced centralized baseline
**Priority: Critical · Effort: Low**

Add `--realtime/--no-realtime` as an explicit flag decoupled from `mode`, and add a `centralized-paced` cell to the campaign grid. Without this, RQ1 is unanswerable (§A2).

### B3. Actually implement the field-of-view overlap in the bid
**Priority: Critical · Effort: Medium**

`camera_agent.py:318` reads `task.get("fov_overlap", {})`, and `coordinator_agent.py:54-59` never populates it. `o` is therefore the constant 0.5 in every run ever executed, and the auction degenerates to "pick any non-originating idle camera" — indistinguishable from round-robin (`01-project-summary.md` §5.4).

Fix:
- Add a per-scenario `fov_overlap` map (camera → zone → overlap in [0,1]) to the manifest, or compute it from declared zone polygons and camera homographies.
- Populate it in the task announcement.
- Add a unit test asserting that a camera with higher declared overlap wins against an equally-idle non-origin peer.
- Re-run the campaign. **Only then is C2's "who verifies matters" claim testable.**

Until this is done, the thesis must not claim the auction selects the best-placed verifier.

### B4. Verify the right frame
**Priority: Critical · Effort: Medium**

`camera_agent.py:339-352` verifies `self._last_frame` — the current frame, not the frame at the incident. Add a small bounded ring buffer of recent `(timestamp, frame)` pairs, protect it with a lock (it is currently a cross-thread read with no synchronisation), and have `_verify()` select the frame nearest the hypothesis's event timestamp. Also make the verification predicate depend on the hypothesis's event type rather than always counting `person` detections.

### B5. Run the explanation layer against a real model
**Priority: Critical · Effort: Medium**

`run_campaign.py` never passes `--llm`; `results/explanation_eval_notes.md` states no key was available. RQ4 therefore has no experimental evidence (`01-project-summary.md` §5.9).

Minimum viable evaluation:
- Run a local model via Ollama (the `ExplanationAgent` already targets an OpenAI-compatible endpoint, `explanation_agent.py:157-160`) so no API cost or data-egress issue arises.
- Run every alert in the campaign through it. Report the **guardrail rejection rate**, the distribution of rejection causes (schema failure, fabricated citation in the list, fabricated identifier in free text), and the fallback rate.
- Add an **adversarial probe**: deliberately prompt-inject through the `extra` field of an event and measure whether the guardrail holds.
- Optionally, an LLM-as-judge or small human rating of explanation usefulness on a sample of 30–50 alerts.

A guardrail rejection rate measured against a real model is a publishable number. A unit test is not.

### B6. Exercise MQTT and Redis in at least one campaign cell
**Priority: High · Effort: Medium**

Every reported result used `--bus local` (`run_campaign.py:100`) and `AlertStore(redis_url=None)` (`replay.py:78`). Contribution C1's two-tier substrate is therefore entirely unevaluated, and the "coordination overhead" figure counts in-process function calls (`01-project-summary.md` §5.6).

Run the full grid once with `--bus mqtt` and Redis enabled, and report: message counts, **bytes on the wire**, broker round-trip latency, and end-to-end latency delta versus `LocalBus`. This makes RQ2's "at what communication cost" answerable, and it is the number the collaborative-perception literature reports.

### B7. Make the bid window not be dead latency
**Priority: High · Effort: Low**

On `LocalBus`, bids arrive synchronously during the task publish, so `time.sleep(self.bid_window)` (`coordinator_agent.py:90`) adds a full second of nothing. Replace the fixed sleep with a wait-for-quorum-or-timeout: wake as soon as all known camera agents have bid, capped by `bid_window`. This is more realistic, removes an artefact from every auction timing number, and is about ten lines.

### B8. Add a per-scenario `configs/` layer
**Priority: High · Effort: Medium**

`README.md`, `chapter5.tex:50` and `CLAUDE.md` all describe a `configs/` directory. `aura_mas/configs/` is empty and no top-level `configs/` exists. All thresholds are hard-coded defaults in constructors, and zone geometry is inline in scenario manifests.

Externalise every free parameter (the ~20 constants listed in `01-project-summary.md` §5.10) into a versioned YAML config, load it in `replay.py`, and record the resolved config in every run JSON. Without this, threshold sensitivity analysis (A13) is not practical and no run is fully reproducible.

### B9. Delete or quarantine the stale root-level duplicates
**Priority: High · Effort: Low**

Fourteen `.py` files exist twice, with the root copies now holding pre-fix logic (`results/methodology_changes.md`, "Note on root-level duplicate files"), plus a failed root-level LaTeX build. `.gitignore` already excludes the root LaTeX files. Move the root `.py` copies to `legacy/` with a README, or delete them. Right now anyone reading the repository can silently run the buggy version.

*(Note: this audit did not modify them — this is a recommendation for you to execute.)*

### B10. Add continuous integration and static checks
**Priority: High · Effort: Low**

No CI configuration, no linter config, no type checking, no coverage measurement. Add: `ruff` for linting, `mypy` in non-strict mode (the codebase already uses `from __future__ import annotations` and type hints throughout, so this is cheap), `pytest --cov`, and a GitHub Actions workflow running the 6 offline tests on push. This turns "6/6 tests pass" from a claim into an artefact.

### B11. Package the project properly
**Priority: Nice-to-have · Effort: Low**

Add `pyproject.toml` with pinned dependencies and an editable install so `aura_mas` is importable from anywhere. Add a lockfile (`uv.lock` or `pip-compile` output) capturing the exact environment used for the campaign, including the optional heavy dependencies that are currently commented out in `requirements.txt`.

### B12. Measure edge resource envelopes
**Priority: High · Effort: Medium**

The architecture is argued as "edge-first" and `README.md` describes a Raspberry Pi deployment, but no run on constrained hardware exists and no resource metric is collected. Add per-agent CPU time, peak resident memory, and frames-per-second to the run JSON; then run at least one scenario on a Raspberry Pi 5 or equivalent single-board computer and report frames-per-second and watts. Without this, "edge-first" is an architectural assertion, not a measured property.

### B13. Fix the audio-backend ablation's construct validity
**Priority: High · Effort: Medium**

DSP mode scores exactly 0.000 on every audio-only scenario because its generic `audio_anomaly` label maps to family `violence_or_hazard` and can never match a `security`/`hazard` ground truth (`core/taxonomy.py:20`). This is a **label-space mismatch**, not a measurement of detection quality — a perfect DSP detector still scores zero.

To make the comparison meaningful, either (a) score DSP mode against a **detection-only** ground truth ("was there an acoustic event in this window", ignoring class), reporting it as a separate detection-versus-classification analysis, or (b) drop the comparison and instead report YAMNet's per-class precision/recall on the ESC-50 clips directly. Presenting a 0.0-versus-0.8 gap caused by label vocabulary as "the most quantitatively dramatic result in the v2 campaign" (`results/evaluation_campaign_v2_notes.md`) will not survive questioning.

### B14. Bound the unbounded state
**Priority: Nice-to-have · Effort: Low**

`ZoneRuleEngine._fired`, `_dwell`, `_static_objects` (`camera_agent.py:57-59`) and `CoordinatorAgent._verifications` (`coordinator_agent.py:35`) grow without eviction. Fine for 60-second clips, a leak for the continuous operation the thesis argues for. Add time-based eviction and a unit test that runs 10,000 synthetic frames and asserts bounded memory.

### B15. Make message schemas forward-compatible
**Priority: Nice-to-have · Effort: Low**

`Event.from_json` is `Event(**json.loads(s))` (`bus.py:65-67`), which raises on any unknown key. Add a filtered constructor that ignores unknown fields, or move to a schema library with explicit versioning. Add a `schema_version` field. The 400+ archived run JSONs are cited evaluation artefacts and currently cannot be read by any future schema.

---

## C. Bugs, code smells, and architectural weaknesses

| # | Location | Problem | Why it matters | Recommended fix | Priority · Effort |
|---|---|---|---|---|---|
| C1 | `aura_mas/agents/camera_agent.py:318` + `coordinator_agent.py:54-59` | `fov_overlap` is read but never written; `o` is always `0.5` | Auction degenerates to round-robin; contribution C2's core claim is untestable | Populate `fov_overlap` in the task; add a unit test | Critical · Medium |
| C2 | `aura_mas/scenarios/replay.py:108` | `realtime = mode != "centralized"` couples pacing to architecture | Confounds RQ1's latency result | Separate `--realtime` flag; add `centralized-paced` cell | Critical · Low |
| C3 | `aura_mas/agents/camera_agent.py:340-341` | `self._last_frame` read cross-thread without a lock, and it is the *current* frame, not the incident frame | Verification checks the wrong image; data race | Locked ring buffer keyed by timestamp | Critical · Medium |
| C4 | `aura_mas/eval/metrics.py:40-52` | Greedy first-fit matching on family only, fixed ±5 s tolerance | Cannot distinguish event types; 73 % acceptance window on `demo_site_01`; order-dependent | Hungarian assignment; exact-type mode; duration-scaled tolerance | Critical · Medium |
| C5 | `aura_mas/eval/metrics.py:60,76` | `false_alerts_per_hour` extrapolates from ~10 s runs | Produces 358–377 "alerts/hour" from 1 false positive | Report counts; per-hour only over ≥1 h aggregate | High · Low |
| C6 | `aura_mas/agents/fusion_agent.py:84-88` | Noisy-OR treats repeated events from the same sensor/track as independent | Confidence saturates to ~1.0 on any busy scene | Deduplicate by `(sensor_id, track_id, event_type)` within the window before fusing; or cap per-sensor contribution | High · Medium |
| C7 | `aura_mas/agents/fusion_agent.py:89-92` | `+0.05` bonuses added after the noisy-OR | Output is no longer a probability under any model | Either fold corroboration into the weights, or rename the output "score" and drop probabilistic language | High · Low |
| C8 | `aura_mas/agents/fusion_agent.py:68`, `agents/policy_agent.py:73` | Fusion window and cooldown use wall-clock time while rules use video time | Different effective temporal width per mode | Pass a scenario clock; use video time consistently | Critical · Medium |
| C9 | `aura_mas/agents/coordinator_agent.py:90` | Fixed `time.sleep(bid_window)` regardless of bids received | 1 s of dead latency in every auction; inflates auction TTA | Wait for quorum or timeout | High · Low |
| C10 | `aura_mas/agents/coordinator_agent.py:51-82` called from `policy_agent.py:58` | `request_verification` blocks the FusionAgent tick thread for up to 4 s | One slow verification stalls all hypothesis flushing site-wide | Move verification to a worker; make `on_hypothesis` non-blocking | High · Medium |
| C11 | `aura_mas/core/bus.py:230` | Audit path derived by `jsonl_path.replace("alerts","audit")` | Silently wrong for any path containing "alerts" elsewhere | Pass the audit path explicitly | Nice-to-have · Low |
| C12 | `aura_mas/core/bus.py:65-67` | `Event(**json.loads(s))` raises on unknown fields | Archived run artefacts become unreadable after any schema change | Filtered constructor + `schema_version` | Nice-to-have · Low |
| C13 | `aura_mas/scenarios/replay.py:96-101` | `store.append` monkey-patched to capture timing | Measured path differs from production path | Add a first-class hook or callback on `AlertStore` | Nice-to-have · Low |
| C14 | `aura_mas/agents/camera_agent.py:57-59`, `coordinator_agent.py:35` | Unbounded dictionaries and sets | Memory leak under continuous operation | Time-based eviction + a long-run test | Nice-to-have · Low |
| C15 | `aura_mas/core/bus.py:246-258` | `make_bus("auto")` silently degrades MQTT → LocalBus | The same class of silent fallback that hid the dead YAMNet URL for an unknown period | Log at WARNING (done) *and* record the resolved transport in the run JSON | High · Low |
| C16 | `aura_mas/core/privacy.py:41-42` | If OpenCV lacks `HOGDescriptor`, the whole frame is blurred | Correct fail-closed behaviour, but silently destroys evidence utility with no signal | Emit a metric counting fail-closed anonymisations; assert it is 0 in campaign runs | High · Low |
| C17 | `aura_mas/agents/camera_agent.py:344-349` | `_verify` always counts `person` detections regardless of hypothesis type | Verifying an `abandoned_object` or `audio_alarm` asks an unrelated question | Dispatch the verification predicate on `event_type` | High · Medium |
| C18 | `docker-compose.yml` | Mosquitto with `mosquitto-no-auth.conf`; Redis with no password; both on host ports | Unauthenticated transport in a system whose thesis argues governance | Add credentials and TLS, or state the limitation explicitly in the manuscript | High · Low |
| C19 | Repository root | 14 `.py` files duplicated with pre-fix logic; a failed second LaTeX build | Anyone can silently run the wrong version | Quarantine to `legacy/` or delete | High · Low |
| C20 | `aura_mas/agents/camera_agent.py:76-80` | Intrusion event confidence is the **detector's** box confidence | A detector confidence is not a probability that an intrusion occurred; it then feeds the noisy-OR as if it were | Separate detection confidence from event confidence; calibrate | High · Medium |
| C21 | `aura_mas/agents/camera_agent.py:82-88` | `_dwell` is reset whenever a track leaves the polygon for one frame | A single missed detection resets the loitering timer, so the rule effectively requires 8 s of unbroken tracking | Add a grace period / hysteresis on zone exit | High · Low |
| C22 | `aura_mas/scripts/run_campaign.py:88-92` | Resume-by-file-existence with no content or version check | A run from an older code version is silently kept and pooled | Store a code-version hash in the run JSON and invalidate on mismatch | High · Low |

---

## D. Feature and extension proposals — to reach state-of-the-art level

Ordered by contribution-per-effort.

### D1. Evaluate on a public benchmark
**Priority: Critical · Effort: High**

The single largest gap between this work and the literature is that **no number in it is comparable to anything published**. Pick one and run it:
- **UCF-Crime** or **XD-Violence** for anomaly detection, reporting frame-level AUC / Average Precision. XD-Violence is the natural choice because it is audio-visual and directly exercises RQ3.
- **MTMMC** or **AI City Challenge Track 1** if the multi-camera coordination story is to be defended.
- Even a **subset** with a clearly stated protocol converts the thesis from "internally consistent demo" to "positioned work". `research/.../findings/F6` and `EXECUTION_PLAN.md §3` already identify this as the top gap.

### D2. Adopt latency-aware and annotation-robust metrics
**Priority: High · Effort: Medium**

Implement **Latency-aware Average Precision (LaAP)** alongside the existing mean time-to-alert. This gives the latency argument — which is the strongest architectural claim available — a citable, comparable instrument instead of a bespoke one. Also compute **inter-annotator agreement (Fleiss' kappa)** by having a second person independently annotate the scenario manifests; the current ground truth was authored by the same process that ran the experiment, which is a construct-validity problem the current chapter does not acknowledge.

### D3. Replace the CLIP prompt set with a domain-matched, calibrated scorer
**Priority: High · Effort: Medium**

AUC = 0.308 with prompts describing indoor warehouses tested on outdoor street footage is a fixable prompt-engineering failure, not a fundamental one. Steps: rewrite prompts to match the actual scenes; use prompt ensembling (multiple paraphrases averaged); calibrate the score with Platt scaling or isotonic regression on a held-out split; report AUC before and after. A move from 0.308 to a plausible 0.65–0.75 is a real, reportable result and rescues a component currently worth nothing.

### D4. Add a second, stronger coordination baseline
**Priority: High · Effort: Medium**

Round-robin and "off" are weak baselines. Add **greedy-by-utility** (no auction, coordinator computes utilities centrally) and, if time permits, **Hungarian assignment** over a utility matrix. Then the auction is compared against the centralized-optimal allocation it claims to approximate at lower communication cost — which is the actual research question, and it makes the O(n)-messages argument measurable rather than asserted.

### D5. Add `contributing_types` to the Alert schema
**Priority: High · Effort: Low**

`Hypothesis.dominant_type()` (`fusion_agent.py:42-44`) returns a single winner, so a genuinely cross-modal alert is labelled `intrusion` and the audio contribution is invisible except in the confidence value — the team documents this in `THESIS_REPATCH.md` Priority 1. Add `contributing_types`, `contributing_modalities`, and per-modality confidence to `Alert`. This makes C3 demonstrable in the alert log itself, fixes part of the metric-matching problem, and is an hour of work.

### D6. Add an explanation-quality evaluation
**Priority: High · Effort: Medium**

Beyond guardrail rejection rate (B5): a rubric-scored evaluation of 30–50 explanations on completeness, factual grounding, actionability and absence of identity speculation, scored by two independent raters plus an LLM-as-judge for scale, with agreement reported. This is what turns C4 from an architectural assertion into an evaluated contribution.

### D7. Add adversarial and robustness probes
**Priority: Nice-to-have · Effort: Medium**

- **Sensor dropout**: kill a camera agent mid-run and measure graceful degradation. The thesis claims robustness (`chapter2.tex:34`) and never tests it.
- **Prompt injection** through event `extra` fields into the ExplanationAgent.
- **Adversarial audio**: does a siren-like distractor cause a false `audio_alarm`?
- **Domain shift**: run the same scenarios on night footage or a different camera.

Each of these produces a figure and directly addresses a claim currently made without evidence.

### D8. Scale the scenario corpus and formalise generation
**Priority: High · Effort: High**

9 scenarios totalling a few minutes of footage cannot support statistical claims. Either build 30–50 scenarios from a public corpus, or generate them: `aura_mas/scripts/make_synthetic_clips.py` already exists as a seed. Synthetic scenario generation with programmatically-known ground truth would also eliminate the annotation-validity problem and is itself a defensible methodological contribution.

### D9. Consider a small on-device VLM for the description node
**Priority: Nice-to-have · Effort: Medium**

The `_describe` node (`explanation_agent.py:82-105`) currently sends base64 JPEGs to an external endpoint — which contradicts the "raw frames never leave the edge" claim in `chapter4.tex:9` (the frames are anonymised, but they are still images leaving the site). A small local vision-language model would make the privacy claim consistent end-to-end and is a good discussion point.

### D10. Publish the evaluation harness as an artefact
**Priority: Nice-to-have · Effort: Medium**

`run_campaign.py` + `metrics.py` + the manifest format + `methodology_changes.md` constitute a reusable system-level evaluation kit for multi-agent surveillance. The literature explicitly names evaluation standardisation as an open challenge. Released with documentation and a licence, this is plausibly the most citable output of the whole project.

---

## E. Technologies, frameworks, models, and techniques to adopt

Each line: what, and why it fits *this* project specifically.

**Evaluation and statistics**
| Technology | Why it fits here | Priority · Effort |
|---|---|---|
| `scipy.stats` (Wilcoxon signed-rank, bootstrap) | The campaign already produces paired `(scenario, repetition)` observations across 4 modes — exactly the design these tests are for. | Critical · Low |
| Hungarian algorithm via `scipy.optimize.linear_sum_assignment` | Replaces the greedy alert-to-ground-truth matcher whose order-dependence the team already documented. | Critical · Low |
| Latency-aware Average Precision (LaAP) | Gives the project's strongest claim (latency) a metric the VAD community recognises. | High · Medium |
| TrackEval (HOTA / MOTA / IDF1) | The thesis cites tracking metrics in `chapter3.tex:16` but reports none; ByteTrack quality directly bounds every zone rule. | High · Medium |
| `cloc` | Verifies the "2,500 lines" claim in `chapter5.tex:6`, currently unsubstantiated. | Nice-to-have · Low |

**Perception**
| Technology | Why it fits here | Priority · Effort |
|---|---|---|
| YOLO11s / YOLO11m as a perception-ceiling ablation | `chapter6.tex:107` names the perception ceiling as a limitation; swapping the model size measures it in one afternoon. | High · Low |
| RT-DETR | Already cited in `chapter3.tex:10` as a "drop-in upgrade path" — actually dropping it in validates the claim that agents encapsulate their detector. | Nice-to-have · Medium |
| Open-vocabulary detection (YOLO-World / Grounding DINO) | Would let zone rules reference arbitrary object classes ("ladder in restricted area") without retraining — a genuine capability extension consistent with the zero-training stance. | Nice-to-have · Medium |
| ONNX Runtime / OpenVINO | Needed to make the "edge-first" claim measurable on a single-board computer (B12); YOLO11n exports cleanly. | High · Medium |
| Platt scaling / isotonic regression | Converts detector and CLIP scores into calibrated probabilities, which is a precondition for the noisy-OR to mean anything. | High · Medium |

**Audio**
| Technology | Why it fits here | Priority · Effort |
|---|---|---|
| PANNs or BEATs as a YAMNet alternative | Turns the audio-backend ablation into a real model comparison rather than a label-space artefact (B13). | High · Medium |
| DCASE task protocol + ESC-50 held-out split | Gives per-class audio precision/recall against a community protocol instead of three self-authored clips. | High · Medium |

**Agent and LLM stack**
| Technology | Why it fits here | Priority · Effort |
|---|---|---|
| Ollama + a small instruct model (7–8B) | Lets B5 run the LLM path with zero cost and zero data egress, making RQ4 evaluable. | Critical · Low |
| LangGraph | `chapter4.tex:118` says the explanation pipeline is "implementable in LangGraph"; actually using it gives checkpointing and a typed state graph, and makes the "state machine" description literally true. | Nice-to-have · Medium |
| Structured output / JSON-schema-constrained decoding | Removes the schema-completeness class of guardrail rejections, isolating the *grounding* failures that are the interesting measurement. | High · Low |
| An LLM-as-judge harness | Scales explanation-quality scoring (D6) beyond what two human raters can cover. | High · Medium |

**Engineering**
| Technology | Why it fits here | Priority · Effort |
|---|---|---|
| `pyproject.toml` + `uv` lockfile | Pins the exact environment that produced 373 runs; currently unreproducible. | High · Low |
| `ruff` + `mypy` + `pytest-cov` in GitHub Actions | Turns "6/6 tests pass" into a verifiable artefact and catches the duplicate-file drift class of problem. | High · Low |
| `hydra` or `pydantic-settings` for configuration | Implements the `configs/` layer the README and `chapter5.tex:50` already promise, and makes threshold sweeps one command. | High · Medium |
| `psutil` + `tracemalloc` instrumentation | Produces the per-agent CPU/memory/frames-per-second numbers the "edge-first" claim needs. | High · Low |
| MQTT over TLS with credentials; Redis ACLs | Makes the transport consistent with the governance argument in `chapter4.tex` Table `tab:privacy`. | High · Low |
| DVC or a plain manifest with checksums for `data/clips_real/` | The clips are cited evaluation artefacts; their provenance and integrity should be verifiable, and the manifest should be cited in the manuscript. | High · Low |

---

## F. Suggested execution order

A realistic sequencing given that the thesis is the deliverable, not the code.

**Days 1–2 (all Critical, all Low effort — do these first, they are cheap and they are the ones that end a defence badly):**
A9 authorship · A7 disclose CLIP AUC · A3 fix or disclose the loitering ground truth · B1 seed control · B2 paced baseline flag · B9 quarantine duplicates · C2, C9, C15, C16.

**Days 3–6 (Critical, Medium):**
B3 wire up field-of-view overlap · C8 unify the time base · A4/C4 fix the matcher · A6 statistics · B5 run the explanation layer against a local model.

**Days 7–10:**
Re-run the full campaign with the fixes (the harness makes this cheap — `run_campaign.py` resumes and isolates) · A1 rewrite chapter 6 from the new data · A2 and A12 threats to validity · A13 the missing ablations.

**Days 11–14:**
A8 bibliography verification (tedious; can run in parallel with the campaign) · A10 update related work · A11 ethics and governance section · A14 reposition the novelty claim.

**Beyond, if time exists:**
D1 a public benchmark · D2 LaAP · D3 fix CLIP · B6 the MQTT/Redis campaign cell · B12 edge resource measurement.

---

## Sources consulted for the state-of-the-art positioning

- [Agentic and LLM-Based Multimodal Anomaly Detection: Architectures, Challenges, and Prospects (Sensors, 2026)](https://www.mdpi.com/1424-8220/26/8/2330)
- [Glance, Scrutinize, and Think: Advancing Video Anomaly Detection from Training-Free to Agentic Reasoning (2026)](https://arxiv.org/html/2608.11260)
- [Rethinking Metrics and Benchmarks of Video Anomaly Detection (2025)](https://arxiv.org/html/2505.19022v1)
- [Holmes-VAU: Towards Long-term Video Anomaly Understanding at Any Granularity (CVPR 2025 Highlight)](https://github.com/pipixin321/HolmesVAU)
- [Holmes-VAD: Towards Unbiased and Explainable Video Anomaly Detection via Multi-modal LLM](https://arxiv.org/html/2406.12235)
- [AVAR-Net: A Lightweight Audio-Visual Anomaly Recognition Framework with a Benchmark Dataset (2025)](https://arxiv.org/html/2510.13630v1)
- [MTMMC: A Large-Scale Real-World Multi-Modal Camera Tracking Benchmark](https://arxiv.org/abs/2403.20225)
- [AI City Challenge 2026 — Track 1 (multi-camera 3D perception)](https://www.aicitychallenge.org/2026-track1/)
- [AI in CCTV: The Gap Between Perception and Reality — A Survey of Multimodal AI, RAG, and Agentic Frameworks in Video Surveillance Systems (Springer, 2026)](https://link.springer.com/chapter/10.1007/978-3-032-27927-9_29)
- [ConfidenceIntervals — bootstrap confidence interval computation for ML evaluation](https://github.com/luferrer/ConfidenceIntervals)
