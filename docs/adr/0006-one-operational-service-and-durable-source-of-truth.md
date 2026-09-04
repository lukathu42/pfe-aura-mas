---
status: accepted
---

# Use one Python operational service and one durable source of truth

A long-running Python API service will own Monitoring Sessions, camera health, policies, Incidents, operator commands, context jobs, search, and telemetry. SQLite in WAL mode is the canonical operational store and the filesystem holds checksum-addressed evidence; MQTT carries sensor traffic, Redis Streams optionally fans out live records, and JSONL is an export format. Next.js and Streamlit are clients and cannot own independent workflow state.

## Considered Options

Preserving direct Next.js access to Redis, JSONL, and in-memory overlays would avoid a new API layer but perpetuate inconsistent state. PostgreSQL would be appropriate at larger deployment scale but adds avoidable operational cost for one defense workstation. Treating Redis or JSONL as the database would weaken relational workflow guarantees and querying.

## Consequences

The service exposes REST commands and Server-Sent Events while video initially remains MJPEG. Historical Alert and result artefacts remain unchanged and are exposed through read-only Legacy Observation adapters; absent Session Modes and Physical Zone mappings remain unknown. Evidence files are referenced by IDs and checksums rather than stored as database blobs.
