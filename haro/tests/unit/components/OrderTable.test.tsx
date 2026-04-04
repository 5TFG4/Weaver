/**
 * OrderTable Tests (M7-5)
 *
 * Tests for the order table component.
 * Validates rendering of order rows and column data.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "../../utils";
import { OrderTable } from "../../../src/components/orders/OrderTable";
import { mockOrders } from "../../mocks/handlers";
import type { Order } from "../../../src/api/types";
import userEvent from "@testing-library/user-event";

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

  // =========================================================================
  // H5: Table accessibility & overflow
  // =========================================================================

  it("table container has overflow-x-auto for horizontal scrolling", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);
    const table = screen.getByRole("table");
    const container = table.closest("div");
    expect(container).toHaveClass("overflow-x-auto");
  });

  it("order rows are keyboard accessible with tabIndex and role", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);
    const row = screen.getByTestId("order-row-order-1");
    expect(row).toHaveAttribute("tabindex", "0");
    expect(row).toHaveAttribute("role", "button");
  });

  it("pressing Enter on a row triggers onOrderClick", async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();
    render(<OrderTable orders={mockOrders} onOrderClick={handleClick} />);

    const row = screen.getByTestId("order-row-order-1");
    row.focus();
    await user.keyboard("{Enter}");

    expect(handleClick).toHaveBeenCalledWith(mockOrders[0]);
  });

  it("pressing Space on a row triggers onOrderClick", async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();
    render(<OrderTable orders={mockOrders} onOrderClick={handleClick} />);

    const row = screen.getByTestId("order-row-order-1");
    row.focus();
    await user.keyboard(" ");

    expect(handleClick).toHaveBeenCalledWith(mockOrders[0]);
  });
});

// Helper to render with userEvent
function renderWithUser(orders: Order[], onClick: (order: Order) => void) {
  const user = userEvent.setup();
  const result = render(<OrderTable orders={orders} onOrderClick={onClick} />);
  return { ...result, user };
}
