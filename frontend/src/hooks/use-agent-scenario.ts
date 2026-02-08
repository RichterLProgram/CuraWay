import { useQuery } from "@tanstack/react-query";
import { getScenario } from "@/lib/api";
import type { ScenarioResponse } from "@/types/healthgrid";

export function useAgentScenario(actionPlan?: Record<string, unknown> | null) {
  return useQuery({
    queryKey: ["agent-scenario", actionPlan],
    queryFn: () =>
      getScenario({ action_plan: actionPlan ?? {} }) as Promise<ScenarioResponse>,
    enabled: Boolean(actionPlan),
    staleTime: 60_000,
  });
}
