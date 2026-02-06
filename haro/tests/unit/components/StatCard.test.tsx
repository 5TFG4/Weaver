/**
 * StatCard Component Tests
 *
 * TDD: RED → GREEN → REFACTOR
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "../../utils";
import { StatCard } from "../../../src/components/common/StatCard";

describe("StatCard", () => {
  it("displays title and value", () => {
    render(<StatCard title="Active Runs" value="3" />);

    expect(screen.getByText("Active Runs")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("displays trend indicator when provided", () => {
    render(<StatCard title="Total Orders" value="127" trend="+12%" />);

    expect(screen.getByText("Total Orders")).toBeInTheDocument();
    expect(screen.getByText("127")).toBeInTheDocument();
    expect(screen.getByText("+12%")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(
      <StatCard
        title="Active Runs"
        value="2"
        icon={<span data-testid="custom-icon">⚡</span>}
      />,
    );

    expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
  });

  it("applies status color variant", () => {
    const { container } = render(
      <StatCard title="API Status" value="Healthy" status="success" />,
    );

    // The value text should have the success color
    const valueEl = screen.getByText("Healthy");
    expect(valueEl).toHaveClass("text-green-400");
  });
});
