"use client";

import { Activity, Check, ShieldAlert, WifiOff } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { IncidentCommand, OperationalState } from "@/lib/operations";

async function loadState(): Promise<OperationalState | null> {
  const response = await fetch("/api/operations", { cache: "no-store" });
  return response.ok ? response.json() : null;
}

export function OperationalPanel() {
  const [state, setState] = useState<OperationalState | null>(null);
  const refresh = useCallback(() => loadState().then(setState).catch(() => setState(null)), []);

  useEffect(() => {
    refresh();
    const source = new EventSource("/api/operations/events");
    source.addEventListener("state", (event) => {
      setState(JSON.parse((event as MessageEvent).data) as OperationalState);
    });
    const timer = setInterval(refresh, 15000);
    return () => {
      source.close();
      clearInterval(timer);
    };
  }, [refresh]);

  const act = async (command: IncidentCommand) => {
    await fetch("/api/operations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(command),
    });
    await refresh();
  };

  if (!state) {
    return (
      <section className="flex items-center gap-2 border-b border-[var(--border-secondary)] bg-[var(--bg-panel-solid)] px-3 py-2 text-[10px] font-mono text-[var(--text-muted)]">
        <WifiOff className="h-3.5 w-3.5" /> OPERATIONAL SERVICE OFFLINE · prepared replays remain separate
      </section>
    );
  }
  if (!state.active_session) {
    return (
      <section className="flex items-center gap-2 border-b border-[var(--border-secondary)] bg-[var(--bg-panel-solid)] px-3 py-2 text-[10px] font-mono text-[var(--text-muted)]">
        <Activity className="h-3.5 w-3.5" /> NO ACTIVE MONITORING SESSION
      </section>
    );
  }

  const session = state.active_session;
  const online = state.camera_health.filter((camera) => camera.state === "ONLINE").length;
  const degraded = state.camera_health.length - online;
  const openIncidents = state.incidents.filter((incident) => incident.workflow_state !== "RESOLVED");
  const measurement = state.measurements.at(0);

  return (
    <section className="border-b border-[var(--border-primary)] bg-[var(--bg-panel-solid)]">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2 text-[10px] font-mono tracking-wider">
        <span className={`severity-tag ${session.mode === "LIVE" ? "severity-tag--resolved" : "severity-tag--warning"}`}>
          {session.mode}
        </span>
        <span className="text-[var(--text-secondary)]">
          POLICY <span className="text-[var(--gold-primary)]">{state.active_policy?.policy_version_id ?? "—"}</span>
        </span>
        <span className="text-[var(--text-secondary)]">
          CAMERAS <span className="text-[var(--cyan-primary)]">{online} ONLINE</span>
          {degraded > 0 && <span className="text-[var(--sev-warning)]"> · {degraded} DEGRADED</span>}
        </span>
        <span className="text-[var(--text-secondary)]">
          SEARCH <span className="text-[var(--cyan-primary)]">{state.search_level.replaceAll("_", " ")}</span>
        </span>
        {measurement && (
          <span className="text-[var(--text-secondary)]">
            PERF <span className="text-[var(--gold-primary)]">{measurement.inference_fps?.toFixed(1) ?? "—"} FPS</span>
            {measurement.alert_latency_ms != null && <> · {Math.round(measurement.alert_latency_ms)} MS ALERT</>}
            {measurement.cpu_percent != null && <> · {Math.round(measurement.cpu_percent)}% CPU</>}
          </span>
        )}
        {session.failure_reason && <span className="text-[var(--sev-warning)]">LIVE FAILURE: {session.failure_reason}</span>}
      </div>
      {openIncidents.length > 0 && (
        <div className="flex gap-2 overflow-x-auto border-t border-[var(--border-secondary)] px-3 py-2">
          {openIncidents.map((incident) => (
            <article key={incident.incident_id} className="flex min-w-[280px] items-center gap-2 rounded border border-[var(--border-secondary)] px-2 py-1.5">
              {incident.category === "SENSOR_HEALTH" ? <WifiOff className="h-4 w-4 text-[var(--sev-warning)]" /> : <ShieldAlert className="h-4 w-4 text-[var(--sev-critical)]" />}
              <div className="min-w-0 flex-1">
                <div className="truncate hud-text text-[10px]">{incident.event_type.replaceAll("_", " ")} · {incident.physical_zone_id ?? "site"}</div>
                <div className="hud-label">{incident.workflow_state} · {incident.verdict}</div>
              </div>
              {incident.workflow_state === "OPEN" && (
                <button aria-label={`Acknowledge ${incident.event_type}`} onClick={() => act({ incident_id: incident.incident_id, action: "ACKNOWLEDGE" })} className="text-[var(--cyan-primary)]">
                  <Check className="h-4 w-4" />
                </button>
              )}
              {incident.workflow_state === "ACKNOWLEDGED" && (
                <button aria-label={`Resolve ${incident.event_type}`} onClick={() => act({ incident_id: incident.incident_id, action: "RESOLVE" })} className="text-[var(--sev-resolved)]">
                  <Activity className="h-4 w-4" />
                </button>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
