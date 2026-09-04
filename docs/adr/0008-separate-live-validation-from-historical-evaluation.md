---
status: accepted
---

# Separate live validation from historical evaluation

New live, private-corpus, and multi-zone runs will form a separate evidence track and will never be pooled into the preserved 373-run campaign. New matching requires exact event type, Physical Zone when specified, and optimal one-to-one temporal assignment; detection latency and alert latency are reported separately, and false alerts per hour is used only on sufficiently long normal recordings.

## Considered Options

Appending new results to the existing aggregate would make the headline table larger but would mix changed code, schemas, scenarios, timing semantics, and hardware. Retaining the current family-level greedy matcher would preserve comparability but can credit the wrong event and wrong zone. Replacing the historical results would break the thesis audit trail.

## Consequences

Historical artefacts remain immutable and readable through legacy adapters. Every new run records the commit and dirty state, Policy Version, manifest and configuration checksums, dependencies, hardware, timestamps, and seeds. Three staged home repetitions are reported as raw deployment outcomes, not statistically reliable accuracy.
