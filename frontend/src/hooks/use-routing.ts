import { useQuery } from "@tanstack/react-query";
import { getRouting } from "@/lib/api";
import type { RoutingResponse } from "@/types/healthgrid";

export function useRouting(
  origin: { lat: number; lng: number } | null,
  destination: { lat: number; lng: number } | null,
  enabled: boolean
) {
  return useQuery({
    queryKey: ["routing", origin, destination],
    queryFn: () =>
      getRouting({
        origin: origin ?? { lat: 0, lng: 0 },
        destination: destination ?? { lat: 0, lng: 0 },
      }) as Promise<RoutingResponse>,
    enabled: enabled && Boolean(origin && destination),
    staleTime: 60_000,
  });
}
