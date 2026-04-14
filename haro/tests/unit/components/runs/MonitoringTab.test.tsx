/**
 * MonitoringTab Component Tests
 */

import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MonitoringTab } from "../../../../src/components/runs/MonitoringTab";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("MonitoringTab", () => {
  it("shows account card and positions for running run", async () => {
    renderWithProviders(<MonitoringTab runId="run-2" isRunning={true} />);

    expect(screen.getByTestId("monitoring-tab")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("account-card")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId("positions-table")).toBeInTheDocument();
    });
  });

  it("shows history note instead of snapshots for non-running run", async () => {
    renderWithProviders(<MonitoringTab runId="run-2" isRunning={false} />);

    expect(screen.getByTestId("monitoring-tab")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("monitoring-history-note")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("account-card")).not.toBeInTheDocument();
  });

  it("still loads fills for non-running run", async () => {
    renderWithProviders(<MonitoringTab runId="run-2" isRunning={false} />);

    await waitFor(() => {
      expect(screen.getByText("ETH/USD")).toBeInTheDocument();
    });
  });

  it("shows fills section heading", async () => {
    renderWithProviders(<MonitoringTab runId="run-2" isRunning={true} />);

    await waitFor(() => {
      expect(screen.getByText("Fills")).toBeInTheDocument();
    });
  });
});
