/**
 * useAccount Hook
 *
 * React Query hooks for account and position data.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchAccount, fetchPositions } from "../api/account";
import type { AccountInfo, PositionListResponse } from "../api/types";

export const accountKeys = {
  all: ["account"] as const,
  info: () => [...accountKeys.all, "info"] as const,
  positions: () => [...accountKeys.all, "positions"] as const,
};

/**
 * Hook to fetch current account snapshot
 */
export function useAccount(options?: { enabled?: boolean }) {
  return useQuery<AccountInfo>({
    queryKey: accountKeys.info(),
    queryFn: fetchAccount,
    enabled: options?.enabled ?? true,
  });
}

/**
 * Hook to fetch open positions
 */
export function usePositions(options?: {
  enabled?: boolean;
  refetchInterval?: number | false;
}) {
  return useQuery<PositionListResponse>({
    queryKey: accountKeys.positions(),
    queryFn: fetchPositions,
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? false,
  });
}
