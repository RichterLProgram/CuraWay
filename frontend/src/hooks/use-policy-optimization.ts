import { useQuery } from "@tanstack/react-query";
import { getPolicyOptimize } from "@/lib/api";
import type { PolicyOptimizeResponse } from "@/types/healthgrid";

export function usePolicyOptimization(
  constraints: Record<string, unknown>,
  enabled: boolean
) {
  return useQuery({
    queryKey: ["policy-optimize", constraints],
    queryFn: () =>
      getPolicyOptimize({ constraints }) as Promise<PolicyOptimizeResponse>,
    enabled,
    staleTime: 60_000,
  });
}
