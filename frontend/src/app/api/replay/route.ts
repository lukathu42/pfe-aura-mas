import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { PREPARED_REPLAYS_DIR } from "@/lib/paths";
import type { PreparedReplay, ReplayCatalogItem } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NAME_RE = /^[a-zA-Z0-9_-]+$/;

async function readReplay(name: string): Promise<PreparedReplay | null> {
  try {
    const raw = await fs.readFile(path.join(PREPARED_REPLAYS_DIR, `${name}.json`), "utf-8");
    const replay = JSON.parse(raw) as PreparedReplay;
    if (![1, 2].includes(replay.schema_version) || replay.scenario !== name) return null;
    return replay;
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  const name = request.nextUrl.searchParams.get("scenario");
  if (name) {
    if (!NAME_RE.test(name)) {
      return NextResponse.json({ error: "invalid scenario name" }, { status: 400 });
    }
    const replay = await readReplay(name);
    if (!replay) {
      return NextResponse.json({ error: "prepared replay not found" }, { status: 404 });
    }
    return NextResponse.json(replay);
  }

  let files: string[] = [];
  try {
    files = (await fs.readdir(PREPARED_REPLAYS_DIR))
      .filter((file) => file.endsWith(".json"))
      .sort();
  } catch {
    return NextResponse.json({ scenarios: [] as ReplayCatalogItem[] });
  }
  const scenarios: ReplayCatalogItem[] = [];
  for (const file of files) {
    const replay = await readReplay(file.replace(/\.json$/, ""));
    if (!replay) continue;
    scenarios.push({
      scenario: replay.scenario,
      mode: replay.mode,
      duration_seconds: replay.duration_seconds,
      ...replay.metadata,
    });
  }
  return NextResponse.json({ scenarios });
}
