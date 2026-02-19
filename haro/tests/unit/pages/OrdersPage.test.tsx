/**
 * OrdersPage Tests (M7-5)
 *
 * Tests for the full orders page including data fetching,
 * filtering, loading/error/empty states, and detail modal.
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor, within } from "../../utils";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { OrdersPage } from "../../../src/pages/OrdersPage";
import userEvent from "@testing-library/user-event";
import type { OrderListResponse } from "../../../src/api/types";

describe("OrdersPage", () => {
  // Loading & Data Display
  it("shows loading state initially", () => {
    render(<OrdersPage />);
    expect(screen.getByTestId("orders-loading")).toBeInTheDocument();
  });

  it("displays order table with data from API", async () => {
    render(<OrdersPage />);
    await waitFor(() => {
      expect(screen.queryByTestId("orders-loading")).not.toBeInTheDocument();
    });
    expect(screen.getByText("order-1")).toBeInTheDocument();
    expect(screen.getByText("order-2")).toBeInTheDocument();
    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
  });

  // Empty State
  it("shows empty state when no orders", async () => {
    server.use(
      http.get("/api/v1/orders", () => {
        const response: OrderListResponse = {
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
        };
        return HttpResponse.json(response);
      }),
    );
    render(<OrdersPage />);
    await waitFor(() => {
      expect(screen.queryByTestId("orders-loading")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("orders-empty")).toBeInTheDocument();
    expect(screen.getByText(/no orders yet/i)).toBeInTheDocument();
  });

  // Error Handling
  it("shows error alert on API failure", async () => {
    server.use(
      http.get("/api/v1/orders", () => {
        return HttpResponse.json(
          { detail: "Internal Server Error" },
          { status: 500 },
        );
      }),
    );
    render(<OrdersPage />);
    await waitFor(
      () => {
        expect(screen.getByTestId("orders-error")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  // Filtering
  it("filters by status dropdown", async () => {
    const user = userEvent.setup();
    render(<OrdersPage />);
    await waitFor(() => {
      expect(screen.queryByTestId("orders-loading")).not.toBeInTheDocument();
    });

    // Select "filled" filter
    const statusFilter = screen.getByTestId("status-filter");
    await user.selectOptions(statusFilter, "filled");

    // Should trigger refetch (status param passed to hook)
    await waitFor(() => {
      expect(screen.getByText("order-1")).toBeInTheDocument();
    });
  });

  // Detail Modal
  it("opens detail modal on row click", async () => {
    const user = userEvent.setup();
    render(<OrdersPage />);
    await waitFor(() => {
      expect(screen.queryByTestId("orders-loading")).not.toBeInTheDocument();
    });

    const row = screen.getByTestId("order-row-order-1");
    await user.click(row);

    await waitFor(() => {
      expect(screen.getByTestId("order-detail-modal")).toBeInTheDocument();
    });
    expect(screen.getByText("Order Details")).toBeInTheDocument();
  });

  it("closes detail modal on close button click", async () => {
    const user = userEvent.setup();
    render(<OrdersPage />);
    await waitFor(() => {
      expect(screen.queryByTestId("orders-loading")).not.toBeInTheDocument();
    });

    // Open modal
    const row = screen.getByTestId("order-row-order-1");
    await user.click(row);
    await waitFor(() => {
      expect(screen.getByTestId("order-detail-modal")).toBeInTheDocument();
    });

    // Close modal - click the X button (aria-label="Close")
    const closeBtn = screen.getAllByRole("button", { name: /close/i })[0];
    await user.click(closeBtn);
    await waitFor(() => {
      expect(
        screen.queryByTestId("order-detail-modal"),
      ).not.toBeInTheDocument();
    });
  });
});
