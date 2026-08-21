import Redis from "ioredis";

const REDIS_URL = process.env.AURA_REDIS_URL || "redis://localhost:6379";

declare global {
  var __auraRedis: Redis | undefined;
}

export function getRedis(): Redis {
  if (!globalThis.__auraRedis) {
    const client = new Redis(REDIS_URL, {
      maxRetriesPerRequest: 1,
      retryStrategy: () => 2000,
      lazyConnect: false,
    });
    client.on("error", () => {
      // Swallowed deliberately — callers probe liveness per-request via
      // ping()/command failure, not via a persistent error listener; an
      // unhandled 'error' event would otherwise crash the Node process.
    });
    globalThis.__auraRedis = client;
  }
  return globalThis.__auraRedis;
}

/** In-memory ack/dismiss overlay. Alert.status in the Redis stream itself
 * is immutable (streams are append-only, same as the existing Streamlit
 * dashboard's approach) — operator actions are tracked here and replayed
 * on top of freshly-read alerts, and durably logged to aura:audit. This
 * overlay resets on server restart, matching Streamlit's session-state
 * behavior today. */
declare global {
  var __auraAlertOverlay: Map<string, "ACKNOWLEDGED" | "DISMISSED"> | undefined;
}

export function getAlertOverlay(): Map<string, "ACKNOWLEDGED" | "DISMISSED"> {
  if (!globalThis.__auraAlertOverlay) {
    globalThis.__auraAlertOverlay = new Map();
  }
  return globalThis.__auraAlertOverlay;
}
