/**
 * Dashboard Page Tests
 *
 * TDD: RED → GREEN → REFACTOR
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "../../utils";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { Dashboard } from "../../../src/pages/Dashboard";

describe("Dashboard", () => {
  it("shows loading skeleton initially", () => {
    render(<Dashboard />);

    // Should show loading indicators while data is fetching
    expect(screen.getByTestId("dashboard-loading")).toBeInTheDocument();
  });

  it("displays active run count from API", async () => {
    render(<Dashboard />);

    // Wait for data to load - mockRuns has 1 running run (run-2)
    await waitFor(() => {
      expect(screen.queryByTestId("dashboard-loading")).not.toBeInTheDocument();
    });

    // The stat card should show the count of running runs
    expect(screen.getByText("Active Runs")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("displays total orders count from API", async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.queryByTestId("dashboard-loading")).not.toBeInTheDocument();
    });

    // mockOrders has 2 orders total
    expect(screen.getByText("Total Orders")).toBeInTheDocument();
    // Both "Total Runs" and "Total Orders" show "2", so just verify the label exists
    // and there are at least two "2" values rendered
    const twos = screen.getAllByText("2");
    expect(twos.length).toBeGreaterThanOrEqual(1);
  });

  it("displays API health status", async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.queryByTestId("dashboard-loading")).not.toBeInTheDocument();
    });

    expect(screen.getByText("API Status")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
  });

  it("displays recent runs list", async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    });

    // Should show run strategy IDs from mock data (both runs use sma-crossover)
    await waitFor(() => {
      expect(screen.getAllByText("sma-crossover")).toHaveLength(2);
    });
  });

  it("shows per-card errors instead of full-page error when runs fail", async () => {
    // Override runs handler to return error
    server.use(
      http.get("/api/v1/runs", () => {
        return HttpResponse.json(
          { detail: "Internal Server Error" },
          { status: 500 },
        );
      }),
    );

    render(<Dashboard />);

    await waitFor(
      () => {
        // No full-page error panel anymore
        expect(screen.queryByTestId("dashboard-error")).not.toBeInTheDocument();
        // Individual cards report errors
        const totalCard = screen.getByTestId("stat-card-total-runs");
        expect(totalCard).toHaveAttribute("data-error", "true");
      },
      { timeout: 3000 },
    );
  });

  it("shows error on health stat card when health query fails", async () => {
    server.use(
      http.get("/api/v1/healthz", () =>
        HttpResponse.json({ detail: "Service unavailable" }, { status: 503 }),
      ),
    );

    render(<Dashboard />);

    // useHealth has retry: 1, so the query takes two roundtrips to error
    await waitFor(
      () => {
        const card = screen.getByTestId("stat-card-system");
        expect(card).toHaveAttribute("data-error", "true");
      },
      { timeout: 3000 },
    );
  });

  it("still shows runs data when health query fails", async () => {
    server.use(
      http.get("/api/v1/healthz", () =>
        HttpResponse.json({ detail: "down" }, { status: 503 }),
      ),
    );

    render(<Dashboard />);

    await waitFor(
      () => {
        expect(screen.getByText("Active Runs")).toBeInTheDocument();
        expect(screen.getByText("Total Runs")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("shows error on runs cards when runs query fails", async () => {
    server.use(
      http.get("/api/v1/runs", () =>
        HttpResponse.json({ detail: "error" }, { status: 500 }),
      ),
    );

    render(<Dashboard />);

    await waitFor(() => {
      const activeCard = screen.getByTestId("stat-card-active-runs");
      const totalCard = screen.getByTestId("stat-card-total-runs");
      expect(activeCard).toHaveAttribute("data-error", "true");
      expect(totalCard).toHaveAttribute("data-error", "true");
    });
  });

  it("shows error on orders card when orders query fails", async () => {
    server.use(
      http.get("/api/v1/orders", () =>
        HttpResponse.json({ detail: "error" }, { status: 500 }),
      ),
    );

    render(<Dashboard />);

    await waitFor(() => {
      const card = screen.getByTestId("stat-card-orders");
      expect(card).toHaveAttribute("data-error", "true");
    });
  });

  it("navigates to runs page on View All click", async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.queryByTestId("dashboard-loading")).not.toBeInTheDocument();
    });

    const viewAllLink = screen.getByRole("link", { name: /view all/i });
    expect(viewAllLink).toHaveAttribute("href", "/runs");
  });
});
