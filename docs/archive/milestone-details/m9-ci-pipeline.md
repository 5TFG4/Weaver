# M9: CI Deployment Pipeline — Detailed Implementation Plan

> **Document Charter**
> **Primary role**: M9 milestone detailed implementation guide.
> **Authoritative for**: M9 task breakdown, workflow specs, file-level change specs, and execution order.
> **Not authoritative for**: milestone summary status (use `MILESTONE_PLAN.md`).

> **Status**: ⏳ PLANNED
> **Prerequisite**: M8 ✅ (940 backend tests, 91 frontend tests, 89.47% backend coverage)
> **Branch**: `ci-pipeline`
> **Key Inputs**: `MILESTONE_PLAN.md` §5, existing `compose-smoke.yml`

---

## Table of Contents

1. [Current CI State — Verified Tool Results](#1-current-ci-state--verified-tool-results)
2. [Goal & Non-Goals](#2-goal--non-goals)
3. [Execution Order & Dependencies](#3-execution-order--dependencies)
4. [M9-0: Fix Lint & Type Errors (Prerequisite)](#4-m9-0-fix-lint--type-errors-prerequisite)
5. [M9-1: Backend Fast CI](#5-m9-1-backend-fast-ci)
6. [M9-2: Frontend Fast CI](#6-m9-2-frontend-fast-ci)
7. [M9-3: Container Smoke Enhancement](#7-m9-3-container-smoke-enhancement)
8. [M9-4: Branch Protection & Governance](#8-m9-4-branch-protection--governance)
9. [Exit Gate](#9-exit-gate)

---

## 1. Current CI State — Verified Tool Results

All tool results below were obtained by running each tool locally in the dev container. These are **not** assumptions — they are measured facts.

### 1.1 Existing CI Infrastructure

| Asset                  | Location                              | Status                                                                                |
| ---------------------- | ------------------------------------- | ------------------------------------------------------------------------------------- |
| Compose smoke workflow | `.github/workflows/compose-smoke.yml` | ✅ Working — builds images, runs Alembic, health-checks API + frontend                |
| Local smoke mirror     | `scripts/ci/compose-smoke-local.sh`   | ✅ Working — `--keep-up` / `--no-build` / `--timeout` options                         |
| Ruff config            | `pyproject.toml [tool.ruff]`          | ✅ Configured — target py313, rules: E/W/F/I/B/C4/UP/ARG/SIM                          |
| MyPy config            | `pyproject.toml [tool.mypy]`          | ✅ Configured — `disallow_untyped_defs`, `strict_optional`                            |
| Pytest config          | `pyproject.toml [tool.pytest]`        | ✅ Configured — markers: unit/integration/container/e2e/slow, `asyncio_mode = "auto"` |
| Coverage config        | `pyproject.toml [tool.coverage]`      | ✅ Configured — `fail_under = 80`, branch=true, source=`src/`                         |
| ESLint config          | `haro/eslint.config.js`               | ⚠️ Missing `.vite` ignore — lints bundled dependencies                                |
| Vitest config          | `haro/vitest.config.ts`               | ✅ Configured — jsdom, v8 coverage                                                    |
| npm scripts            | `haro/package.json`                   | ✅ `lint`, `test`, `build`, `test:coverage` defined                                   |

### 1.2 Tool Exit Codes — Actual Results

| Tool            | Command                            | Exit Code | Result                                       |
| --------------- | ---------------------------------- | --------- | -------------------------------------------- |
| **ruff check**  | `ruff check src/ tests/`           | ❌ **1**  | 1127 errors (843 auto-fixable with `--fix`)  |
| **ruff format** | `ruff format --check src/ tests/`  | ❌ **1**  | 88 files need reformatting                   |
| **mypy**        | `mypy src/`                        | ❌ **1**  | 34 errors in 15 files                        |
| **pytest**      | `pytest -m "not container"`        | ✅ **0**  | 940 passed in 47s                            |
| **coverage**    | `pytest --cov=src`                 | ✅ **0**  | 89.47% ≥ 80% threshold                       |
| **ESLint**      | `npx eslint .` (in `haro/`)        | ❌ **1**  | 16 errors (13 source + 3 from `.vite/deps/`) |
| **TypeScript**  | `npx tsc -b --noEmit` (in `haro/`) | ✅ **0**  | Clean                                        |
| **Vitest**      | `npm run test` (in `haro/`)        | ✅ **0**  | 91 passed (15 files) in 6s                   |
| **Vite build**  | `npm run build` (in `haro/`)       | ✅ **0**  | 297 KB bundle                                |

**Conclusion**: 4 of 9 tools fail. CI workflows created without fixing these will always be red. **M9-0 (fix errors) must run before M9-1/M9-2.**

### 1.3 Ruff Error Breakdown (1127 total)

After running `ruff check --fix` (safe fixes only) + `ruff format`, exactly **57 errors remain**:

| Rule   | Count | Description                                 | Fix Type                               |
| ------ | ----- | ------------------------------------------- | -------------------------------------- |
| E402   | 17    | Module import not at top of file            | Manual — restructure imports           |
| UP042  | 13    | `str, Enum` → use `StrEnum`                 | Manual — change base class             |
| ARG002 | 10    | Unused method argument                      | Manual — prefix with `_`               |
| F841   | 3     | Unused variable                             | Manual — remove or prefix with `_`     |
| SIM102 | 3     | Collapsible if → single `if` with `and`     | Manual — flatten                       |
| SIM105 | 3     | `try/except/pass` → `contextlib.suppress()` | Manual — rewrite                       |
| F821   | 2     | Undefined name (string annotation)          | Manual — add import or `TYPE_CHECKING` |
| SIM108 | 2     | `if/else` → ternary                         | Manual — rewrite                       |
| C408   | 1     | `dict()` → `{}` literal                     | Manual — rewrite                       |
| SIM103 | 1     | Needless bool                               | Manual — inline                        |
| SIM116 | 1     | `if/elif` chain → dict lookup               | Manual — rewrite                       |
| UP007  | 1     | `Union[X, Y]` → `X \| Y`                    | Manual — rewrite                       |

**Verified**: After `ruff check --fix` + `ruff format`, all 940 tests still pass (confirmed by running pytest).

### 1.4 MyPy Error Breakdown (34 total)

| File                                       | Errors | Error Types                                                                               |
| ------------------------------------------ | ------ | ----------------------------------------------------------------------------------------- |
| `src/glados/app.py`                        | 8      | `no-untyped-def`(3), `arg-type`(1), `assignment`(2), `union-attr`(1), `no-untyped-def`(1) |
| `src/glados/dependencies.py`               | 5      | `no-any-return`(5) — all `get_*` dependency functions                                     |
| `src/veda/adapters/alpaca_adapter.py`      | 3      | `no-untyped-def`(3)                                                                       |
| `src/veda/adapters/mock_adapter.py`        | 2      | `override`(2) — `stream_bars`/`stream_quotes` async iterator mismatch                     |
| `src/glados/routes/orders.py`              | 2      | `assignment`(1), `arg-type`(1) — `Order` vs `OrderState`                                  |
| `src/glados/routes/sse.py`                 | 2      | `no-any-return`(1), `no-untyped-def`(1)                                                   |
| `src/config.py`                            | 2      | `prop-decorator`(2) — decorators on top of `@property`                                    |
| `src/walle/repositories/bar_repository.py` | 3      | `unused-ignore`(1), `no-any-return`(1), `attr-defined`(1)                                 |
| `src/marvin/base_strategy.py`              | 1      | `no-untyped-def` — `on_tick`                                                              |
| `src/marvin/strategies/sma_strategy.py`    | 1      | `no-untyped-def` — `on_tick`                                                              |
| `src/marvin/strategies/sample_strategy.py` | 1      | `no-untyped-def` — `on_tick`                                                              |
| `src/marvin/strategy_loader.py`            | 1      | `no-any-return`                                                                           |
| `src/veda/adapter_loader.py`               | 1      | `no-any-return`                                                                           |
| `src/marvin/strategy_runner.py`            | 1      | `no-untyped-def`                                                                          |
| `src/events/offsets.py`                    | 1      | `no-any-return`                                                                           |

### 1.5 ESLint Error Breakdown (16 total)

**3 errors from `.vite/deps/` (false positives — ESLint is scanning bundled dependencies)**:

- `.vite/deps/react-router-dom.js`: `jsx-a11y/anchor-has-content`, `react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps` — rules not found (wrong plugin applied to vendor bundle)

**Fix**: Add `.vite` to `globalIgnores` in `haro/eslint.config.js`.

**13 real errors in test files**:

| File                                                 | Error                                                 | Rule                                   |
| ---------------------------------------------------- | ----------------------------------------------------- | -------------------------------------- |
| `tests/unit/components/OrderStatusBadge.test.tsx:11` | `OrderSide` defined but never used                    | `no-unused-vars`                       |
| `tests/unit/components/OrderTable.test.tsx:9`        | `within` defined but never used                       | `no-unused-vars`                       |
| `tests/unit/components/OrderTable.test.tsx:62`       | `require()` import forbidden                          | `no-require-imports`                   |
| `tests/unit/components/StatCard.test.tsx:40`         | `container` assigned but never used                   | `no-unused-vars`                       |
| `tests/unit/components/Toast.test.tsx:8`             | `vi` defined but never used                           | `no-unused-vars`                       |
| `tests/unit/components/Toast.test.tsx:8`             | `afterEach` defined but never used                    | `no-unused-vars`                       |
| `tests/unit/hooks/useRuns.test.tsx:1`                | `vi` defined but never used                           | `no-unused-vars`                       |
| `tests/unit/pages/Dashboard.test.tsx:13`             | `RunListResponse` defined but never used              | `no-unused-vars`                       |
| `tests/unit/pages/Dashboard.test.tsx:14`             | `OrderListResponse` defined but never used            | `no-unused-vars`                       |
| `tests/unit/pages/OrdersPage.test.tsx:9`             | `within` defined but never used                       | `no-unused-vars`                       |
| `tests/unit/stores/notificationStore.test.ts:14`     | `Notification` defined but never used                 | `no-unused-vars`                       |
| `tests/utils.tsx:21`                                 | Fast refresh: file exports non-components             | `react-refresh/only-export-components` |
| `tests/utils.tsx:38`                                 | Fast refresh: `export *` can't verify components only | `react-refresh/only-export-components` |

### 1.6 Design Rationale — Two-Tier CI

```
Tier 1: Fast CI (< 2 min)           Tier 2: Container Smoke (~ 5-10 min)
┌─────────────────────────┐         ┌──────────────────────────────┐
│ backend-ci.yml          │         │ compose-smoke.yml            │
│  ruff check + format    │         │  Docker build                │
│  mypy                   │         │  Alembic migration           │
│  pytest (unit only)     │         │  API health check            │
│                         │         │  Frontend availability       │
│ frontend-ci.yml         │         │                              │
│  eslint                 │         │                              │
│  tsc --noEmit           │         │                              │
│  vitest                 │         │                              │
│  vite build             │         │                              │
└─────────────────────────┘         └──────────────────────────────┘
 Runs on EVERY PR                    Runs on docker/src/haro changes
 Required for merge                  Required for merge
```

---

## 2. Goal & Non-Goals

### Goals

- All lint/type/test tools exit 0 on the current codebase (prerequisite)
- Every PR gets fast code-quality feedback (lint + types + unit tests) in < 2 min
- Container-level smoke test covers runtime integration for relevant changes
- Branch protection prevents merging broken code to `main`
- CI troubleshooting is documented for self-service debugging

### Non-Goals

- CD / automated deployment (not in M9 scope)
- Integration test CI (requires DB; covered by compose-smoke container flow)
- Coverage badge or third-party reporting tools
- Frontend coverage enforcement (backend keeps `fail_under = 80%`; frontend is report-only)

---

## 3. Execution Order & Dependencies

```
M9-0: Fix Lint & Type Errors  ← MUST DO FIRST (without this, all CI = red)
  │
  ├── M9-0a: ruff auto-fix + format (1070 of 1127 errors)
  ├── M9-0b: ruff manual fixes (57 remaining errors)
  ├── M9-0c: mypy fixes (34 errors)
  ├── M9-0d: ESLint fixes (16 errors)
  │
  ▼
M9-1: Backend Fast CI (create workflow file)
  │
  ▼
M9-2: Frontend Fast CI (create workflow file)
  │
  ▼
M9-3: Compose Smoke Enhancement (patch existing workflow)
  │
  ▼
M9-4: Branch Protection & Governance (documentation)
```

---

## 4. M9-0: Fix Lint & Type Errors (Prerequisite)

**Why this phase exists**: The CI workflows run `ruff check`, `ruff format --check`, `mypy`, and `eslint`. If these tools don't exit 0 on the codebase, CI will always fail. This phase makes the codebase CI-clean.

### 4.0 Pre-Flight Verification

Run these commands to confirm the starting state matches this document:

```bash
cd /weaver
ruff check src/ tests/ 2>&1 | tail -3
# Expected: Found 1127 errors.

ruff format --check src/ tests/ 2>&1 | tail -3
# Expected: 88 files would be reformatted

mypy src/ 2>&1 | tail -1
# Expected: Found 34 errors in 15 files

cd haro && npx eslint . 2>&1 | tail -1
# Expected: ✖ 17 problems (16 errors, 1 warning)
```

### 4.1 M9-0a: Ruff Auto-Fix + Format

**What**: Run `ruff check --fix` then `ruff format` to eliminate 1070 of 1127 errors automatically.

**Exact commands** (run from repo root):

```bash
cd /weaver

# Step 1: Apply safe auto-fixes (fixes 909 errors: unused imports, datetime UTC, sorted imports, etc.)
ruff check --fix src/ tests/
# Expected output: "Found 1194 errors (909 fixed, 285 remaining)."
# Note: the total goes up because format-only issues are exposed, but net errors drop.

# Step 2: Format all files (fixes W293 whitespace, W291 trailing whitespace, W292 missing newline, etc.)
ruff format src/ tests/
# Expected output: "83 files reformatted, 85 files left unchanged"

# Step 3: Verify remaining errors
ruff check src/ tests/ --statistics
# Expected output: 57 errors remaining — see table in §1.3

# Step 4: Confirm tests still pass (CRITICAL — must verify no auto-fix broke behavior)
pytest -m "not container" -x -q --tb=short
# Expected: 940 passed
```

**Verified**: This exact sequence was tested — all 940 tests pass after auto-fix + format.

**Commit**: `fix(lint): apply ruff auto-fix and format to entire codebase`

### 4.2 M9-0b: Ruff Manual Fixes (57 remaining errors)

Fix the 57 errors that `ruff --fix` cannot auto-resolve. Grouped by fix type for efficient batch processing.

#### 4.2.1 UP042: `str, Enum` → `StrEnum` (13 errors)

**What**: Python 3.11+ has `enum.StrEnum`. Replace `class Foo(str, Enum)` with `class Foo(StrEnum)`.

**Files and exact changes**:

| File                          | Line | Class               | Change                                                                      |
| ----------------------------- | ---- | ------------------- | --------------------------------------------------------------------------- |
| `src/glados/schemas.py`       | 20   | `RunMode`           | `class RunMode(str, Enum):` → `class RunMode(StrEnum):`                     |
| `src/glados/schemas.py`       | 28   | `RunStatus`         | `class RunStatus(str, Enum):` → `class RunStatus(StrEnum):`                 |
| `src/glados/schemas.py`       | 99   | `OrderSide`         | `class OrderSide(str, Enum):` → `class OrderSide(StrEnum):`                 |
| `src/glados/schemas.py`       | 106  | `OrderType`         | `class OrderType(str, Enum):` → `class OrderType(StrEnum):`                 |
| `src/glados/schemas.py`       | 115  | `OrderStatus`       | `class OrderStatus(str, Enum):` → `class OrderStatus(StrEnum):`             |
| `src/marvin/base_strategy.py` | 13   | `ActionType`        | `class ActionType(str, Enum):` → `class ActionType(StrEnum):`               |
| `src/marvin/base_strategy.py` | 20   | `StrategyOrderSide` | `class StrategyOrderSide(str, Enum):` → `class StrategyOrderSide(StrEnum):` |
| `src/marvin/base_strategy.py` | 27   | `StrategyOrderType` | `class StrategyOrderType(str, Enum):` → `class StrategyOrderType(StrEnum):` |
| `src/veda/models.py`          | 19   | `OrderSide`         | `class OrderSide(str, Enum):` → `class OrderSide(StrEnum):`                 |
| `src/veda/models.py`          | 26   | `OrderType`         | `class OrderType(str, Enum):` → `class OrderType(StrEnum):`                 |
| `src/veda/models.py`          | 35   | `TimeInForce`       | `class TimeInForce(str, Enum):` → `class TimeInForce(StrEnum):`             |
| `src/veda/models.py`          | 44   | `OrderStatus`       | `class OrderStatus(str, Enum):` → `class OrderStatus(StrEnum):`             |
| `src/veda/models.py`          | 63   | `PositionSide`      | `class PositionSide(str, Enum):` → `class PositionSide(StrEnum):`           |

**For each file**, also update the import:

- Add `from enum import StrEnum` (or change existing `from enum import Enum` to `from enum import Enum, StrEnum`)
- Keep `Enum` import if other non-str enums still use it in the same file

**Post-fix verification**:

```bash
ruff check src/ tests/ --select UP042
# Expected: no errors

pytest -m "not container" -x -q --tb=short
# Expected: 940 passed
```

#### 4.2.2 E402: Module import not at top of file (17 errors)

**Files**:

- `src/veda/adapters/alpaca_adapter.py` (lines 22–25, 40–53) — 6 errors
- `src/veda/adapters/mock_adapter.py` (lines 19–25, 24–34) — 6 errors
- `tests/conftest.py` (lines 183–188) — 5 errors

**Root cause**: These files have module-level constants or `try/except` import guards above the regular imports.

**Fix pattern**:

- For `alpaca_adapter.py` and `mock_adapter.py`: The `ADAPTER_META` dict and `try/except` for optional Alpaca SDK are at the top. Move all standard library and local imports above `ADAPTER_META`, or add `# noqa: E402` if the ordering is intentional for adapter metadata discovery.
- For `tests/conftest.py`: There's a section separator comment (`# ===...`) with imports below it. Move those imports to the file top.

**Decision point**: If the `ADAPTER_META` dict must be at the top of the file for adapter discovery (which is the current design), use `# noqa: E402` for imports that follow it:

```python
# In alpaca_adapter.py, after the ADAPTER_META dict:
from collections.abc import AsyncIterator  # noqa: E402
from datetime import datetime  # noqa: E402
# ... etc
```

**Post-fix verification**:

```bash
ruff check src/ tests/ --select E402
# Expected: no errors

pytest -m "not container" -x -q --tb=short
# Expected: 940 passed
```

#### 4.2.3 ARG002: Unused method argument (10 errors)

**Fix**: Prefix unused arguments with `_` to indicate intentional non-use.

| File                                       | Line | Argument     | Change To     |
| ------------------------------------------ | ---- | ------------ | ------------- |
| `src/events/log.py`                        | 144  | `connection` | `_connection` |
| `src/events/log.py`                        | 443  | `connection` | `_connection` |
| `src/events/log.py`                        | 444  | `pid`        | `_pid`        |
| `src/events/log.py`                        | 445  | `channel`    | `_channel`    |
| `src/greta/fill_simulator.py`              | 142  | `side`       | `_side`       |
| `src/greta/greta_service.py`               | 408  | `timestamp`  | `_timestamp`  |
| `src/marvin/strategies/sample_strategy.py` | 51   | `tick`       | `_tick`       |
| `src/marvin/strategies/sma_strategy.py`    | 77   | `tick`       | `_tick`       |
| `src/veda/adapters/mock_adapter.py`        | 349  | `symbols`    | `_symbols`    |
| `src/veda/adapters/mock_adapter.py`        | 355  | `symbols`    | `_symbols`    |

**Important**: Also rename any usage of these arguments inside the function body. Search for each argument name in the function body before renaming. For these 10, none are used in the function body (verified — they are truly unused).

**Post-fix verification**:

```bash
ruff check src/ tests/ --select ARG002
# Expected: no errors

pytest -m "not container" -x -q --tb=short
# Expected: 940 passed
```

#### 4.2.4 SIM102/SIM103/SIM105/SIM108/SIM116: Simplification suggestions (10 errors)

**SIM105 — `try/except/pass` → `contextlib.suppress()` (3 errors)**:

| File                            | Line | Exception                | Change                                                                     |
| ------------------------------- | ---- | ------------------------ | -------------------------------------------------------------------------- |
| `src/glados/clock/base.py`      | 107  | `asyncio.CancelledError` | `async with contextlib.suppress(asyncio.CancelledError): await self._task` |
| `src/glados/clock/base.py`      | 122  | `asyncio.CancelledError` | Same pattern                                                               |
| `src/glados/sse_broadcaster.py` | 94   | `asyncio.QueueFull`      | `with contextlib.suppress(asyncio.QueueFull): queue.put_nowait(event)`     |

Add `import contextlib` to each file if not already present.

**SIM102 — Collapsible nested `if` (3 errors)**:

| File                                    | Line | Change                                                                                                                                                                        |
| --------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/marvin/strategies/sma_strategy.py` | 193  | `if fast_above_slow and not self._prev_fast_above_slow:` + `if not self._has_position:` → `if fast_above_slow and not self._prev_fast_above_slow and not self._has_position:` |
| `src/marvin/strategies/sma_strategy.py` | 206  | `if not fast_above_slow and self._prev_fast_above_slow:` + `if self._has_position:` → `if not fast_above_slow and self._prev_fast_above_slow and self._has_position:`         |
| `tests/unit/events/test_types.py`       | 113  | `if isinstance(value, str) and "." in value:` + `if value not in ALL_EVENT_TYPES:` → `if isinstance(value, str) and "." in value and value not in ALL_EVENT_TYPES:`           |

**SIM108 — If/else → ternary (2 errors)**:

| File                                   | Line | Change                                                                                                                                                                                                         |
| -------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/glados/services/domain_router.py` | 76   | `if run.mode == RunMode.BACKTEST: target_domain = "backtest" else: target_domain = "live"` → `target_domain = "backtest" if run.mode == RunMode.BACKTEST else "live"`                                          |
| `src/veda/veda_service.py`             | 146  | `if state.status == OrderStatus.REJECTED: event_type = "orders.Rejected" else: event_type = "orders.Created"` → `event_type = "orders.Rejected" if state.status == OrderStatus.REJECTED else "orders.Created"` |

**SIM103 — Needless bool (1 error)**:

- `src/events/protocol.py:142` — `if self.filter_fn is not None and not self.filter_fn(envelope): return False; return True` → `return self.filter_fn is None or self.filter_fn(envelope)`

**SIM116 — If/elif chain → dict (1 error)**:

- `src/veda/adapters/alpaca_adapter.py:579` — Convert timeframe unit if/elif to dict lookup:

```python
unit_map = {"m": "Min", "h": "Hour", "d": "Day", "w": "Week"}
suffix = unit_map.get(unit)
return f"{value}{suffix}" if suffix else timeframe
```

#### 4.2.5 Remaining small fixes (4 errors)

**F841 — Unused variable (3 errors)**:
All in `tests/unit/glados/services/test_event_pipeline.py` — `with TestClient(app) as client:` where `client` is unused.
Fix: `with TestClient(app) as _client:` or `with TestClient(app):` (if Python version allows).

**F821 — Undefined name (2 errors)**:

| File                                     | Line | Undefined Name  | Fix                                                                                                                        |
| ---------------------------------------- | ---- | --------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `tests/factories/runs.py`                | 278  | `RunManager`    | File already has `from __future__ import annotations`, but ruff still flags string annotation. Add `TYPE_CHECKING` import. |
| `tests/unit/veda/test_alpaca_adapter.py` | 553  | `AlpacaAdapter` | Same pattern — string annotation `"AlpacaAdapter"` but name not at module scope. Add `TYPE_CHECKING` import.               |

Fix pattern for both:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.glados.services.run_manager import RunManager  # or AlpacaAdapter
```

**UP007 — Union syntax (1 error)**:

- `src/glados/clock/base.py:53` — `Union[Callable[...], Callable[...]]` → `Callable[...] | Callable[...]`

**C408 — `dict()` → `{}` (1 error)**:

- `tests/unit/glados/services/test_run_persistence.py:28` — `defaults: dict[str, Any] = dict(strategy_id="sma", ...)` → `defaults: dict[str, Any] = {"strategy_id": "sma", ...}`

#### 4.2.6 Final ruff verification

```bash
ruff check src/ tests/
# Expected: All checks passed!

ruff format --check src/ tests/
# Expected: 168 files already formatted.

pytest -m "not container" -x -q --tb=short
# Expected: 940 passed
```

**Commit**: `fix(lint): resolve all ruff manual errors (57 fixes)`

### 4.3 M9-0c: MyPy Fixes (34 errors)

Fix all 34 mypy errors. Grouped by error type for batch processing.

#### 4.3.1 `no-untyped-def` — Missing type annotations (9 errors)

| File                                       | Line | Function                               | Fix                                        |
| ------------------------------------------ | ---- | -------------------------------------- | ------------------------------------------ |
| `src/marvin/base_strategy.py`              | 100  | `on_tick(self, tick)`                  | Add type: `on_tick(self, tick: ClockTick)` |
| `src/marvin/strategies/sma_strategy.py`    | 78   | `on_tick(self, tick)`                  | Add type: `on_tick(self, tick: ClockTick)` |
| `src/marvin/strategies/sample_strategy.py` | 52   | `on_tick(self, tick)`                  | Add type: `on_tick(self, tick: ClockTick)` |
| `src/marvin/strategy_runner.py`            | 102  | Missing annotation                     | Check function signature, add types        |
| `src/veda/adapters/alpaca_adapter.py`      | 531  | Missing annotation                     | Check function signature, add types        |
| `src/veda/adapters/alpaca_adapter.py`      | 563  | Missing annotation                     | Check function signature, add types        |
| `src/veda/adapters/alpaca_adapter.py`      | 576  | Missing annotation                     | Check function signature, add types        |
| `src/glados/app.py`                        | 88   | Missing annotation                     | Check function signature, add types        |
| `src/glados/app.py`                        | 138  | Missing annotation                     | Check function signature, add types        |
| `src/glados/app.py`                        | 345  | Missing both return type and arg types | Check function signature, add types        |
| `src/glados/routes/sse.py`                 | 53   | Missing return type                    | Check function signature, add return type  |

**How to fix each**: Open the file, go to the line, look at the function signature, and add the missing type annotations. For the `on_tick` methods, the `tick` parameter should be typed as `ClockTick` (import from `src/glados/clock/base.py` or wherever the type is defined). For `glados/app.py` functions, inspect the function body to determine the correct types.

#### 4.3.2 `no-any-return` — Returning Any from typed function (9 errors)

| File                            | Line | Function                        | Fix                                                                      |
| ------------------------------- | ---- | ------------------------------- | ------------------------------------------------------------------------ |
| `src/glados/dependencies.py`    | 23   | `get_config()`                  | Add explicit cast: `return cast(WeaverConfig, request.app.state.config)` |
| `src/glados/dependencies.py`    | 28   | `get_run_manager()`             | Same pattern with `cast(RunManager, ...)`                                |
| `src/glados/dependencies.py`    | 33   | `get_order_service()`           | Same pattern with `cast(MockOrderService, ...)`                          |
| `src/glados/dependencies.py`    | 38   | `get_market_data_service()`     | Same pattern with `cast(MockMarketDataService, ...)`                     |
| `src/glados/dependencies.py`    | 43   | `get_sse_broadcaster()`         | Same pattern with `cast(SSEBroadcaster, ...)`                            |
| `src/glados/routes/sse.py`      | 50   | return typed as bool            | Add `cast()` or explicit type narrowing                                  |
| `src/marvin/strategy_loader.py` | 214  | returns `type[BaseStrategy]`    | Add `cast(type[BaseStrategy], ...)`                                      |
| `src/veda/adapter_loader.py`    | 189  | returns `type[ExchangeAdapter]` | Add `cast(type[ExchangeAdapter], ...)`                                   |
| `src/events/offsets.py`         | 214  | returns `list[tuple[int, Any]]` | Add `cast()` or fix return expression                                    |

Add `from typing import cast` to each file. The `dependencies.py` file has 5 errors all with the same pattern — all accessing `request.app.state.*` which is `Any`.

#### 4.3.3 `assignment` — Incompatible type assignment (3 errors)

| File                          | Line | Issue                                                     | Fix                                                                                                     |
| ----------------------------- | ---- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `src/glados/app.py`           | 131  | `InMemoryEventLog` assigned to `PostgresEventLog \| None` | Widen the variable type annotation to `EventLogProtocol \| None` or use a union type that includes both |
| `src/glados/app.py`           | 200  | `Any \| None` assigned to `VedaService`                   | Add explicit type annotation or use `cast()`                                                            |
| `src/glados/routes/orders.py` | 178  | `list[Order]` vs `list[OrderState]`                       | Check the actual type returned and fix the annotation                                                   |

#### 4.3.4 `override` — Incompatible return types (2 errors)

| File                                | Line | Issue                                                                                                  | Fix                                                                                                                                                                                             |
| ----------------------------------- | ---- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/veda/adapters/mock_adapter.py` | 353  | `stream_bars` returns `AsyncIterator[Bar]` but supertype declares `Coroutine[..., AsyncIterator[Bar]]` | Remove `async` from the method in the base class `ExchangeAdapter.stream_bars`, or make mock_adapter match. The mypy note says: "Consider declaring `stream_bars` in supertype without `async`" |
| `src/veda/adapters/mock_adapter.py` | 359  | Same for `stream_quotes`                                                                               | Same fix                                                                                                                                                                                        |

These 2 errors require deciding: is the interface method an `async def` that returns `AsyncIterator`, or a regular `def` that returns `AsyncIterator`? Check `src/veda/interfaces.py` and make all implementations consistent.

#### 4.3.5 Other errors (11 errors)

| File                                       | Line     | Code                                               | Fix                                                                                                                                               |
| ------------------------------------------ | -------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/config.py`                            | 124, 130 | `prop-decorator`                                   | Mypy doesn't support stacking decorators on `@property`. Move the other decorator or restructure.                                                 |
| `src/glados/app.py`                        | 103      | `arg-type`                                         | `get_credentials("str")` but expects `Literal["live", "paper"]`. Use the correct literal type or variable.                                        |
| `src/glados/app.py`                        | 142      | `union-attr`                                       | `event_log` is `PostgresEventLog \| None` but `.subscribe` is called. Add `assert event_log is not None` before the call, or use `if event_log:`. |
| `src/glados/routes/orders.py`              | 180      | `arg-type`                                         | `OrderState` passed where `Order` expected. Fix the type or the function signature.                                                               |
| `src/walle/repositories/bar_repository.py` | 103      | `unused-ignore` + `no-any-return` + `attr-defined` | The `# type: ignore` doesn't cover the right errors. Replace with `# type: ignore[no-any-return, attr-defined]` or fix the underlying code.       |

#### 4.3.6 Final mypy verification

```bash
mypy src/
# Expected: Success: no issues found in 73 source files

pytest -m "not container" -x -q --tb=short
# Expected: 940 passed
```

**Commit**: `fix(types): resolve all mypy errors (34 fixes)`

### 4.4 M9-0d: ESLint Fixes (16 errors)

#### 4.4.1 Fix `.vite/deps/` false positives (3 errors)

**File**: `haro/eslint.config.js`

**Change**: Add `.vite` to `globalIgnores`:

```javascript
// Before:
globalIgnores(['dist']),

// After:
globalIgnores(['dist', '.vite']),
```

This eliminates 3 false-positive errors from bundled vendor code.

#### 4.4.2 Fix unused imports in test files (10 errors)

Remove the unused imports. Each fix is a simple deletion of the unused import:

| File                                                 | Import to Remove                                                                             |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `tests/unit/components/OrderStatusBadge.test.tsx:11` | `OrderSide`                                                                                  |
| `tests/unit/components/OrderTable.test.tsx:9`        | `within`                                                                                     |
| `tests/unit/components/StatCard.test.tsx:40`         | `container` (destructured but unused — change to `const { } = render(...)` or `render(...)`) |
| `tests/unit/components/Toast.test.tsx:8`             | `vi`, `afterEach`                                                                            |
| `tests/unit/hooks/useRuns.test.tsx:1`                | `vi`                                                                                         |
| `tests/unit/pages/Dashboard.test.tsx:13-14`          | `RunListResponse`, `OrderListResponse`                                                       |
| `tests/unit/pages/OrdersPage.test.tsx:9`             | `within`                                                                                     |
| `tests/unit/stores/notificationStore.test.ts:14`     | `Notification`                                                                               |

#### 4.4.3 Fix `require()` import (1 error)

**File**: `tests/unit/components/OrderTable.test.tsx:62`

Change `require()` to a standard ES import. Check what's being required and convert to `import ... from ...` at the top of the file.

#### 4.4.4 Fix `react-refresh/only-export-components` (2 errors)

**File**: `tests/utils.tsx:21,38`

This is a test utility file that exports helper functions alongside components. Options:

1. **Recommended**: Add an ESLint disable comment for this rule in the test utils file (it's a test helper, not a component file):
   ```typescript
   // eslint-disable-next-line react-refresh/only-export-components
   ```
2. Or split the file into component exports and function exports.

#### 4.4.5 Final ESLint verification

```bash
cd haro
npx eslint .
# Expected: no errors

npm run test
# Expected: 91 passed

npm run build
# Expected: build succeeds
```

**Commit**: `fix(lint): resolve all ESLint errors (16 fixes)`

---

## 5. M9-1: Backend Fast CI

### 5.1 Pre-Condition

All these commands must exit 0 before creating this workflow:

```bash
ruff check src/ tests/        # exit 0
ruff format --check src/ tests/  # exit 0
mypy src/                      # exit 0
pytest -m "not container" --cov=src  # exit 0, coverage ≥ 80%
```

If any fail, go back to M9-0 and fix them.

### 5.2 TDD: CI Contract Test

**RED**: Create `tests/unit/test_ci_contract.py` to verify CI tooling configurations exist in `pyproject.toml`.

```python
"""Tests that CI tooling configurations are present and correct in pyproject.toml."""

from pathlib import Path

import tomllib
import pytest

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text())


class TestCIContract:
    def test_ruff_target_version(self, pyproject: dict) -> None:
        assert pyproject["tool"]["ruff"]["target-version"] == "py313"

    def test_mypy_disallow_untyped_defs(self, pyproject: dict) -> None:
        assert pyproject["tool"]["mypy"]["disallow_untyped_defs"] is True

    def test_pytest_markers_registered(self, pyproject: dict) -> None:
        markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]
        marker_names = {m.split(":")[0].strip() for m in markers}
        assert {"unit", "integration", "container", "e2e", "slow"} <= marker_names

    def test_pytest_default_excludes_container(self, pyproject: dict) -> None:
        addopts = pyproject["tool"]["pytest"]["ini_options"]["addopts"]
        assert "not container" in addopts

    def test_coverage_fail_under(self, pyproject: dict) -> None:
        assert pyproject["tool"]["coverage"]["report"]["fail_under"] == 80

    def test_ruff_lint_select_includes_core_rules(self, pyproject: dict) -> None:
        select = pyproject["tool"]["ruff"]["lint"]["select"]
        for rule in ("E", "W", "F", "I", "B"):
            assert rule in select, f"Missing core ruff rule: {rule}"
```

**GREEN**: Run the test:

```bash
pytest tests/unit/test_ci_contract.py -v
# Expected: 6 passed
```

These test against existing config so they should pass immediately.

**Commit**: `test(ci): add CI configuration contract tests`

### 5.3 Create Workflow File

**File**: `.github/workflows/backend-ci.yml`

```yaml
name: Backend CI

on:
  workflow_dispatch:
  pull_request:
    paths:
      - "src/**"
      - "tests/**"
      - "pyproject.toml"
      - "weaver.py"
      - "alembic.ini"
      - ".github/workflows/backend-ci.yml"

jobs:
  backend-checks:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ hashFiles('docker/backend/requirements.dev.txt') }}
          restore-keys: pip-

      - name: Install dependencies
        run: pip install -r docker/backend/requirements.dev.txt

      - name: Ruff lint check
        run: ruff check src/ tests/

      - name: Ruff format check
        run: ruff format --check src/ tests/

      - name: MyPy type check
        run: mypy src/

      - name: Pytest (unit tests + coverage)
        run: pytest -m "not container" --cov=src --cov-report=term-missing
```

**Commit**: `ci(backend): add fast CI workflow for ruff, mypy, pytest`

### 5.4 Local Pre-Push Check Script

Create `scripts/ci/check-local.sh` — a one-command local CI that mirrors all GitHub Actions checks. Run this before pushing to catch errors locally (fast, free) instead of waiting for GitHub (slow, costs Actions minutes).

**File**: `scripts/ci/check-local.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
# Any step that fails stops the script immediately.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo " Local CI Check"
echo "=========================================="

echo ""
echo "--- Backend: ruff check ---"
ruff check src/ tests/

echo "--- Backend: ruff format ---"
ruff format --check src/ tests/

echo "--- Backend: mypy ---"
mypy src/

echo "--- Backend: pytest + coverage ---"
pytest -m "not container" --cov=src --cov-report=term-missing -q

echo ""
echo "--- Frontend: eslint ---"
(cd haro && npm run lint)

echo "--- Frontend: tsc ---"
(cd haro && npx tsc -b --noEmit)

echo "--- Frontend: vitest ---"
(cd haro && npm run test)

echo "--- Frontend: build ---"
(cd haro && npm run build)

echo ""
echo "=========================================="
echo " ✅ ALL CHECKS PASSED — safe to push"
echo "=========================================="
```

**Usage**:

```bash
# Make executable (first time only)
chmod +x scripts/ci/check-local.sh

# Run before every push
./scripts/ci/check-local.sh

# All green → push
git push origin ci-pipeline
```

If any step fails, the script stops immediately and shows which check failed. Fix the issue, then re-run.

**Commit**: `ci(local): add pre-push local CI check script`

### 5.5 Verification

Push the branch and open a PR that touches `src/` or `tests/`. Confirm:

1. The `Backend CI` workflow runs automatically
2. All 4 steps (ruff check, ruff format, mypy, pytest) show green checks
3. Coverage output shows ≥ 80%

---

## 6. M9-2: Frontend Fast CI

### 6.1 Pre-Condition

All these commands must exit 0 before creating this workflow:

```bash
cd haro
npx eslint .                # exit 0
npx tsc -b --noEmit         # exit 0
npm run test                 # exit 0
npm run build                # exit 0
```

If any fail, go back to M9-0d and fix them.

### 6.2 Create Workflow File

**File**: `.github/workflows/frontend-ci.yml`

```yaml
name: Frontend CI

on:
  workflow_dispatch:
  pull_request:
    paths:
      - "haro/**"
      - ".github/workflows/frontend-ci.yml"

jobs:
  frontend-checks:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    defaults:
      run:
        working-directory: haro

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: haro/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: ESLint check
        run: npm run lint

      - name: TypeScript check
        run: npx tsc -b --noEmit

      - name: Vitest tests
        run: npm run test

      - name: Vite build
        run: npm run build
```

**Commit**: `ci(frontend): add fast CI workflow for eslint, tsc, vitest, vite build`

### 6.3 Verification

Push and open a PR that touches `haro/`. Confirm:

1. The `Frontend CI` workflow runs automatically
2. All 4 steps (eslint, tsc, vitest, build) show green checks

---

## 7. M9-3: Container Smoke Enhancement

### 7.1 Scope

Patch the existing `.github/workflows/compose-smoke.yml` — three targeted changes.

### 7.2 Change 1 — Extend trigger paths

**File**: `.github/workflows/compose-smoke.yml`

```yaml
# BEFORE (lines 6-11):
    paths:
      - "docker/**"
      - "src/**"
      - "weaver.py"
      - "pyproject.toml"
      - ".github/workflows/compose-smoke.yml"

# AFTER:
    paths:
      - "docker/**"
      - "src/**"
      - "haro/**"
      - "weaver.py"
      - "pyproject.toml"
      - "alembic.ini"
      - ".github/workflows/compose-smoke.yml"
```

**Why**: `haro/**` changes affect the frontend Docker image build. `alembic.ini` changes affect migrations.

### 7.3 Change 2 — Capture container logs on failure

Add this step **before** the existing `Teardown` step:

```yaml
- name: Capture container logs
  if: failure()
  run: |
    docker compose -f docker/docker-compose.yml logs --no-color > /tmp/weaver_container_logs.out 2>&1 || true
```

### 7.4 Change 3 — Upload logs artifact on failure

Add this step **after** the `Teardown` step:

```yaml
- name: Upload failure logs
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: compose-smoke-logs
    path: /tmp/weaver_*.out
    retention-days: 7
```

**Step ordering** (final order in compose-smoke.yml):

```
... existing health check steps ...
- Capture container logs    ← NEW (if: failure(), runs BEFORE teardown to capture live containers)
- Teardown                  ← EXISTING (if: always())
- Upload failure logs       ← NEW (if: failure(), runs AFTER teardown, uploads saved files)
```

**Why this order matters**: The `Capture` step must run **before** `Teardown` because `docker compose logs` needs the containers to still exist. The `Upload` step can run after `Teardown` because it reads saved files from `/tmp/`, not from containers.

**Commit**: `ci(smoke): extend trigger paths and add failure artifact upload`

### 7.5 Verification

The compose-smoke workflow still works as before — the only difference is it now triggers on more paths and uploads artifacts if it fails. No behavioral change to existing passing logic.

---

## 8. M9-4: Branch Protection & Governance

### 8.1 Scope

Add a CI & Branch Protection section to `docs/DEVELOPMENT.md`. Uses **Option A** (documentation-only — manual setup via GitHub Settings UI).

### 8.2 Content to Add

Append the following section to `docs/DEVELOPMENT.md`:

```markdown
## CI & Branch Protection

### CI Workflows

| Workflow      | File                                  | Trigger Paths                                                            | Speed     | Job Name          |
| ------------- | ------------------------------------- | ------------------------------------------------------------------------ | --------- | ----------------- |
| Backend CI    | `.github/workflows/backend-ci.yml`    | `src/`, `tests/`, `pyproject.toml`, `weaver.py`, `alembic.ini`           | ~2 min    | `backend-checks`  |
| Frontend CI   | `.github/workflows/frontend-ci.yml`   | `haro/**`                                                                | ~2 min    | `frontend-checks` |
| Compose Smoke | `.github/workflows/compose-smoke.yml` | `docker/`, `src/`, `haro/`, `pyproject.toml`, `weaver.py`, `alembic.ini` | ~5-10 min | `compose-smoke`   |

All three workflows also trigger on `workflow_dispatch` (manual) and changes to their own YAML file.

### Branch Protection Setup (GitHub Settings)

Go to **Settings → Branches → Add branch protection rule**:

1. **Branch name pattern**: `main`
2. **Require status checks to pass before merging**: ✅
3. **Status checks that are required**:
   - `backend-checks`
   - `frontend-checks`
   - `compose-smoke`
4. **Require branches to be up to date before merging**: ✅
5. **Do not allow force pushes**: ✅
6. **Do not allow deletions**: ✅

### CI Troubleshooting

**Ruff format drift**: Run `ruff format src/ tests/` locally before pushing. If CI fails on format check, your editor may not be auto-formatting on save.

**MyPy strict errors**: All new code must have type annotations. If adding a new function, include full type annotations for all parameters and return type.

**ESLint unused imports**: Remove unused imports in test files. IDE auto-import sometimes adds unused imports that eslint catches.

**Compose smoke timeout**: The health check retries 60 times with 2-second intervals (2 min total). If the backend or frontend takes longer to boot, check the Docker build logs.

**Downloading failure artifacts**: When compose-smoke fails, go to the workflow run page → Artifacts section → download `compose-smoke-logs`. The ZIP contains container logs and HTTP response bodies.
```

**Commit**: `docs(ci): add branch protection and CI troubleshooting guide`

---

## 9. Exit Gate

### 9.1 Definition of Done

All items must pass for M9 to close:

- [ ] `ruff check src/ tests/` exits 0
- [ ] `ruff format --check src/ tests/` exits 0
- [ ] `mypy src/` exits 0
- [ ] `pytest -m "not container" --cov=src` exits 0 with coverage ≥ 80%
- [ ] `npx eslint .` (in `haro/`) exits 0
- [ ] `npx tsc -b --noEmit` (in `haro/`) exits 0
- [ ] `npm run test` (in `haro/`) exits 0
- [ ] `npm run build` (in `haro/`) exits 0
- [ ] `scripts/ci/check-local.sh` runs all checks locally and exits 0
- [ ] `backend-ci.yml` runs on PR and exits green
- [ ] `frontend-ci.yml` runs on PR and exits green
- [ ] `compose-smoke.yml` triggers on `haro/**` changes and uploads failure artifacts
- [ ] CI contract test (`test_ci_contract.py`) is green
- [ ] Branch protection requirements documented in `DEVELOPMENT.md`
- [ ] CI troubleshooting runbook documented in `DEVELOPMENT.md`
- [ ] All existing tests still pass: backend 940 + frontend 91 (no regressions)

### 9.2 Commit Sequence

| Order | Commit Message                                                           | Phase |
| ----- | ------------------------------------------------------------------------ | ----- |
| 1     | `fix(lint): apply ruff auto-fix and format to entire codebase`           | M9-0a |
| 2     | `fix(lint): resolve all ruff manual errors (57 fixes)`                   | M9-0b |
| 3     | `fix(types): resolve all mypy errors (34 fixes)`                         | M9-0c |
| 4     | `fix(lint): resolve all ESLint errors (16 fixes)`                        | M9-0d |
| 5     | `test(ci): add CI configuration contract tests`                          | M9-1  |
| 6     | `ci(backend): add fast CI workflow for ruff, mypy, pytest`               | M9-1  |
| 7     | `ci(local): add pre-push local CI check script`                          | M9-1  |
| 8     | `ci(frontend): add fast CI workflow for eslint, tsc, vitest, vite build` | M9-2  |
| 9     | `ci(smoke): extend trigger paths and add failure artifact upload`        | M9-3  |
| 10    | `docs(ci): add branch protection and CI troubleshooting guide`           | M9-4  |

### 9.3 Files Created

| File                                | Purpose                                                     |
| ----------------------------------- | ----------------------------------------------------------- |
| `.github/workflows/backend-ci.yml`  | Backend PR quality gate                                     |
| `.github/workflows/frontend-ci.yml` | Frontend PR quality gate                                    |
| `scripts/ci/check-local.sh`         | Local pre-push CI check (mirrors all GitHub Actions checks) |
| `tests/unit/test_ci_contract.py`    | CI configuration contract tests                             |

### 9.4 Files Modified

| File                                  | Change                                           |
| ------------------------------------- | ------------------------------------------------ |
| `src/**` and `tests/**` (many files)  | Ruff auto-fix + format + manual lint/type fixes  |
| `haro/eslint.config.js`               | Added `.vite` to `globalIgnores`                 |
| `haro/tests/**` (several test files)  | Removed unused imports, fixed ESLint errors      |
| `.github/workflows/compose-smoke.yml` | Extended trigger paths + failure artifact upload |
| `docs/DEVELOPMENT.md`                 | Added CI & Branch Protection section             |
| `docs/MILESTONE_PLAN.md`              | M9 status update                                 |
| `docs/architecture/roadmap.md`        | M9 status update                                 |

---

_Created: 2025-07-13_
_Verified against: ruff 0.15.2, mypy 1.19.1, pytest 9.0.2, ESLint 9.39.1, TypeScript 5.9.3, Vitest 4.0.18, Vite 7.3.1_
