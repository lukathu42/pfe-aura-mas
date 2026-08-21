"use client";

import { useEffect, useState } from "react";
import { useAuraData } from "./DataProvider";

export function StatusBar() {
  const { connected, scenario, alerts } = useAuraData();
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toISOString().split("T")[1].slice(0, 8) + "Z");
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, []);

  const openCount = alerts.filter((a) => a.status === "OPEN").length;
  const sensorCount = scenario?.sensors.length ?? 0;

  return (
    <div className="h-[30px] shrink-0 flex items-center gap-4 px-4 border-t border-[var(--border-secondary)] bg-[var(--bg-panel-solid)]/90 backdrop-blur-xl text-[10px] font-mono tracking-wider">
      <div className="flex items-center gap-1.5">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            connected.mqtt ? "bg-[var(--cyan-primary)] animate-osiris-pulse" : "bg-[var(--text-muted)]"
          }`}
        />
        <span className={connected.mqtt ? "text-[var(--cyan-primary)]" : "text-[var(--text-muted)]"}>
          MQTT {connected.mqtt ? "ONLINE" : "OFFLINE"}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            connected.redis ? "bg-[var(--sev-resolved)] animate-osiris-pulse" : "bg-[var(--text-muted)]"
          }`}
        />
        <span className={connected.redis ? "text-[var(--sev-resolved)]" : "text-[var(--text-muted)]"}>
          REDIS {connected.redis ? "ONLINE" : "OFFLINE"}
        </span>
      </div>
      <span className="w-px h-3 bg-[var(--border-secondary)]" />
      <span className="text-[var(--text-secondary)]">
        SCENARIO <span className="text-[var(--gold-primary)]">{scenario?.name ?? "—"}</span>
      </span>
      <span className="text-[var(--text-secondary)]">
        SENSORS <span className="text-[var(--gold-primary)]">{sensorCount}</span>
      </span>
      <span className="text-[var(--text-secondary)]">
        OPEN ALERTS{" "}
        <span className={openCount > 0 ? "text-[var(--sev-critical)]" : "text-[var(--gold-primary)]"}>
          {openCount}
        </span>
      </span>
      <span className="ml-auto text-[var(--text-muted)]">{clock}</span>
    </div>
  );
}
