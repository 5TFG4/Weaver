/**
 * EquityCurveChart Tests
 *
 * Note: Recharts relies heavily on SVG rendering which jsdom doesn't fully
 * support. We test the component mount, empty state, and data acceptance
 * rather than pixel-level chart rendering.
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EquityCurveChart } from "../../../src/components/runs/EquityCurveChart";
import { mockBacktestResult } from "../../mocks/handlers";

describe("EquityCurveChart", () => {
  it("renders chart container with data", () => {
    render(<EquityCurveChart data={mockBacktestResult.equity_curve} />);

    expect(screen.getByTestId("equity-chart")).toBeInTheDocument();
    expect(screen.getByText("Equity Curve")).toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    render(<EquityCurveChart data={[]} />);

    expect(screen.getByTestId("equity-chart-empty")).toBeInTheDocument();
    expect(screen.getByText("No equity data available.")).toBeInTheDocument();
  });
});
