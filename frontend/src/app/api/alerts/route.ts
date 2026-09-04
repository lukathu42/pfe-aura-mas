import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { getAlertOverlay, getRedis } from "@/lib/redis";
import { DATA_ROOT } from "@/lib/paths";
import type { Alert } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ALERT_STREAM = "aura:alerts";
const AUDIT_STREAM = "aura:audit";

function fieldsToMap(fields: string[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (let i = 0; i < fields.length; i += 2) map[fields[i]] = fields[i + 1];
  return map;
}

function applyOverlay(alert: Alert, overlay: Map<string, "ACKNOWLEDGED" | "DISMISSED">): Alert {
  const overridden = overlay.get(alert.alert_id);
  return overridden ? { ...alert, status: overridden } : alert;
}

function sortAlerts(alerts: Alert[]): Alert[] {
  return [...alerts].sort((a, b) => {
    const aPriority = a.priority_score ?? -1;
    const bPriority = b.priority_score ?? -1;
    if (aPriority !== bPriority) return bPriority - aPriority;
    return b.timestamp - a.timestamp;
  });
}

// aura_mas.scenarios.replay (the CLI everything in this repo actually runs
// through) constructs its AlertStore with redis_url=None — every alert from
// a replay run lands in data/alerts_<scenario>_<mode>.jsonl, never in Redis
// Streams. The Streamlit dashboard already handles this by reading Redis
// first and falling back to globbing those JSONL files
// (aura_mas/dashboard/app.py:32-43); this mirrors that exactly so alerts
// actually show up when the console is pointed at a real replay run.
const SCENARIO_RE = /^[a-zA-Z0-9_-]+$/;

async function readJsonlAlerts(scenario: string | null): Promise<Alert[]> {
  let files: string[];
  try {
    const prefix = scenario ? `alerts_${scenario}_` : "alerts_";
    files = (await fs.readdir(DATA_ROOT)).filter(
      (f) => f.startsWith(prefix) && f.endsWith(".jsonl"),
    );
  } catch {
    return [];
  }
  const alerts: Alert[] = [];
  for (const file of files) {
    try {
      const raw = await fs.readFile(path.join(DATA_ROOT, file), "utf-8");
      for (const line of raw.split("\n")) {
        if (!line.trim()) continue;
        try {
          alerts.push(JSON.parse(line) as Alert);
        } catch {
          // skip malformed line
        }
      }
    } catch {
      // skip unreadable file
    }
  }
  return sortAlerts(alerts);
}

// GET: prefers the real Redis stream AlertStore.append() writes to when
// something's actually there, otherwise falls back to the JSONL files a
// replay run actually produces (see readJsonlAlerts). Ack/dismiss overlay
// applies either way.
export async function GET(request: NextRequest) {
  const countParam = request.nextUrl.searchParams.get("count");
  const count = Math.min(Math.max(parseInt(countParam ?? "200", 10) || 200, 1), 500);
  const overlay = getAlertOverlay();
  const scenario = request.nextUrl.searchParams.get("scenario");
  if (scenario && !SCENARIO_RE.test(scenario)) {
    return NextResponse.json({ error: "invalid scenario name" }, { status: 400 });
  }

  const redisAlerts: Alert[] = [];
  let redisReachable = false;
  if (!scenario) {
    try {
      const redis = getRedis();
      const rows = await redis.xrevrange(ALERT_STREAM, "+", "-", "COUNT", count);
      redisReachable = true;
      for (const [, fields] of rows) {
        const raw = fieldsToMap(fields).json;
        if (!raw) continue;
        try {
          redisAlerts.push(JSON.parse(raw) as Alert);
        } catch {
          // skip malformed entry
        }
      }
    } catch {
      redisReachable = false;
    }
  }

  if (redisAlerts.length > 0) {
    return NextResponse.json({
      alerts: sortAlerts(redisAlerts).slice(0, count).map((a) => applyOverlay(a, overlay)),
      source: "redis" as const,
    });
  }

  const jsonlAlerts = await readJsonlAlerts(scenario);
  if (jsonlAlerts.length > 0) {
    return NextResponse.json({
      alerts: jsonlAlerts.slice(0, count).map((a) => applyOverlay(a, overlay)),
      source: "jsonl" as const,
    });
  }

  const emptyIsValid = Boolean(scenario) || redisReachable;
  return NextResponse.json(
    { alerts: [] as Alert[], source: emptyIsValid ? "empty" : "offline" },
    { status: emptyIsValid ? 200 : 503 },
  );
}

// POST {alert_id, action: "acknowledge" | "dismiss"} — mirrors the
// Streamlit dashboard's Acknowledge/Dismiss buttons: writes a durable
// audit entry (aura:audit, same shape AlertStore.audit() writes) and
// overlays the new status for subsequent GETs.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const alertId = typeof body?.alert_id === "string" ? body.alert_id : null;
  const action = body?.action;
  if (!alertId || (action !== "acknowledge" && action !== "dismiss")) {
    return NextResponse.json({ error: "invalid request" }, { status: 400 });
  }
  const status = action === "acknowledge" ? "ACKNOWLEDGED" : "DISMISSED";

  try {
    const redis = getRedis();
    const entry = {
      timestamp: Date.now() / 1000,
      actor: "operator",
      action,
      alert_id: alertId,
    };
    await redis.xadd(AUDIT_STREAM, "*", "json", JSON.stringify(entry));
    getAlertOverlay().set(alertId, status);
    return NextResponse.json({ alert_id: alertId, status });
  } catch {
    return NextResponse.json({ error: "bus offline" }, { status: 503 });
  }
}
