---
name: F2_bousetouane_strongest_local_precedent
---
# F2 — Bousetouane (2015, PhD, Annaba) is the strongest local multi-agent surveillance precedent, and defines the bar a new contribution must clear

**Claim**: A 2015 PhD thesis in the parent Documents/ corpus already implements a genuine multi-agent architecture for surveillance: each camera is an autonomous "cognitive agent," coordination is via a formal consensus protocol (not ad hoc), validated on a real 7-camera ad-hoc wireless testbed (90.11% mean cross-camera re-identification rate). This is architecturally real MAS, not loose terminology.

**Evidence**: sources/05_these-bousetouane-fouad.md, verbatim quotes on the consensus algorithm (thesis eq. 5.10, printed p.139) and the explicit multi-agent framing (Résumé, printed p.2).

**What it does NOT do** (the gap a new thesis must fill to not be redundant): no deep learning (2015, classical GMM/particle-filter/Haralick-texture pipeline), no learning-based or LLM-based reasoning, no anomaly detection, no explainable/natural-language alerting, small self-collected evaluation (4 scenarios, 6 subjects, no public re-ID benchmark used), no confidence-weighted consensus (author's own named limitation), fragile to camera motion (author's own named limitation).

**Confidence**: High (full-text read, 6 tool-use passes, verbatim quotes with page numbers).

**Implication**: Any claim that "multi-agent coordination for surveillance" alone is novel must be qualified against this thesis. Novelty must sit in: (a) modern learned perception replacing classical CV, (b) learning/LLM-based agent reasoning replacing hard-coded consensus rules, (c) anomaly/explainable-alert generation (absent here entirely), (d) rigorous benchmark-grounded evaluation (absent here — self-collected only). See [[F4_monitorix_shows_mas_surveillance_is_25_years_old]] for the same conclusion at a broader literature level.
