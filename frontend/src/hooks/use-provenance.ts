import { useQuery } from "@tanstack/react-query";
import { getProvenance } from "@/lib/api";
import type { ProvenanceResponse } from "@/types/healthgrid";

export function useProvenance(provenanceId?: string | null) {
  return useQuery({
    queryKey: ["provenance", provenanceId],
    queryFn: () =>
      getProvenance(provenanceId ?? "") as Promise<ProvenanceResponse>,
    enabled: Boolean(provenanceId),
    staleTime: 60_000,
  });
}
