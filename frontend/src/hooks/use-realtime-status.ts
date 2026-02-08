import { useQuery } from "@tanstack/react-query";
import { getRealtimeStatus } from "@/lib/api";
import type { RealtimeStatusResponse } from "@/types/healthgrid";

export function useRealtimeStatus(enabled: boolean) {
  return useQuery({
    queryKey: ["realtime-status"],
    queryFn: () => getRealtimeStatus() as Promise<RealtimeStatusResponse>,
    enabled,
    staleTime: 15_000,
    refetchInterval: 15_000,
  });
}
