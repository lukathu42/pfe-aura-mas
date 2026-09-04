import "server-only";

import { NextResponse } from "next/server";

const OPERATIONS_URL = process.env.AURA_OPERATIONS_URL ?? "http://127.0.0.1:8090";

export function requestOperations(path: string, init?: RequestInit) {
  return fetch(`${OPERATIONS_URL}${path}`, { ...init, cache: "no-store" });
}

export async function forwardOperationsJson(path: string, init?: RequestInit) {
  try {
    const response = await requestOperations(path, {
      ...init,
      signal: AbortSignal.timeout(2500),
    });
    const payload = await response.json().catch(() => ({ error: "invalid operational response" }));
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "operational service unavailable", active_session: null },
      { status: 503 },
    );
  }
}
