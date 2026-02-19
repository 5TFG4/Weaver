/**
 * Orders API
 *
 * API functions for managing orders.
 */

import { get, del } from "./client";
import type { Order, OrderListResponse } from "./types";

/**
 * Fetch paginated list of orders
 */
export async function fetchOrders(params?: {
  page?: number;
  page_size?: number;
  run_id?: string;
  status?: string;
}): Promise<OrderListResponse> {
  const queryParams: Record<string, string> = {};
  if (params?.page) queryParams.page = String(params.page);
  if (params?.page_size) queryParams.page_size = String(params.page_size);
  if (params?.run_id) queryParams.run_id = params.run_id;
  if (params?.status) queryParams.status = params.status;

  return get<OrderListResponse>("/orders", queryParams);
}

/**
 * Fetch a single order by ID
 */
export async function fetchOrder(orderId: string): Promise<Order> {
  return get<Order>(`/orders/${orderId}`);
}

/**
 * Cancel an order
 */
export async function cancelOrder(orderId: string): Promise<void> {
  return del<void>(`/orders/${orderId}`);
}
