/**
 * Pagination Component Tests — H6
 *
 * Tests for the generic prev/next pagination component.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "../../utils";
import userEvent from "@testing-library/user-event";
import { Pagination } from "../../../src/components/common/Pagination";

describe("Pagination", () => {
  it("renders current page and total pages", () => {
    render(<Pagination page={2} totalPages={5} onPageChange={vi.fn()} />);
    expect(screen.getByText(/Page 2 of 5/)).toBeInTheDocument();
  });

  it("disables Previous button on first page", () => {
    render(<Pagination page={1} totalPages={5} onPageChange={vi.fn()} />);
    const prevBtn = screen.getByRole("button", { name: /previous/i });
    expect(prevBtn).toBeDisabled();
  });

  it("disables Next button on last page", () => {
    render(<Pagination page={5} totalPages={5} onPageChange={vi.fn()} />);
    const nextBtn = screen.getByRole("button", { name: /next/i });
    expect(nextBtn).toBeDisabled();
  });

  it("calls onPageChange with page-1 when Previous is clicked", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);

    await user.click(screen.getByRole("button", { name: /previous/i }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange with page+1 when Next is clicked", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={3} totalPages={5} onPageChange={onPageChange} />);

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(onPageChange).toHaveBeenCalledWith(4);
  });

  it("does not render when totalPages <= 1", () => {
    const { container } = render(
      <Pagination page={1} totalPages={1} onPageChange={vi.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });
});
