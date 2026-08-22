/** Build a URL through the scoped /api/media route for a repo-root-relative
 * path already stored on Alert.evidence / ScenarioSensor.source (e.g.
 * "data/evidence/cam_01_x.jpg", "data/clips/people.mp4"). */
export function mediaUrl(storedPath: string): string {
  const clean = storedPath.replace(/^\/+/, "");
  return `/api/media/${clean.split("/").map(encodeURIComponent).join("/")}`;
}

export function formatClock(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toISOString().split("T")[1].slice(0, 8) + "Z";
}

export function formatLocalTime(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleTimeString([], {
    hour12: false,
  });
}
