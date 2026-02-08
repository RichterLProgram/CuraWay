import { useQuery } from "@tanstack/react-query";
import { getCausalImpact } from "@/lib/api";
import type { CausalImpactResponse } from "@/types/healthgrid";

export function useCausalImpact(baseline: number[], post: number[], enabled: boolean) {
  return useQuery({
    queryKey: ["causal-impact", baseline, post],
    queryFn: () =>
      getCausalImpact({ baseline, post, metric: "coverage" }) as Promise<CausalImpactResponse>,
    enabled: enabled && baseline.length > 1 && post.length > 1,
    staleTime: 60_000,
  });
}
