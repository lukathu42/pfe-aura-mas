import { AuraDataProvider } from "@/components/DataProvider";
import { CameraWall } from "@/components/CameraWall";
import { IncidentRail } from "@/components/IncidentRail";
import { IncidentDetail } from "@/components/IncidentDetail";
import { ZoneRail } from "@/components/ZoneRail";
import { CoordinationConsole } from "@/components/CoordinationConsole";
import { StatusBar } from "@/components/StatusBar";

const DEFAULT_SCENARIO = "combined_audio_video_01";

export default async function Home(props: PageProps<"/">) {
  const searchParams = await props.searchParams;
  const scenarioParam = searchParams?.scenario;
  const scenarioName =
    (Array.isArray(scenarioParam) ? scenarioParam[0] : scenarioParam) || DEFAULT_SCENARIO;

  return (
    <AuraDataProvider scenarioName={scenarioName}>
      <div className="flex flex-col h-full bg-[var(--bg-void)]">
        <div className="flex-1 flex flex-col lg:flex-row gap-3 p-3 overflow-hidden">
          <div className="flex flex-col gap-3 flex-[2] min-w-0 min-h-0">
            <div className="flex-[3] min-h-0">
              <CameraWall />
            </div>
            <div className="flex-[2] min-h-0 flex">
              <IncidentDetail />
            </div>
          </div>
          <div className="flex flex-col gap-3 lg:w-[340px] shrink-0 min-h-0">
            <div className="h-[220px] shrink-0">
              <ZoneRail />
            </div>
            <div className="flex-1 min-h-0">
              <IncidentRail />
            </div>
            <div className="h-[260px] shrink-0">
              <CoordinationConsole />
            </div>
          </div>
        </div>
        <StatusBar />
      </div>
    </AuraDataProvider>
  );
}
