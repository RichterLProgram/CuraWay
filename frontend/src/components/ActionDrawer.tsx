import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import type {
  ActionGraphResponse,
  CausalImpactResponse,
  PolicyOptimizeResponse,
} from "@/types/healthgrid";

export interface ActionPlan {
  region: string;
  priority: string;
  estimatedCost: string;
  capexCost?: string;
  opexCost?: string;
  impact: string;
  timeline: string[];
  actions: string[];
  risks: string[];
  confidence?: "low" | "medium" | "high";
  dependencies?: string[];
}

interface ActionDrawerProps {
  open: boolean;
  onClose: () => void;
  plan?: ActionPlan | null;
  actionGraph?: ActionGraphResponse;
  causalImpact?: CausalImpactResponse;
  policyOptimization?: PolicyOptimizeResponse;
}

const ActionDrawer = ({
  open,
  onClose,
  plan,
  actionGraph,
  causalImpact,
  policyOptimization,
}: ActionDrawerProps) => {
  

  const criticalPathLabels = useMemo(() => {
    if (!actionGraph) return [];
    return actionGraph.critical_path
      .map((id) => actionGraph.nodes.find((node) => node.id === id)?.label)
      .filter(Boolean) as string[];
  }, [actionGraph]);

  if (!open || !plan) return null;

  return (
    <div className="fixed inset-0 z-[60]">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        className="absolute right-0 top-0 h-full w-full max-w-xl bg-background border-l border-border/50 p-8 overflow-y-auto"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Take Action Plan
            </div>
            <h2 className="mt-3 text-2xl font-semibold">{plan.region}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Priority: <span className="capitalize">{plan.priority}</span>
            </p>
          </div>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="mt-8 grid gap-6">
          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Cost Breakdown
            </div>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                  One-time Capex
                </div>
                <div className="mt-2 text-2xl font-semibold">
                  {plan.capexCost ?? plan.estimatedCost}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                  Opex (annual)
                </div>
                <div className="mt-2 text-2xl font-semibold">
                  {plan.opexCost ?? "$280K"}
                </div>
              </div>
            </div>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Expected Impact
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{plan.impact}</p>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Recommended Actions
            </div>
            <ul className="mt-3 space-y-2 text-sm">
              {plan.actions.map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-foreground" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              AI Confidence
            </div>
            <div className="mt-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="uppercase tracking-[0.3em]">
                  {(plan.confidence ?? "medium")}
                </span>
                <span>
                  {plan.confidence === "high"
                    ? "84%"
                    : plan.confidence === "low"
                    ? "38%"
                    : "62%"}
                </span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-foreground/80"
                  style={{
                    width:
                      plan.confidence === "high"
                        ? "84%"
                        : plan.confidence === "low"
                        ? "38%"
                        : "62%",
                  }}
                />
              </div>
            </div>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Timeline
            </div>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {plan.timeline.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Dependencies
            </div>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {(plan.dependencies ?? [
                "Requires staffing approval",
                "Supply chain lead time 6–8 weeks",
                "Regional stakeholder alignment",
              ]).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="glass rounded-2xl p-5">
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
              Risk Flags
            </div>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {plan.risks.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          {actionGraph && (
            <div className="glass rounded-2xl p-5">
              <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                Action Graph
              </div>
              <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                {actionGraph.edges.map((edge) => {
                  const from = actionGraph.nodes.find(
                    (n) => n.id === edge.from_action
                  )?.label;
                  const to = actionGraph.nodes.find(
                    (n) => n.id === edge.to_action
                  )?.label;
                  return (
                    <div key={`${edge.from_action}-${edge.to_action}`}>
                      {from} → {to} {edge.reason ? `· ${edge.reason}` : ""}
                    </div>
                  );
                })}
              </div>
              {criticalPathLabels.length > 0 && (
                <div className="mt-4 text-xs text-muted-foreground">
                  Critical path: {criticalPathLabels.join(" → ")}
                </div>
              )}
            </div>
          )}

          {causalImpact && (
            <div className="glass rounded-2xl p-5">
              <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                Causal Impact Snapshot
              </div>
              <div className="mt-3 text-sm text-muted-foreground">
                Effect {causalImpact.effect} · Uplift {causalImpact.uplift_pct}% · Confidence{" "}
                {(causalImpact.confidence * 100).toFixed(0)}%
              </div>
            </div>
          )}

          {policyOptimization?.options?.length ? (
            <div className="glass rounded-2xl p-5">
              <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                Policy Options
              </div>
              <div className="mt-3 space-y-2 text-sm text-muted-foreground">
                {policyOptimization.options.slice(0, 2).map((option) => (
                  <div key={option.id}>
                    {option.label}: +{option.coverage_gain_pct}% coverage · -{option.underserved_reduction_k}K underserved
                  </div>
                ))}
              </div>
            </div>
          ) : null}

        </div>

        <div className="mt-8 flex items-center gap-3">
          <Button className="bg-demand text-white hover:bg-demand/90">
            Book Call
          </Button>
          <Button
            variant="outline"
            onClick={() => window.open("/simulation", "_blank", "noopener")}
          >
            Run Simulation
          </Button>
          <Button variant="ghost">Export plan PDF</Button>
        </div>
      </aside>
    </div>
  );
};

export default ActionDrawer;
