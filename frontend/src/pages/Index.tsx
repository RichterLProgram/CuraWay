import { useEffect, useMemo, useState } from "react";
import Header from "@/components/Header";
import { useHealthGridData } from "@/hooks/use-health-grid-data";
import { useAgentCouncil } from "@/hooks/use-agent-council";
import { useActionGraph } from "@/hooks/use-action-graph";
import { useCausalImpact } from "@/hooks/use-causal-impact";
import { usePolicyOptimization } from "@/hooks/use-policy-optimization";
import { useRealtimeStatus } from "@/hooks/use-realtime-status";
import { useRouting } from "@/hooks/use-routing";
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
    if (data.plannerEngine?.action_plan) {
      const plan = data.plannerEngine.action_plan;
      return {
        region: plan.region,
        priority: plan.priority,
        estimatedCost: plan.estimated_cost,
        capexCost: plan.capex_cost,
        opexCost: plan.opex_cost,
        impact: plan.impact,
        actions: plan.actions,
        timeline: plan.timeline,
        risks: plan.risks,
        confidence: plan.confidence,
        dependencies: plan.dependencies,
      };
    }

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

  const agentQuery = useMemo(() => {
    if (!data || !selectedRegion) return "";
    const desert =
      data.plannerEngine?.hotspots?.find((d) => d.region === selectedRegion) ??
      data.gap.deserts.find((d) => d.region_name === selectedRegion);
    if (!desert) return "";
    const gapScore =
      "gap_score" in desert ? (desert.gap_score * 100).toFixed(0) : "—";
    const population =
      "population_affected" in desert
        ? desert.population_affected.toLocaleString()
        : "—";
    return `Generate an evidence-backed action plan for ${selectedRegion}. Gap score: ${gapScore}%. Underserved population: ${population}. Provide actions, risks, and timeline.`;
  }, [data, selectedRegion]);

  const { data: agentResult } = useAgentCouncil(
    agentQuery,
    Boolean(agentQuery && activeTab === "demo")
  );

  const { data: actionGraph } = useActionGraph(
    actionPlan?.actions ?? [],
    actionPlan?.dependencies
  );

  const baselineSeries = useMemo(() => {
    const base = data?.demand.total_count ?? 100;
    return Array.from({ length: 6 }, (_, idx) => base + idx * 2);
  }, [data]);

  const postSeries = useMemo(() => {
    const base = data?.demand.total_count ?? 100;
    return Array.from({ length: 6 }, (_, idx) => base - 6 + idx);
  }, [data]);

  const { data: causalImpact } = useCausalImpact(
    baselineSeries,
    postSeries,
    activeTab === "demo"
  );

  const policyConstraints = useMemo(() => {
    const parseCost = (value?: string) => {
      if (!value) return 1_000_000;
      const digits = Number(value.replace(/[^0-9.]/g, ""));
      if (Number.isNaN(digits)) return 1_000_000;
      return digits * (value.toLowerCase().includes("m") ? 1_000_000 : 1_000);
    };
    return {
      budget: parseCost(actionPlan?.estimatedCost),
      staff: 60,
      max_travel_minutes: 180,
    };
  }, [actionPlan]);

  const { data: policyOptimization } = usePolicyOptimization(
    policyConstraints,
    activeTab === "demo"
  );

  const { data: realtimeStatus } = useRealtimeStatus(activeTab === "demo");

  const routingOrigin = useMemo(() => {
    if (!data || !selectedRegion) return null;
    const desert =
      data.plannerEngine?.hotspots?.find((d) => d.region === selectedRegion) ??
      data.gap.deserts.find((d) => d.region_name === selectedRegion);
    if (!desert) return null;
    return {
      lat: "lat" in desert ? desert.lat : 0,
      lng: "lng" in desert ? desert.lng : 0,
    };
  }, [data, selectedRegion]);

  const routingDestination = useMemo(() => {
    const facility = data?.supply.facilities[0];
    if (!facility) return null;
    return { lat: facility.lat, lng: facility.lng };
  }, [data]);

  const { data: routingStats } = useRouting(
    routingOrigin,
    routingDestination,
    activeTab === "demo"
  );

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
                        agentResult={agentResult}
                        causalImpact={causalImpact}
                        policyOptimization={policyOptimization}
                        realtimeStatus={realtimeStatus}
                        routingStats={routingStats}
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
        actionGraph={actionGraph}
        agentResult={agentResult}
        causalImpact={causalImpact}
        policyOptimization={policyOptimization}
      />
    </div>
  );
};

export default Index;
