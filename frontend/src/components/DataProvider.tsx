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
  AlertStatus,
  AuraEvent,
  CoordinationAward,
  CoordinationBid,
  CoordinationRound,
  CoordinationTask,
  CoordinationVerification,
  PreparedReplay,
  ReplayCatalogItem,
  ScenarioManifest,
} from "@/lib/types";

const MAX_EVENTS = 200;
const MAX_ROUNDS = 8;
const RECENT_SCENE_EVENT_S = 5;

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
      return { ...state, events: [action.payload, ...state.events].slice(0, MAX_EVENTS) };
    case "status":
      return { ...state, mqttConnected: action.payload.mqtt };
    case "task":
      return {
        ...state,
        rounds: [{ task: action.payload, bids: [], award: null, verification: null }, ...state.rounds]
          .slice(0, MAX_ROUNDS),
      };
    case "bid":
      return {
        ...state,
        rounds: state.rounds.map((round) =>
          round.task.task_id === action.payload.task_id
            ? { ...round, bids: [...round.bids, action.payload] }
            : round,
        ),
      };
    case "award":
      return {
        ...state,
        rounds: state.rounds.map((round) =>
          round.task.task_id === action.payload.task_id
            ? { ...round, award: action.payload }
            : round,
        ),
      };
    case "verification":
      return {
        ...state,
        rounds: state.rounds.map((round) =>
          round.task.task_id === action.payload.task_id
            ? { ...round, verification: action.payload }
            : round,
        ),
      };
  }
}

function itemTime(item: PreparedReplay["timeline"][number]): number {
  return item.scene_time_seconds ?? item.wall_offset_seconds;
}

function replayRounds(replay: PreparedReplay, currentTime: number): CoordinationRound[] {
  const rounds = new Map<string, CoordinationRound>();
  for (const item of replay.timeline) {
    if (itemTime(item) > currentTime) continue;
    if (item.kind === "task") {
      const task = item.payload as unknown as CoordinationTask;
      rounds.set(task.task_id, { task, bids: [], award: null, verification: null });
      continue;
    }
    if (!["bid", "award", "verification"].includes(item.kind)) continue;
    const payload = item.payload as unknown as { task_id: string };
    const round = rounds.get(payload.task_id);
    if (!round) continue;
    if (item.kind === "bid") round.bids.push(item.payload as unknown as CoordinationBid);
    if (item.kind === "award") round.award = item.payload as unknown as CoordinationAward;
    if (item.kind === "verification") {
      round.verification = item.payload as unknown as CoordinationVerification;
    }
  }
  return [...rounds.values()].reverse().slice(0, MAX_ROUNDS);
}

interface AuraData {
  events: AuraEvent[];
  rounds: CoordinationRound[];
  alerts: Alert[];
  scenario: ScenarioManifest | null;
  replay: PreparedReplay | null;
  catalogue: ReplayCatalogItem[];
  connected: { mqtt: boolean; redis: boolean };
  selectedAlertId: string | null;
  selectAlert: (id: string | null) => void;
  ackAlert: (id: string) => Promise<void>;
  dismissAlert: (id: string) => Promise<void>;
  recentEventFor: (sensorId: string) => AuraEvent | null;
  currentTime: number;
  duration: number;
  playing: boolean;
  playbackRate: number;
  seek: (seconds: number) => void;
  setPlaying: (playing: boolean) => void;
  setPlaybackRate: (rate: number) => void;
  updatePrimaryTime: (seconds: number) => void;
}

const AuraDataContext = createContext<AuraData | null>(null);

export function useAuraData(): AuraData {
  const ctx = useContext(AuraDataContext);
  if (!ctx) throw new Error("useAuraData must be used within AuraDataProvider");
  return ctx;
}

