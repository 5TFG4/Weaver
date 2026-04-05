/**
 * OrderDetailModal Tests — H4: Modal Accessibility
 *
 * Verifies proper ARIA attributes, keyboard interactions (Escape to close),
 * and that content renders correctly via @headlessui/react Dialog.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "../../utils";
import { OrderDetailModal } from "../../../src/components/orders/OrderDetailModal";
import userEvent from "@testing-library/user-event";
import type { Order } from "../../../src/api/types";

const mockOrder: Order = {
  id: "order-test-1",
  run_id: "run-1",
  client_order_id: "client-1",
  symbol: "BTC/USD",
  side: "buy",
  order_type: "market",
  qty: "0.5",
  time_in_force: "day",
  filled_qty: "0.5",
  filled_avg_price: "42000.00",
  status: "filled",
  created_at: "2026-01-15T10:00:00Z",
};

describe("OrderDetailModal — a11y", () => {
  it("renders with role='dialog'", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("has aria-modal='true'", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });
  });

  it("has aria-labelledby pointing to a visible title", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      const labelledBy = dialog.getAttribute("aria-labelledby");
      expect(labelledBy).toBeTruthy();
      const title = document.getElementById(labelledBy!);
      expect(title).toBeTruthy();
      expect(title!.textContent).toContain("Order Details");
    });
  });

  it("closes on Escape key press", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<OrderDetailModal order={mockOrder} onClose={onClose} />);
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("displays order detail content", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    expect(screen.getByText("order-test-1")).toBeInTheDocument();
    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getAllByText("0.5").length).toBeGreaterThanOrEqual(1);
  });

  it("preserves data-testid for integration tests", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByTestId("order-detail-modal")).toBeInTheDocument();
    });
  });
});
