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
