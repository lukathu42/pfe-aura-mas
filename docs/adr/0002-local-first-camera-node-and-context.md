---
status: accepted
---

# Keep camera acquisition and contextual processing local-first

The Raspberry Pi 5 and Camera Module 2 will serve as a Camera Node that publishes a standards-based local-network stream, while the laptop performs primary vision inference, fusion, policy, persistence, and contextual search. Raw home footage will remain on the local network by default. Context Annotation will use the existing provider-neutral adapter and remain outside the alert-authority path; a cloud provider may be configured only as an explicit optional mode.

## Considered Options

Running the full pipeline on the Pi would strengthen the edge-computing story but risks sacrificing throughput and demo reliability without measurements. Making a cloud VLM mandatory would simplify access to capable models but would contradict the privacy boundary. Integrating Unblink as a second surveillance platform would duplicate AURA-MAS boundaries and introduce AGPL coupling; its incident-context and semantic-search ideas will instead inform native AURA-MAS capabilities.

## Consequences

The project must measure the Pi-to-alert path, clearly report where inference executes, and never describe capture-only operation as edge inference. VLM failures or delays cannot alter deterministic alert decisions.
