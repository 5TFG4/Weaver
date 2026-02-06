/**
 * OrderTable Tests (M7-5)
 *
 * Tests for the order table component.
 * Validates rendering of order rows and column data.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "../../utils";
import { OrderTable } from "../../../src/components/orders/OrderTable";
import { mockOrders } from "../../mocks/handlers";
import type { Order } from "../../../src/api/types";

describe("OrderTable", () => {
  it("renders order rows with correct data", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);
    // First order
    expect(screen.getByText("order-1")).toBeInTheDocument();
    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("0.1")).toBeInTheDocument();
    expect(screen.getByText("filled")).toBeInTheDocument();

    // Second order
    expect(screen.getByText("order-2")).toBeInTheDocument();
    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
    expect(screen.getByText("1.0")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  it("renders buy/sell side badges", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);
    const buyBadges = screen.getAllByText("buy");
    expect(buyBadges.length).toBeGreaterThanOrEqual(2);
  });

  it("shows empty state when no orders", () => {
    render(<OrderTable orders={[]} onOrderClick={vi.fn()} />);
    expect(screen.getByText(/no orders/i)).toBeInTheDocument();
  });

  it("calls onOrderClick when row is clicked", async () => {
    const handleClick = vi.fn();
    const { user } = renderWithUser(mockOrders, handleClick);
    const row = screen.getByTestId("order-row-order-1");
    await user.click(row);
    expect(handleClick).toHaveBeenCalledWith(mockOrders[0]);
  });

  it("displays price column for limit orders", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);
    expect(screen.getByText("2500.00")).toBeInTheDocument();
  });

  it("displays dash for market orders without price", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

// Helper to render with userEvent
function renderWithUser(orders: Order[], onClick: (order: Order) => void) {
  const userEvent = require("@testing-library/user-event").default;
  const user = userEvent.setup();
  const result = render(<OrderTable orders={orders} onOrderClick={onClick} />);
  return { ...result, user };
}
