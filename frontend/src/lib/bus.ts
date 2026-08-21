import mqtt, { type MqttClient } from "mqtt";
import { EventEmitter } from "node:events";

const MQTT_URL = process.env.AURA_MQTT_URL || "mqtt://localhost:1883";

const TOPICS = [
  "site/events",
  "site/coordination/tasks",
  "site/coordination/bids",
  "site/coordination/awards",
  "site/coordination/verifications",
] as const;

interface BusState {
  client: MqttClient;
  emitter: EventEmitter;
  connected: boolean;
}

// Survive Next.js dev-mode module reloads with a single shared MQTT
// connection instead of opening a new one per hot-reload / per SSE client.
declare global {
  var __auraBus: BusState | undefined;
}

function getBus(): BusState {
  if (!globalThis.__auraBus) {
    const emitter = new EventEmitter();
    emitter.setMaxListeners(0);
    const client = mqtt.connect(MQTT_URL, {
      reconnectPeriod: 2000,
      connectTimeout: 4000,
    });
    const state: BusState = { client, emitter, connected: false };

    client.on("connect", () => {
      state.connected = true;
      client.subscribe(TOPICS as unknown as string[], { qos: 1 });
      emitter.emit("_status", true);
    });
    client.on("close", () => {
      state.connected = false;
      emitter.emit("_status", false);
    });
    client.on("error", () => {
      state.connected = false;
      emitter.emit("_status", false);
    });
    client.on("message", (topic, payload) => {
      emitter.emit("message", { topic, payload: payload.toString("utf-8") });
    });

    globalThis.__auraBus = state;
  }
  return globalThis.__auraBus;
}

export function isMqttConnected(): boolean {
  return getBus().connected;
}

/** Subscribe to relayed bus messages + connectivity flips. Returns an
 * unsubscribe function — callers (SSE route handlers) must call it when
 * the client disconnects, or listeners accumulate for the process lifetime. */
export function subscribeToBus(
  onMessage: (topic: string, payload: string) => void,
  onStatus: (connected: boolean) => void,
): () => void {
  const bus = getBus();
  const msgHandler = (m: { topic: string; payload: string }) =>
    onMessage(m.topic, m.payload);
  const statusHandler = (c: boolean) => onStatus(c);

  bus.emitter.on("message", msgHandler);
  bus.emitter.on("_status", statusHandler);
  onStatus(bus.connected);

  return () => {
    bus.emitter.off("message", msgHandler);
    bus.emitter.off("_status", statusHandler);
  };
}
