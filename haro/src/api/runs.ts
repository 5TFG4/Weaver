/**
 * Runs API
 *
 * API functions for managing trading runs.
 */

import { get, post } from "./client";
import type { Run, RunCreate, RunListResponse } from "./types";

/**
 * Fetch paginated list of runs
 */
export async function fetchRuns(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<RunListResponse> {
  const queryParams: Record<string, string> = {};
  if (params?.page) queryParams.page = String(params.page);
  if (params?.page_size) queryParams.page_size = String(params.page_size);
  if (params?.status) queryParams.status = params.status;

  return get<RunListResponse>("/runs", queryParams);
}

/**
 * Fetch a single run by ID
 */
export async function fetchRun(runId: string): Promise<Run> {
  return get<Run>(`/runs/${runId}`);
}

/**
 * Create a new run
 */
export async function createRun(data: RunCreate): Promise<Run> {
  return post<Run>("/runs", data);
}

/**
 * Start a run
 */
export async function startRun(runId: string): Promise<Run> {
  return post<Run>(`/runs/${runId}/start`);
}

/**
 * Stop a run
 */
export async function stopRun(runId: string): Promise<Run> {
  return post<Run>(`/runs/${runId}/stop`);
}
