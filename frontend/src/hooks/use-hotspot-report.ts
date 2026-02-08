import { useQuery } from "@tanstack/react-query";
import { getHotspotReport } from "@/lib/api";
import type { HotspotReportResponse } from "@/types/healthgrid";

export function useHotspotReport(
  hotspot?: Record<string, unknown> | null,
  demand?: Record<string, unknown>,
  supply?: Record<string, unknown>,
  gap?: Record<string, unknown>,
  recommendations?: Array<Record<string, unknown>>,
  baseline_kpis?: Record<string, unknown>
) {
  return useQuery({
    queryKey: ["hotspot-report", hotspot, demand, supply, gap],
    queryFn: () =>
      getHotspotReport({
        hotspot: hotspot ?? {},
        demand,
        supply,
        gap,
        recommendations,
        baseline_kpis,
      }) as Promise<HotspotReportResponse>,
    enabled: Boolean(hotspot),
    staleTime: 300_000, // 5 minutes
  });
}
