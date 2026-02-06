/**
 * ActivityFeed Component Tests
 *
 * TDD: RED → GREEN → REFACTOR
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "../../utils";
import { ActivityFeed } from "../../../src/components/dashboard/ActivityFeed";
import type { Run } from "../../../src/api/types";

const mockRuns: Run[] = [
  {
    id: "run-1",
    strategy_id: "sma-crossover",
    mode: "paper",
    status: "running",
    symbols: ["BTC/USD"],
    timeframe: "1h",
    created_at: new Date().toISOString(),
  },
  {
    id: "run-2",
    strategy_id: "sma-crossover",
    mode: "backtest",
    status: "completed",
    symbols: ["ETH/USD"],
    timeframe: "15m",
    created_at: "2026-02-01T10:00:00Z",
  },
];

describe("ActivityFeed", () => {
  it("displays run entries with strategy and symbols", () => {
    render(<ActivityFeed runs={mockRuns} />);

    expect(screen.getAllByText("sma-crossover")).toHaveLength(2);
    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
  });

  it("displays status badges for each run", () => {
    render(<ActivityFeed runs={mockRuns} />);

    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("shows empty state when no runs", () => {
    render(<ActivityFeed runs={[]} />);

    expect(screen.getByText("No recent activity")).toBeInTheDocument();
  });

  it("shows loading skeleton", () => {
    render(<ActivityFeed runs={[]} isLoading />);

    expect(screen.getByTestId("activity-loading")).toBeInTheDocument();
  });
});
