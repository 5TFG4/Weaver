# M12-B: Frontend Hardening — Design Framework & Decision Points

> **Document Charter**
> **Primary role**: M12-B milestone design framework — options analysis for decision-making.
> **Status**: 🔒 DECISIONS LOCKED — All 9 decision points confirmed. Ready for detailed planning.
> **Prerequisite**: M12 ✅ (Spec Alignment)
> **Key Input**: Frontend audit report (2026-04-03)
> **Branch**: `m12b-frontend-hardening`

---

## Table of Contents

1. [Background & Scope](#1-background--scope)
2. [Current Test Baseline](#2-current-test-baseline)
3. [Issue List & Severity](#3-issue-list--severity)
4. [Dependency Graph](#4-dependency-graph)
5. [Phase 1: SSE Safety Hardening (H1)](#5-phase-1-sse-safety-hardening-h1)
6. [Phase 2: Symbols Input UX (H2)](#6-phase-2-symbols-input-ux-h2)
7. [Phase 3: Dead Code Cleanup (H3)](#7-phase-3-dead-code-cleanup-h3)
8. [Phase 4: Modal Accessibility (H4)](#8-phase-4-modal-accessibility-h4)
9. [Phase 5: Table Fixes (H5)](#9-phase-5-table-fixes-h5)
10. [Phase 6: Pagination UI (H6)](#10-phase-6-pagination-ui-h6)
11. [Phase 7: Responsive Sidebar (H7)](#11-phase-7-responsive-sidebar-h7)
12. [TDD Execution Strategy](#12-tdd-execution-strategy)
13. [Risk Assessment](#13-risk-assessment)
14. [Exit Gate](#14-exit-gate)
15. [Decision Points Summary](#15-decision-points-summary)

---

## 1. Background & Scope

### 1.1 Why M12-B Is Needed

M12 (Spec Alignment) completed the full-stack alignment from backend to frontend. During that process, the frontend underwent extensive rewrites (CreateRunForm with RJSF dynamic forms, strategy dropdown, etc.). A comprehensive audit afterwards revealed **7 categories totaling 26 issues**, spanning runtime safety, user experience, accessibility, and code hygiene.

### 1.2 Why Split From M12

- M12 document is already 2538 lines, exceeding single-context window capacity
- M12 focused on **spec alignment** (backend architecture → frontend adaptation), while M12-B focuses on **frontend quality hardening**
- The two have completely different concerns, affected files, and test coverage directions
- Independent documents enable independent progress tracking without interference

### 1.3 M12 vs M12-B vs M13 Boundaries

| Milestone | Core Objective                                                          | Status          |
| --------- | ----------------------------------------------------------------------- | --------------- |
| **M12**   | Backend spec alignment: Run config refactor, strategy interface, API    | ✅ Complete     |
| **M12-B** | Frontend quality hardening: SSE safety, UX, a11y, code cleanup         | 🔵 This doc    |
| **M13**   | Multi-exchange (VedaService dict), Bar exchange field, on-demand fetch  | Deferred        |

### 1.4 Items Excluded From M12-B

| Item                                  | Reason                                                                             |
| ------------------------------------- | ---------------------------------------------------------------------------------- |
| E-3: Pagination/filtering E2E tests   | Pagination UI will generate new E2E test needs, but E2E tests belong to M13+ scope |
| R-1: Connection resilience            | Backend infrastructure, unrelated to frontend                                      |
| R-2: Multi-symbol backtests           | Backend logic, unrelated to frontend                                               |
| Full Combobox async search (symbols)  | Requires backend `/symbols` endpoint + 3rd-party lib, high effort, listed as alternative but not default |

---

## 2. Current Test Baseline

| Category           | Count    | Notes                     |
| ------------------ | -------- | ------------------------- |
| Backend unit       | 987      | pytest tests/unit/        |
| Backend integration| 50       | pytest tests/integration/ |
| E2E (Playwright)   | 33       | pytest tests/e2e/ -m e2e  |
| Frontend unit (Vitest) | 109  | npx vitest run            |
| **Total**          | **1179** |                           |

---

## 3. Issue List & Severity

The audit found 7 categories of issues, sorted by severity:

| ID     | Issue                                                                    | Severity    | Impact Area        | Affected Files                   |
| ------ | ------------------------------------------------------------------------ | ----------- | ------------------ | -------------------------------- |
| **H1** | SSE `JSON.parse` has no try/catch, 7 occurrences                        | 🔴 High    | Runtime crash      | `hooks/useSSE.ts`                |
| **H2** | Symbols free-text input is error-prone, no dropdown/autocomplete        | 🔴 High    | User experience    | Strategy `config_schema` + RJSF  |
| **H3** | Dead code: 3 unused hooks, 1 unused export, 10 dead CSS vars, missing barrel export | 🟡 Medium | Code hygiene | Multiple files              |
| **H4** | Modal missing 6 accessibility features                                  | 🟡 Medium  | Accessibility      | `OrderDetailModal.tsx`           |
| **H5** | Table `overflow-hidden` clipping + rows not keyboard accessible         | 🟡 Medium  | Small screens + a11y | `OrderTable.tsx`, `RunsPage.tsx` |
| **H6** | No pagination UI, hardcoded page_size=50                                | 🟡 Medium  | Data visibility    | 3 page components                |
| **H7** | Sidebar fixed w-64, no responsive collapse                             | 🟢 Low     | Mobile layout      | `Sidebar.tsx`, `Layout.tsx`      |

---

## 4. Dependency Graph

```
H1 (SSE safety) ──── independent, no dependencies
H2 (Symbols dropdown) ──── independent, no dependencies
H3 (Dead code cleanup) ──── independent, no dependencies
H4 (Modal a11y) ──── independent, no dependencies
H5 (Table fixes) ──── independent, no dependencies
H6 (Pagination UI) ──── independent, no dependencies
H7 (Responsive sidebar) ──── independent, no dependencies
```

> All 7 phases are independent. They can be executed in any order or in parallel.
> Recommended execution order: highest severity first (H1 → H7).

---

## 5. Phase 1: SSE Safety Hardening (H1)

### 5.1 Current State

`hooks/useSSE.ts` has 7 `JSON.parse(e.data)` calls distributed across the following event listeners:

| Event Name         | Line | JSON.parse | try/catch |
| ------------------ | ---- | ---------- | --------- |
| `run.Started`      | ~68  | ✅         | ❌        |
| `run.Stopped`      | ~76  | ✅         | ❌        |
| `run.Completed`    | ~84  | ✅         | ❌        |
| `run.Error`        | ~92  | ✅         | ❌        |
| `orders.Created`   | ~104 | ✅         | ❌        |
| `orders.Rejected`  | ~120 | ✅         | ❌        |
| `orders.Cancelled` | ~128 | ✅         | ❌        |

**Risk**: When the server sends a malformed SSE message, `JSON.parse` throws an uncaught exception. EventSource's `onerror` only handles connection-level errors, not JS exceptions within event listeners. The consequence is SSE silently stops working, the page no longer updates in real-time, and the user gets no indication.

### 5.2 Decision Point D-1: JSON Parse Safety Strategy

**Option A: Extract `safeParse` utility function (recommended ✅)**

```typescript
function safeParse(raw: string): Record<string, unknown> | null {
  try {
    return JSON.parse(raw);
  } catch {
    console.warn("[SSE] Failed to parse event data:", raw);
    return null;
  }
}

// Each listener:
eventSource.addEventListener("run.Started", (e: MessageEvent) => {
  const data = safeParse(e.data);
  if (!data) return;
  // ... original logic
});
```

| Pros                                             | Cons |
| ------------------------------------------------ | ---- |
| Minimal code (function extraction + 2-line change per call) | None |
| Graceful degradation on parse failure (skip event, no crash) |  |
| console.warn aids debugging                      |      |

**Option B: Independent try/catch at each site**

```typescript
eventSource.addEventListener("run.Started", (e: MessageEvent) => {
  try {
    const data = JSON.parse(e.data);
    // ... original logic
  } catch (err) {
    console.warn("[SSE] Failed to parse run.Started:", err);
  }
});
```

| Pros                                | Cons                                        |
| ----------------------------------- | ------------------------------------------- |
| Each event can have custom error handling | Repetitive code (7 try/catch blocks)   |
|                                     | All catch blocks are identical, no differentiation |

**Option C: Notify user on parse failure**

Same as Option A, but `safeParse` also calls `addNotification({ type: "warning", message: "Received malformed SSE message" })` when returning null.

| Pros                      | Cons                                                      |
| ------------------------- | --------------------------------------------------------- |
| User can see something is wrong | May cause notification fatigue (if backend sends bad data continuously) |
|                           | Most users don't care about this technical detail         |

**Recommendation**: Option A. Parse failures are fundamentally backend bugs — console.warn is sufficient for developer debugging and shouldn't bother the user.

> **🔒 Decision D-1: Option A (safeParse utility function)**

### 5.3 Estimated Changes

| File              | Change                                    |
| ----------------- | ----------------------------------------- |
| `hooks/useSSE.ts` | Add `safeParse` function, replace 7 calls |

### 5.4 TDD Test Plan

| Test                                             | Description                       | Type |
| ------------------------------------------------ | --------------------------------- | ---- |
| `safeParse returns parsed object for valid JSON` | Valid JSON input → returns object | unit |
| `safeParse returns null for malformed JSON`      | Input `"not json"` → returns null | unit |
| `SSE listeners skip event on parse failure`      | Simulate bad data → no crash, no notification | unit |

**Estimated new tests**: ~3

---

## 6. Phase 2: Symbols Input UX (H2)

### 6.1 Current State

The strategy `config_schema` defines symbols as a free-text array:

```json
{
  "symbols": {
    "type": "array",
    "items": { "type": "string" },
    "description": "Trading symbols"
  }
}
```

RJSF renders this as a text input where users must manually type `BTC/USD`, etc. Prone to typos (e.g., `BTC/USDT`, `btc/usd`, `BTCUSD`), and the system performs no validation before submission.

### 6.2 Decision Point D-2: Symbols Input Method

**Option A: Add enum to config_schema (recommended ✅)**

In each strategy's `STRATEGY_META.config_schema`, change `items` from `{"type": "string"}` to `{"type": "string", "enum": ["BTC/USD", "ETH/USD", ...]}`. RJSF will automatically render as a dropdown select.

```python
# sma_strategy.py
"symbols": {
    "type": "array",
    "items": {"type": "string", "enum": ["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"]},
    "description": "Trading symbols",
},
```

| Pros                           | Cons                                               |
| ------------------------------ | -------------------------------------------------- |
| Zero frontend code changes     | Symbol list hardcoded, adding new symbols requires code change and redeploy |
| RJSF auto-renders as `<select>`| Different strategies may need different symbol sets (but each can define its own enum) |
| Backend JSON Schema can also validate |                                              |
| 5-minute implementation        |                                                    |

**Option B: Backend `/symbols` endpoint + custom RJSF widget**

1. Backend adds `GET /api/v1/symbols` endpoint returning exchange-supported symbols
2. Frontend creates custom `SymbolsWidget` replacing the default RJSF text input
3. Widget calls `/symbols` API internally, renders as searchable dropdown

```python
# Backend
@router.get("/symbols")
async def list_symbols(exchange: str = "alpaca"):
    return await veda_service.get_available_symbols(exchange)
```

```typescript
// Frontend SymbolsWidget
function SymbolsWidget(props) {
  const { data: symbols } = useQuery({ queryKey: ["symbols"], queryFn: fetchSymbols });
  return <select ...>{symbols.map(s => <option>{s}</option>)}</select>;
}
```

| Pros                                   | Cons                                           |
| -------------------------------------- | ---------------------------------------------- |
| Dynamic symbol list, always up-to-date | Requires new backend endpoint + frontend component + hook |
| Different exchanges return different symbols | Alpaca API call may need authentication  |
| Extensible to search/filter            | Effort: ~half day                              |

**Option C: Frontend Combobox (react-select / downshift)**

Similar to Option B, but uses a professional Combobox component (type-ahead search, multi-select, tag-style display).

```typescript
// Requires installing react-select or downshift
import Select from "react-select";

function SymbolsWidget(props) {
  const { data: symbols } = useQuery(...);
  return <Select isMulti options={symbols.map(s => ({value: s, label: s}))} ... />;
}
```

| Pros                                    | Cons                                    |
| --------------------------------------- | --------------------------------------- |
| Best UX (search + multi-select + tags)  | New dependency (react-select 18KB gzip) |
| Handles thousands of symbols smoothly   | Styling needs Tailwind dark theme adaptation |
|                                         | Effort: ~1-2 days                       |
|                                         | RJSF integration needs custom widget wrapper |

**Option D: Option A first + Option B later (incremental ✅✅)**

Use Option A (5 minutes) for immediate error prevention, implement Option B's dynamic symbol list in M13.

| Pros                                          | Cons                       |
| --------------------------------------------- | -------------------------- |
| Immediate effect (dropdown on next deploy)    | Symbol list is static short-term |
| Seamless upgrade path to Option B later       |                            |
| Lowest risk                                   |                            |

**Recommendation**: Option D (A first, B later) — only do A in this milestone. If you want to go all-in with B directly, that works too.

> **🔒 Decision D-2: Option D (enum dropdown first, dynamic API in M13)**

### 6.3 Symbol List Source (for Option A)

**Decision D-2b: Symbol list contents**

| Option              | Symbol List                                                                                                          |
| ------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Minimal set (recommended) | `["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"]` — covers crypto + stocks for basic testing                   |
| Alpaca crypto full  | `["BTC/USD", "ETH/USD", "LTC/USD", "BCH/USD", "UNI/USD", "AAVE/USD", "SUSHI/USD", "DOT/USD", "LINK/USD", "SOL/USD"]` |
| Custom              | You provide the desired list                                                                                         |

> **🔒 Decision D-2b: Minimal set `["BTC/USD", "ETH/USD", "SPY", "AAPL", "MSFT"]`**

### 6.4 Estimated Changes

**Option A**:

| File                                       | Change               |
| ------------------------------------------ | --------------------- |
| `src/marvin/strategies/sample_strategy.py` | Add `enum` to `items` |
| `src/marvin/strategies/sma_strategy.py`    | Add `enum` to `items` |

**Option B** (if selected):

| File                                         | Change                     |
| -------------------------------------------- | -------------------------- |
| `src/glados/routes/`                         | New `symbols.py` route     |
| `src/veda/`                                  | New `get_symbols()` method |
| `haro/src/api/symbols.ts`                    | New API function           |
| `haro/src/hooks/useSymbols.ts`               | New hook                   |
| `haro/src/components/runs/SymbolsWidget.tsx` | New custom RJSF widget     |
| `haro/src/components/runs/CreateRunForm.tsx` | Register custom widget     |

### 6.5 TDD Test Plan

**Option A**:

| Test                                | Description                              | Type          |
| ----------------------------------- | ---------------------------------------- | ------------- |
| `config_schema symbols has enum`    | Verify schema symbols.items has enum     | backend unit  |
| `RJSF renders dropdown for symbols` | Mock strategy schema with enum → renders select | frontend unit |

**Estimated new tests**: ~2 (Option A) / ~8 (Option B)

---

## 7. Phase 3: Dead Code Cleanup (H3)

### 7.1 Current State

The audit found the following dead code:

| Type           | File                 | Details                                                                  | Action             |
| -------------- | -------------------- | ------------------------------------------------------------------------ | ------------------ |
| Unused hook    | `hooks/useRuns.ts`   | `useStartRun()` — defined but no component calls it                     | Keep or remove?    |
| Unused hook    | `hooks/useOrders.ts` | `useOrder()` — single order query, no component uses it                 | Keep or remove?    |
| Unused hook    | `hooks/useOrders.ts` | `useCancelOrder()` — cancel order, no component uses it                 | Keep or remove?    |
| Unused export  | `api/client.ts`      | `apiClient` object — wraps get/post/del, but all consumers use named exports directly | Remove     |
| Unused export  | `api/client.ts`      | `ApiClientError` — only used internally in client.ts, no external imports | Stop exporting    |
| Dead CSS       | `index.css`          | 10 `--color-*` custom properties — all styling uses Tailwind classes, nobody uses `var()` | Remove   |
| Missing export | `hooks/index.ts`     | `useStrategies` not re-exported from barrel file                        | Add                |
| Unused type    | `api/types.ts`       | `OrderCreate` — exported but no consumers                               | Keep (may be used later) |

### 7.2 Decision Point D-3: Unused Hook Handling Strategy

These three hooks (`useStartRun`, `useOrder`, `useCancelOrder`) are currently unused, but they represent real features (start a run, view single order, cancel order). Future UI enhancements will very likely use them.

**Option A: Keep all, only clean up comments and exports (recommended ✅)**

Keep hook code, annotate in barrel with `// Available for future use`. Only remove confirmed-dead exports (`apiClient`) and dead CSS.

| Pros                                    | Cons                          |
| --------------------------------------- | ----------------------------- |
| Doesn't delete potentially useful code  | A few extra exports in barrel |
| Ready to use when adding pagination/order details later | Code looks "unused" |

**Option B: Delete all**

Remove three unused hooks. Rewrite if needed later.

| Pros         | Cons                                                  |
| ------------ | ----------------------------------------------------- |
| Cleanest code | Must rewrite later                                   |
| YAGNI principle | These hooks are simple but have been verified correct |

**Option C: Handle each by likelihood of use (recommended alternative)**

- `useStartRun`: Keep — RunsPage may soon need a Start button
- `useOrder`: Keep — order detail modal may need to refresh a single order
- `useCancelOrder`: Keep — orders page may need a cancel button
- `apiClient`: Remove — confirmed unused
- Dead CSS: Remove — confirmed unused
- Barrel add `useStrategies`: Add

**Recommendation**: Option C (fine-grained: keep hooks, remove junk).

> **🔒 Decision D-3: Option C (keep hooks, remove apiClient + dead CSS, add useStrategies to barrel)**

### 7.3 Estimated Changes

| File             | Change                                 |
| ---------------- | -------------------------------------- |
| `api/client.ts`  | Remove `apiClient` export object       |
| `index.css`      | Remove 10 `--color-*` variables        |
| `hooks/index.ts` | Add `export * from "./useStrategies"`  |

### 7.4 TDD Test Plan

| Test                                    | Description                        | Type          |
| --------------------------------------- | ---------------------------------- | ------------- |
| `useStrategies is exported from barrel` | Import from `hooks/index` succeeds | frontend unit |

**Estimated new tests**: ~1

---

## 8. Phase 4: Modal Accessibility (H4)

### 8.1 Current State

`OrderDetailModal.tsx` is missing the following standard features:

| Feature               | Status     | WCAG Standard |
| --------------------- | ---------- | ------------- |
| `role="dialog"`       | ❌ Missing | WCAG 4.1.2    |
| `aria-modal="true"`   | ❌ Missing | WCAG 4.1.2    |
| `aria-labelledby`     | ❌ Missing | WCAG 4.1.2    |
| Escape key to close   | ❌ Missing | WCAG 2.1.1    |
| Backdrop click close  | ❌ Missing | Standard UX   |
| Focus trap            | ❌ Missing | WCAG 2.4.3    |

### 8.2 Decision Point D-4: Modal Refactor Approach

**Option A: Manually implement all features (recommended ✅)**

Add directly to `OrderDetailModal.tsx`:

- `role="dialog"` + `aria-modal="true"` + `aria-labelledby`
- `useEffect` to listen for Escape key
- Backdrop `onClick` calls `onClose`
- Simple focus trap: focus modal on open, restore on close

```typescript
// Escape key
useEffect(() => {
  const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
  document.addEventListener("keydown", handler);
  return () => document.removeEventListener("keydown", handler);
}, [onClose]);

// Backdrop click
<div onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div onClick={(e) => e.stopPropagation()}>
    <h2 id="modal-title">Order Details</h2>
    ...
  </div>
</div>
```

| Pros              | Cons                                                     |
| ----------------- | -------------------------------------------------------- |
| Zero dependencies | Will repeat if more modals are added later               |
| Small code (~15 lines) | Focus trap is not 100% robust (but sufficient for a single modal) |
| Full control      |                                                          |

**Option B: Extract generic Modal component**

Create `components/common/Modal.tsx` generic component encapsulating all a11y features. `OrderDetailModal` refactored to use it.

```typescript
// Modal.tsx
function Modal({ isOpen, onClose, title, children }) {
  // Built-in Escape, backdrop click, focus trap, aria
}

// OrderDetailModal.tsx
function OrderDetailModal({ order, onClose }) {
  return (
    <Modal isOpen={!!order} onClose={onClose} title="Order Details">
      <OrderDetails order={order} />
    </Modal>
  );
}
```

| Pros                                    | Cons                                      |
| --------------------------------------- | ----------------------------------------- |
| Reusable (other dialogs can use it too) | Only 1 modal currently, may be over-engineering |
| Write once, benefit everywhere          | Slightly more code                        |

**Option C: Use Headless UI library (@headlessui/react)**

Install `@headlessui/react` (official Tailwind companion), use its `Dialog` component.

```typescript
import { Dialog } from "@headlessui/react";

<Dialog open={!!order} onClose={onClose}>
  <Dialog.Backdrop className="..." />
  <Dialog.Panel>
    <Dialog.Title>Order Details</Dialog.Title>
    ...
  </Dialog.Panel>
</Dialog>
```

| Pros                                   | Cons                       |
| -------------------------------------- | -------------------------- |
| All a11y behavior out of the box       | New dependency (~8KB gzip) |
| Officially maintained by Tailwind team, great compatibility | Need to learn the API |
| Complete focus trap                    |                            |

**Recommendation**: Option B. Only 1 modal currently, but CreateRunForm could also be converted to a modal popup (currently inline), making a generic component more valuable. If you don't want extra code, choose Option A.

> **🔒 Decision D-4: Option C (@headlessui/react library) — go all-in, don't reinvent the wheel**

### 8.3 Estimated Changes

**Option C (@headlessui/react)**:

| File                                     | Change                                                            |
| ---------------------------------------- | ----------------------------------------------------------------- |
| `package.json`                           | Install `@headlessui/react`                                       |
| `components/orders/OrderDetailModal.tsx` | Refactor to use Headless UI `Dialog` component with built-in role/aria/escape/focus trap |

### 8.4 TDD Test Plan

| Test                                     | Description                             | Type          |
| ---------------------------------------- | --------------------------------------- | ------------- |
| `modal has role="dialog" and aria-modal` | Check attributes after render           | frontend unit |
| `modal closes on Escape key`             | Simulate keyboard event → close callback called | frontend unit |
| `modal closes on backdrop click`         | Simulate backdrop click → close callback called | frontend unit |
| `modal has aria-labelledby`              | Check title association                 | frontend unit |

**Estimated new tests**: ~4

---

## 9. Phase 5: Table Fixes (H5)

### 9.1 Current State

Two issues:

**9.1.1 Horizontal overflow is clipped**

Both table containers use `overflow-hidden`, clipping right-side columns on small screens:

- `OrderTable.tsx` line 51
- `RunsPage.tsx` line 172

**Fix**: `overflow-hidden` → `overflow-x-auto`

**9.1.2 Clickable rows not keyboard accessible**

`OrderTable.tsx`'s `<tr>` has `onClick` and `cursor-pointer`, but lacks:

- `tabIndex={0}`
- `role="button"`
- `onKeyDown` (Enter/Space triggers click)

### 9.2 Decision Point D-5: Table Row Keyboard Interaction

**Option A: Add tabIndex + onKeyDown to `<tr>` (recommended ✅)**

```tsx
<tr
  onClick={() => onSelect(order)}
  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSelect(order); }}
  tabIndex={0}
  role="button"
  className="cursor-pointer ..."
>
```

| Pros            | Cons                                    |
| --------------- | --------------------------------------- |
| Simple, direct  | `<tr>` as button is not ideal semantically |
| 3 lines of code |                                         |

**Option B: Add explicit "View" button to each row**

Don't make `<tr>` clickable; instead add a "View" button in the last column.

| Pros                                  | Cons                                 |
| ------------------------------------- | ------------------------------------ |
| More semantically correct             | Extra column                         |
| Clearly indicates interactivity       | Visually less clean than full-row click |

**Recommendation**: Option A. Trading dashboard users expect to click the entire row to view details; adding a button would feel unnatural.

> **🔒 Decision D-5: Option A (add tabIndex + onKeyDown to tr)**

### 9.3 Estimated Changes

| File             | Change                                                                    |
| ---------------- | ------------------------------------------------------------------------- |
| `OrderTable.tsx` | `overflow-hidden` → `overflow-x-auto`; `<tr>` add tabIndex/role/onKeyDown |
| `RunsPage.tsx`   | `overflow-hidden` → `overflow-x-auto`; table add `aria-label`            |

### 9.4 TDD Test Plan

| Test                               | Description                            | Type          |
| ---------------------------------- | -------------------------------------- | ------------- |
| `order table scrolls horizontally` | Container has `overflow-x-auto` class  | frontend unit |
| `order row is keyboard accessible` | Simulate Enter key → triggers onSelect | frontend unit |
| `tables have accessible labels`    | Check aria-label or caption            | frontend unit |

**Estimated new tests**: ~3

---

## 10. Phase 6: Pagination UI (H6)

### 10.1 Current State

All pages hardcode `page: 1, page_size: 50`:

- `RunsPage.tsx` line 38
- `OrdersPage.tsx` line 36
- `Dashboard.tsx` line 17

The API already returns `total`, `page`, and `page_size` fields (`RunListResponse`/`OrderListResponse`), but the frontend does not use these fields to implement paging.

### 10.2 Decision Point D-6: Pagination Implementation

**Option A: Simple prev/next buttons (recommended ✅)**

Add prev/next buttons at the bottom of Runs and Orders pages, using `useState` to manage current page.

```typescript
const [page, setPage] = useState(1);
const { data } = useRuns({ page, page_size: 20 });
const totalPages = data ? Math.ceil(data.total / 20) : 0;

// Footer
<div>
  <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
  <span>Page {page} of {totalPages}</span>
  <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
</div>
```

| Pros             | Cons                      |
| ---------------- | ------------------------- |
| Simple, ~30 lines | Cannot jump to a specific page |
| Low cognitive load |                          |

**Option B: Full page number selector (1, 2, 3 ... 10)**

Display numbered page buttons supporting jump to any page.

| Pros         | Cons                                           |
| ------------ | ---------------------------------------------- |
| Can jump pages | More complex (ellipsis logic, edge cases)     |
| More standard UI | Initial data volumes don't need it          |

**Option C: Extract generic Pagination component (recommended alternative)**

```typescript
// components/common/Pagination.tsx
function Pagination({ page, totalPages, onPageChange }) { ... }
```

Both pages reuse the same component. Use Option A's simple logic wrapped in a generic component.

**Recommendation**: Option A + C (simple functionality + generic component).

> **🔒 Decision D-6: Option A+C (prev/next + Pagination generic component)**

### 10.3 Does Dashboard Need Pagination?

Dashboard only shows "Recent Runs" and "Recent Activity".

**D-6b: Dashboard pagination strategy**

| Option               | Approach                                                                           |
| -------------------- | ---------------------------------------------------------------------------------- |
| No pagination (recommended ✅) | Dashboard keeps `page_size: 5`, shows only the 5 most recent. Add "View All →" link to full list page |
| Pagination           | Add pagination controls to dashboard (over-engineering)                            |

> **🔒 Decision D-6b: No pagination, page_size=5 + "View All →" link**

### 10.4 Estimated Changes

| File                               | Change                                |
| ---------------------------------- | ------------------------------------- |
| `components/common/Pagination.tsx` | New generic pagination component      |
| `pages/RunsPage.tsx`               | Add page state + Pagination           |
| `pages/OrdersPage.tsx`             | Add page state + Pagination           |
| `pages/Dashboard.tsx`              | Change page_size to 5, add "View All" link |

### 10.5 TDD Test Plan

| Test                                               | Description                                 | Type          |
| -------------------------------------------------- | ------------------------------------------- | ------------- |
| `Pagination renders current page and total`        | Displays "1 / 5"                             | frontend unit |
| `Pagination prev disabled on first page`           | page=1 → prev button disabled               | frontend unit |
| `Pagination next disabled on last page`            | page=totalPages → next button disabled       | frontend unit |
| `Pagination calls onPageChange`                    | Click → callback fires                      | frontend unit |
| `RunsPage shows pagination when items > page_size` | 50+ items → pagination appears              | frontend unit |
| `OrdersPage shows pagination`                      | Same as above                               | frontend unit |
| `Dashboard has View All link`                      | Check link exists and points to /runs        | frontend unit |

**Estimated new tests**: ~7

---

## 11. Phase 7: Responsive Sidebar (H7) — ⬇️ Deferred to M13+

> **🔒 Decision D-7: Deferred to M13+**. Trading dashboard is primarily used on desktop; mobile responsiveness is not a current priority.

This phase is not in M12-B scope. Original design preserved below for M13 reference.

### 11.1 Current State

`Sidebar.tsx` sidebar width is fixed at `w-64` (256px) with no responsive logic. In `Layout.tsx` the sidebar is always visible.

For a trading dashboard system, **mobile support is lower priority** (users primarily work on desktop), but basic responsive handling still has value (e.g., landscape tablet use).

### 11.2 Decision Point D-7: Sidebar Responsive Approach

**Option A: Tailwind breakpoint hide + hamburger button (recommended ✅)**

- Small screens (`md:` and below): hide sidebar, show hamburger button ☰ in Header
- Click hamburger → sidebar slides in as overlay
- Large screens (`md:` and above): keep current fixed sidebar

```tsx
// Layout.tsx
const [sidebarOpen, setSidebarOpen] = useState(false);

<div className="flex h-screen">
  {/* Desktop fixed sidebar */}
  <div className="hidden md:block w-64">
    <Sidebar />
  </div>

  {/* Mobile overlay sidebar */}
  {sidebarOpen && (
    <div className="fixed inset-0 z-50 md:hidden">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => setSidebarOpen(false)}
      />
      <div className="relative w-64">
        <Sidebar />
      </div>
    </div>
  )}

  <div className="flex-1">
    <Header onMenuClick={() => setSidebarOpen(true)} />
    ...
  </div>
</div>;
```

| Pros                                     | Cons                              |
| ---------------------------------------- | --------------------------------- |
| Standard pattern, immediately intuitive  | Requires adding hamburger button to Header |
| Moderate effort                          |                                   |

**Option B: Sidebar collapses to icon rail**

On small screens, sidebar doesn't fully hide but narrows to an icon-only rail (`w-16`).

| Pros                  | Cons                                                 |
| --------------------- | ---------------------------------------------------- |
| Navigation always visible | Need icons for each nav item (current SVGs exist) |
| More sophisticated interaction | More complex implementation                  |

**Option C: Defer to M13+**

No responsive changes in this milestone. Trading dashboard core users are all on desktop.

| Pros         | Cons                                       |
| ------------ | ------------------------------------------ |
| Zero effort  | Poor experience if opened on tablet        |

**Recommendation**: Option A or C. If M12-B should be kept lean, defer to M13.

> **🔒 Decision D-7: Option C (defer to M13+) — trading dashboard is primarily desktop, mobile is not urgent**

### 11.3 Estimated Changes

**Option A**:

| File                            | Change                                      |
| ------------------------------- | ------------------------------------------- |
| `components/layout/Layout.tsx`  | Add sidebarOpen state, mobile overlay       |
| `components/layout/Header.tsx`  | Add hamburger button (visible below md:)    |
| `components/layout/Sidebar.tsx` | Add `aria-label="Main navigation"`          |

### 11.4 TDD Test Plan

| Test                                       | Description                     | Type          |
| ------------------------------------------ | ------------------------------- | ------------- |
| `sidebar hidden on mobile`                 | Check `hidden md:block` class   | frontend unit |
| `hamburger button visible on mobile`       | Check button exists             | frontend unit |
| `sidebar overlay opens on hamburger click` | Click → overlay appears         | frontend unit |
| `sidebar overlay closes on backdrop click` | Click backdrop → closes         | frontend unit |

**Estimated new tests**: ~4 (Option A) / 0 (Option C)

---

## 12. TDD Execution Strategy

Same as M12, each phase strictly follows the red-green-refactor cycle:

```
1. Write failing tests first (Red)
2. Write minimal code to make tests pass (Green)
3. Refactor / clean up (Refactor)
4. Run full test suite to confirm no regressions
```

### 12.1 Verification Commands Per Phase

```bash
# Frontend tests
cd /weaver/haro && npx vitest run

# Backend tests (if strategy schema was changed)
cd /weaver && python -m pytest tests/ -x -q

# E2E tests (if UI was changed)
cd /weaver && python -m pytest tests/e2e/ -m e2e -x -q

# TypeScript compilation check
cd /weaver/haro && npx tsc --noEmit
```

### 12.2 Execution Order

```
Phase 1 (H1): SSE safety ← highest priority, affects runtime stability
Phase 2 (H2): Symbols dropdown ← highest UX improvement
Phase 3 (H3): Dead code cleanup ← quick win
Phase 4 (H4): Modal a11y ← accessibility improvement
Phase 5 (H5): Table fixes ← small screens + keyboard usability
Phase 6 (H6): Pagination UI ← moderate effort
Phase 7 (H7): Responsive sidebar ← deferred to M13+
```

---

## 13. Risk Assessment

| Risk                              | Probability | Impact | Mitigation                                      |
| --------------------------------- | ----------- | ------ | ----------------------------------------------- |
| SSE changes introduce regressions | Low         | High   | Mock EventSource unit test coverage             |
| RJSF enum changes affect E2E tests | Medium    | Medium | Run all 33 E2E tests after change               |
| Modal focus trap incomplete       | Low         | Low    | Using @headlessui/react provides complete focus trap |
| Pagination changes break existing E2E | Medium  | Medium | E2E tests use fixed data, should stay within page_size=50 |
| Responsive changes cause desktop layout shift | Low | Medium | Deferred to M13+, no risk in M12-B          |

---

## 14. Exit Gate

All criteria must pass for M12-B to be considered complete:

| #   | Criterion                                        | Verification                                        |
| --- | ------------------------------------------------ | --------------------------------------------------- |
| 1   | All SSE `JSON.parse` calls protected by try/catch | `grep -c "safeParse\|try" haro/src/hooks/useSSE.ts` |
| 2   | Symbols input rendered as dropdown (not free text) | UI screenshot or E2E test                          |
| 3   | No dead code: `apiClient` removed, dead CSS cleaned | `grep "apiClient" haro/src/api/client.ts` returns 0 |
| 4   | `useStrategies` exported from barrel             | `grep "useStrategies" haro/src/hooks/index.ts`      |
| 5   | Modal uses @headlessui/react Dialog component    | Frontend unit tests                                 |
| 6   | Table containers have `overflow-x-auto`          | Frontend unit tests                                 |
| 7   | Table rows support keyboard interaction          | Frontend unit tests                                 |
| 8   | Pagination UI available on Runs and Orders pages | Frontend unit tests                                 |
| 9   | All existing tests pass (no regressions)         | `pytest tests/ -x -q && cd haro && npx vitest run`  |
| 10  | ~20 new tests added                              | `npx vitest run` count                              |

---

## 15. Decision Points Summary

| #    | Decision                 | Options                                                              | Locked     |
| ---- | ------------------------ | -------------------------------------------------------------------- | ---------- |
| D-1  | JSON parse safety        | A: safeParse utility / B: per-site try/catch / C: notify user on failure | **🔒 A** |
| D-2  | Symbols input method     | A: enum dropdown / B: /symbols endpoint / C: Combobox lib / D: A then B | **🔒 D** |
| D-2b | Symbol list contents     | Minimal set / Alpaca crypto / Custom                                 | **🔒 Minimal set** |
| D-3  | Unused hook handling     | A: keep all / B: delete all / C: fine-grained                       | **🔒 C**  |
| D-4  | Modal refactor approach  | A: manual / B: generic Modal component / C: Headless UI library     | **🔒 C**  |
| D-5  | Table row keyboard       | A: add tabIndex to tr / B: add View button per row                  | **🔒 A**  |
| D-6  | Pagination implementation | A: prev/next / B: full page numbers / C: generic component         | **🔒 A+C** |
| D-6b | Dashboard pagination     | No pagination + View All link / Pagination                          | **🔒 No pagination** |
| D-7  | Sidebar responsive       | A: hamburger button / B: icon rail collapse / C: defer              | **🔒 C**  |

---

## Estimated Test Impact Summary

| Phase                | New Tests  | Files Changed |
| -------------------- | ---------- | ------------- |
| H1: SSE safety       | ~3         | 1             |
| H2: Symbols dropdown | ~2         | 2 (backend)   |
| H3: Dead code cleanup| ~1         | 3             |
| H4: Modal a11y       | ~4         | 1-2           |
| H5: Table fixes      | ~3         | 2             |
| H6: Pagination UI    | ~7         | 4             |
| H7: Responsive sidebar | Deferred M13+ | 0        |
| **Total**            | **~20**    | **~13**       |

Target: 109 frontend tests → ~129 frontend tests

---

_Status: DECISIONS LOCKED (2026-04-03) — All 9 decision points confirmed. Phase 7 (H7) deferred to M13+, this milestone executes Phases 1-6. Ready for detailed planning._
