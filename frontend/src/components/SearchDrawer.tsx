"use client";

import { Search, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import type { SearchResult } from "@/lib/types";

export function SearchDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    if (!open) return;
    fetch("/api/search?limit=20", { cache: "no-store" }).then((r) => r.json()).then((data) => {
      setResults(data.results ?? []); setAvailable(data.index_available !== false);
    }).catch(() => setResults([]));
  }, [open]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=30`, { cache: "no-store" });
    const data = response.ok ? await response.json() : { results: [] };
    setResults(data.results ?? []); setAvailable(data.index_available !== false);
  }

  if (!open) return null;
  return <aside className="absolute inset-y-0 right-0 z-30 flex w-full max-w-[430px] flex-col border-l border-[var(--border-primary)] bg-[var(--bg-panel-solid)] shadow-2xl">
    <div className="flex items-center justify-between border-b border-[var(--border-secondary)] p-3"><span className="hud-text text-[11px] text-[var(--cyan-primary)]">INDEXED EVENT / VIDEO SEARCH</span><button aria-label="Close search" onClick={onClose}><X className="h-4 w-4" /></button></div>
    <form onSubmit={submit} className="flex gap-2 p-3"><input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="fight, bag, glass, person down…" className="min-w-0 flex-1 rounded border border-[var(--border-primary)] bg-[var(--bg-void)] px-2 py-2 text-xs" /><button className="rounded border border-[var(--cyan-primary)] px-3"><Search className="h-4 w-4" /></button></form>
    {!available && <p className="px-3 text-xs text-[var(--text-secondary)]">Search index is not generated yet. Run <code>python -m aura_mas.search_index</code>.</p>}
    <div className="flex-1 overflow-y-auto p-3 space-y-2">{results.map((result) => <button key={result.document_id} onClick={() => { onClose(); router.push(`/?scenario=${encodeURIComponent(result.scenario)}&t=${Math.max(0, result.scene_time_seconds)}`, { scroll: false }); }} className="w-full rounded border border-[var(--border-secondary)] p-3 text-left hover:border-[var(--cyan-primary)]">
      <div className="flex justify-between gap-2"><span className="hud-text text-[10px] text-[var(--gold-primary)]">{result.title}</span><span className="hud-label">{Math.floor(result.scene_time_seconds / 60)}:{String(Math.floor(result.scene_time_seconds % 60)).padStart(2, "0")}</span></div>
      <p className="mt-1 text-xs text-[var(--text-primary)]">{result.summary || result.event_type}</p><p className="mt-1 hud-label">{result.zone ?? "site"} · {result.sensors.join(", ")} · {result.context_source}</p>
    </button>)}</div>
  </aside>;
}
