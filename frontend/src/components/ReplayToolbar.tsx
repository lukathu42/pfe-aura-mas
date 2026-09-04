"use client";

import { Pause, Play, RotateCcw, Search, ShieldCheck, Video } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAuraData } from "./DataProvider";

function formatTime(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function ReplayToolbar({ onSearch, onLive }: { onSearch: () => void; onLive: () => void }) {
  const router = useRouter();
  const {
    catalogue,
    replay,
    currentTime,
    duration,
    playing,
    playbackRate,
    seek,
    setPlaying,
    setPlaybackRate,
  } = useAuraData();
  const replayReady = Boolean(replay);
  const anomalyKey = replay?.metadata.anomaly_key ?? "";
  const anomalyGroups = [...new Map(catalogue.map((item) => [
    item.anomaly_key ?? "unknown", item.title,
  ])).entries()];
  const examples = catalogue.filter((item) => (item.anomaly_key ?? "unknown") === anomalyKey);

  return (
    <div className="shrink-0 border-b border-[var(--border-secondary)] bg-[var(--bg-panel-solid)]/95 px-3 py-2 flex flex-col gap-2 xl:flex-row xl:items-center">
      <div className="flex min-w-0 items-center gap-2 xl:w-[520px]">
        <ShieldCheck className="h-4 w-4 shrink-0 text-[var(--gold-primary)]" />
        <select
          aria-label="Anomaly family"
          value={anomalyKey}
          onChange={(event) => {
            const next = catalogue.find((item) => (item.anomaly_key ?? "unknown") === event.target.value);
            if (!next) return;
            setPlaying(false);
            router.push(`/?scenario=${encodeURIComponent(next.scenario)}`, { scroll: false });
          }}
          className="min-w-0 flex-1 rounded border border-[var(--border-primary)] bg-[var(--bg-panel-solid)] px-2 py-1 hud-text text-[10px] text-[var(--text-primary)]"
        >
          {!replay && <option value="">Loading anomaly families…</option>}
          {anomalyGroups.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
        <select
          aria-label="Prepared example"
          value={replay?.scenario ?? ""}
          onChange={(event) => {
            setPlaying(false);
            router.push(`/?scenario=${encodeURIComponent(event.target.value)}`, { scroll: false });
          }}
          className="min-w-0 flex-1 rounded border border-[var(--border-primary)] bg-[var(--bg-panel-solid)] px-2 py-1 hud-text text-[10px] text-[var(--text-primary)]"
        >
          {examples.map((item) => (
            <option key={item.scenario} value={item.scenario}>
              {item.sample_label ?? item.scenario}
            </option>
          ))}
        </select>
      </div>
      <div className="flex gap-1">
        <button onClick={onSearch} className="flex items-center gap-1 rounded border border-[var(--border-secondary)] px-2 py-1 hud-text text-[9px] text-[var(--text-secondary)]"><Search className="h-3 w-3" />SEARCH</button>
        <button onClick={onLive} className="flex items-center gap-1 rounded border border-[var(--border-secondary)] px-2 py-1 hud-text text-[9px] text-[var(--text-secondary)]"><Video className="h-3 w-3" />LIVE</button>
      </div>

      <div className="flex min-w-0 flex-1 items-center gap-2">
        <button
          aria-label={playing ? "Pause replay" : "Play replay"}
          onClick={() => setPlaying(!playing)}
          disabled={!replayReady}
          className="rounded border border-[var(--cyan-primary)]/50 p-1 text-[var(--cyan-primary)] disabled:opacity-30"
        >
          {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
        </button>
        <button
          aria-label="Restart replay"
          onClick={() => {
            seek(0);
            setPlaying(false);
          }}
          disabled={!replayReady}
          className="rounded border border-[var(--border-secondary)] p-1 text-[var(--text-secondary)] disabled:opacity-30"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
        <span className="w-[74px] hud-text text-[9px] text-[var(--cyan-primary)]">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
        <input
          aria-label="Replay position"
          className="min-w-[100px] flex-1 accent-[var(--cyan-primary)]"
          type="range"
          min={0}
          max={Math.max(duration, 0.1)}
          step={0.1}
          value={Math.min(currentTime, duration)}
          disabled={!replayReady}
          onChange={(event) => {
            setPlaying(false);
            seek(Number(event.target.value));
          }}
        />
        <select
          aria-label="Playback speed"
          value={playbackRate}
          onChange={(event) => setPlaybackRate(Number(event.target.value))}
          className="rounded border border-[var(--border-secondary)] bg-[var(--bg-panel-solid)] px-1.5 py-1 hud-text text-[9px] text-[var(--text-secondary)]"
        >
          {[0.5, 1, 1.5, 2].map((rate) => (
            <option key={rate} value={rate}>{rate}×</option>
          ))}
        </select>
      </div>

      <div
        className="hidden min-w-0 xl:block xl:w-[430px]"
        title={replay?.metadata.attribution}
      >
        <div className="truncate hud-text text-[10px] text-[var(--gold-primary)]">
          {replay?.metadata.title ?? "Prepared replay"}
        </div>
        <div className="truncate hud-label">
          {replay
            ? `${replay.metadata.dataset} · ${replay.metadata.attribution}`
            : "Loading scenario timeline…"}
        </div>
      </div>
      <span className="severity-tag severity-tag--resolved shrink-0">PREPARED REPLAY</span>
    </div>
  );
}
