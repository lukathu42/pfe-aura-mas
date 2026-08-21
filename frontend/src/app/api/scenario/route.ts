import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { SCENARIOS_DIR } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_SCENARIO = process.env.AURA_SCENARIO || "combined_audio_video_01";
const NAME_RE = /^[a-zA-Z0-9_-]+$/;

export async function GET(request: NextRequest) {
  if (request.nextUrl.searchParams.has("list")) {
    try {
      const files = await fs.readdir(SCENARIOS_DIR);
      const names = files
        .filter((f) => f.endsWith(".json"))
        .map((f) => f.replace(/\.json$/, ""))
        .sort();
      return NextResponse.json({ scenarios: names });
    } catch {
      return NextResponse.json({ scenarios: [] });
    }
  }

  const name = request.nextUrl.searchParams.get("name") || DEFAULT_SCENARIO;
  if (!NAME_RE.test(name)) {
    return NextResponse.json({ error: "invalid scenario name" }, { status: 400 });
  }
  const filePath = path.join(SCENARIOS_DIR, `${name}.json`);
  try {
    const raw = await fs.readFile(filePath, "utf-8");
    return new NextResponse(raw, { headers: { "Content-Type": "application/json" } });
  } catch {
    return NextResponse.json({ error: "scenario not found" }, { status: 404 });
  }
}
