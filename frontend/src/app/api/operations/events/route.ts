import { NextResponse } from "next/server";
import { requestOperations } from "@/lib/operations-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const upstream = await requestOperations("/v1/events");
    if (!upstream.ok || !upstream.body) {
      return NextResponse.json({ error: "operational event stream unavailable" }, { status: 502 });
    }
    return new Response(upstream.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
      },
    });
  } catch {
    return NextResponse.json({ error: "operational service unavailable" }, { status: 503 });
  }
}
