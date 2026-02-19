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

  it("displays symbols for each run", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
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
    expect(screen.getByLabelText(/symbols/i)).toBeInTheDocument();
  });

  it("creates a run via form submission", async () => {
    const user = userEvent.setup();

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // Open form
    await user.click(screen.getByRole("button", { name: /new run/i }));

    // Fill form
    await user.type(screen.getByLabelText(/strategy/i), "sma-crossover");
    await user.type(screen.getByLabelText(/symbols/i), "BTC/USD");

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
});
