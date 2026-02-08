import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { usePlannerEngine } from "@/hooks/use-planner-engine";
import { useAgentScenario } from "@/hooks/use-agent-scenario";

const fallbackScenarios = {
  Low: {
    deltas: { coverage: 12, underserved: 62, roi: "3.4 yrs" },
    demandImpact: [
      { month: "M1", baseline: 100, simulated: 97 },
      { month: "M2", baseline: 102, simulated: 95 },
      { month: "M3", baseline: 104, simulated: 92 },
      { month: "M4", baseline: 106, simulated: 90 },
      { month: "M5", baseline: 108, simulated: 88 },
      { month: "M6", baseline: 110, simulated: 86 },
    ],
    coverageShift: [
      { region: "North", baseline: 42, simulated: 52 },
      { region: "Central", baseline: 55, simulated: 62 },
      { region: "East", baseline: 48, simulated: 57 },
      { region: "South", baseline: 62, simulated: 68 },
    ],
  },
  Balanced: {
    deltas: { coverage: 24, underserved: 142, roi: "2.1 yrs" },
    demandImpact: [
      { month: "M1", baseline: 100, simulated: 92 },
      { month: "M2", baseline: 102, simulated: 85 },
      { month: "M3", baseline: 104, simulated: 78 },
      { month: "M4", baseline: 106, simulated: 72 },
      { month: "M5", baseline: 108, simulated: 68 },
      { month: "M6", baseline: 110, simulated: 64 },
    ],
    coverageShift: [
      { region: "North", baseline: 42, simulated: 58 },
      { region: "Central", baseline: 55, simulated: 70 },
      { region: "East", baseline: 48, simulated: 66 },
      { region: "South", baseline: 62, simulated: 75 },
    ],
  },
  Aggressive: {
    deltas: { coverage: 35, underserved: 220, roi: "1.6 yrs" },
    demandImpact: [
      { month: "M1", baseline: 100, simulated: 88 },
      { month: "M2", baseline: 102, simulated: 78 },
      { month: "M3", baseline: 104, simulated: 70 },
      { month: "M4", baseline: 106, simulated: 64 },
      { month: "M5", baseline: 108, simulated: 58 },
      { month: "M6", baseline: 110, simulated: 54 },
    ],
    coverageShift: [
      { region: "North", baseline: 42, simulated: 65 },
      { region: "Central", baseline: 55, simulated: 78 },
      { region: "East", baseline: 48, simulated: 74 },
      { region: "South", baseline: 62, simulated: 84 },
    ],
  },
} as const;

const fallbackCostCurve = [
  { scenario: "Low", cost: 350, impact: 18 },
  { scenario: "Balanced", cost: 550, impact: 26 },
  { scenario: "Aggressive", cost: 820, impact: 34 },
];

const SimulationDashboard = () => {
  const [scenario, setScenario] = useState<keyof typeof fallbackScenarios>(
    "Balanced"
  );
  const { data } = usePlannerEngine();
  const { data: agentScenario } = useAgentScenario(data?.action_plan ?? null);
  const scenarios = agentScenario?.simulation_presets ?? data?.simulation_presets ?? fallbackScenarios;
  const activeScenario = useMemo(() => scenarios[scenario], [scenario, scenarios]);
  const activePresets = agentScenario?.simulation_presets ?? data?.simulation_presets;
  const costCurve = activePresets
    ? [
        {
          scenario: "Low",
          ...activePresets.Low.cost_curve,
        },
        {
          scenario: "Balanced",
          ...activePresets.Balanced.cost_curve,
        },
        {
          scenario: "Aggressive",
          ...activePresets.Aggressive.cost_curve,
        },
      ]
    : fallbackCostCurve;
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-[1400px] mx-auto px-10 pt-10 pb-16 space-y-10">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Simulation Lab
          </div>
          <h1 className="mt-3 text-3xl font-semibold">
            Scenario outcomes for targeted intervention
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare baseline trends with simulated improvements based on the current plan.
          </p>
        </div>

        <div className="glass rounded-2xl p-4 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          {(["Low", "Balanced", "Aggressive"] as const).map((item) => (
            <button
              key={item}
              onClick={() => setScenario(item)}
              className={`px-4 py-2 rounded-full transition-colors ${
                scenario === item
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass rounded-2xl p-6">
            <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              Coverage Delta
            </div>
            <div className="mt-3 text-3xl font-semibold">
              +{activeScenario.deltas.coverage}%
            </div>
            <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-emerald-300">
              Improved
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Projected increase in effective coverage within 6 months.
            </p>
          </div>
          <div className="glass rounded-2xl p-6">
            <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              Underserved Reduction
            </div>
            <div className="mt-3 text-3xl font-semibold">
              -{activeScenario.deltas.underserved}K
            </div>
            <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-emerald-300">
              Reduced
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Estimated population moved into reliable access range.
            </p>
          </div>
          <div className="glass rounded-2xl p-6">
            <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              ROI Window
            </div>
            <div className="mt-3 text-3xl font-semibold">
              {activeScenario.deltas.roi}
            </div>
            <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-amber-500/30 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-amber-300">
              Modeled
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Expected time to cost recovery under base scenario.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass rounded-2xl p-6 h-[360px]">
            <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground mb-4">
              Demand Load Over Time
            </div>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activeScenario.demandImpact}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="baseline" stroke="#ef4444" fill="rgba(239,68,68,0.2)" />
                <Area type="monotone" dataKey="simulated" stroke="#10b981" fill="rgba(16,185,129,0.2)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="glass rounded-2xl p-6 h-[360px]">
            <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground mb-4">
              Coverage by Region
            </div>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activeScenario.coverageShift}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="region" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                <Bar dataKey="baseline" fill="rgba(148,163,184,0.4)" />
                <Bar dataKey="simulated" fill="rgba(16,185,129,0.7)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass rounded-2xl p-6 h-[360px]">
          <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground mb-4">
            Cost vs Impact
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={costCurve}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="scenario" stroke="#94a3b8" />
              <YAxis yAxisId="left" stroke="#94a3b8" />
              <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="cost" stroke="#f59e0b" />
              <Line yAxisId="right" type="monotone" dataKey="impact" stroke="#10b981" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default SimulationDashboard;
