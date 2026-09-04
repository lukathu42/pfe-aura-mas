"use client";
/* eslint-disable @next/next/no-img-element -- MJPEG streams cannot use the optimizing Image loader. */

import { X } from "lucide-react";
import { useEffect, useState } from "react";
import type { LiveCameraHealth } from "@/lib/types";

export function LiveCameraDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [cameras, setCameras] = useState<LiveCameraHealth[]>([]);
  useEffect(() => {
    if (!open) return;
    const refresh = () => fetch("/api/cameras", { cache: "no-store" }).then((r) => r.json()).then((data) => setCameras(data.cameras ?? [])).catch(() => setCameras([]));
    refresh(); const timer = setInterval(refresh, 3000); return () => clearInterval(timer);
  }, [open]);
  if (!open) return null;
  return <aside className="absolute inset-y-0 right-0 z-30 flex w-full max-w-[520px] flex-col border-l border-[var(--border-primary)] bg-[var(--bg-panel-solid)] shadow-2xl">
    <div className="flex items-center justify-between border-b border-[var(--border-secondary)] p-3"><span className="hud-text text-[11px] text-[var(--cyan-primary)]">LIVE CAMERA HEALTH · READ ONLY</span><button aria-label="Close live cameras" onClick={onClose}><X className="h-4 w-4" /></button></div>
    <div className="flex-1 overflow-y-auto p-3 space-y-3">{cameras.length === 0 && <p className="text-xs text-[var(--text-secondary)]">No live runner is publishing camera health.</p>}{cameras.map((camera) => <section key={camera.id} className="overflow-hidden rounded border border-[var(--border-secondary)]"><div className="flex items-center justify-between p-2"><span className="hud-text text-[10px]">{camera.label}</span><span className={`severity-tag ${camera.state === "ONLINE" ? "severity-tag--resolved" : "severity-tag--warning"}`}>{camera.state}</span></div>{camera.state !== "OFFLINE" && <img src={camera.stream} alt={`${camera.label} live stream`} className="aspect-video w-full bg-black object-contain" />}{camera.last_error && <p className="p-2 hud-label">{camera.last_error} · retries {camera.reconnect_attempts}</p>}</section>)}</div>
  </aside>;
}
