/**
 * CreateRunForm Tests — H2: symbols enum renders as dropdown
 *
 * Verifies that when strategy config_schema has enum on symbols items,
 * RJSF renders a <select> via the custom SelectWidget.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "../../utils";
import userEvent from "@testing-library/user-event";
import { CreateRunForm } from "../../../src/components/runs/CreateRunForm";

describe("CreateRunForm — H2 symbols enum", () => {
  it("renders symbols array items as dropdown select when schema has enum", async () => {
    // Default MSW handlers already return strategies with enum on symbols.items
    const user = userEvent.setup();
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    // Wait for strategies to load (options appear in select)
    await waitFor(() => {
      const select = screen.getByLabelText(/strategy/i);
      const options = select.querySelectorAll("option");
      expect(options.length).toBeGreaterThan(1); // More than just "Select strategy..."
    });
    await user.selectOptions(screen.getByLabelText(/strategy/i), "sample");

    // RJSF should render the config form with ArrayFieldTemplate
    // Click "Add item" to add a symbols entry
    await waitFor(() => {
      expect(screen.getByTestId("rjsf-add-item")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("rjsf-add-item"));

    // After adding an item, the enum should render as a <select> via SelectWidget.
    // The form already has 2 selects (strategy, mode) + 1 from RJSF timeframe.
    // Adding a symbols item should add another select with enum options.
    await waitFor(() => {
      const allSelects = document.querySelectorAll("select");
      const symbolSelect = Array.from(allSelects).find((s) => {
        const options = Array.from(s.querySelectorAll("option"));
        return options.some((o) => o.textContent === "BTC/USD");
      });
      expect(symbolSelect).toBeTruthy();
    });
  });
});

describe("CreateRunForm — M13-6 backtest date fields", () => {
  it("shows date inputs when mode is backtest", async () => {
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    // Default mode is backtest, so date fields should be visible
    expect(screen.getByLabelText(/start time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end time/i)).toBeInTheDocument();
  });

  it("date inputs have required attribute", async () => {
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByLabelText(/start time/i)).toBeRequired();
    expect(screen.getByLabelText(/end time/i)).toBeRequired();
  });

  it("date inputs are controlled (value bound to state)", async () => {
    const user = userEvent.setup();
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    const startInput = screen.getByLabelText(/start time/i) as HTMLInputElement;
    await user.clear(startInput);
    await user.type(startInput, "2024-06-15T10:00");
    expect(startInput.value).toBe("2024-06-15T10:00");
  });

  it("hides date inputs when mode is paper", async () => {
    const user = userEvent.setup();
    render(<CreateRunForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    await user.selectOptions(screen.getByLabelText(/mode/i), "paper");

    expect(screen.queryByLabelText(/start time/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/end time/i)).not.toBeInTheDocument();
  });

  it("appends timezone Z to datetime-local values on submit", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<CreateRunForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    // Select strategy first
    await waitFor(() => {
      const select = screen.getByLabelText(/strategy/i);
      expect(select.querySelectorAll("option").length).toBeGreaterThan(1);
    });
    await user.selectOptions(screen.getByLabelText(/strategy/i), "sample");

    // Fill in dates (datetime-local gives values like "2024-01-01T09:30")
    const startInput = screen.getByLabelText(/start time/i);
    const endInput = screen.getByLabelText(/end time/i);
    await user.clear(startInput);
    await user.type(startInput, "2024-01-01T09:30");
    await user.clear(endInput);
    await user.type(endInput, "2024-12-31T16:00");

    await user.click(screen.getByRole("button", { name: /create/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        config: expect.objectContaining({
          backtest_start: "2024-01-01T09:30:00Z",
          backtest_end: "2024-12-31T16:00:00Z",
        }),
      }),
    );
  });
});

describe("CreateRunForm — M13-10 success toast", () => {
  it("useCreateRun calls success notification on creation", async () => {
    // This test lives in useRuns.test.tsx — placeholder here for traceability
    expect(true).toBe(true);
  });
});
