/**
 * OrderStatusBadge Component
 *
 * Specialized badge for displaying order status and side (buy/sell).
 * Color-coded for quick visual identification of order states.
 */

import type { OrderSide, OrderStatus } from "../../api/types";

const statusStyles: Record<OrderStatus, string> = {
  pending: "bg-slate-500/20 text-slate-400",
  submitted: "bg-blue-500/20 text-blue-400",
  accepted: "bg-blue-500/20 text-blue-400",
  partial: "bg-yellow-500/20 text-yellow-400",
  filled: "bg-green-500/20 text-green-400",
  cancelled: "bg-slate-500/20 text-slate-400",
  rejected: "bg-red-500/20 text-red-400",
  expired: "bg-slate-500/20 text-slate-400",
};

const sideStyles: Record<OrderSide, string> = {
  buy: "bg-green-500/20 text-green-400",
  sell: "bg-red-500/20 text-red-400",
};

export interface OrderStatusBadgeProps {
  status?: OrderStatus;
  side?: OrderSide;
}

export function OrderStatusBadge({ status, side }: OrderStatusBadgeProps) {
  if (side) {
    const style = sideStyles[side];
    return (
      <span
        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${style}`}
      >
        {side}
      </span>
    );
  }

  if (status) {
    const style = statusStyles[status] ?? statusStyles.pending;
    return (
      <span
        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${style}`}
      >
        {status}
      </span>
    );
  }

  return null;
}
