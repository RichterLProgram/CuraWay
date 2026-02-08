import type { HealthGridData } from "@/hooks/use-health-grid-data";
import { Button } from "@/components/ui/button";

interface DemoInsightsProps {
  data?: HealthGridData;
  selectedRegion?: string | null;
  onSelectRegion: (region: string) => void;
  onTakeAction: () => void;
  className?: string;
}

const DemoInsights = ({
  data,
  selectedRegion,
  onSelectRegion,
  onTakeAction,
  className,
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
    </div>
  );
};

export default DemoInsights;
