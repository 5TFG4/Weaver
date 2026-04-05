/**
 * Strategies API
 *
 * API functions for fetching available trading strategies.
 */

import { get } from "./client";
import type { StrategyMeta } from "./types";

/**
 * Fetch all available strategies
 */
export async function fetchStrategies(): Promise<StrategyMeta[]> {
  return get<StrategyMeta[]>("/strategies");
}
