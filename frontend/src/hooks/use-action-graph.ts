import { useQuery } from "@tanstack/react-query";
import { getActionGraph } from "@/lib/api";
import type { ActionGraphResponse } from "@/types/healthgrid";

export function useActionGraph(actions: string[], dependencies?: string[]) {
  return useQuery({
    queryKey: ["action-graph", actions, dependencies],
    queryFn: () =>
      getActionGraph({ actions, dependencies }) as Promise<ActionGraphResponse>,
    enabled: actions.length > 0,
    staleTime: 60_000,
  });
}
