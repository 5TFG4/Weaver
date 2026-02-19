/**
 * useHealth Hook
 *
 * React Query hook for API health status.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api/health";
import type { HealthResponse } from "../api/types";

export const healthKeys = {
  all: ["health"] as const,
};

/**
 * Hook to fetch API health status
 */
export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: healthKeys.all,
    queryFn: fetchHealth,
    refetchInterval: 30_000, // Poll every 30s
    retry: 1,
  });
}
