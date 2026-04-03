/**
 * useStrategies Hook
 *
 * React Query hook for fetching available trading strategies.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchStrategies } from "../api/strategies";

export function useStrategies() {
  return useQuery({ queryKey: ["strategies"], queryFn: fetchStrategies });
}
