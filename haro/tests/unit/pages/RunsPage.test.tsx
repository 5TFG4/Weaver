/**
 * RunsPage Tests
 *
 * TDD: RED → GREEN → REFACTOR
 *
 * Tests the Runs page which displays a list of trading runs,
 * allows creating new runs, and provides start/stop controls.
 */

import { describe, it, expect } from "vitest";
import { render, screen, waitFor, within } from "../../utils";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { mockRuns } from "../../mocks/handlers";
import { RunsPage } from "../../../src/pages/RunsPage";
import userEvent from "@testing-library/user-event";
import type { RunListResponse } from "../../../src/api/types";

describe("RunsPage", () => {
  // =========================================================================
  // Loading & Data Display
  // =========================================================================

  it("shows loading state initially", () => {
    render(<RunsPage />);

    expect(screen.getByTestId("runs-loading")).toBeInTheDocument();
  });

  it("displays runs table with data from API", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // Should show strategy IDs from mock data
    expect(screen.getAllByText("sma-crossover")).toHaveLength(2);
    // Should show run IDs
    expect(screen.getByText("run-1")).toBeInTheDocument();
    expect(screen.getByText("run-2")).toBeInTheDocument();
  });

  it("renders run IDs as links to detail page", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const link1 = screen.getByRole("link", { name: "run-1" });
    expect(link1).toHaveAttribute("href", "/runs/run-1");
    const link2 = screen.getByRole("link", { name: "run-2" });
    expect(link2).toHaveAttribute("href", "/runs/run-2");
  });

  it("displays run mode badges", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // run-1 is backtest, run-2 is paper
    expect(screen.getByText("backtest")).toBeInTheDocument();
    expect(screen.getByText("paper")).toBeInTheDocument();
  });

  it("displays run status badges with correct styling", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // run-1 is completed, run-2 is running
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("displays symbols and timeframe for each run", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
    expect(screen.getByText("1h")).toBeInTheDocument();
    expect(screen.getByText("15m")).toBeInTheDocument();
  });

  // =========================================================================
  // Empty State
  // =========================================================================

  it("shows empty state when no runs exist", async () => {
    server.use(
      http.get("/api/v1/runs", () => {
        const response: RunListResponse = {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        };
        return HttpResponse.json(response);
      }),
    );

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    expect(screen.getByTestId("runs-empty")).toBeInTheDocument();
    expect(screen.getByText(/no runs yet/i)).toBeInTheDocument();
  });

  // =========================================================================
  // Error Handling
  // =========================================================================

  it("shows error alert on API failure", async () => {
    server.use(
      http.get("/api/v1/runs", () => {
        return HttpResponse.json(
          { detail: "Internal Server Error" },
          { status: 500 },
        );
      }),
    );

    render(<RunsPage />);

    await waitFor(
      () => {
        expect(screen.getByTestId("runs-error")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  // =========================================================================
  // Run Actions (Start / Stop)
  // =========================================================================

  it("shows stop button for running runs", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // run-2 is running, should have stop button
    const row = screen.getByTestId("run-row-run-2");
    expect(
      within(row).getByRole("button", { name: /stop/i }),
    ).toBeInTheDocument();
  });

  it("shows start button for pending runs", async () => {
    server.use(
      http.get("/api/v1/runs", () => {
        const response: RunListResponse = {
          items: [
            {
              id: "run-pending",
              strategy_id: "sma-crossover",
              mode: "backtest",
              status: "pending",
              config: { symbols: ["BTC/USD"], timeframe: "1h" },
              error: null,
              created_at: "2026-02-01T10:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        };
        return HttpResponse.json(response);
      }),
    );

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const row = screen.getByTestId("run-row-run-pending");
    expect(
      within(row).getByRole("button", { name: /start/i }),
    ).toBeInTheDocument();
  });

  it("calls start API when start button clicked", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/v1/runs", () => {
        const response: RunListResponse = {
          items: [
            {
              id: "run-pending",
              strategy_id: "sma-crossover",
              mode: "backtest",
              status: "pending",
              config: { symbols: ["BTC/USD"], timeframe: "1h" },
              error: null,
              created_at: "2026-02-01T10:00:00Z",
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        };
        return HttpResponse.json(response);
      }),
      http.post("/api/v1/runs/:id/start", ({ params }) => {
        return HttpResponse.json({
          id: params.id as string,
          strategy_id: "sma-crossover",
          mode: "backtest",
          status: "running",
          config: { symbols: ["BTC/USD"], timeframe: "1h" },
          created_at: "2026-02-01T10:00:00Z",
          started_at: new Date().toISOString(),
        });
      }),
    );

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const row = screen.getByTestId("run-row-run-pending");
    const startBtn = within(row).getByRole("button", { name: /start/i });
    await user.click(startBtn);

    // After start, the run status should optimistically update to running
    await waitFor(() => {
      expect(within(row).getByText("running")).toBeInTheDocument();
    });
  });

  it("does not show start button for running runs", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // run-2 is running, should NOT have start button
    const row = screen.getByTestId("run-row-run-2");
    expect(
      within(row).queryByRole("button", { name: /start/i }),
    ).not.toBeInTheDocument();
  });

  it("does not show stop button for completed runs", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // run-1 is completed, should NOT have stop button
    const row = screen.getByTestId("run-row-run-1");
    expect(
      within(row).queryByRole("button", { name: /stop/i }),
    ).not.toBeInTheDocument();
  });

  it("calls stop API when stop button clicked", async () => {
    const user = userEvent.setup();

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const row = screen.getByTestId("run-row-run-2");
    const stopBtn = within(row).getByRole("button", { name: /stop/i });
    await user.click(stopBtn);

    // After stop, the run status should update (MSW returns stopped)
    await waitFor(() => {
      expect(within(row).getByText("stopped")).toBeInTheDocument();
    });
  });

  // =========================================================================
  // Create Run
  // =========================================================================

  it("has a New Run button", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    expect(
      screen.getByRole("button", { name: /new run/i }),
    ).toBeInTheDocument();
  });

  it("shows create run form when New Run clicked", async () => {
    const user = userEvent.setup();

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /new run/i }));

    // Form fields should appear
    expect(screen.getByLabelText(/strategy/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mode/i)).toBeInTheDocument();
  });

  it("creates a run via form submission", async () => {
    const user = userEvent.setup();

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // Open form
    await user.click(screen.getByRole("button", { name: /new run/i }));

    // Fill form — Strategy is a dropdown now
    await user.selectOptions(
      screen.getByLabelText(/strategy/i),
      "sma-crossover",
    );

    // Submit
    await user.click(screen.getByRole("button", { name: /create/i }));

    // Form should close and list should refresh
    await waitFor(() => {
      expect(screen.queryByLabelText(/strategy/i)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // Navigation
  // =========================================================================

  it("links to orders page", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const ordersLink = screen.getByRole("link", { name: /orders/i });
    expect(ordersLink).toHaveAttribute("href", "/orders");
  });

  // =========================================================================
  // H5: Table overflow
  // =========================================================================

  it("runs table container has overflow-x-auto", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const table = screen.getByRole("table");
    const container = table.closest("div");
    expect(container).toHaveClass("overflow-x-auto");
  });

  // =========================================================================
  // H6: Pagination
  // =========================================================================

  it("shows pagination controls when total exceeds page size", async () => {
    server.use(
      http.get("/api/v1/runs", ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get("page") || "1");
        const response: RunListResponse = {
          items: mockRuns,
          total: 100,
          page,
          page_size: 20,
        };
        return HttpResponse.json(response);
      }),
    );

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /previous/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument();
  });
});
