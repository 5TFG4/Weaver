/**
 * TradeLogTable Tests
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TradeLogTable } from "../../../src/components/runs/TradeLogTable";
import { mockBacktestResult } from "../../mocks/handlers";

describe("TradeLogTable", () => {
  it("renders table with fills data", () => {
    render(<TradeLogTable fills={mockBacktestResult.fills} />);

    expect(screen.getByTestId("trade-log")).toBeInTheDocument();
    expect(screen.getByText("Trade Log")).toBeInTheDocument();
    // Column headers
    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Side")).toBeInTheDocument();
    expect(screen.getByText("Qty")).toBeInTheDocument();
    expect(screen.getByText("Price")).toBeInTheDocument();
  });

  it("renders fill rows with correct data", () => {
    render(<TradeLogTable fills={mockBacktestResult.fills} />);

    expect(screen.getAllByText("BTC/USD")).toHaveLength(2);
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(screen.getByText("sell")).toBeInTheDocument();
    expect(screen.getByText("100.50")).toBeInTheDocument();
    expect(screen.getByText("102.00")).toBeInTheDocument();
  });

  it("shows empty state when no fills", () => {
    render(<TradeLogTable fills={[]} />);

    expect(screen.getByTestId("trade-log-empty")).toBeInTheDocument();
    expect(screen.getByText("No trades recorded.")).toBeInTheDocument();
  });

  it("colors buy side green and sell side red", () => {
    render(<TradeLogTable fills={mockBacktestResult.fills} />);

    const buy = screen.getByText("buy");
    const sell = screen.getByText("sell");
    expect(buy.className).toContain("text-green-400");
    expect(sell.className).toContain("text-red-400");
  });
});
