import { useQuery } from "@tanstack/react-query";
import { runAgent } from "@/lib/api";
import type { AgentRunResponse } from "@/types/healthgrid";

export function useAgentCouncil(query: string, enabled: boolean) {
  return useQuery({
    queryKey: ["agent-council", query],
    queryFn: async () => {
      try {
        return await runAgent({
          query,
          top_k: 4,
          enable_rag: false,
        }) as Promise<AgentRunResponse>;
      } catch (error) {
        // Fallback wenn API Key fehlt - return empty response
        console.warn("AI Agent unavailable (API key missing?), using fallback");
        return {
          answer: "",
          citations: [],
          council: [],
          trace_id: "",
          provenance_id: "",
        } as AgentRunResponse;
      }
    },
    enabled: enabled && Boolean(query),
    staleTime: 30_000,
    retry: false, // Don't retry if AI is unavailable
  });
}
