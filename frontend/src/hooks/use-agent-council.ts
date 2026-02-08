import { useQuery } from "@tanstack/react-query";
import { runAgent } from "@/lib/api";
import type { AgentRunResponse } from "@/types/healthgrid";

export function useAgentCouncil(query: string, enabled: boolean) {
  return useQuery({
    queryKey: ["agent-council", query],
    queryFn: () =>
      runAgent({
        query,
        top_k: 4,
        enable_rag: true,
      }) as Promise<AgentRunResponse>,
    enabled: enabled && Boolean(query),
    staleTime: 30_000,
  });
}
