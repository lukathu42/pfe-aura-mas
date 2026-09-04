import path from "node:path";

// frontend/ is a sibling of scenarios/ and data/ at the repo root — this
// file only ever runs server-side (Node route handlers), where
// process.cwd() is the frontend/ package dir `next dev`/`next start` was
// launched from.
export const REPO_ROOT = path.resolve(process.cwd(), "..");
export const SCENARIOS_DIR = path.join(REPO_ROOT, "scenarios");
export const DATA_ROOT = path.join(REPO_ROOT, "data");
export const PREPARED_REPLAYS_DIR = path.join(REPO_ROOT, "results", "prepared_replays");
export const SEARCH_DOCUMENTS_PATH = path.join(REPO_ROOT, "results", "search_documents.jsonl");
export const LIVE_CAMERA_HEALTH_PATH = path.join(REPO_ROOT, "results", "live_camera_health.json");

/**
 * Resolve a catch-all route path (already split on "/") against the repo's
 * data/ directory, refusing anything that would escape it (e.g. "..", an
 * absolute path snuck through a param). Evidence/clip paths stored in
 * Alert.evidence / ScenarioSensor.source already start with "data/..." —
 * pass their segments straight through.
 */
export function resolveDataPath(segments: string[]): string | null {
  if (!segments.length || segments.some((s) => s === "" || s === "." || s === "..")) {
    return null;
  }
  const resolved = path.resolve(REPO_ROOT, ...segments);
  if (resolved === DATA_ROOT || resolved.startsWith(DATA_ROOT + path.sep)) {
    return resolved;
  }
  return null;
}
