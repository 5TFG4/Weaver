# M12-B: Frontend Hardening — Detailed Execution Plan

> **Document Charter**
> **Primary role**: Step-by-step TDD execution guide — follow brainlessly, get identical results.
> **Companion**: [m12b-frontend-hardening.md](m12b-frontend-hardening.md) (design framework & decisions)
> **Status**: 📋 READY FOR EXECUTION
> **Branch**: `m12b-frontend-hardening`
> **Test baseline**: 109 frontend unit tests → target ~129

---

## Table of Contents

1. [Pre-Flight Checklist](#1-pre-flight-checklist)
2. [Phase 1: SSE Safety Hardening (H1)](#2-phase-1-sse-safety-hardening-h1)
3. [Phase 2: Symbols Enum Dropdown (H2)](#3-phase-2-symbols-enum-dropdown-h2)
4. [Phase 3: Dead Code Cleanup (H3)](#4-phase-3-dead-code-cleanup-h3)
5. [Phase 4: Modal Accessibility (H4)](#5-phase-4-modal-accessibility-h4)
6. [Phase 5: Table Fixes (H5)](#6-phase-5-table-fixes-h5)
7. [Phase 6: Pagination UI (H6)](#7-phase-6-pagination-ui-h6)
8. [Post-Flight Verification](#8-post-flight-verification)

---

## 1. Pre-Flight Checklist

Before starting any phase, run these commands to ensure a clean baseline:

```bash
# 1. Verify frontend tests pass
cd /weaver/haro && npx vitest run
# Expected: 109 tests pass

# 2. Verify backend tests pass
cd /weaver && python -m pytest tests/unit/ -x -q
# Expected: 987 tests pass

# 3. Verify TypeScript compiles
cd /weaver/haro && npx tsc --noEmit
# Expected: no errors

# 4. Create branch (if not already)
cd /weaver && git checkout -b m12b-frontend-hardening
```

**Convention**: Each phase follows red-green-refactor. Write tests FIRST → see them fail → implement → see them pass → refactor.

---

## 2. Phase 1: SSE Safety Hardening (H1)

**Decision**: D-1 🔒 Option A — `safeParse` utility function
**Files to modify**: `haro/src/hooks/useSSE.ts`
**Test file**: `haro/tests/unit/hooks/useSSE.test.tsx`

### 2.1 Step 1: Write Failing Tests (RED)

Add the following tests to `haro/tests/unit/hooks/useSSE.test.tsx`, inside the existing `describe("useSSE", ...)` block, at the end (before the closing `})`):

```typescript
  // =========================================================================
  // H1: SSE Safety — safeParse protection
  // =========================================================================

  it("does not crash when SSE event has malformed JSON data", () => {
    const wrapper = createWrapper();
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    // Send malformed JSON — should NOT throw
    expect(() => {
      act(() => {
        const es = MockEventSource.latest();
        const event = new MessageEvent("run.Started", {
          data: "NOT VALID JSON{{{",
        });
        const listeners =
          (es as unknown as { listeners: Map<string, EventSourceListener[]> })
            .listeners.get("run.Started") || [];
        listeners.forEach((l) => l(event));
      });
    }).not.toThrow();

    // Should log a warning
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("[SSE]"),
      expect.anything(),
    );

    // Should NOT add a notification (safeParse silently skips)
    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(0);

    consoleSpy.mockRestore();
  });

  it("does not crash when orders.Rejected has malformed JSON", () => {
    const wrapper = createWrapper();
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    expect(() => {
      act(() => {
        const es = MockEventSource.latest();
        const event = new MessageEvent("orders.Rejected", {
          data: "<html>bad gateway</html>",
        });
        const listeners =
          (es as unknown as { listeners: Map<string, EventSourceListener[]> })
            .listeners.get("orders.Rejected") || [];
        listeners.forEach((l) => l(event));
      });
    }).not.toThrow();

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("processes valid JSON normally after safeParse is added", () => {
    const wrapper = createWrapper();
    renderHook(() => useSSE(), { wrapper });

    act(() => {
      MockEventSource.latest().simulateOpen();
    });

    // Valid JSON should still work as before
    act(() => {
      MockEventSource.latest().simulateEvent("run.Completed", {
        run_id: "run-safe-1",
      });
    });

    const { notifications } = useNotificationStore.getState();
    expect(notifications).toHaveLength(1);
    expect(notifications[0].message).toContain("run-safe-1");
  });
```

**Run tests — expect 2 failures** (malformed JSON tests throw):
```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useSSE.test.tsx
```

### 2.2 Step 2: Implement safeParse (GREEN)

Edit `haro/src/hooks/useSSE.ts`. Add `safeParse` function after the constants section and before the hook:

```typescript
// =============================================================================
// Utilities
// =============================================================================

function safeParse(raw: string): Record<string, unknown> | null {
  try {
    return JSON.parse(raw);
  } catch {
    console.warn("[SSE] Failed to parse event data:", raw);
    return null;
  }
}
```

Then replace every `JSON.parse(e.data)` call with `safeParse(e.data)` + early return. There are **7 occurrences** (the `orders.Filled` listener does NOT parse JSON — it has no `e.data` usage, so skip it). The exact changes:

**Listener 1: `run.Started`** (current line ~68):
```typescript
// BEFORE:
eventSource.addEventListener("run.Started", (e: MessageEvent) => {
  const data = JSON.parse(e.data);
  queryClient.invalidateQueries({ queryKey: ["runs"] });
  addNotification({
    type: "success",
    message: `Run ${data.run_id} started`,
  });
});

// AFTER:
eventSource.addEventListener("run.Started", (e: MessageEvent) => {
  const data = safeParse(e.data);
  if (!data) return;
  queryClient.invalidateQueries({ queryKey: ["runs"] });
  addNotification({
    type: "success",
    message: `Run ${data.run_id} started`,
  });
});
```

**Listener 2: `run.Stopped`** (current line ~76):
```typescript
// BEFORE:
const data = JSON.parse(e.data);
// AFTER:
const data = safeParse(e.data);
if (!data) return;
```

**Listener 3: `run.Completed`** (current line ~84):
```typescript
// Same pattern: JSON.parse → safeParse + if (!data) return;
```

**Listener 4: `run.Error`** (current line ~92):
```typescript
// Same pattern
```

**Listener 5: `orders.Created`** (current line ~104):
```typescript
// Same pattern
```

**Listener 6: `orders.Rejected`** (current line ~120):
```typescript
// Same pattern
```

**Listener 7: `orders.Cancelled`** (current line ~128):
```typescript
// Same pattern
```

**Total**: Replace `JSON.parse(e.data)` → `safeParse(e.data)` in 7 places, add `if (!data) return;` after each.

### 2.3 Step 3: Verify (GREEN)

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useSSE.test.tsx
# Expected: all tests pass (existing 11 + 3 new = 14)
```

### 2.4 Step 4: Full Suite Regression Check

```bash
cd /weaver/haro && npx vitest run
# Expected: 112 tests pass (109 + 3)
```

### 2.5 Summary of Changes

| File | Change |
|------|--------|
| `haro/src/hooks/useSSE.ts` | Add `safeParse()`, replace 7 `JSON.parse` calls |
| `haro/tests/unit/hooks/useSSE.test.tsx` | Add 3 tests: malformed run event, malformed order event, valid JSON still works |

**New test count**: +3 → 112 total

---

## 3. Phase 2: Symbols Enum Dropdown (H2)

**Decisions**: D-2 🔒 Option D (enum now, API later), D-2b 🔒 `["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"]`
**Backend files to modify**: `src/marvin/strategies/sample_strategy.py`, `src/marvin/strategies/sma_strategy.py`
**Test files**: Backend: `tests/unit/marvin/` (strategy tests), Frontend: `haro/tests/unit/components/CreateRunForm.test.tsx` (new)

### 3.1 Step 1: Write Failing Backend Test (RED)

Find or create the test file for strategy metadata. Look for existing config_schema tests:

```bash
grep -r "config_schema" tests/unit/marvin/ --include="*.py" -l
```

If no test file exists for the strategy metadata, create one. Add to the appropriate test file (e.g., `tests/unit/marvin/test_strategies.py` or wherever strategy STRATEGY_META is tested):

```python
def test_sample_strategy_config_schema_symbols_has_enum():
    """H2: symbols items must have enum for dropdown rendering."""
    from src.marvin.strategies.sample_strategy import STRATEGY_META

    schema = STRATEGY_META["config_schema"]
    symbols_prop = schema["properties"]["symbols"]
    items = symbols_prop["items"]
    assert "enum" in items, "symbols.items must have enum for RJSF dropdown"
    assert isinstance(items["enum"], list)
    assert len(items["enum"]) >= 3


def test_sma_strategy_config_schema_symbols_has_enum():
    """H2: symbols items must have enum for dropdown rendering."""
    from src.marvin.strategies.sma_strategy import STRATEGY_META

    schema = STRATEGY_META["config_schema"]
    symbols_prop = schema["properties"]["symbols"]
    items = symbols_prop["items"]
    assert "enum" in items, "symbols.items must have enum for RJSF dropdown"
    assert isinstance(items["enum"], list)
    assert len(items["enum"]) >= 3
```

**Run tests — expect failures**:
```bash
cd /weaver && python -m pytest tests/unit/marvin/test_strategies.py -x -q -k "enum"
```

### 3.2 Step 2: Write Failing Frontend Test (RED)

Create `haro/tests/unit/components/CreateRunForm.test.tsx` if it doesn't exist, or add to the existing file. This test verifies that when a strategy has enum in its symbols schema, RJSF renders a `<select>` element:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "../../utils";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { CreateRunForm } from "../../../src/components/runs/CreateRunForm";
import userEvent from "@testing-library/user-event";
import type { StrategyMeta } from "../../../src/api/types";
import { vi } from "vitest";

const strategyWithEnum: StrategyMeta[] = [
  {
    id: "sample",
    name: "Sample Strategy",
    version: "1.0.0",
    description: "Test strategy",
    author: "test",
    config_schema: {
      type: "object",
      properties: {
        symbols: {
          type: "array",
          items: {
            type: "string",
            enum: ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"],
          },
          description: "Trading symbols",
        },
        timeframe: {
          type: "string",
          default: "1m",
          enum: ["1m", "5m", "15m", "1h", "4h", "1d"],
        },
      },
      required: ["symbols"],
    },
  },
];

describe("CreateRunForm — H2 symbols enum", () => {
  it("renders symbols as dropdown select when schema has enum", async () => {
    // Override strategies endpoint with enum-bearing schema
    server.use(
      http.get("/api/v1/strategies", () => {
        return HttpResponse.json(strategyWithEnum);
      }),
    );

    const user = userEvent.setup();
    render(
      <CreateRunForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    // Wait for strategies to load
    await waitFor(() => {
      expect(screen.getByLabelText(/strategy/i)).toBeInTheDocument();
    });

    // Select the strategy to show its config form
    await user.selectOptions(screen.getByLabelText(/strategy/i), "sample");

    // RJSF should render the config form
    // The symbols array has items with enum — RJSF renders <select> for each item
    // Click "Add item" to add a symbols entry
    await waitFor(() => {
      expect(screen.getByTestId("rjsf-add-item")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("rjsf-add-item"));

    // After adding an item, there should be a <select> with the enum options
    await waitFor(() => {
      const selects = screen.getAllByRole("combobox");
      // At least one select should contain the enum options
      const symbolSelect = selects.find((s) => {
        const options = s.querySelectorAll("option");
        return Array.from(options).some((o) => o.textContent === "BTC/USD");
      });
      expect(symbolSelect).toBeTruthy();
    });
  });
});
```

> **Note**: If RJSF renders `<select>` elements with role `combobox` vs `listbox` depends on your SelectWidget. The test queries for selects containing "BTC/USD" option text. Adjust the query if the custom `SelectWidget` uses a different role.

### 3.3 Step 3: Implement Backend Changes (GREEN)

Edit `src/marvin/strategies/sample_strategy.py`, change `config_schema.properties.symbols.items`:

```python
# BEFORE:
"symbols": {
    "type": "array",
    "items": {"type": "string"},
    "description": "Trading symbols",
},

# AFTER:
"symbols": {
    "type": "array",
    "items": {
        "type": "string",
        "enum": ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"],
    },
    "description": "Trading symbols",
},
```

Edit `src/marvin/strategies/sma_strategy.py`, same change:

```python
# BEFORE:
"symbols": {
    "type": "array",
    "items": {"type": "string"},
    "description": "Trading symbols",
},

# AFTER:
"symbols": {
    "type": "array",
    "items": {
        "type": "string",
        "enum": ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"],
    },
    "description": "Trading symbols",
},
```

### 3.4 Step 4: Update MSW Mock Data

The MSW mock `mockStrategies` in `haro/tests/mocks/handlers.ts` must also have `enum` in its config_schema to match the real API response. Update both mock strategy schemas:

```typescript
// In handlers.ts, both mockStrategies entries:
// BEFORE:
symbols: { type: "array", items: { type: "string" } },

// AFTER:
symbols: {
  type: "array",
  items: {
    type: "string",
    enum: ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"],
  },
},
```

### 3.5 Step 5: Verify

```bash
# Backend tests
cd /weaver && python -m pytest tests/unit/marvin/ -x -q -k "enum"
# Expected: 2 new tests pass

# Frontend tests
cd /weaver/haro && npx vitest run tests/unit/components/CreateRunForm.test.tsx
# Expected: 1 new test passes

# Full regression
cd /weaver/haro && npx vitest run
# Expected: 113 tests pass (112 + 1)
```

### 3.6 E2E Impact Check

The mock data change in `handlers.ts` may affect existing tests that expect free-text symbols. Verify:

```bash
cd /weaver/haro && npx vitest run
# If RunsPage create-run tests break, update them to select from the dropdown
# instead of typing free text
```

### 3.7 Summary of Changes

| File | Change |
|------|--------|
| `src/marvin/strategies/sample_strategy.py` | Add `enum` to `symbols.items` |
| `src/marvin/strategies/sma_strategy.py` | Add `enum` to `symbols.items` |
| `haro/tests/mocks/handlers.ts` | Update `mockStrategies` schemas with `enum` |
| `haro/tests/unit/components/CreateRunForm.test.tsx` | New test: enum renders as dropdown |
| `tests/unit/marvin/test_strategies.py` | 2 new tests: enum exists in schema |

**New test count**: +1 frontend + 2 backend → 113 frontend, 989 backend

---

## 4. Phase 3: Dead Code Cleanup (H3)

**Decision**: D-3 🔒 Option C — keep hooks, remove `apiClient` + dead CSS, add `useStrategies` barrel export
**Files to modify**: `haro/src/api/client.ts`, `haro/src/index.css`, `haro/src/hooks/index.ts`
**Test file**: `haro/tests/unit/hooks/useStrategies.test.tsx` (already exists — add barrel import test)

### 4.1 Step 1: Write Failing Test (RED)

Add to existing `haro/tests/unit/hooks/useStrategies.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";

describe("useStrategies barrel export", () => {
  it("can be imported from hooks barrel", async () => {
    // This test verifies that useStrategies is re-exported from hooks/index.ts
    const barrel = await import("../../../src/hooks/index");
    expect(barrel.useStrategies).toBeDefined();
    expect(typeof barrel.useStrategies).toBe("function");
  });
});
```

**Run — expect failure** (useStrategies is not currently in the barrel):
```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useStrategies.test.tsx
```

### 4.2 Step 2: Implement Changes (GREEN)

#### 4.2.1 Add barrel export

Edit `haro/src/hooks/index.ts`:

```typescript
// BEFORE:
export * from "./useRuns";
export * from "./useOrders";
export * from "./useHealth";
export * from "./useSSE";

// AFTER:
export * from "./useRuns";
export * from "./useOrders";
export * from "./useHealth";
export * from "./useSSE";
export * from "./useStrategies";
```

#### 4.2.2 Remove `apiClient` export

Edit `haro/src/api/client.ts`. Delete the `apiClient` object at the end of the file:

```typescript
// DELETE this entire block (lines ~115-120):
/**
 * API client object for convenient imports
 */
export const apiClient = {
  get,
  post,
  delete: del,
};
```

Also stop exporting `ApiClientError` publicly (make it a non-exported class — but first check if anything imports it):

```bash
grep -r "ApiClientError" haro/src/ --include="*.ts" --include="*.tsx"
```

If only `client.ts` itself uses it, keep the class but stop exporting it. If other files import it, keep the export.

> **Caution**: The `ApiClientError` class is used in `handleResponse()` within the same file. It is imported by test files via `api/client`. Check with grep before removing the export. If only internal usage: change `export class` → `class`. If imported elsewhere: keep `export`.

#### 4.2.3 Remove dead CSS variables

Edit `haro/src/index.css`. Remove the entire `:root { ... }` block containing the 10 `--color-*` variables:

```css
/* BEFORE: */
@import "tailwindcss";

:root {
  --color-primary: #3b82f6;
  --color-primary-dark: #2563eb;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-bg: #0f172a;
  --color-bg-secondary: #1e293b;
  --color-text: #f8fafc;
  --color-text-muted: #94a3b8;
  --color-border: #334155;
}

body {
  @apply bg-slate-900 text-slate-100 antialiased;
  font-family: system-ui, -apple-system, sans-serif;
}

#root {
  @apply min-h-screen;
}

/* AFTER: */
@import "tailwindcss";

body {
  @apply bg-slate-900 text-slate-100 antialiased;
  font-family: system-ui, -apple-system, sans-serif;
}

#root {
  @apply min-h-screen;
}
```

Verify no file uses `var(--color-*)`:
```bash
grep -r "var(--color" haro/src/ --include="*.css" --include="*.tsx" --include="*.ts"
# Should return 0 results
```

### 4.3 Step 3: Verify

```bash
cd /weaver/haro && npx vitest run tests/unit/hooks/useStrategies.test.tsx
# Expected: barrel export test passes

cd /weaver/haro && npx vitest run
# Expected: 114 tests pass (113 + 1)

cd /weaver/haro && npx tsc --noEmit
# Expected: no errors
```

### 4.4 Summary of Changes

| File | Change |
|------|--------|
| `haro/src/hooks/index.ts` | Add `export * from "./useStrategies"` |
| `haro/src/api/client.ts` | Remove `apiClient` export object |
| `haro/src/index.css` | Remove `:root` block with 10 `--color-*` variables |
| `haro/tests/unit/hooks/useStrategies.test.tsx` | Add barrel import test |

**New test count**: +1 → 114 total

---

## 5. Phase 4: Modal Accessibility (H4)

**Decision**: D-4 🔒 Option C — `@headlessui/react` Dialog component
**Files to modify**: `haro/package.json` (new dep), `haro/src/components/orders/OrderDetailModal.tsx`
**Test file**: `haro/tests/unit/components/OrderDetailModal.test.tsx` (new)

### 5.1 Step 0: Install Dependency

```bash
cd /weaver/haro && npm install @headlessui/react
```

Verify install:
```bash
node -e "require('@headlessui/react')" 2>&1 || echo "FAIL"
# Should not print FAIL
```

### 5.2 Step 1: Write Failing Tests (RED)

Create `haro/tests/unit/components/OrderDetailModal.test.tsx`:

```typescript
/**
 * OrderDetailModal Tests — H4: Modal Accessibility
 *
 * Tests that the modal has proper ARIA attributes,
 * keyboard interactions (Escape to close), and focus management.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "../../utils";
import { OrderDetailModal } from "../../../src/components/orders/OrderDetailModal";
import userEvent from "@testing-library/user-event";
import type { Order } from "../../../src/api/types";

const mockOrder: Order = {
  id: "order-test-1",
  run_id: "run-1",
  client_order_id: "client-1",
  symbol: "BTC/USD",
  side: "buy",
  order_type: "market",
  qty: "0.5",
  time_in_force: "day",
  filled_qty: "0.5",
  filled_avg_price: "42000.00",
  status: "filled",
  created_at: "2026-01-15T10:00:00Z",
};

describe("OrderDetailModal — a11y", () => {
  it("renders with role='dialog'", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("has aria-modal='true'", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);

    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });
  });

  it("has aria-labelledby pointing to dialog title", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);

    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");

      const labelledBy = dialog.getAttribute("aria-labelledby");
      const title = document.getElementById(labelledBy!);
      expect(title).toBeTruthy();
      expect(title!.textContent).toContain("Order Details");
    });
  });

  it("closes on Escape key press", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<OrderDetailModal order={mockOrder} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("displays order details content", async () => {
    render(<OrderDetailModal order={mockOrder} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    expect(screen.getByText("order-test-1")).toBeInTheDocument();
    expect(screen.getByText("BTC/USD")).toBeInTheDocument();
    expect(screen.getByText("0.5")).toBeInTheDocument();
  });
});
```

**Run — expect failures** (current modal has no `role="dialog"`, no `aria-modal`, no Escape handler):
```bash
cd /weaver/haro && npx vitest run tests/unit/components/OrderDetailModal.test.tsx
```

> **Important**: The `@headlessui/react` Dialog renders via a React portal (appended to `<body>`), so `screen.getByRole("dialog")` should work because it queries the entire document. If tests fail due to portal issues, ensure `jsdom` is used (already configured in vitest).

### 5.3 Step 2: Refactor OrderDetailModal to Use Headless UI (GREEN)

Rewrite `haro/src/components/orders/OrderDetailModal.tsx` using the Headless UI Dialog component:

```typescript
/**
 * OrderDetailModal Component
 *
 * Modal overlay displaying full details of a single order.
 * Uses @headlessui/react Dialog for built-in accessibility:
 *   - role="dialog" + aria-modal="true"
 *   - aria-labelledby via DialogTitle
 *   - Escape key closes
 *   - Click outside DialogPanel closes
 *   - Focus trap
 */

import {
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
} from "@headlessui/react";
import type { Order } from "../../api/types";
import { OrderStatusBadge } from "./OrderStatusBadge";

export interface OrderDetailModalProps {
  order: Order;
  onClose: () => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export function OrderDetailModal({ order, onClose }: OrderDetailModalProps) {
  return (
    <Dialog
      open={true}
      onClose={onClose}
      className="relative z-50"
      data-testid="order-detail-modal"
    >
      <DialogBackdrop className="fixed inset-0 bg-black/60" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="bg-slate-800 rounded-lg border border-slate-700 w-full max-w-lg shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
            <DialogTitle className="text-lg font-semibold text-white">
              Order Details
            </DialogTitle>
            <button
              onClick={onClose}
              aria-label="Close"
              className="text-slate-400 hover:text-white transition-colors"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Order ID" value={order.id} mono />
              <DetailField label="Run ID" value={order.run_id} mono />
              <DetailField label="Symbol" value={order.symbol} />
              <div>
                <span className="text-sm text-slate-400">Side</span>
                <div className="mt-1">
                  <OrderStatusBadge side={order.side} />
                </div>
              </div>
              <DetailField label="Type" value={order.order_type} />
              <DetailField label="Quantity" value={order.qty} />
              {order.price && (
                <DetailField label="Price" value={order.price} />
              )}
              {order.stop_price && (
                <DetailField label="Stop Price" value={order.stop_price} />
              )}
              <DetailField
                label="Time in Force"
                value={order.time_in_force}
              />
              <div>
                <span className="text-sm text-slate-400">Status</span>
                <div className="mt-1">
                  <OrderStatusBadge status={order.status} />
                </div>
              </div>
              <DetailField label="Filled Qty" value={order.filled_qty} />
              {order.filled_avg_price && (
                <DetailField
                  label="Filled Avg Price"
                  value={order.filled_avg_price}
                />
              )}
              <DetailField
                label="Created"
                value={formatDate(order.created_at)}
              />
              {order.submitted_at && (
                <DetailField
                  label="Submitted"
                  value={formatDate(order.submitted_at)}
                />
              )}
              {order.filled_at && (
                <DetailField
                  label="Filled"
                  value={formatDate(order.filled_at)}
                />
              )}
            </div>

            {order.reject_reason && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                <span className="text-sm text-red-400 font-medium">
                  Reject Reason:
                </span>
                <p className="text-sm text-red-300 mt-1">
                  {order.reject_reason}
                </p>
              </div>
            )}

            {order.exchange_order_id && (
              <DetailField
                label="Exchange Order ID"
                value={order.exchange_order_id}
                mono
              />
            )}
            {order.client_order_id && (
              <DetailField
                label="Client Order ID"
                value={order.client_order_id}
                mono
              />
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end px-6 py-4 border-t border-slate-700">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
            >
              Close
            </button>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}

function DetailField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <span className="text-sm text-slate-400">{label}</span>
      <p className={`text-sm text-white mt-1 ${mono ? "font-mono" : ""}`}>
        {value}
      </p>
    </div>
  );
}
```

**Key differences from original**:
- Wraps everything in `<Dialog open={true} onClose={onClose}>` — provides role, aria-modal, Escape handler, focus trap automatically
- Uses `<DialogBackdrop>` for backdrop (clicking it triggers onClose automatically)
- Uses `<DialogPanel>` for the content area (clicking outside closes)
- Uses `<DialogTitle>` instead of plain `<h2>` — automatically sets `aria-labelledby`
- `data-testid="order-detail-modal"` moves to the `<Dialog>` root element

> **Portal behavior**: Headless UI `Dialog` renders via a portal. The `data-testid` on the `<Dialog>` root will still be findable via `screen.getByTestId()` because Testing Library queries the full document.

### 5.4 Step 3: Handle Existing Tests

The existing `OrdersPage.test.tsx` tests that open the modal use `screen.getByTestId("order-detail-modal")`. Since `Dialog` renders via portal, these queries should still work as they search the full DOM. But verify:

```bash
cd /weaver/haro && npx vitest run tests/unit/pages/OrdersPage.test.tsx
```

If the "closes detail modal" test fails because Headless UI Dialog uses portal rendering, the close button may need to be found differently. The existing test clicks `button[name=/close/i]` which should still work since we kept the explicit Close button.

### 5.5 Step 4: Verify

```bash
# New modal tests
cd /weaver/haro && npx vitest run tests/unit/components/OrderDetailModal.test.tsx
# Expected: 5 tests pass

# Regression on OrdersPage (uses modal)
cd /weaver/haro && npx vitest run tests/unit/pages/OrdersPage.test.tsx

# Full suite
cd /weaver/haro && npx vitest run
# Expected: 119 tests (114 + 5)
```

### 5.6 Summary of Changes

| File | Change |
|------|--------|
| `haro/package.json` | Add `@headlessui/react` dependency |
| `haro/src/components/orders/OrderDetailModal.tsx` | Rewrite to use Headless UI Dialog |
| `haro/tests/unit/components/OrderDetailModal.test.tsx` | New: 5 a11y tests |

**New test count**: +5 → 119 total

---

## 6. Phase 5: Table Fixes (H5)

**Decision**: D-5 🔒 Option A — add tabIndex + onKeyDown to `<tr>`
**Files to modify**: `haro/src/components/orders/OrderTable.tsx`, `haro/src/pages/RunsPage.tsx`
**Test file**: `haro/tests/unit/components/OrderTable.test.tsx` (existing — add tests)

### 6.1 Step 1: Write Failing Tests (RED)

Add to `haro/tests/unit/components/OrderTable.test.tsx`:

```typescript
  // =========================================================================
  // H5: Table Accessibility & Overflow
  // =========================================================================

  it("table container has overflow-x-auto for horizontal scrolling", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);

    // The outer container with the table should have overflow-x-auto
    const table = screen.getByRole("table");
    const container = table.closest("div");
    expect(container).toHaveClass("overflow-x-auto");
  });

  it("order rows are keyboard accessible with tabIndex", () => {
    render(<OrderTable orders={mockOrders} onOrderClick={vi.fn()} />);

    const row = screen.getByTestId("order-row-order-1");
    expect(row).toHaveAttribute("tabindex", "0");
    expect(row).toHaveAttribute("role", "button");
  });

  it("pressing Enter on a row triggers onOrderClick", async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<OrderTable orders={mockOrders} onOrderClick={handleClick} />);

    const row = screen.getByTestId("order-row-order-1");
    row.focus();
    await user.keyboard("{Enter}");

    expect(handleClick).toHaveBeenCalledWith(mockOrders[0]);
  });
```

Also add a test for RunsPage table overflow. Add to `haro/tests/unit/pages/RunsPage.test.tsx`:

```typescript
  // =========================================================================
  // H5: Table overflow
  // =========================================================================

  it("runs table container has overflow-x-auto", async () => {
    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    const table = screen.getByRole("table");
    const container = table.closest("div");
    expect(container).toHaveClass("overflow-x-auto");
  });
```

**Run — expect 4 failures**:
```bash
cd /weaver/haro && npx vitest run tests/unit/components/OrderTable.test.tsx tests/unit/pages/RunsPage.test.tsx
```

### 6.2 Step 2: Implement Changes (GREEN)

#### 6.2.1 Fix OrderTable.tsx

Edit `haro/src/components/orders/OrderTable.tsx`:

**Change 1**: Container `overflow-hidden` → `overflow-x-auto`:
```tsx
// BEFORE:
<div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">

// AFTER:
<div className="bg-slate-800 rounded-lg border border-slate-700 overflow-x-auto">
```

**Change 2**: Add keyboard accessibility to `<tr>`:
```tsx
// BEFORE:
<tr
  key={order.id}
  data-testid={`order-row-${order.id}`}
  onClick={() => onOrderClick(order)}
  className="hover:bg-slate-700/30 transition-colors cursor-pointer"
>

// AFTER:
<tr
  key={order.id}
  data-testid={`order-row-${order.id}`}
  onClick={() => onOrderClick(order)}
  onKeyDown={(e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onOrderClick(order);
    }
  }}
  tabIndex={0}
  role="button"
  className="hover:bg-slate-700/30 transition-colors cursor-pointer"
>
```

#### 6.2.2 Fix RunsPage.tsx

Edit `haro/src/pages/RunsPage.tsx`:

**Change**: Container `overflow-hidden` → `overflow-x-auto`:
```tsx
// BEFORE:
<div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">

// AFTER:
<div className="bg-slate-800 rounded-lg border border-slate-700 overflow-x-auto">
```

### 6.3 Step 3: Verify

```bash
cd /weaver/haro && npx vitest run tests/unit/components/OrderTable.test.tsx tests/unit/pages/RunsPage.test.tsx
# Expected: all tests pass

cd /weaver/haro && npx vitest run
# Expected: 123 tests (119 + 4)
```

### 6.4 Summary of Changes

| File | Change |
|------|--------|
| `haro/src/components/orders/OrderTable.tsx` | `overflow-hidden` → `overflow-x-auto`; `<tr>` add `tabIndex`, `role`, `onKeyDown` |
| `haro/src/pages/RunsPage.tsx` | `overflow-hidden` → `overflow-x-auto` |
| `haro/tests/unit/components/OrderTable.test.tsx` | 3 new tests: overflow, tabIndex, keyboard Enter |
| `haro/tests/unit/pages/RunsPage.test.tsx` | 1 new test: overflow |

**New test count**: +4 → 123 total

---

## 7. Phase 6: Pagination UI (H6)

**Decisions**: D-6 🔒 A+C (prev/next + generic Pagination component), D-6b 🔒 No pagination on Dashboard (page_size=5 + "View All →")
**Files to create**: `haro/src/components/common/Pagination.tsx`
**Files to modify**: `haro/src/pages/RunsPage.tsx`, `haro/src/pages/OrdersPage.tsx`, `haro/src/pages/Dashboard.tsx`
**Test files**: `haro/tests/unit/components/Pagination.test.tsx` (new), updates to page tests

### 7.1 Step 1: Write Failing Tests for Pagination Component (RED)

Create `haro/tests/unit/components/Pagination.test.tsx`:

```typescript
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
    render(
      <Pagination page={2} totalPages={5} onPageChange={vi.fn()} />,
    );

    expect(screen.getByText(/2/)).toBeInTheDocument();
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  it("disables Previous button on first page", () => {
    render(
      <Pagination page={1} totalPages={5} onPageChange={vi.fn()} />,
    );

    const prevBtn = screen.getByRole("button", { name: /previous/i });
    expect(prevBtn).toBeDisabled();
  });

  it("disables Next button on last page", () => {
    render(
      <Pagination page={5} totalPages={5} onPageChange={vi.fn()} />,
    );

    const nextBtn = screen.getByRole("button", { name: /next/i });
    expect(nextBtn).toBeDisabled();
  });

  it("calls onPageChange with page-1 when Previous is clicked", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();

    render(
      <Pagination page={3} totalPages={5} onPageChange={onPageChange} />,
    );

    await user.click(screen.getByRole("button", { name: /previous/i }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange with page+1 when Next is clicked", async () => {
    const onPageChange = vi.fn();
    const user = userEvent.setup();

    render(
      <Pagination page={3} totalPages={5} onPageChange={onPageChange} />,
    );

    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(onPageChange).toHaveBeenCalledWith(4);
  });

  it("does not render when totalPages <= 1", () => {
    const { container } = render(
      <Pagination page={1} totalPages={1} onPageChange={vi.fn()} />,
    );

    // Should not render any pagination UI
    expect(container.innerHTML).toBe("");
  });
});
```

**Run — expect failures** (component doesn't exist yet):
```bash
cd /weaver/haro && npx vitest run tests/unit/components/Pagination.test.tsx
```

### 7.2 Step 2: Implement Pagination Component (GREEN)

Create `haro/src/components/common/Pagination.tsx`:

```typescript
/**
 * Pagination Component
 *
 * Generic prev/next pagination with page indicator.
 * Does not render when there's only 1 page.
 */

export interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-sm rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        ← Previous
      </button>
      <span className="text-sm text-slate-400">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        Next →
      </button>
    </div>
  );
}
```

**Verify component tests pass**:
```bash
cd /weaver/haro && npx vitest run tests/unit/components/Pagination.test.tsx
# Expected: 6 tests pass
```

### 7.3 Step 3: Write Failing Page Integration Tests (RED)

#### 7.3.1 RunsPage pagination test

Add to `haro/tests/unit/pages/RunsPage.test.tsx`:

```typescript
  // =========================================================================
  // H6: Pagination
  // =========================================================================

  it("shows pagination when total items exceed page size", async () => {
    // Override MSW handler to return total > page_size
    server.use(
      http.get("/api/v1/runs", ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get("page") || "1");
        const response: RunListResponse = {
          items: mockRuns,
          total: 100, // More items than page_size
          page,
          page_size: 20,
        };
        return HttpResponse.json(response);
      }),
    );

    render(<RunsPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("runs-loading")).not.toBeInTheDocument();
    });

    // Pagination should be visible
    expect(
      screen.getByRole("button", { name: /next/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /previous/i }),
    ).toBeInTheDocument();
  });
```

#### 7.3.2 OrdersPage pagination test

Add to `haro/tests/unit/pages/OrdersPage.test.tsx`:

```typescript
  // =========================================================================
  // H6: Pagination
  // =========================================================================

  it("shows pagination when total items exceed page size", async () => {
    server.use(
      http.get("/api/v1/orders", ({ request }) => {
        const url = new URL(request.url);
        const page = parseInt(url.searchParams.get("page") || "1");
        const response: OrderListResponse = {
          items: mockOrders,
          total: 100,
          page,
          page_size: 20,
        };
        return HttpResponse.json(response);
      }),
    );

    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.queryByTestId("orders-loading")).not.toBeInTheDocument();
    });

    expect(
      screen.getByRole("button", { name: /next/i }),
    ).toBeInTheDocument();
  });
```

#### 7.3.3 Dashboard page_size=5 test

This test is partially covered by the existing "navigates to runs page on View All click" test. The existing Dashboard test already checks for the "View All →" link. We just need to verify the query uses the right page_size. Since Dashboard currently fetches `page_size: 50` and we need to change it to `page_size: 5`, this is a code change. The existing test should still pass since it doesn't assert on page_size.

**Run — expect 2 new test failures** (pagination buttons don't exist on pages yet):
```bash
cd /weaver/haro && npx vitest run tests/unit/pages/
```

### 7.4 Step 4: Implement Page Changes (GREEN)

#### 7.4.1 RunsPage.tsx — Add pagination

Edit `haro/src/pages/RunsPage.tsx`:

**Change 1**: Add imports and page state:
```typescript
// Add import at top:
import { Pagination } from "../components/common/Pagination";

// Add state inside RunsPage function, below existing useState:
const [page, setPage] = useState(1);
const PAGE_SIZE = 20;
```

**Change 2**: Use page state in useRuns call:
```typescript
// BEFORE:
const runsQuery = useRuns(
  { page: 1, page_size: 50 },
  { enabled: !isDeepLink },
);

// AFTER:
const runsQuery = useRuns(
  { page, page_size: PAGE_SIZE },
  { enabled: !isDeepLink },
);
```

**Change 3**: Calculate totalPages and add Pagination component after the runs table (before Quick Links):
```typescript
// After the closing tag of the runs table div, before {/* Quick Links */}:
const totalPages = runsQuery.data
  ? Math.ceil(runsQuery.data.total / PAGE_SIZE)
  : 0;

// In the JSX, after the table </div> and before {/* Quick Links */}:
{!isDeepLink && totalPages > 1 && (
  <Pagination
    page={page}
    totalPages={totalPages}
    onPageChange={setPage}
  />
)}
```

The exact placement: insert the `totalPages` calculation inside the component body (after the `runs` variable) and the JSX element after the table block.

#### 7.4.2 OrdersPage.tsx — Add pagination

Edit `haro/src/pages/OrdersPage.tsx`:

**Change 1**: Add import and state:
```typescript
// Add import:
import { Pagination } from "../components/common/Pagination";

// Add state:
const [page, setPage] = useState(1);
const PAGE_SIZE = 20;
```

**Change 2**: Use page state:
```typescript
// BEFORE:
const ordersQuery = useOrders({
  page: 1,
  page_size: 50,
  run_id: runIdFilter || undefined,
  status: statusFilter || undefined,
});

// AFTER:
const ordersQuery = useOrders({
  page,
  page_size: PAGE_SIZE,
  run_id: runIdFilter || undefined,
  status: statusFilter || undefined,
});
```

**Change 3**: Reset page on filter change:
```typescript
// In the status filter onChange handler:
// BEFORE:
onChange={(e) => setStatusFilter(e.target.value)}

// AFTER:
onChange={(e) => {
  setStatusFilter(e.target.value);
  setPage(1);
}}
```

**Change 4**: Add Pagination after OrderTable:
```typescript
// Calculate totalPages in the component body:
const totalPages = ordersQuery.data
  ? Math.ceil(ordersQuery.data.total / PAGE_SIZE)
  : 0;

// In JSX, after <OrderTable>:
{totalPages > 1 && (
  <Pagination
    page={page}
    totalPages={totalPages}
    onPageChange={setPage}
  />
)}
```

#### 7.4.3 Dashboard.tsx — Change page_size to 5

Edit `haro/src/pages/Dashboard.tsx`:

```typescript
// BEFORE:
const runsQuery = useRuns({ page: 1, page_size: 50 });

// AFTER:
const runsQuery = useRuns({ page: 1, page_size: 5 });
```

The "View All →" link already exists pointing to `/runs`, so D-6b is already satisfied.

### 7.5 Step 5: Verify

```bash
# Pagination component tests
cd /weaver/haro && npx vitest run tests/unit/components/Pagination.test.tsx
# Expected: 6 pass

# Page tests
cd /weaver/haro && npx vitest run tests/unit/pages/
# Expected: all existing + 2 new pass

# Full suite
cd /weaver/haro && npx vitest run
# Expected: ~131 tests (123 + 6 + 2)
```

### 7.6 Summary of Changes

| File | Change |
|------|--------|
| `haro/src/components/common/Pagination.tsx` | New generic pagination component |
| `haro/src/pages/RunsPage.tsx` | Add page state, use PAGE_SIZE=20, add Pagination |
| `haro/src/pages/OrdersPage.tsx` | Add page state, use PAGE_SIZE=20, add Pagination, reset page on filter |
| `haro/src/pages/Dashboard.tsx` | Change page_size from 50 to 5 |
| `haro/tests/unit/components/Pagination.test.tsx` | New: 6 Pagination tests |
| `haro/tests/unit/pages/RunsPage.test.tsx` | 1 new pagination test |
| `haro/tests/unit/pages/OrdersPage.test.tsx` | 1 new pagination test |

**New test count**: +8 → ~131 total

---

## 8. Post-Flight Verification

After all 6 phases are complete, run the full verification suite:

```bash
# 1. TypeScript compilation
cd /weaver/haro && npx tsc --noEmit
# Expected: 0 errors

# 2. Frontend lint
cd /weaver/haro && npx eslint .
# Expected: 0 errors

# 3. Frontend tests
cd /weaver/haro && npx vitest run
# Expected: ~131 tests pass (109 baseline + ~22 new)

# 4. Backend tests
cd /weaver && python -m pytest tests/unit/ -x -q
# Expected: ~989 tests pass

# 5. Integration tests
cd /weaver && python -m pytest tests/integration/ -x -q
# Expected: 50 tests pass

# 6. E2E tests (if stack is running)
cd /weaver && python -m pytest tests/e2e/ -m e2e -x -q
# Expected: 33 tests pass
```

### 8.1 Exit Gate Checklist

| #  | Criterion | Verification Command | Expected |
|----|-----------|---------------------|----------|
| 1  | SSE JSON.parse protected | `grep -c "safeParse" haro/src/hooks/useSSE.ts` | ≥ 7 |
| 2  | Symbols dropdown | `grep "enum" src/marvin/strategies/sample_strategy.py` | Found |
| 3  | apiClient removed | `grep "apiClient" haro/src/api/client.ts` | 0 results |
| 4  | useStrategies in barrel | `grep "useStrategies" haro/src/hooks/index.ts` | Found |
| 5  | Modal uses Headless UI | `grep "Dialog" haro/src/components/orders/OrderDetailModal.tsx` | Found |
| 6  | Tables overflow-x-auto | `grep "overflow-x-auto" haro/src/components/orders/OrderTable.tsx` | Found |
| 7  | Table rows keyboard | `grep "tabIndex" haro/src/components/orders/OrderTable.tsx` | Found |
| 8  | Pagination on pages | `grep "Pagination" haro/src/pages/RunsPage.tsx haro/src/pages/OrdersPage.tsx` | 2 results |
| 9  | No regressions | Full test suite passes | ✅ |
| 10 | ~20 new tests | `npx vitest run` count | ~131 (was 109) |

### 8.2 Test Impact Summary

| Phase | New Frontend Tests | New Backend Tests |
|-------|-------------------|-------------------|
| H1: SSE safety | 3 | 0 |
| H2: Symbols enum | 1 | 2 |
| H3: Dead code | 1 | 0 |
| H4: Modal a11y | 5 | 0 |
| H5: Table fixes | 4 | 0 |
| H6: Pagination | 8 | 0 |
| **Total** | **22** | **2** |

Final frontend tests: 109 → ~131
Final backend tests: 987 → ~989

### 8.3 New & Modified Files Summary

| File | Action |
|------|--------|
| `haro/src/hooks/useSSE.ts` | Modified (safeParse) |
| `haro/src/api/client.ts` | Modified (remove apiClient) |
| `haro/src/index.css` | Modified (remove dead CSS vars) |
| `haro/src/hooks/index.ts` | Modified (add useStrategies export) |
| `haro/src/components/orders/OrderDetailModal.tsx` | Rewritten (Headless UI Dialog) |
| `haro/src/components/orders/OrderTable.tsx` | Modified (overflow + keyboard a11y) |
| `haro/src/components/common/Pagination.tsx` | **New** |
| `haro/src/pages/RunsPage.tsx` | Modified (overflow + pagination) |
| `haro/src/pages/OrdersPage.tsx` | Modified (pagination) |
| `haro/src/pages/Dashboard.tsx` | Modified (page_size 50→5) |
| `haro/package.json` | Modified (add @headlessui/react) |
| `haro/tests/mocks/handlers.ts` | Modified (enum in mock schemas) |
| `src/marvin/strategies/sample_strategy.py` | Modified (enum in config_schema) |
| `src/marvin/strategies/sma_strategy.py` | Modified (enum in config_schema) |
| `haro/tests/unit/hooks/useSSE.test.tsx` | Modified (+3 tests) |
| `haro/tests/unit/hooks/useStrategies.test.tsx` | Modified (+1 test) |
| `haro/tests/unit/components/CreateRunForm.test.tsx` | **New** (+1 test) |
| `haro/tests/unit/components/OrderDetailModal.test.tsx` | **New** (+5 tests) |
| `haro/tests/unit/components/OrderTable.test.tsx` | Modified (+3 tests) |
| `haro/tests/unit/components/Pagination.test.tsx` | **New** (+6 tests) |
| `haro/tests/unit/pages/RunsPage.test.tsx` | Modified (+2 tests) |
| `haro/tests/unit/pages/OrdersPage.test.tsx` | Modified (+1 test) |
| Backend strategy test file | Modified (+2 tests) |

---

_Document created: 2026-04-03. Companion to [m12b-frontend-hardening.md](m12b-frontend-hardening.md)._
_Execute phases in order H1→H6. Each phase is independent — commit after each._
