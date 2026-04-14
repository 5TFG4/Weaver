/**
 * RunFillsTable Component Tests
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RunFillsTable } from "../../../../src/components/runs/RunFillsTable";
import { mockFills } from "../../../mocks/handlers";

describe("RunFillsTable", () => {
  it("renders table headers", () => {
    render(
      <RunFillsTable fills={mockFills} isLoading={false} isError={false} />,
    );

    expect(screen.getByText("Time")).toBeInTheDocument();
    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Side")).toBeInTheDocument();
    expect(screen.getByText("Qty")).toBeInTheDocument();
    expect(screen.getByText("Price")).toBeInTheDocument();
    expect(screen.getByText("Commission")).toBeInTheDocument();
  });

  it("renders fill rows", () => {
    render(
      <RunFillsTable fills={mockFills} isLoading={false} isError={false} />,
    );

    expect(screen.getByText("ETH/USD")).toBeInTheDocument();
    expect(screen.getByText("2500.00")).toBeInTheDocument();
    expect(screen.getByText("1.0")).toBeInTheDocument();
    expect(screen.getByText("1.00")).toBeInTheDocument();
  });

  it("colors buy side green and sell side red", () => {
    const fills = [
      { ...mockFills[0], id: "f1", side: "buy" as const },
      {
        ...mockFills[0],
        id: "f2",
        side: "sell" as const,
        filled_at: "2026-02-04T08:10:00Z",
      },
    ];
    render(<RunFillsTable fills={fills} isLoading={false} isError={false} />);

    const buySide = screen.getAllByText("buy")[0];
    expect(buySide).toHaveClass("text-green-400");

    const sellSide = screen.getByText("sell");
    expect(sellSide).toHaveClass("text-red-400");
  });

  it("renders empty state when no fills", () => {
    render(<RunFillsTable fills={[]} isLoading={false} isError={false} />);

    expect(screen.getByTestId("fills-empty")).toBeInTheDocument();
    expect(screen.getByText(/no fills recorded/i)).toBeInTheDocument();
  });

  it("renders loading skeleton", () => {
    render(<RunFillsTable fills={[]} isLoading={true} isError={false} />);

    expect(screen.getByTestId("fills-loading")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(<RunFillsTable fills={[]} isLoading={false} isError={true} />);

    expect(screen.getByTestId("fills-error")).toBeInTheDocument();
  });

  it("shows dash when commission is null", () => {
    const fills = [{ ...mockFills[0], commission: null }];
    render(<RunFillsTable fills={fills} isLoading={false} isError={false} />);

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
