/**
 * PositionsTable Component Tests
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PositionsTable } from "../../../../src/components/runs/PositionsTable";
import { mockPositions } from "../../../mocks/handlers";

describe("PositionsTable", () => {
  it("renders table headers", () => {
    render(<PositionsTable positions={mockPositions} />);

    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Qty")).toBeInTheDocument();
    expect(screen.getByText("Side")).toBeInTheDocument();
    expect(screen.getByText("Avg Entry")).toBeInTheDocument();
    expect(screen.getByText("Market Value")).toBeInTheDocument();
    expect(screen.getByText("Unrealized P&L")).toBeInTheDocument();
  });

  it("renders position rows", () => {
    render(<PositionsTable positions={mockPositions} />);

    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
    expect(screen.getByText("1.0")).toBeInTheDocument();
    expect(screen.getByText("long")).toBeInTheDocument();
  });

  it("shows positive P&L in green", () => {
    render(<PositionsTable positions={mockPositions} />);

    const pnlCell = screen.getByTestId("pnl-ETH/USD");
    expect(pnlCell).toHaveClass("text-green-400");
  });

  it("shows negative P&L in red", () => {
    const negativePosition = [
      {
        ...mockPositions[0],
        symbol: "BTC/USD",
        unrealized_pnl: "-100.00",
        unrealized_pnl_percent: "-1.50",
      },
    ];
    render(<PositionsTable positions={negativePosition} />);

    const pnlCell = screen.getByTestId("pnl-BTC/USD");
    expect(pnlCell).toHaveClass("text-red-400");
  });

  it("renders empty state when no positions", () => {
    render(<PositionsTable positions={[]} />);

    expect(screen.getByTestId("positions-empty")).toBeInTheDocument();
    expect(screen.getByText(/no open positions/i)).toBeInTheDocument();
  });
});
