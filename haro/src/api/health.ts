/**
 * Health API
 *
 * API function for system health check.
 */

import { get } from "./client";
import type { HealthResponse } from "./types";

/**
 * Fetch API health status
 */
export async function fetchHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/healthz");
}
