/**
 * Fills API
 *
 * API functions for run fill data.
 */

import { get } from "./client";
import type { FillListResponse } from "./types";

/**
 * Fetch fills for a specific run
 */
export async function fetchFills(runId: string): Promise<FillListResponse> {
  return get<FillListResponse>(`/runs/${runId}/fills`);
}
