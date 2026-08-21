import { subscribeToBus } from "@/lib/bus";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const TOPIC_KIND: Record<string, string> = {
  "site/events": "event",
  "site/coordination/tasks": "task",
  "site/coordination/bids": "bid",
  "site/coordination/awards": "award",
  "site/coordination/verifications": "verification",
};

// Server-Sent Events relay: one shared MQTT connection (lib/bus.ts) fans
// out to every connected browser tab as its own SSE stream, rather than
// each tab opening its own MQTT connection.
export async function GET(request: Request) {
  const encoder = new TextEncoder();
  let unsubscribe: (() => void) | null = null;
  let heartbeat: ReturnType<typeof setInterval> | null = null;

  const stream = new ReadableStream({
    start(controller) {
      const send = (event: string, data: unknown) => {
        try {
          controller.enqueue(
            encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
          );
        } catch {
          // controller already closed (client disconnected mid-flush)
        }
      };

      unsubscribe = subscribeToBus(
        (topic, payload) => {
          const kind = TOPIC_KIND[topic];
          if (!kind) return;
          let parsed: unknown;
          try {
            parsed = JSON.parse(payload);
          } catch {
            return;
          }
          send(kind, parsed);
        },
        (connected) => send("status", { mqtt: connected }),
      );

      heartbeat = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(": ping\n\n"));
        } catch {
          // ignore
        }
      }, 15000);
    },
    cancel() {
      if (unsubscribe) unsubscribe();
      if (heartbeat) clearInterval(heartbeat);
    },
  });

  request.signal.addEventListener("abort", () => {
    if (unsubscribe) unsubscribe();
    if (heartbeat) clearInterval(heartbeat);
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
