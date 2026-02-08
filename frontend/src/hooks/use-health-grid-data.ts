import { useQuery } from "@tanstack/react-query";
import {
  getDemandData,
  getSupplyData,
  getGapAnalysis,
  getMapData,
  getPlannerRecommendations,
  getPlannerEngine,
} from "@/lib/api";
import type {
  DemandData,
  SupplyData,
  GapAnalysis,
  MapData,
  PlannerRecommendations,
  PlannerEngineResponse,
} from "@/types/healthgrid";

export interface HealthGridData {
  demand: DemandData;
  supply: SupplyData;
  gap: GapAnalysis;
  map: MapData;
  recommendations: PlannerRecommendations;
  plannerEngine?: PlannerEngineResponse;
}

async function fetchHealthGridData(): Promise<HealthGridData> {
  const [demand, supply, gap, map, recommendations, plannerEngine] =
    await Promise.all([
    getDemandData(),
    getSupplyData(),
    getGapAnalysis(),
    getMapData(),
    getPlannerRecommendations(),
      getPlannerEngine(),
    ]);

  return {
    demand: demand as DemandData,
    supply: supply as SupplyData,
    gap: gap as GapAnalysis,
    map: map as MapData,
    recommendations: recommendations as PlannerRecommendations,
    plannerEngine: plannerEngine as PlannerEngineResponse,
  };
}

export function useHealthGridData() {
  return useQuery({
    queryKey: ["healthgrid-data"],
    queryFn: fetchHealthGridData,
    staleTime: 60_000,
  });
}
