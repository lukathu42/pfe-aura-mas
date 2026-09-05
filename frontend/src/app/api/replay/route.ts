import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { PREPARED_REPLAYS_DIR, SCENARIOS_DIR } from "@/lib/paths";
import type { PreparedReplay, ReplayCatalogItem, ScenarioManifest } from "@/lib/types";

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

async function readManifest(name: string): Promise<ScenarioManifest | null> {
  try {
    const raw = await fs.readFile(path.join(SCENARIOS_DIR, `${name}.json`), "utf-8");
    const manifest = JSON.parse(raw) as ScenarioManifest;
    return manifest.name === name ? manifest : null;
  } catch {
    return null;
  }
}

function manifestCatalogItem(manifest: ScenarioManifest): ReplayCatalogItem {
  const dataset = manifest.dataset ?? "Scenario manifest";
  const anomalyKey = manifest.dataset
    ? manifest.dataset.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")
    : manifest.name;
  return {
    title: manifest.dataset ?? "Scenario manifest",
    anomaly_type: "scenario",
    anomaly_key: anomalyKey,
    sample_id: manifest.clip_id,
    sample_label: manifest.name,
    description: manifest.notes ?? `Scenario manifest for ${manifest.name}.`,
    dataset,
    attribution: "",
    tags: ["scenario manifest", ...(manifest.split ? [manifest.split] : [])],
    camera_count: manifest.sensors.filter((sensor) => sensor.type === "camera").length,
    scenario: manifest.name,
    mode: "manifest",
    duration_seconds: manifest.duration_seconds,
    replay_available: false,
  };
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
    // The scenario manifest catalogue is still useful when no replay directory exists.
  }
  const scenarios = new Map<string, ReplayCatalogItem>();
  for (const file of files) {
    const replay = await readReplay(file.replace(/\.json$/, ""));
    if (!replay) continue;
    scenarios.set(replay.scenario, {
      scenario: replay.scenario,
      mode: replay.mode,
      duration_seconds: replay.duration_seconds,
      replay_available: true,
      ...replay.metadata,
    });
  }

  try {
    const manifestFiles = (await fs.readdir(SCENARIOS_DIR))
      .filter((file) => file.endsWith(".json"))
      .sort();
    for (const file of manifestFiles) {
      const name = file.replace(/\.json$/, "");
      if (!scenarios.has(name)) {
        const manifest = await readManifest(name);
        if (manifest) scenarios.set(name, manifestCatalogItem(manifest));
      }
    }
  } catch {
    // Prepared replays remain available when scenario manifests cannot be read.
  }

  return NextResponse.json({ scenarios: [...scenarios.values()] });
}
