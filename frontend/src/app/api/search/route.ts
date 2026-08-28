import fs from "node:fs/promises";
import { NextRequest, NextResponse } from "next/server";
import { SEARCH_DOCUMENTS_PATH } from "@/lib/paths";
import type { SearchResult } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type SearchDocument = Omit<SearchResult, "score"> & { search_text: string };

function tokens(value: string): string[] {
  return value.toLocaleLowerCase().match(/[\p{L}\p{N}_-]+/gu) ?? [];
}

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const query = (params.get("q") ?? "").trim().slice(0, 200);
  const limit = Math.min(100, Math.max(1, Number(params.get("limit")) || 20));
  const from = params.has("from") ? Number(params.get("from")) : null;
  const to = params.has("to") ? Number(params.get("to")) : null;
  if ((from !== null && !Number.isFinite(from)) || (to !== null && !Number.isFinite(to))) {
    return NextResponse.json({ error: "invalid time filter" }, { status: 400 });
  }
  let lines: string[];
  try {
    lines = (await fs.readFile(SEARCH_DOCUMENTS_PATH, "utf8")).split("\n").filter(Boolean);
  } catch {
    return NextResponse.json({ results: [], total: 0, index_available: false });
  }
  const queryTokens = tokens(query);
  const phrase = query.toLocaleLowerCase();
  const filters = {
    anomaly: params.get("anomaly"), scenario: params.get("scenario"),
    zone: params.get("zone"), sensor: params.get("sensor"),
  };
  const ranked: SearchResult[] = [];
  for (const line of lines) {
    let doc: SearchDocument;
    try { doc = JSON.parse(line) as SearchDocument; } catch { continue; }
    if (filters.anomaly && doc.anomaly_key !== filters.anomaly) continue;
    if (filters.scenario && doc.scenario !== filters.scenario) continue;
    if (filters.zone && doc.zone !== filters.zone) continue;
    if (filters.sensor && !doc.sensors.includes(filters.sensor)) continue;
    if (from !== null && doc.scene_time_seconds < from) continue;
    if (to !== null && doc.scene_time_seconds > to) continue;
    const haystack = doc.search_text.toLocaleLowerCase();
    if (queryTokens.some((token) => !haystack.includes(token))) continue;
    const exactPhrase = phrase && haystack.includes(phrase) ? 8 : 0;
    const titleHits = queryTokens.filter((token) => doc.title.toLocaleLowerCase().includes(token)).length;
    const eventHits = queryTokens.filter((token) => (doc.event_type ?? "").toLocaleLowerCase().includes(token)).length;
    const frequency = queryTokens.reduce((sum, token) => sum + haystack.split(token).length - 1, 0);
    ranked.push({ ...doc, score: Number((exactPhrase + titleHits * 4 + eventHits * 3 + frequency).toFixed(3)) });
  }
  ranked.sort((a, b) => b.score - a.score || a.scene_time_seconds - b.scene_time_seconds || a.document_id.localeCompare(b.document_id));
  return NextResponse.json({ results: ranked.slice(0, limit), total: ranked.length, index_available: true });
}
