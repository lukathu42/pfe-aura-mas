import { AuraDataProvider } from "@/components/DataProvider";
import { AuraDashboardView } from "@/components/AuraDashboardView";

const DEFAULT_SCENARIO = process.env.AURA_SCENARIO || "perimeter_chain_01";

export default async function Home(props: PageProps<"/">) {
  const searchParams = await props.searchParams;
  const scenarioParam = searchParams?.scenario;
  const scenarioName =
    (Array.isArray(scenarioParam) ? scenarioParam[0] : scenarioParam) || DEFAULT_SCENARIO;
  const rawTime = Array.isArray(searchParams?.t) ? searchParams.t[0] : searchParams?.t;
  const parsedTime = rawTime === undefined ? 0 : Number(rawTime);
  const initialTime = Number.isFinite(parsedTime) && parsedTime >= 0 ? parsedTime : 0;

  return (
    <AuraDataProvider key={`${scenarioName}:${initialTime}`} scenarioName={scenarioName} initialTime={initialTime}>
      <AuraDashboardView />
    </AuraDataProvider>
  );
}
