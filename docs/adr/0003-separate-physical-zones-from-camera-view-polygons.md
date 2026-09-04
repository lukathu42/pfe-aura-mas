---
status: accepted
---

# Separate Physical Zones from Camera View Zones

AURA-MAS will identify a real monitored location with a stable Physical Zone ID and map each camera-specific polygon to that ID through a Camera View Zone. Fusion, incident association, policy ownership, search, and operator reporting use the Physical Zone ID; geometric rules evaluate the corresponding Camera View Zone. Two polygons are never treated as observing the same place merely because their display names match.

## Considered Options

Keeping the existing single `zone` string would be simpler but can silently merge unrelated camera views and cannot represent two geometrically different views of one place. Treating every polygon as a separate zone would prevent cross-camera verification of the same physical occurrence.

## Consequences

Event and configuration schemas need backward-compatible physical-zone and camera-view identifiers. Archived artefacts that contain only `zone` remain legacy records and must not be silently reinterpreted as verified cross-camera observations. An Incident may associate compatible observations from multiple cameras within its configured association window only when their Camera View Zones map to the same Physical Zone.
