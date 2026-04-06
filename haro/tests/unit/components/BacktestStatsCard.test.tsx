/**
 * BacktestStatsCard Tests
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BacktestStatsCard } from "../../../src/components/runs/BacktestStatsCard";
import { mockBacktestResult } from "../../mocks/handlers";

describe("BacktestStatsCard", () => {
  it("renders key statistics from result", () => {
    render(<BacktestStatsCard result={mockBacktestResult} />);

    expect(screen.getByTestId("backtest-stats")).toBeInTheDocument();
    expect(screen.getByText("Statistics")).toBeInTheDocument();
    expect(screen.getByText("Final Equity")).toBeInTheDocument();
    expect(screen.getByText("Total Return")).toBeInTheDocument();
    expect(screen.getByText("Sharpe Ratio")).toBeInTheDocument();
    expect(screen.getByText("Max Drawdown")).toBeInTheDocument();
  });

  it("displays formatted stat values", () => {
    render(<BacktestStatsCard result={mockBacktestResult} />);

    // Total Return: 0.05 → 5.00%
    expect(screen.getByText("5.00%")).toBeInTheDocument();
    // Sharpe Ratio: 1.23
    expect(screen.getByText("1.23")).toBeInTheDocument();
    // Max Drawdown: -0.02 → -2.00%
    expect(screen.getByText("-2.00%")).toBeInTheDocument();
    // Total Trades: 5
    expect(screen.getByText("5")).toBeInTheDocument();
    // Win Rate: 0.6 → 60.00%
    expect(screen.getByText("60.00%")).toBeInTheDocument();
  });

  it("displays bars processed and duration", () => {
    render(<BacktestStatsCard result={mockBacktestResult} />);

    expect(screen.getByText("100")).toBeInTheDocument(); // bars
    expect(screen.getByText("1.2s")).toBeInTheDocument(); // 1234ms
  });
});
