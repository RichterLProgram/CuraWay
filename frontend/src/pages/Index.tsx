import { useEffect, useMemo, useState } from "react";
import Header from "@/components/Header";
import { useHealthGridData } from "@/hooks/use-health-grid-data";
import KineticDotsLoader from "@/components/ui/kinetic-dots-loader";
import { ParticleButton } from "@/components/ui/particle-button";
import InteractiveMap from "@/components/InteractiveMap";
import DemoInsights from "@/components/DemoInsights";
import ActionDrawer, { ActionPlan } from "@/components/ActionDrawer";

const Index = () => {
  const { data, isLoading, isError } = useHealthGridData();
  const [activeTab, setActiveTab] = useState<"overview" | "demo">("overview");
  const [demoTab, setDemoTab] = useState<"demand" | "supply" | "gap">("demand");
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [actionOpen, setActionOpen] = useState(false);

  const topDeserts = useMemo(() => {
    if (!data) return [];
    return [...data.gap.deserts].sort((a, b) => b.gap_score - a.gap_score);
  }, [data]);

  useEffect(() => {
    if (!selectedRegion && topDeserts.length > 0) {
      setSelectedRegion(topDeserts[0].region_name);
    }
  }, [selectedRegion, topDeserts]);

  const actionPlan: ActionPlan | null = useMemo(() => {
    if (!data) return null;
    const region = selectedRegion ?? topDeserts[0]?.region_name;
    const recommendation =
      data.recommendations.recommendations.find((rec) => rec.region === region) ??
      data.recommendations.recommendations[0];

    if (!recommendation) return null;

    const capabilitySteps = recommendation.capability_needed
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    return {
      region: region ?? "Regional Plan",
      priority: recommendation.priority,
      estimatedCost: recommendation.roi,
      capexCost: "$520K",
      opexCost: "$180K",
      impact: recommendation.estimated_impact,
      actions: [recommendation.action, ...capabilitySteps].slice(0, 4),
      timeline: [
        "0-2 weeks: validate demand signals",
        "2-6 weeks: align stakeholders and budget",
        "6-12 weeks: deploy resources and monitor impact",
      ],
      risks: [
        "Supply chain constraints",
        "Staffing availability",
        "Regulatory lead time",
      ],
      confidence: "medium",
      dependencies: [
        "Requires staffing approval",
        "Supply chain lead time 6–8 weeks",
        "Regional stakeholder alignment",
      ],
    };
  }, [data, selectedRegion, topDeserts]);

  return (
    <div className="min-h-screen bg-background relative">
      {/* Subtle ambient glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-15%] left-[-5%] w-[400px] h-[400px] rounded-full bg-demand/[0.025] blur-[100px]" />
        <div className="absolute bottom-[-15%] right-[-5%] w-[400px] h-[400px] rounded-full bg-supply/[0.025] blur-[100px]" />
      </div>

      <div className="relative z-10">
        <Header
          showIndicators={activeTab === "demo"}
          indicators={{
            demand: data?.demand.total_count.toLocaleString() ?? "—",
            underserved: data
              ? `${(data.gap.total_population_underserved / 1000).toFixed(0)}K`
              : "—",
            gapScore: data ? `${(data.gap.avg_gap_score * 100).toFixed(0)}%` : "—",
          }}
          onTakeAction={activeTab === "demo" ? () => setActionOpen(true) : undefined}
        />

        <main className="max-w-[1400px] mx-auto px-10 pt-14 pb-10">
          {isError && (
            <div className="mb-4 rounded-xl border border-demand/30 bg-demand/10 px-4 py-3 text-xs text-demand">
              Backend connection failed. Check the API server and try again.
            </div>
          )}

          {isLoading && !data ? (
            <div className="min-h-[70vh] flex items-center justify-center">
              <KineticDotsLoader />
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-8" />

              {activeTab === "overview" ? (
                <>
                  <section className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                    <div className="lg:col-span-6 space-y-6">
                  <h1 className="text-4xl lg:text-5xl font-semibold leading-tight">
                    Clarity for healthcare decisions.
                  </h1>
                  <p className="text-base text-muted-foreground leading-relaxed">
                    One surface for demand, capacity, and access—designed for leadership.
                  </p>
                      <div className="flex flex-wrap items-center gap-3">
                        <ParticleButton
                          size="lg"
                          variant="secondary"
                          className="gap-2 glow-sheen"
                          onClick={() => setActiveTab("demo")}
                        >
                          Demo
                        </ParticleButton>
                        <a
                          href="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80"
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs uppercase tracking-[0.3em] text-muted-foreground hover:text-foreground transition-colors"
                        >
                          Documentation
                        </a>
                      </div>
                    </div>
                    <div className="lg:col-span-6">
                      <div className="hero-visual">
                        <div className="hero-visual-frame" />
                        <div className="hero-visual-overlay">
                          <div className="hero-visual-chip">3D Clinical Intelligence</div>
                          <div className="hero-visual-title">Spatial context. Instant clarity.</div>
                        </div>
                      </div>
                    </div>
                  </section>
                </>
              ) : (
                <section className="space-y-6 demo-zoomed">
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                    <div className="lg:col-span-7">
                      <div className="glass rounded-[28px] border border-border/40 p-5">
                        <InteractiveMap
                          activeTab={demoTab}
                          data={data}
                          isLoading={isLoading}
                          height={560}
                          focusLat={
                            selectedRegion
                              ? data?.gap.deserts.find(
                                  (d) => d.region_name === selectedRegion
                                )?.lat
                              : null
                          }
                          focusLng={
                            selectedRegion
                              ? data?.gap.deserts.find(
                                  (d) => d.region_name === selectedRegion
                                )?.lng
                              : null
                          }
                          focusZoom={selectedRegion ? 10 : 8}
                          onModeChange={(mode) => setDemoTab(mode)}
                        />
                      </div>
                    </div>
                    <div className="lg:col-span-5 self-start pt-1">
                      <DemoInsights
                        data={data}
                        selectedRegion={selectedRegion}
                        onSelectRegion={setSelectedRegion}
                        onTakeAction={() => setActionOpen(true)}
                      />
                    </div>
                  </div>
                </section>
              )}
            </>
          )}
        </main>
      </div>
      <ActionDrawer
        open={actionOpen}
        plan={actionPlan}
        onClose={() => setActionOpen(false)}
      />
    </div>
  );
};

export default Index;
