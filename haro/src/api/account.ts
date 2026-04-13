/**
 * Account API
 *
 * API functions for account and position data.
 */

import { get } from "./client";
import type { AccountInfo, PositionListResponse } from "./types";

/**
 * Fetch current account snapshot
 */
export async function fetchAccount(): Promise<AccountInfo> {
  return get<AccountInfo>("/account");
}

/**
 * Fetch open positions
 */
export async function fetchPositions(): Promise<PositionListResponse> {
  return get<PositionListResponse>("/account/positions");
}
