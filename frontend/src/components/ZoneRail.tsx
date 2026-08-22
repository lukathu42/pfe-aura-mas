"use client";

import { MapPin } from "lucide-react";
import { GlassPanel } from "./primitives/GlassPanel";
import { HudLabel } from "./primitives/Hud";
import { useAuraData } from "./DataProvider";

/** Honest substitute for a floor-plan map: real zone names already present
 * on every scenario's sensors, not an invented site geometry — see the
 * plan's "Site floor-plan" note (no camera x/y position data exists yet). */
export function ZoneRail() {
  const { scenario, alerts } = useAuraData();

  const zones = new Map<string, string[]>(); // zone -> sensor ids
  for (const sensor of scenario?.sensors ?? []) {
    if (sensor.type === "camera") {
      for (const z of sensor.zones ?? []) {
        zones.set(z.name, [...(zones.get(z.name) ?? []), sensor.id]);
      }
    } else if (sensor.zone) {
      zones.set(sensor.zone, [...(zones.get(sensor.zone) ?? []), sensor.id]);
    }
  }

  return (
    <GlassPanel className="flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border-secondary)]">
        <MapPin className="w-3.5 h-3.5 text-[var(--gold-primary)]" />
        <span className="hud-text text-[11px] text-[var(--text-primary)]">Zones</span>
      </div>
      <div className="flex flex-col gap-1.5 p-2 styled-scrollbar overflow-y-auto">
        {zones.size === 0 && (
          <span className="hud-label px-2 py-2">No zones in scenario</span>
        )}
        {[...zones.entries()].map(([zone, sensorIds]) => {
          const openCount = alerts.filter(
            (a) => a.zone === zone && a.status === "OPEN",
          ).length;
          return (
            <div
              key={zone}
              className="glass-panel-sm flex items-center justify-between px-3 py-2"
            >
              <div className="flex flex-col">
                <span className="hud-text text-[10px] text-[var(--text-primary)]">{zone}</span>
                <HudLabel>{sensorIds.join(", ")}</HudLabel>
              </div>
              {openCount > 0 ? (
                <span className="severity-tag severity-tag--critical">{openCount}</span>
              ) : (
                <span className="severity-tag severity-tag--resolved">CLEAR</span>
              )}
            </div>
          );
        })}
      </div>
    </GlassPanel>
  );
}
