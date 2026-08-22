import { NextResponse } from "next/server";
import { isMqttConnected } from "@/lib/bus";
import { getRedis } from "@/lib/redis";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  let redis = false;
  try {
    redis = (await getRedis().ping()) === "PONG";
  } catch {
    redis = false;
  }
  return NextResponse.json({
    mqtt: isMqttConnected(),
    redis,
    timestamp: Date.now() / 1000,
  });
}
