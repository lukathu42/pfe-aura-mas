"use client";

import { Camera, Mic } from "lucide-react";
import { mediaUrl } from "@/lib/media";
import type { ScenarioSensor } from "@/lib/types";
import { PulseRing } from "./primitives/GlassPanel";
import { useAuraData } from "./DataProvider";

function gridColsClass(n: number): string {
  if (n <= 1) return "grid-cols-1";
  if (n <= 2) return "grid-cols-2";
  if (n <= 4) return "grid-cols-2";
  if (n <= 6) return "grid-cols-3";
  return "grid-cols-4";
}

function CameraTile({ sensor }: { sensor: ScenarioSensor }) {
  const { recentEventFor } = useAuraData();
  const event = recentEventFor(sensor.id);
  const zoneName = sensor.zones?.[0]?.name ?? "site";

  return (
    <div className="corner-frame relative aspect-video overflow-hidden rounded-lg border border-[var(--border-primary)] bg-black">
      <video
        className="h-full w-full object-cover opacity-90"
        src={mediaUrl(sensor.source)}
        autoPlay
        loop
        muted
        playsInline
      />
      <div className="tactical-grid absolute inset-0 pointer-events-none opacity-10" />

      {/* Top meta strip */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-2 py-1 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center gap-1.5">
          <PulseRing variant="cyan" size={6} />
          <span className="hud-text text-[9px] text-[var(--cyan-primary)]">REPLAY</span>
        </div>
        <span className="hud-text text-[9px] text-[var(--text-secondary)]">{sensor.id}</span>
      </div>

      {/* Bottom meta strip */}
      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-2 py-1 bg-gradient-to-t from-black/80 to-transparent">
        <span className="hud-text text-[9px] text-[var(--gold-primary)]">{zoneName}</span>
        {event && (
          <span className="severity-tag severity-tag--warning">{event.event_type}</span>
        )}
      </div>
    </div>
  );
}

function AudioStrip({ sensors }: { sensors: ScenarioSensor[] }) {
  const { recentEventFor } = useAuraData();
  if (sensors.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {sensors.map((sensor) => {
        const event = recentEventFor(sensor.id);
        return (
          <div
            key={sensor.id}
            className="glass-panel-sm flex items-center gap-2 px-3 py-1.5"
          >
            <Mic className="w-3.5 h-3.5 text-[var(--cyan-primary)]" />
            <span className="hud-text text-[9px] text-[var(--text-primary)]">{sensor.id}</span>
            <span className="hud-label">{sensor.zone ?? "site"}</span>
            {event ? (
              <span className="severity-tag severity-tag--warning">{event.event_type}</span>
            ) : (
              <span className="severity-tag severity-tag--resolved">quiet</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function CameraWall() {
  const { scenario } = useAuraData();
  const cameras = (scenario?.sensors ?? []).filter((s) => s.type === "camera");
  const mics = (scenario?.sensors ?? []).filter((s) => s.type === "audio");

  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="flex items-center gap-2">
        <Camera className="w-4 h-4 text-[var(--gold-primary)]" />
        <span className="hud-text text-[12px] text-[var(--text-heading)]">Camera Wall</span>
        <span className="hud-label">{cameras.length} SENSORS · SCENARIO REPLAY, NOT LIVE HARDWARE</span>
      </div>

      {cameras.length === 0 ? (
        <div className="glass-panel flex-1 flex items-center justify-center">
          <span className="hud-label">No camera sensors in active scenario</span>
        </div>
      ) : (
        <div className={`grid ${gridColsClass(cameras.length)} gap-3 flex-1`}>
          {cameras.map((sensor) => (
            <CameraTile key={sensor.id} sensor={sensor} />
          ))}
        </div>
      )}

      <AudioStrip sensors={mics} />
    </div>
  );
}
