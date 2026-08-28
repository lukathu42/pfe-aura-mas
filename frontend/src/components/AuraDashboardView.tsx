"use client";

import { useState } from "react";
import { CameraWall } from "@/components/CameraWall";
import { IncidentRail } from "@/components/IncidentRail";
import { IncidentDetail } from "@/components/IncidentDetail";
import { ZoneRail } from "@/components/ZoneRail";
import { CoordinationConsole } from "@/components/CoordinationConsole";
import { StatusBar } from "@/components/StatusBar";
import { CopilotDrawer } from "@/components/CopilotDrawer";
import { ReplayToolbar } from "@/components/ReplayToolbar";
import { SearchDrawer } from "@/components/SearchDrawer";
import { LiveCameraDrawer } from "@/components/LiveCameraDrawer";
import { OperationalPanel } from "@/components/OperationalPanel";

export function AuraDashboardView() {
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [liveOpen, setLiveOpen] = useState(false);

  return (
    <div className="flex flex-col h-full min-h-0 bg-[var(--bg-void)] relative">
      <OperationalPanel />
      <ReplayToolbar onSearch={() => { setLiveOpen(false); setSearchOpen(true); }} onLive={() => { setSearchOpen(false); setLiveOpen(true); }} />
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-3 p-3 overflow-y-auto lg:overflow-hidden">
        <div className="grid grid-rows-[auto_auto] lg:grid-rows-[minmax(0,3fr)_minmax(0,2fr)] gap-3 flex-[2] min-w-0 lg:min-h-0">
          <div className="min-w-0 lg:min-h-0">
            <CameraWall />
          </div>
          <div className="min-h-[320px] flex lg:min-h-0">
            <IncidentDetail />
          </div>
        </div>
        <div className="flex flex-col gap-3 lg:w-[340px] shrink-0 lg:min-h-0">
          <div className="h-[220px] shrink-0">
            <ZoneRail />
          </div>
          <div className="h-[320px] lg:h-auto lg:flex-1 lg:min-h-0">
            <IncidentRail />
          </div>
          <div className="h-[260px] shrink-0">
            <CoordinationConsole />
          </div>
        </div>
      </div>
      <StatusBar onToggleCopilot={() => setCopilotOpen((v) => !v)} />
      <CopilotDrawer isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} />
      <SearchDrawer open={searchOpen} onClose={() => setSearchOpen(false)} />
      <LiveCameraDrawer open={liveOpen} onClose={() => setLiveOpen(false)} />
    </div>
  );
}
