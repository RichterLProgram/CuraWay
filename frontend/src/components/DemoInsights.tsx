import type { HealthGridData } from "@/hooks/use-health-grid-data";
import type {
  AgentRunResponse,
  CausalImpactResponse,
  PolicyOptimizeResponse,
  RealtimeStatusResponse,
  RoutingResponse,
} from "@/types/healthgrid";
import { Button } from "@/components/ui/button";

interface DemoInsightsProps {
  data?: HealthGridData;
  selectedRegion?: string | null;
  onSelectRegion: (region: string) => void;
  onTakeAction: () => void;
  className?: string;
  agentResult?: AgentRunResponse;
  causalImpact?: CausalImpactResponse;
  policyOptimization?: PolicyOptimizeResponse;
  realtimeStatus?: RealtimeStatusResponse;
  routingStats?: RoutingResponse;
}

const DemoInsights = ({
  data,
  selectedRegion,
  onSelectRegion,
  onTakeAction,
  className,
  agentResult,
  causalImpact,
  policyOptimization,
  realtimeStatus,
  routingStats,
}: DemoInsightsProps) => {
  if (!data) return null;

  const topDeserts = data.plannerEngine?.hotspots?.length
    ? data.plannerEngine.hotspots.slice(0, 3)
    : [...data.gap.deserts].sort((a, b) => b.gap_score - a.gap_score).slice(0, 3);

  const selectedDesert =
    (data.plannerEngine?.hotspots?.length
      ? data.plannerEngine.hotspots.find((d) => d.region === selectedRegion)
      : data.gap.deserts.find((d) => d.region_name === selectedRegion)) ?? topDeserts[0];

  const selectedRegionName =
    selectedDesert && "region_name" in selectedDesert
      ? selectedDesert.region_name
      : selectedDesert?.region;

  const summary = data.plannerEngine?.summary
    ? data.plannerEngine.summary
    : selectedDesert
      ? `AI flags ${selectedRegionName} with a ${(
          selectedDesert.gap_score * 100
        ).toFixed(0)}% gap score and ${selectedDesert.population_affected.toLocaleString()} people underserved.`
      : "AI insights will appear once a hotspot is selected.";

  return (
    <div className={`space-y-6 ${className ?? ""}`}>
      <div className="glass rounded-2xl p-6">
        <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
          Hotspots
        </div>
        <div className="mt-4 grid gap-3">
          {topDeserts.map((desert) => (
            <button
              key={"region_name" in desert ? desert.region_name : desert.region}
              onClick={() =>
                onSelectRegion(
                  "region_name" in desert ? desert.region_name : desert.region
                )
              }
              className={`rounded-xl border px-4 py-3 text-left transition-all ${
                ("region_name" in desert
                  ? selectedDesert?.region_name === desert.region_name
                  : selectedDesert?.region === desert.region)
                  ? "border-foreground/60 bg-foreground text-background"
                  : "border-border/60 bg-transparent hover:border-foreground/40"
              }`}
            >
              <div className="text-sm font-semibold">
                {"region_name" in desert ? desert.region_name : desert.region}
              </div>
              <div className="mt-1 text-xs opacity-70">
                Gap {(desert.gap_score * 100).toFixed(0)}% ·{" "}
                {desert.population_affected.toLocaleString()} people
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="glass rounded-2xl p-8 border border-supply/40">
        <div className="text-[10px] uppercase tracking-[0.4em] text-supply">
          Try Your Own Dataset
        </div>
        <p className="mt-4 text-xl font-semibold leading-relaxed text-foreground">
          Upload or connect your data to generate AI recommendations tailored to your regions.
        </p>
        <div className="mt-6 flex items-center gap-3">
          <Button className="bg-supply text-white hover:bg-supply/90">
            Try Your Own Dataset
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <div className="glass rounded-2xl p-6">
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Causal Impact
          </div>
          {causalImpact ? (
            <div className="mt-3 space-y-2 text-sm text-muted-foreground">
              <div>
                Effect: <span className="text-foreground">{causalImpact.effect}</span>
              </div>
              <div>
                Uplift: <span className="text-foreground">{causalImpact.uplift_pct}%</span>
              </div>
              <div>
                Confidence: <span className="text-foreground">{(causalImpact.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">
              Causal impact will populate once data is available.
            </p>
          )}
        </div>

        <div className="glass rounded-2xl p-6">
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Policy Optimization
          </div>
          <div className="mt-4 space-y-3 text-sm text-muted-foreground">
            {policyOptimization?.options?.slice(0, 2).map((option) => (
              <div key={option.id} className="rounded-xl border border-border/60 p-4">
                <div className="text-sm font-semibold text-foreground">{option.label}</div>
                <div className="mt-2">
                  Coverage +{option.coverage_gain_pct}% · Underserved -{option.underserved_reduction_k}K
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  Budget ${option.budget.toLocaleString()} · Avg travel {option.avg_travel_minutes} min
                </div>
              </div>
            )) ?? (
              <p className="text-sm text-muted-foreground">Policy options will appear shortly.</p>
            )}
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Realtime Feed
          </div>
          <div className="mt-3 text-sm text-muted-foreground">
            Status: <span className="text-foreground">{realtimeStatus?.status ?? "idle"}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            Topic: {realtimeStatus?.topic ?? "healthgrid.events"}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            Last ingest: {realtimeStatus?.last_ingested_at ?? "—"}
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Routing Insight
          </div>
          <div className="mt-3 text-sm text-muted-foreground">
            Travel time:{" "}
            <span className="text-foreground">
              {routingStats?.minutes ? `${routingStats.minutes} min` : "—"}
            </span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            Source: {routingStats?.source ?? "n/a"}
          </div>
        </div>
      </div>

      <div className="glass rounded-2xl p-6">
        <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
          AI Council
        </div>
        {agentResult ? (
          <div className="mt-4 space-y-4">
            {agentResult.council.map((item) => (
              <div key={item.role} className="rounded-xl border border-border/60 p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold capitalize">{item.role}</div>
                  <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                    {item.confidence ?? "medium"}
                  </div>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
              </div>
            ))}
            <div className="rounded-xl border border-border/60 p-4">
              <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                Evidence
              </div>
              <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
                {agentResult.citations.slice(0, 4).map((cite) => (
                  <li key={cite.source}>
                    {cite.source} {cite.score ? `· ${(cite.score * 100).toFixed(0)}%` : ""}
                  </li>
                ))}
              </ul>
            </div>
            {agentResult.risk_flags.length > 0 && (
              <div className="rounded-xl border border-demand/40 bg-demand/10 p-4">
                <div className="text-[10px] uppercase tracking-[0.3em] text-demand">
                  Risk Flags
                </div>
                <ul className="mt-3 space-y-2 text-xs text-demand">
                  {agentResult.risk_flags.map((risk) => (
                    <li key={risk}>{risk}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">
            Agent insights will appear after the hotspot is selected.
          </p>
        )}
      </div>
    </div>
  );
};

export default DemoInsights;
