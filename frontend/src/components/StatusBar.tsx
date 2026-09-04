"use client";

import { useEffect, useState } from "react";
import { Bot } from "lucide-react";
import { useAuraData } from "./DataProvider";

export function StatusBar({ onToggleCopilot }: { onToggleCopilot?: () => void }) {
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
    <div className="h-[32px] shrink-0 flex items-center gap-4 px-4 border-t border-[var(--border-secondary)] bg-[var(--bg-panel-solid)]/90 backdrop-blur-xl text-[10px] font-mono tracking-wider">
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

      {onToggleCopilot && (
        <button
          onClick={onToggleCopilot}
          className="ml-auto flex items-center gap-1.5 px-2 py-1 rounded border border-[var(--gold-primary)]/50 bg-[var(--gold-glow)] text-[var(--gold-primary)] hover:bg-[var(--gold-primary)] hover:text-black transition"
        >
          <Bot className="w-3 h-3" />
          <span>AURA COPILOT</span>
        </button>
      )}

      <span className={onToggleCopilot ? "text-[var(--text-muted)]" : "ml-auto text-[var(--text-muted)]"}>{clock}</span>
    </div>
  );
}
