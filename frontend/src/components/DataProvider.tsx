"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useState,
} from "react";
import type {
  Alert,
  AuraEvent,
  CoordinationAward,
  CoordinationBid,
  CoordinationRound,
  CoordinationTask,
  CoordinationVerification,
  ScenarioManifest,
} from "@/lib/types";

const MAX_EVENTS = 200;
const MAX_ROUNDS = 8;
const RECENT_EVENT_WINDOW_S = 20;

interface StreamState {
  events: AuraEvent[];
  rounds: CoordinationRound[];
  mqttConnected: boolean;
}

type StreamAction =
  | { type: "event"; payload: AuraEvent }
  | { type: "task"; payload: CoordinationTask }
  | { type: "bid"; payload: CoordinationBid }
  | { type: "award"; payload: CoordinationAward }
  | { type: "verification"; payload: CoordinationVerification }
  | { type: "status"; payload: { mqtt: boolean } };

function streamReducer(state: StreamState, action: StreamAction): StreamState {
  switch (action.type) {
    case "event":
      return {
        ...state,
        events: [action.payload, ...state.events].slice(0, MAX_EVENTS),
      };
    case "status":
      return { ...state, mqttConnected: action.payload.mqtt };
    case "task": {
      const round: CoordinationRound = {
        task: action.payload,
        bids: [],
        award: null,
        verification: null,
      };
      return { ...state, rounds: [round, ...state.rounds].slice(0, MAX_ROUNDS) };
    }
    case "bid": {
      const rounds = state.rounds.map((r) =>
        r.task.task_id === action.payload.task_id
          ? { ...r, bids: [...r.bids, action.payload] }
          : r,
      );
      return { ...state, rounds };
    }
    case "award": {
      const rounds = state.rounds.map((r) =>
        r.task.task_id === action.payload.task_id
          ? { ...r, award: action.payload }
          : r,
      );
      return { ...state, rounds };
    }
    case "verification": {
      const rounds = state.rounds.map((r) =>
        r.task.task_id === action.payload.task_id
          ? { ...r, verification: action.payload }
          : r,
      );
      return { ...state, rounds };
    }
    default:
      return state;
  }
}

interface AuraData {
  events: AuraEvent[];
  rounds: CoordinationRound[];
  alerts: Alert[];
  scenario: ScenarioManifest | null;
  connected: { mqtt: boolean; redis: boolean };
  selectedAlertId: string | null;
  selectAlert: (id: string | null) => void;
  ackAlert: (id: string) => Promise<void>;
  dismissAlert: (id: string) => Promise<void>;
  recentEventFor: (sensorId: string) => AuraEvent | null;
}

const AuraDataContext = createContext<AuraData | null>(null);

export function useAuraData(): AuraData {
  const ctx = useContext(AuraDataContext);
  if (!ctx) throw new Error("useAuraData must be used within AuraDataProvider");
  return ctx;
}

export function AuraDataProvider({
  scenarioName,
  children,
}: {
  scenarioName: string;
  children: React.ReactNode;
}) {
  const [stream, dispatch] = useReducer(streamReducer, {
    events: [],
    rounds: [],
    mqttConnected: false,
  });
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [redisConnected, setRedisConnected] = useState(false);
  const [scenario, setScenario] = useState<ScenarioManifest | null>(null);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  // Scenario manifest — fetched once, drives the Camera Wall + Zone rail layout.
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/scenario?name=${encodeURIComponent(scenarioName)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data) setScenario(data as ScenarioManifest);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [scenarioName]);

  // Live bus relay (MQTT via SSE) — browsers auto-reconnect EventSource on
  // drop, no manual retry loop needed.
  useEffect(() => {
    const source = new EventSource("/api/events");
    source.addEventListener("event", (e) =>
      dispatch({ type: "event", payload: JSON.parse((e as MessageEvent).data) }),
    );
    source.addEventListener("task", (e) =>
      dispatch({ type: "task", payload: JSON.parse((e as MessageEvent).data) }),
    );
    source.addEventListener("bid", (e) =>
      dispatch({ type: "bid", payload: JSON.parse((e as MessageEvent).data) }),
    );
    source.addEventListener("award", (e) =>
      dispatch({ type: "award", payload: JSON.parse((e as MessageEvent).data) }),
    );
    source.addEventListener("verification", (e) =>
      dispatch({ type: "verification", payload: JSON.parse((e as MessageEvent).data) }),
    );
    source.addEventListener("status", (e) =>
      dispatch({ type: "status", payload: JSON.parse((e as MessageEvent).data) }),
    );
    return () => source.close();
  }, []);

  // Alerts — polled (they're durable/low-frequency escalations, not worth
  // a dedicated stream) at a cadence fast enough to feel live.
  const refetchAlerts = useCallback(async () => {
    try {
      const res = await fetch("/api/alerts?count=200", { cache: "no-store" });
      if (!res.ok && res.status !== 200) return;
      const data = await res.json();
      setAlerts(data.alerts ?? []);
    } catch {
      // leave alerts as-is; connectivity is tracked separately via /api/status
    }
  }, []);

  // Redis connectivity is a real ping (/api/status), independent of where
  // alerts data came from — a replay run's alerts live in JSONL files
  // (see api/alerts/route.ts) even while Redis itself is perfectly reachable
  // for ack/dismiss audit writes, so "alerts source" is not a valid proxy.
  const refetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/status", { cache: "no-store" });
      if (!res.ok) {
        setRedisConnected(false);
        return;
      }
      const data = await res.json();
      setRedisConnected(Boolean(data.redis));
    } catch {
      setRedisConnected(false);
    }
  }, []);

  useEffect(() => {
    // Fetch-on-mount + poll: intentional, not a derived-state cascade — these
    // effects don't read the state they set, so they can't loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refetchAlerts();
    refetchStatus();
    const alertsIv = setInterval(refetchAlerts, 4000);
    const statusIv = setInterval(refetchStatus, 5000);
    return () => {
      clearInterval(alertsIv);
      clearInterval(statusIv);
    };
  }, [refetchAlerts, refetchStatus]);

  const ackAlert = useCallback(
    async (id: string) => {
      await fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alert_id: id, action: "acknowledge" }),
      }).catch(() => {});
      await refetchAlerts();
    },
    [refetchAlerts],
  );

  const dismissAlert = useCallback(
    async (id: string) => {
      await fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alert_id: id, action: "dismiss" }),
      }).catch(() => {});
      await refetchAlerts();
    },
    [refetchAlerts],
  );

  const recentEventFor = useCallback(
    (sensorId: string): AuraEvent | null => {
      const now = Date.now() / 1000;
      return (
        stream.events.find(
          (e) => e.sensor_id === sensorId && now - e.timestamp < RECENT_EVENT_WINDOW_S,
        ) ?? null
      );
    },
    [stream.events],
  );

  const value = useMemo<AuraData>(
    () => ({
      events: stream.events,
      rounds: stream.rounds,
      alerts,
      scenario,
      connected: { mqtt: stream.mqttConnected, redis: redisConnected },
      selectedAlertId,
      selectAlert: setSelectedAlertId,
      ackAlert,
      dismissAlert,
      recentEventFor,
    }),
    [
      stream.events,
      stream.rounds,
      stream.mqttConnected,
      alerts,
      scenario,
      redisConnected,
      selectedAlertId,
      ackAlert,
      dismissAlert,
      recentEventFor,
    ],
  );

  return <AuraDataContext.Provider value={value}>{children}</AuraDataContext.Provider>;
}
