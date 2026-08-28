import fs from "node:fs/promises";
import { NextResponse } from "next/server";
import { LIVE_CAMERA_HEALTH_PATH } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: RouteContext<"/api/cameras/[id]/stream">) {
  const { id } = await context.params;
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return new NextResponse("invalid camera", { status: 400 });
  let port = 8080;
  try {
    const health = JSON.parse(await fs.readFile(LIVE_CAMERA_HEALTH_PATH, "utf8"));
    if (!(health.cameras ?? []).some((camera: { id: string }) => camera.id === id)) {
      return new NextResponse("camera not found", { status: 404 });
    }
    if (Number.isInteger(health.mjpeg_port) && health.mjpeg_port > 0 && health.mjpeg_port < 65536) port = health.mjpeg_port;
  } catch {
    return new NextResponse("camera service unavailable", { status: 503 });
  }
  try {
    const upstream = await fetch(`http://127.0.0.1:${port}/stream/${encodeURIComponent(id)}`, { cache: "no-store" });
    if (!upstream.ok || !upstream.body) return new NextResponse("stream unavailable", { status: 502 });
    return new Response(upstream.body, { headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "multipart/x-mixed-replace; boundary=--frame",
      "Cache-Control": "no-store",
    }});
  } catch {
    return new NextResponse("camera service unavailable", { status: 503 });
  }
}
