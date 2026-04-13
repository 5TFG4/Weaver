/**
 * useFills Hook
 *
 * React Query hook for run fill data.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchFills } from "../api/fills";
import type { FillListResponse } from "../api/types";

export const fillKeys = {
  all: ["fills"] as const,
  runs: () => [...fillKeys.all, "run"] as const,
  run: (runId: string) => [...fillKeys.runs(), runId] as const,
};

/**
 * Hook to fetch fills for a specific run
 */
export function useFills(runId: string, options?: { enabled?: boolean }) {
  return useQuery<FillListResponse>({
    queryKey: fillKeys.run(runId),
    queryFn: () => fetchFills(runId),
    enabled: (options?.enabled ?? true) && Boolean(runId),
  });
}
