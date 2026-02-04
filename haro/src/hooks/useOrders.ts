/**
 * useOrders Hook
 *
 * React Query hooks for orders data management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchOrders, fetchOrder, cancelOrder } from "../api/orders";
import type { Order, OrderListResponse } from "../api/types";

// Query keys for cache invalidation
export const orderKeys = {
  all: ["orders"] as const,
  lists: () => [...orderKeys.all, "list"] as const,
  list: (params?: { page?: number; run_id?: string; status?: string }) =>
    [...orderKeys.lists(), params] as const,
  details: () => [...orderKeys.all, "detail"] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
};

/**
 * Hook to fetch paginated list of orders
 */
export function useOrders(params?: {
  page?: number;
  page_size?: number;
  run_id?: string;
  status?: string;
}) {
  return useQuery<OrderListResponse>({
    queryKey: orderKeys.list(params),
    queryFn: () => fetchOrders(params),
  });
}

/**
 * Hook to fetch a single order by ID
 */
export function useOrder(orderId: string) {
  return useQuery<Order>({
    queryKey: orderKeys.detail(orderId),
    queryFn: () => fetchOrder(orderId),
    enabled: Boolean(orderId),
  });
}

/**
 * Hook to cancel an order
 */
export function useCancelOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orderId: string) => cancelOrder(orderId),
    onSuccess: (_data, orderId) => {
      // Invalidate order cache
      queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) });
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
}
