/**
 * OrderDetailModal Component
 *
 * Modal overlay displaying full details of a single order.
 * Shows all fields including timestamps, prices, and reject reason.
 */

import type { Order } from "../../api/types";
import { OrderStatusBadge } from "./OrderStatusBadge";

export interface OrderDetailModalProps {
  order: Order;
  onClose: () => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export function OrderDetailModal({ order, onClose }: OrderDetailModalProps) {
  return (
    <div
      data-testid="order-detail-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    >
      <div className="bg-slate-800 rounded-lg border border-slate-700 w-full max-w-lg mx-4 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Order Details</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <DetailField label="Order ID" value={order.id} mono />
            <DetailField label="Run ID" value={order.run_id} mono />
            <DetailField label="Symbol" value={order.symbol} />
            <div>
              <span className="text-sm text-slate-400">Side</span>
              <div className="mt-1">
                <OrderStatusBadge side={order.side} />
              </div>
            </div>
            <DetailField label="Type" value={order.order_type} />
            <DetailField label="Quantity" value={order.qty} />
            {order.price && <DetailField label="Price" value={order.price} />}
            {order.stop_price && (
              <DetailField label="Stop Price" value={order.stop_price} />
            )}
            <DetailField label="Time in Force" value={order.time_in_force} />
            <div>
              <span className="text-sm text-slate-400">Status</span>
              <div className="mt-1">
                <OrderStatusBadge status={order.status} />
              </div>
            </div>
            <DetailField label="Filled Qty" value={order.filled_qty} />
            {order.filled_avg_price && (
              <DetailField
                label="Filled Avg Price"
                value={order.filled_avg_price}
              />
            )}
            <DetailField label="Created" value={formatDate(order.created_at)} />
            {order.submitted_at && (
              <DetailField
                label="Submitted"
                value={formatDate(order.submitted_at)}
              />
            )}
            {order.filled_at && (
              <DetailField label="Filled" value={formatDate(order.filled_at)} />
            )}
          </div>

          {order.reject_reason && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <span className="text-sm text-red-400 font-medium">
                Reject Reason:
              </span>
              <p className="text-sm text-red-300 mt-1">{order.reject_reason}</p>
            </div>
          )}

          {order.exchange_order_id && (
            <DetailField
              label="Exchange Order ID"
              value={order.exchange_order_id}
              mono
            />
          )}
          {order.client_order_id && (
            <DetailField
              label="Client Order ID"
              value={order.client_order_id}
              mono
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-4 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <span className="text-sm text-slate-400">{label}</span>
      <p className={`text-sm text-white mt-1 ${mono ? "font-mono" : ""}`}>
        {value}
      </p>
    </div>
  );
}
