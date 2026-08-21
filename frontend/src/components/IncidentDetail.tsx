"use client";

import { useState } from "react";
import { FileText, ImageOff } from "lucide-react";
import { GlassPanel, TacticalButton } from "./primitives/GlassPanel";
import { SeverityTag, StatusTag } from "./primitives/SeverityTag";
import { HudRow } from "./primitives/Hud";
import { mediaUrl, formatLocalTime } from "@/lib/media";
import { useAuraData } from "./DataProvider";

export function IncidentDetail() {
  const { alerts, selectedAlertId, ackAlert, dismissAlert } = useAuraData();
  const [busy, setBusy] = useState(false);
  const alert = alerts.find((a) => a.alert_id === selectedAlertId) ?? null;

  if (!alert) {
    return (
      <GlassPanel className="flex-1 flex items-center justify-center">
        <span className="hud-label">Select an incident from the rail</span>
      </GlassPanel>
    );
  }

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  return (
    <GlassPanel className="flex-1 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-secondary)]">
        <span className="hud-text text-[13px] text-[var(--text-heading)]">
          {alert.event_type.replace(/_/g, " ")}
        </span>
        <div className="flex items-center gap-2">
          <SeverityTag severity={alert.severity} />
          <StatusTag status={alert.status} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto styled-scrollbar p-4 flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          <HudRow label="Confidence" value={alert.confidence.toFixed(2)} />
          <HudRow label="Zone" value={alert.zone ?? "site"} />
          <HudRow label="Sensors" value={alert.sensors.join(", ") || "—"} />
          <HudRow label="Time" value={formatLocalTime(alert.timestamp)} />
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-[var(--gold-primary)]" />
            <span className="hud-label">Agentic incident report</span>
          </div>
          <p className="font-[family-name:var(--font-body)] text-[13px] leading-relaxed text-[var(--text-primary)]">
            {alert.explanation || "No explanation available for this incident."}
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="hud-label">Anonymized evidence</span>
          {alert.evidence.length === 0 ? (
            <div className="flex items-center gap-2 hud-label py-4">
              <ImageOff className="w-4 h-4" />
              audio-only incident — no visual evidence
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {alert.evidence.map((path) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={path}
                  src={mediaUrl(path)}
                  alt="Blurred evidence frame"
                  className="rounded-md border border-[var(--border-secondary)] aspect-video object-cover skeleton-shimmer"
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 px-4 py-3 border-t border-[var(--border-secondary)]">
        <TacticalButton
          disabled={busy || alert.status !== "OPEN"}
          onClick={() => run(() => ackAlert(alert.alert_id))}
        >
          Acknowledge
        </TacticalButton>
        <TacticalButton
          variant="cyan"
          disabled={busy || alert.status !== "OPEN"}
          onClick={() => run(() => dismissAlert(alert.alert_id))}
        >
          Dismiss (false alarm)
        </TacticalButton>
      </div>
    </GlassPanel>
  );
}
