import { NextResponse } from "next/server";
import { forwardOperationsJson } from "@/lib/operations-server";
import { INCIDENT_ACTIONS } from "@/lib/operations";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const INCIDENT_ID = /^[A-Za-z0-9_-]+$/;

export async function GET() {
  return forwardOperationsJson("/v1/state");
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body || !INCIDENT_ID.test(body.incident_id ?? "")) {
    return NextResponse.json({ error: "invalid incident" }, { status: 400 });
  }
  const allowedActions = new Set<string>(INCIDENT_ACTIONS);
  if (!allowedActions.has(body.action)) {
    return NextResponse.json({ error: "invalid action" }, { status: 400 });
  }
  return forwardOperationsJson(`/v1/incidents/${encodeURIComponent(body.incident_id)}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action: body.action,
      actor: "operator",
      details: body.details ?? {},
    }),
  });
}
