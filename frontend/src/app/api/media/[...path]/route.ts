import { NextRequest } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";
import { resolveDataPath } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const CONTENT_TYPES: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".mp4": "video/mp4",
  ".mov": "video/quicktime",
  ".avi": "video/x-msvideo",
  ".wav": "audio/wav",
  ".mp3": "audio/mpeg",
};

// Scoped file server for the two things the console legitimately needs
// from local disk: already-blurred evidence JPEGs (data/evidence/) and
// scenario source clips (data/clips*/) — both referenced by paths already
// stored relative to the repo root in Alert.evidence / ScenarioSensor.source.
// resolveDataPath() refuses anything that would resolve outside data/.
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path: segments } = await params;
  const resolved = segments ? resolveDataPath(segments) : null;
  if (!resolved) {
    return new Response("Forbidden", { status: 403 });
  }

  let stat;
  try {
    stat = await fs.stat(resolved);
  } catch {
    return new Response("Not found", { status: 404 });
  }
  if (!stat.isFile()) {
    return new Response("Not found", { status: 404 });
  }

  const ext = path.extname(resolved).toLowerCase();
  const contentType = CONTENT_TYPES[ext] ?? "application/octet-stream";
  const range = request.headers.get("range");

  if (range) {
    const match = /bytes=(\d*)-(\d*)/.exec(range);
    const start = match?.[1] ? parseInt(match[1], 10) : 0;
    const end = match?.[2] ? parseInt(match[2], 10) : stat.size - 1;
    if (match && start <= end && end < stat.size) {
      const chunkSize = end - start + 1;
      const handle = await fs.open(resolved, "r");
      try {
        const buf = Buffer.alloc(chunkSize);
        await handle.read(buf, 0, chunkSize, start);
        return new Response(buf, {
          status: 206,
          headers: {
            "Content-Type": contentType,
            "Content-Range": `bytes ${start}-${end}/${stat.size}`,
            "Accept-Ranges": "bytes",
            "Content-Length": String(chunkSize),
            "Cache-Control": "no-store",
          },
        });
      } finally {
        await handle.close();
      }
    }
  }

  const data = await fs.readFile(resolved);
  return new Response(new Uint8Array(data), {
    headers: {
      "Content-Type": contentType,
      "Content-Length": String(stat.size),
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-store",
    },
  });
}
