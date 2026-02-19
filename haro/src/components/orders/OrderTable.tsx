/**
 * OrderTable Component
 *
 * Displays a table of orders with status badges, side indicators,
 * and clickable rows for viewing order details.
 */

import type { Order } from "../../api/types";
import { OrderStatusBadge } from "./OrderStatusBadge";

export interface OrderTableProps {
  orders: Order[];
  onOrderClick: (order: Order) => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export function OrderTable({ orders, onOrderClick }: OrderTableProps) {
  if (orders.length === 0) {
    return (
      <div
        data-testid="orders-empty"
        className="bg-slate-800 rounded-lg border border-slate-700 p-12"
      >
        <div className="text-center text-slate-400">
          <svg
            className="w-12 h-12 mx-auto mb-4 text-slate-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <p>No orders yet</p>
          <p className="text-sm mt-1">
            Orders will appear here when strategies generate trades
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <table className="w-full">
        <thead className="bg-slate-700/50">
          <tr>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Order ID
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Symbol
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Side
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Type
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Qty
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Price
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Status
            </th>
            <th className="text-left px-6 py-3 text-sm font-medium text-slate-300">
              Time
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {orders.map((order) => (
            <tr
              key={order.id}
              data-testid={`order-row-${order.id}`}
              onClick={() => onOrderClick(order)}
              className="hover:bg-slate-700/30 transition-colors cursor-pointer"
            >
              <td className="px-6 py-4 text-sm text-slate-200 font-mono">
                {order.id}
              </td>
              <td className="px-6 py-4 text-sm text-slate-200">
                {order.symbol}
              </td>
              <td className="px-6 py-4">
                <OrderStatusBadge side={order.side} />
              </td>
              <td className="px-6 py-4 text-sm text-slate-200">
                {order.order_type}
              </td>
              <td className="px-6 py-4 text-sm text-slate-200 text-right">
                {order.qty}
              </td>
              <td className="px-6 py-4 text-sm text-slate-200 text-right">
                {order.price ?? "—"}
              </td>
              <td className="px-6 py-4">
                <OrderStatusBadge status={order.status} />
              </td>
              <td className="px-6 py-4 text-sm text-slate-400">
                {formatDate(order.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
