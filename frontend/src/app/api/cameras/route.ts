import fs from "node:fs/promises";
import { NextResponse } from "next/server";
import { LIVE_CAMERA_HEALTH_PATH } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const value = JSON.parse(await fs.readFile(LIVE_CAMERA_HEALTH_PATH, "utf8"));
    return NextResponse.json({ schema_version: 1, generated_at: value.generated_at, cameras: value.cameras ?? [] });
  } catch {
    return NextResponse.json({ schema_version: 1, cameras: [] });
  }
}
