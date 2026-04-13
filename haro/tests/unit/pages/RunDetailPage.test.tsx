/**
 * RunDetailPage Tests
 */

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { RunDetailPage } from "../../../src/pages/RunDetailPage";
import { server } from "../../mocks/server";

function renderWithRoute(runId: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/runs/${runId}`]}>
        <Routes>
          <Route path="/runs/:runId" element={<RunDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RunDetailPage", () => {
  it("shows loading state initially", () => {
    renderWithRoute("run-1");
    expect(screen.getByTestId("run-detail-loading")).toBeInTheDocument();
  });

  it("shows run metadata after loading", async () => {
    renderWithRoute("run-1");

    await waitFor(() => {
      expect(screen.getByTestId("run-detail")).toBeInTheDocument();
    });

    expect(screen.getByText("sma-crossover")).toBeInTheDocument();
    expect(screen.getByText("backtest")).toBeInTheDocument();
  });

  it("shows error state for unknown run", async () => {
    server.use(
      http.get("/api/v1/runs/:id", () =>
        HttpResponse.json({ detail: "Run not found" }, { status: 404 }),
      ),
    );

    renderWithRoute("nonexistent");

    await waitFor(() => {
      expect(screen.getByTestId("run-detail-error")).toBeInTheDocument();
    });
  });

  it("shows backtest results for completed backtest run", async () => {
    renderWithRoute("run-1");

    await waitFor(() => {
      expect(screen.getByTestId("backtest-stats")).toBeInTheDocument();
    });

    expect(screen.getByTestId("equity-chart")).toBeInTheDocument();
    expect(screen.getByTestId("trade-log")).toBeInTheDocument();
  });

  it("shows monitoring tab for running paper run", async () => {
    renderWithRoute("run-2");

    await waitFor(() => {
      expect(screen.getByTestId("run-detail")).toBeInTheDocument();
    });

    expect(screen.getByText("Monitoring")).toBeInTheDocument();
    expect(screen.getByTestId("monitoring-tab")).toBeInTheDocument();
  });

  it("shows error field when run has error", async () => {
    server.use(
      http.get("/api/v1/runs/:id", () =>
        HttpResponse.json({
          id: "run-err",
          strategy_id: "sma-crossover",
          mode: "backtest",
          status: "error",
          config: {},
          error: "Broker connection failed",
          created_at: "2026-02-01T10:00:00Z",
        }),
      ),
    );

    renderWithRoute("run-err");

    await waitFor(() => {
      expect(screen.getByText("Broker connection failed")).toBeInTheDocument();
    });
  });

  it("renders back-to-runs link", async () => {
    renderWithRoute("run-1");

    await waitFor(() => {
      expect(screen.getByTestId("run-detail")).toBeInTheDocument();
    });

    const backLink = screen.getByText(/back to runs/i);
    expect(backLink).toBeInTheDocument();
    expect(backLink.closest("a")).toHaveAttribute("href", "/runs");
  });

  it("shows results tab label for completed backtest", async () => {
    renderWithRoute("run-1");

    await waitFor(() => {
      expect(screen.getByText("Results")).toBeInTheDocument();
    });
  });

  it("shows pending message for non-completed backtest", async () => {
    server.use(
      http.get("/api/v1/runs/:id", () =>
        HttpResponse.json({
          id: "run-bt-pending",
          strategy_id: "sma-crossover",
          mode: "backtest",
          status: "running",
          config: {},
          error: null,
          created_at: "2026-02-01T10:00:00Z",
          started_at: "2026-02-01T10:00:01Z",
        }),
      ),
    );

    renderWithRoute("run-bt-pending");

    await waitFor(() => {
      expect(screen.getByTestId("run-detail")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Results will appear here once the run completes."),
    ).toBeInTheDocument();
  });
});
