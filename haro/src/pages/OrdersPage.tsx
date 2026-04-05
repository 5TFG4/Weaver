/**
 * OrdersPage
 *
 * Displays a paginated list of orders with status/run_id filtering,
 * status badges, and a detail modal for inspecting individual orders.
 * Consumes data via TanStack Query hooks.
 */

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useOrders } from "../hooks/useOrders";
import { OrderTable } from "../components/orders/OrderTable";
import { OrderDetailModal } from "../components/orders/OrderDetailModal";
import { Pagination } from "../components/common/Pagination";
import type { Order, OrderStatus } from "../api/types";

const ORDER_STATUSES: OrderStatus[] = [
  "pending",
  "submitted",
  "accepted",
  "partial",
  "filled",
  "cancelled",
  "rejected",
  "expired",
];

export function OrdersPage() {
  const [searchParams] = useSearchParams();
  const urlRunId = searchParams.get("run_id") ?? undefined;

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [runIdFilter] = useState<string>(urlRunId ?? "");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const ordersQuery = useOrders({
    page,
    page_size: PAGE_SIZE,
    run_id: runIdFilter || undefined,
    status: statusFilter || undefined,
  });

  const isLoading = ordersQuery.isLoading;
  const isError = ordersQuery.isError;

  // Error State
  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Orders</h1>
          <p className="text-slate-400 mt-1">View and manage orders</p>
        </div>
        <div
          data-testid="orders-error"
          className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400"
        >
          <p className="font-medium">Failed to load orders</p>
          <p className="text-sm mt-1">
            {ordersQuery.error?.message ?? "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  // Loading State
  if (isLoading) {
    return (
      <div data-testid="orders-loading" className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Orders</h1>
          <p className="text-slate-400 mt-1">View and manage orders</p>
        </div>
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-12 bg-slate-700/50 rounded animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Data State
  const orders = ordersQuery.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Orders</h1>
          <p className="text-slate-400 mt-1">
            {runIdFilter
              ? `Orders for run ${runIdFilter}`
              : "View and manage orders"}
          </p>
        </div>
        <div className="flex gap-2">
          <select
            data-testid="status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded-lg text-sm"
          >
            <option value="">All Status</option>
            {ORDER_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <OrderTable orders={orders} onOrderClick={setSelectedOrder} />

      {(ordersQuery.data?.total ?? 0) > PAGE_SIZE && (
        <Pagination
          page={page}
          totalPages={Math.ceil((ordersQuery.data?.total ?? 0) / PAGE_SIZE)}
          onPageChange={setPage}
        />
      )}

      {selectedOrder && (
        <OrderDetailModal
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
        />
      )}
    </div>
  );
}
