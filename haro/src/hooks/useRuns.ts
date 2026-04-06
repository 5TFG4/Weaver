/**
 * useRuns Hook
 *
 * React Query hooks for runs data management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchRuns,
  fetchRun,
  createRun,
  startRun,
  stopRun,
  fetchRunResults,
} from "../api/runs";
import type { BacktestResult, Run, RunCreate, RunListResponse } from "../api/types";
import { useNotificationStore } from "../stores/notificationStore";

// Query keys for cache invalidation
export const runKeys = {
  all: ["runs"] as const,
  lists: () => [...runKeys.all, "list"] as const,
  list: (params?: { page?: number; status?: string }) =>
    [...runKeys.lists(), params] as const,
  details: () => [...runKeys.all, "detail"] as const,
  detail: (id: string) => [...runKeys.details(), id] as const,
  results: (id: string) => [...runKeys.all, "results", id] as const,
};

/**
 * Hook to fetch paginated list of runs
 */
export function useRuns(
  params?: {
    page?: number;
    page_size?: number;
    status?: string;
  },
  options?: { enabled?: boolean },
) {
  return useQuery<RunListResponse>({
    queryKey: runKeys.list(params),
    queryFn: () => fetchRuns(params),
    enabled: options?.enabled ?? true,
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
 * Hook to fetch backtest results for a completed run
 */
export function useRunResults(
  runId: string,
  options?: { enabled?: boolean },
) {
  return useQuery<BacktestResult>({
    queryKey: runKeys.results(runId),
    queryFn: () => fetchRunResults(runId),
    enabled: (options?.enabled ?? true) && Boolean(runId),
  });
}

/**
 * Hook to create a new run
 */
export function useCreateRun() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);

  return useMutation({
    mutationFn: (data: RunCreate) => createRun(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
      addNotification({
        type: "success",
        message: "Run created successfully",
      });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to create run",
      });
    },
  });
}

/**
 * Hook to start a run
 */
export function useStartRun() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);

  return useMutation({
    mutationFn: (runId: string) => startRun(runId),
    onSuccess: (data) => {
      // Update cache with new run state
      queryClient.setQueryData(runKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to start run",
      });
    },
  });
}

/**
 * Hook to stop a run
 */
export function useStopRun() {
  const queryClient = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);

  return useMutation({
    mutationFn: (runId: string) => stopRun(runId),
    onSuccess: (data) => {
      // Update cache with new run state
      queryClient.setQueryData(runKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
    },
    onError: (error: Error) => {
      addNotification({
        type: "error",
        message: error.message || "Failed to stop run",
      });
    },
  });
}