export function AuraDataProvider({
  scenarioName,
  initialTime,
  children,
}: {
  scenarioName: string;
  initialTime: number;
  children: React.ReactNode;
}) {
  const [stream, dispatch] = useReducer(streamReducer, {
    events: [],
    rounds: [],
    mqttConnected: false,
  });
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);
  const [redisConnected, setRedisConnected] = useState(false);
  const [scenario, setScenario] = useState<ScenarioManifest | null>(null);
  const [replay, setReplay] = useState<PreparedReplay | null>(null);
  const [catalogue, setCatalogue] = useState<ReplayCatalogItem[]>([]);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(initialTime);
  const [playing, setPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [alertOverrides, setAlertOverrides] = useState<Record<string, AlertStatus>>({});

  useEffect(() => {
    fetch("/api/replay", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : { scenarios: [] }))
      .then((data) => setCatalogue(data.scenarios ?? []))
      .catch(() => setCatalogue([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    // Scenario navigation is an external URL change; clear the prior replay
    // immediately so its alerts and video state cannot flash under the new URL.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setScenario(null);
    setReplay(null);
    setCurrentTime(initialTime);
    setPlaying(false);
    setSelectedAlertId(null);
    setAlertOverrides({});
    Promise.all([
      fetch(`/api/scenario?name=${encodeURIComponent(scenarioName)}`).then((r) =>
        r.ok ? r.json() : null,
      ),
      fetch(`/api/replay?scenario=${encodeURIComponent(scenarioName)}`, {
        cache: "no-store",
      }).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([manifest, prepared]) => {
        if (cancelled) return;
        const typedPrepared = prepared as PreparedReplay | null;
        const typedManifest = manifest as ScenarioManifest | null;
        const displaySources = typedPrepared?.metadata.display_sources;
        setScenario(
          typedManifest && displaySources
            ? {
                ...typedManifest,
                sensors: typedManifest.sensors.map((sensor) => ({
                  ...sensor,
                  source: displaySources[sensor.id] ?? sensor.source,
                })),
              }
            : typedManifest,
        );
        setReplay(typedPrepared);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [scenarioName, initialTime]);

  useEffect(() => {
    const source = new EventSource("/api/events");
    for (const eventName of ["event", "task", "bid", "award", "verification", "status"] as const) {
      source.addEventListener(eventName, (event) =>
        dispatch({
          type: eventName,
          payload: JSON.parse((event as MessageEvent).data),
        } as StreamAction),
      );
    }
    return () => source.close();
  }, []);

  const refetchAlerts = useCallback(async () => {
    try {
      const params = new URLSearchParams({ count: "200", scenario: scenarioName });
      const response = await fetch(`/api/alerts?${params}`, { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      setLiveAlerts(data.alerts ?? []);
    } catch {
      // Retain the last durable snapshot while the local service reconnects.
    }
  }, [scenarioName]);

  const refetchStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      const data = response.ok ? await response.json() : null;
      setRedisConnected(Boolean(data?.redis));
    } catch {
      setRedisConnected(false);
    }
  }, []);

  useEffect(() => {
    // Fetch-on-mount plus polling; neither callback reads the state it sets.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refetchAlerts();
    refetchStatus();
    const alertsTimer = setInterval(refetchAlerts, 4000);
    const statusTimer = setInterval(refetchStatus, 5000);
    return () => {
      clearInterval(alertsTimer);
      clearInterval(statusTimer);
    };
  }, [refetchAlerts, refetchStatus]);

  const visibleReplayItems = useMemo(
    () => replay?.timeline.filter((item) => itemTime(item) <= currentTime) ?? [],
    [replay, currentTime],
  );
  const events = useMemo(
    () =>
      replay
        ? visibleReplayItems
            .filter((item) => item.kind === "event")
            .map((item) => item.payload as unknown as AuraEvent)
            .reverse()
        : stream.events,
    [replay, visibleReplayItems, stream.events],
  );
  const rounds = useMemo(
    () => (replay ? replayRounds(replay, currentTime) : stream.rounds),
    [replay, currentTime, stream.rounds],
  );
  const alerts = useMemo(() => {
    const base = replay
      ? replay.alerts.filter((alert) => (alert.scene_time_seconds ?? 0) <= currentTime)
      : liveAlerts;
    return base.map((alert) => ({
      ...alert,
      status: alertOverrides[alert.alert_id] ?? alert.status,
    }));
  }, [replay, currentTime, liveAlerts, alertOverrides]);

  const updateAlert = useCallback(
    async (id: string, action: "acknowledge" | "dismiss") => {
      const status = action === "acknowledge" ? "ACKNOWLEDGED" : "DISMISSED";
      setAlertOverrides((value) => ({ ...value, [id]: status }));
      await fetch("/api/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alert_id: id, action }),
      }).catch(() => {});
      if (!replay) await refetchAlerts();
    },
    [replay, refetchAlerts],
  );

  const recentEventFor = useCallback(
    (sensorId: string) =>
      events.find((event) => {
        if (event.sensor_id !== sensorId) return false;
        const eventTime = event.scene_time_seconds;
        return replay && eventTime != null
          ? currentTime - eventTime <= RECENT_SCENE_EVENT_S
          : Date.now() / 1000 - event.timestamp <= 20;
      }) ?? null,
    [events, replay, currentTime],
  );

  const duration = replay?.duration_seconds ?? scenario?.duration_seconds ?? 0;
  const seek = useCallback(
    (seconds: number) => setCurrentTime(Math.min(Math.max(seconds, 0), duration)),
    [duration],
  );
  const updatePrimaryTime = useCallback((seconds: number) => setCurrentTime(seconds), []);

  const value = useMemo<AuraData>(
    () => ({
      events,
      rounds,
      alerts,
      scenario,
      replay,
      catalogue,
      connected: { mqtt: stream.mqttConnected, redis: redisConnected },
      selectedAlertId,
      selectAlert: setSelectedAlertId,
      ackAlert: (id) => updateAlert(id, "acknowledge"),
      dismissAlert: (id) => updateAlert(id, "dismiss"),
      recentEventFor,
      currentTime,
      duration,
      playing,
      playbackRate,
      seek,
      setPlaying,
      setPlaybackRate,
      updatePrimaryTime,
    }),
    [
      events, rounds, alerts, scenario, replay, catalogue, stream.mqttConnected,
      redisConnected, selectedAlertId, updateAlert, recentEventFor, currentTime,
      duration, playing, playbackRate, seek, updatePrimaryTime,
    ],
  );

  return <AuraDataContext.Provider value={value}>{children}</AuraDataContext.Provider>;
}
