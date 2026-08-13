# Explanation quality eval — findings (W3.6)

No LLM API key is configured in this environment (`OPENAI_API_KEY` unset), so
`ExplanationAgent` exercises its intended fallback path end-to-end — this is
the schedule's own documented fallback ("LLM API unavailable/cost ->
Template-based explanation generator"), not a workaround.

## Guardrail unit test

`aura_mas/tests/test_pipeline.py::test_explanation_guardrail_rejects_fabricated_evidence`
already covers the hallucination-probe requirement from W3.2 (passes, part of
the 6/6 suite). Not re-derived here.

## Evidence-completeness check on real alerts

Ran `demo_site_01` under `mas-auction` with `--llm` (2026-08-13). All 3 real
alerts produced went through `ExplanationAgent._fallback()` (no LLM
reachable), and in every case the explanation's cited evidence IDs matched
`alert.fused_events` exactly — no missing IDs, no fabricated ones:

| alert | fused_events | cited in explanation |
|---|---|---|
| intrusion zone_B conf=0.75 | `ev_78b30bf229` | `ev_78b30bf229` |
| intrusion zone_A conf=0.52 | `ev_cc16b67e4b` | `ev_cc16b67e4b` |
| intrusion zone_A conf=0.96 | `ev_fe1a9592f4, ev_e47b923005, ev_bddb1408c2` | same 3, same order |

3/3 evidence-complete. This is a small sample (one scenario, one run) --
sufficient to confirm the fallback path behaves correctly, not a substitute
for the fuller "hallucination rate on 20 alerts" rubric the schedule
describes for when a real LLM is available. That fuller pass needs an actual
API key/local model (Qwen2.5-VL via Ollama is the schedule's own suggested
fallback-of-the-fallback) and is out of scope here.
