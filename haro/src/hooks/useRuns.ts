/**
 * useRuns Hook
 *
 * React Query hooks for runs data management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchRuns, fetchRun, createRun, startRun, stopRun } from "../api/runs";
import type { Run, RunCreate, RunListResponse } from "../api/types";

// Query keys for cache invalidation
export const runKeys = {
  all: ["runs"] as const,
  lists: () => [...runKeys.all, "list"] as const,
  list: (params?: { page?: number; status?: string }) =>
    [...runKeys.lists(), params] as const,
  details: () => [...runKeys.all, "detail"] as const,
  detail: (id: string) => [...runKeys.details(), id] as const,
};

/**
 * Hook to fetch paginated list of runs
 */
export function useRuns(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}) {
  return useQuery<RunListResponse>({
    queryKey: runKeys.list(params),
    queryFn: () => fetchRuns(params),
  });
}

/**
 * Hook to fetch a single run by ID
 */
export function useRun(runId: string) {
  return useQuery<Run>({
    queryKey: runKeys.detail(runId),
    queryFn: () => fetchRun(runId),
    enabled: Boolean(runId),
  });
}

/**
 * Hook to create a new run
 */
export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RunCreate) => createRun(data),
    onSuccess: () => {
      // Invalidate runs list to refetch
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
  });
}

/**
 * Hook to start a run
 */
export function useStartRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => startRun(runId),
    onSuccess: (data) => {
      // Update cache with new run state
      queryClient.setQueryData(runKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
  });
}

/**
 * Hook to stop a run
 */
export function useStopRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => stopRun(runId),
    onSuccess: (data) => {
      // Update cache with new run state
      queryClient.setQueryData(runKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
  });
}
