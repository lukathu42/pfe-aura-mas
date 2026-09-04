"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { GlassPanel } from "./primitives/GlassPanel";
import { SeverityTag } from "./primitives/SeverityTag";
import { formatLocalTime } from "@/lib/media";
import { useAuraData } from "./DataProvider";
import type { Severity } from "@/lib/types";

const SEVERITIES: Severity[] = ["CRITICAL", "WARNING", "INFO"];

export function IncidentRail() {
  const { alerts, selectedAlertId, selectAlert } = useAuraData();
  const [expanded, setExpanded] = useState(true);
  const [filter, setFilter] = useState<Severity[]>(SEVERITIES);

  const openCount = alerts.filter((a) => a.status === "OPEN").length;
  const filtered = alerts
    .filter((a) => filter.includes(a.severity))
    .sort((a, b) => {
      const aPriority = a.priority_score ?? -1;
      const bPriority = b.priority_score ?? -1;
      if (aPriority !== bPriority) return bPriority - aPriority;
      return b.timestamp - a.timestamp;
    });

  const toggleFilter = (sev: Severity) => {
    setFilter((f) => (f.includes(sev) ? f.filter((s) => s !== sev) : [...f, sev]));
  };

  return (
    <GlassPanel className="flex flex-col overflow-hidden h-full">
      <div
        onClick={() => setExpanded((v) => !v)}
        role="button"
        tabIndex={0}
        className="shrink-0 flex items-center justify-between px-3 py-2 border-b border-[var(--border-secondary)] cursor-pointer hover:bg-[var(--hover-accent)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--sev-critical)]" />
          <span className="hud-text text-[11px] text-[var(--text-primary)]">Incidents</span>
          <span className="severity-tag severity-tag--critical">{openCount}</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        )}
      </div>

      {expanded && (
        <>
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-[var(--border-secondary)]">
            {SEVERITIES.map((sev) => (
              <button
                key={sev}
                onClick={() => toggleFilter(sev)}
                className={`severity-tag ${
                  sev === "CRITICAL"
                    ? "severity-tag--critical"
                    : sev === "WARNING"
                      ? "severity-tag--warning"
                      : "severity-tag--info"
                } ${filter.includes(sev) ? "" : "opacity-30"}`}
              >
                {sev}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto styled-scrollbar flex flex-col gap-1 p-2">
            {filtered.length === 0 && (
              <span className="hud-label px-2 py-3">No incidents match filter</span>
            )}
            {filtered.map((alert) => (
              <button
                key={alert.alert_id}
                onClick={() => selectAlert(alert.alert_id)}
                className={`glass-panel-sm text-left px-3 py-2 flex flex-col gap-1 transition-colors hover:border-[var(--border-active)] ${
                  selectedAlertId === alert.alert_id ? "border-[var(--border-active)]" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="hud-text text-[10px] text-[var(--text-primary)]">
                    {alert.event_type.replace(/_/g, " ")}
                  </span>
                  <SeverityTag severity={alert.severity} />
                </div>
                <div className="flex items-center justify-between hud-label">
                  <span>
                    {alert.scene_time_seconds != null
                      ? `T+${alert.scene_time_seconds.toFixed(1)}s`
                      : formatLocalTime(alert.timestamp)}{" "}
                    · {alert.zone ?? "site"}
                  </span>
                  <span>
                    {alert.priority_score != null
                      ? `${alert.priority_label ?? "ML"} ${(alert.priority_score * 100).toFixed(0)}%`
                      : alert.status}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </GlassPanel>
  );
}
