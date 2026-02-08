import { useQuery } from "@tanstack/react-query";
import { getPlannerEngine } from "@/lib/api";
import type { PlannerEngineResponse } from "@/types/healthgrid";

export function usePlannerEngine() {
  return useQuery({
    queryKey: ["planner-engine"],
    queryFn: () => getPlannerEngine() as Promise<PlannerEngineResponse>,
    staleTime: 60_000,
  });
}
