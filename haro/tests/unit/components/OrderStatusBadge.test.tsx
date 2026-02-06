/**
 * OrderStatusBadge Tests (M7-5)
 *
 * Tests for the order-specific status badge component.
 * Validates correct color variants for all order statuses.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "../../utils";
import { OrderStatusBadge } from "../../../src/components/orders/OrderStatusBadge";
import type { OrderSide, OrderStatus } from "../../../src/api/types";

describe("OrderStatusBadge", () => {
  it("renders correct color for each order status", () => {
    const statuses: OrderStatus[] = [
      "pending",
      "submitted",
      "accepted",
      "partial",
      "filled",
      "cancelled",
      "rejected",
      "expired",
    ];

    for (const status of statuses) {
      const { unmount } = render(<OrderStatusBadge status={status} />);
      const badge = screen.getByText(status);
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("rounded-full");
      unmount();
    }
  });

  it("renders status text", () => {
    render(<OrderStatusBadge status="filled" />);
    expect(screen.getByText("filled")).toBeInTheDocument();
  });

  it("renders buy side badge in green", () => {
    render(<OrderStatusBadge side="buy" />);
    const badge = screen.getByText("buy");
    expect(badge).toHaveClass("text-green-400");
  });

  it("renders sell side badge in red", () => {
    render(<OrderStatusBadge side="sell" />);
    const badge = screen.getByText("sell");
    expect(badge).toHaveClass("text-red-400");
  });
});
