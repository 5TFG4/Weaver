# Weaver Spec Deviation Analysis Report

> **Purpose**: Compare finalized system spec documents (docs/spec/) against actual code implementation and document all deviations.
> Each deviation notes the relevant code locations, spec requirements, current state, and severity.
>
> **Created**: 2026-04-01 (original version)
> **Updated**: 2026-04-02 (comprehensive rewrite after deep scan)
> **Reference**: `SYSTEM_SPEC.md`, `SPEC_BACKEND.md`, `SPEC_FRONTEND.md`, `SPEC_FLOWS.md`

---

## Table of Contents

1. [Run Model Structure Deviations](#1-run-model-structure-deviations)
2. [Strategy Interface Deviations](#2-strategy-interface-deviations)
3. [Strategy Metadata Deviations](#3-strategy-metadata-deviations)
4. [Strategy API Endpoint Deviations](#4-strategy-api-endpoint-deviations)
5. [Exchange Abstraction Layer Deviations](#5-exchange-abstraction-layer-deviations)
6. [Bar Data Model Deviations](#6-bar-data-model-deviations)
7. [Backtest Engine Deviations](#7-backtest-engine-deviations)
8. [Production Mode Resilience Deviations](#8-production-mode-resilience-deviations)
9. [Frontend Types & Component Deviations](#9-frontend-types--component-deviations)
10. [Pre-existing Functional Gaps (Retained)](#10-pre-existing-functional-gaps-retained)
11. [Full Deviation Summary Table](#11-full-deviation-summary-table)

---

## 1. Run Model Structure Deviations

**Spec Requirement** (SYSTEM_SPEC §2.2, SPEC_BACKEND §1.2):

- `symbols`, `timeframe`, `start_time`, `end_time` should all be moved from Run top-level fields into the `config` dictionary
- `config` should be a required field (`dict[str, Any]`), not nullable
- `RunCreate` should contain only three fields: `strategy_id`, `mode`, `config`

**Current Code**:

| Location                                           | Current State                                                                                                       | Deviation                                                                   |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `src/glados/schemas.py` RunCreate                  | `symbols: list[str]`, `timeframe: str`, `start_time`, `end_time` as top-level fields; `config: dict \| None = None` | Four fields should be moved into config; config should be required          |
| `src/glados/schemas.py` RunResponse                | Same: `symbols`, `timeframe` top-level; `config` optional                                                           | Same as above                                                               |
| `src/glados/services/run_manager.py` Run dataclass | `symbols`, `timeframe`, `start_time`, `end_time` as top-level attributes; `config: dict \| None`                    | Should all be inside config                                                 |
| `src/walle/models.py` RunRecord                    | `symbols` (JSONB nullable), `timeframe` (String nullable), `config` (JSONB nullable) as separate columns            | symbols/timeframe should be in config; config column should not be nullable |
| `src/glados/services/run_manager.py` create()      | Copies from `request.symbols`, `request.timeframe`, etc. individually to Run top-level                              | Should populate config dictionary                                           |

**Impact**: Architecture-level — Data structure inconsistency throughout the full stack; all frontend/backend API contracts need adjustment.

---

## 2. Strategy Interface Deviations

### 2.1 initialize() Signature

**Spec Requirement** (SYSTEM_SPEC §2.4, SPEC_BACKEND §2.1):

- `async def initialize(self, config: dict) -> None`

**Current Code**:

| Location                                                    | Current State                                                   | Deviation                     |
| ----------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------- |
| `src/marvin/base_strategy.py` BaseStrategy.initialize()     | `async def initialize(self, symbols: list[str]) -> None`        | Should accept `config: dict`  |
| `src/marvin/strategy_runner.py` StrategyRunner.initialize() | Calls `await self._strategy.initialize(symbols)`                | Should pass config dictionary |
| `src/glados/services/run_manager.py` \_start_backtest()     | `await runner.initialize(run_id=..., symbols=run.symbols, ...)` | Should pass run.config        |

### 2.2 Strategy Actions (StrategyAction)

**Spec Requirement** (SYSTEM_SPEC §2.6):

- Should have three ActionTypes: `FETCH_WINDOW`, `PLACE_ORDER`, `STOP_RUN`
- `FETCH_WINDOW` and `PLACE_ORDER` should include an optional `exchange: str | None` parameter

**Current Code**:

| Location                                        | Current State                                 | Deviation                              |
| ----------------------------------------------- | --------------------------------------------- | -------------------------------------- |
| `src/marvin/base_strategy.py` ActionType enum   | Only has `FETCH_WINDOW`, `PLACE_ORDER`        | Missing `STOP_RUN`                     |
| `src/marvin/base_strategy.py` StrategyAction    | No `exchange` field                           | Missing `exchange: str \| None = None` |
| `src/marvin/strategy_runner.py` \_emit_action() | Only handles `FETCH_WINDOW` and `PLACE_ORDER` | Does not handle `STOP_RUN`             |

**Impact**: Architecture-level — Strategy cannot proactively stop a run, nor specify a target exchange.

---

## 3. Strategy Metadata Deviations

**Spec Requirement** (SYSTEM_SPEC §2.3, SPEC_BACKEND §2.2):

- `STRATEGY_META` should include a `config_schema: dict | None` field (JSON Schema format)
- Frontend dynamically renders strategy configuration forms based on this schema

**Current Code**:

| Location                                                 | Current State                                                                                         | Deviation                         |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | --------------------------------- |
| `src/marvin/strategy_meta.py` StrategyMeta class         | Fields: `id`, `class_name`, `name`, `version`, `description`, `author`, `dependencies`, `module_path` | Missing `config_schema`           |
| `src/marvin/strategy_meta.py` from_dict()                | Does not parse `config_schema`                                                                        | Should parse it                   |
| `src/marvin/strategies/sma_strategy.py` STRATEGY_META    | No `config_schema` key                                                                                | Should have SMAConfig JSON Schema |
| `src/marvin/strategies/sample_strategy.py` STRATEGY_META | No `config_schema` key                                                                                | Should have config Schema         |

**Impact**: Important — Frontend cannot dynamically render configuration forms based on strategy type.

---

## 4. Strategy API Endpoint Deviations

**Spec Requirement** (SPEC_BACKEND §1.4):

- Should have a `GET /api/v1/strategies` endpoint that returns a list of all available strategy metadata

**Current Code**:

| Location                                         | Current State                                                        | Deviation                                 |
| ------------------------------------------------ | -------------------------------------------------------------------- | ----------------------------------------- |
| `src/glados/routes/` routes directory            | Routes: `/healthz`, `/runs`, `/orders`, `/candles`, `/events/stream` | No `/strategies` route                    |
| `src/glados/app.py` route registration           | Registers 5 routers — no strategies                                  | strategies router not registered          |
| `src/marvin/strategy_loader.py` list_available() | Returns `list[StrategyMeta]`, but not exposed via HTTP               | Backend capability exists but not exposed |

**Impact**: Important — Frontend cannot fetch strategy list, cannot implement dropdown selection.

---

## 5. Exchange Abstraction Layer Deviations

**Spec Requirement** (SYSTEM_SPEC §4.3, SPEC_BACKEND §3.1):

- Not bound to Alpaca — Alpaca is just one exchange adapter instance
- `VedaService` should manage multiple `ExchangeAdapter` instances (e.g., `adapters: dict[str, ExchangeAdapter]`)
- Factory should be exchange-agnostic, not hardcoding Alpaca

**Current Code**:

| Location                                                 | Current State                                                                 | Deviation                                                              |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `src/veda/interfaces.py` ExchangeAdapter                 | Abstract ABC exists                                                           | Compliant                                                              |
| `src/veda/adapters/` AlpacaAdapter, MockExchangeAdapter  | Plugin loader exists                                                          | Compliant                                                              |
| `src/veda/veda_service.py` VedaService.**init**()        | Accepts a single `adapter: ExchangeAdapter`                                   | Should manage multiple adapters `adapters: dict[str, ExchangeAdapter]` |
| `src/veda/adapters/factory.py` create_adapter_for_mode() | Hardcoded logic: has Alpaca credentials → AlpacaAdapter, else Mock            | Should be exchange-agnostic                                            |
| `src/glados/app.py` lifespan                             | Creates single adapter from Alpaca credentials → passes to single VedaService | Should support multi-exchange startup                                  |

**Impact**: Important — Underlying interfaces are correctly abstracted, but upper-layer wiring is still bound to a single exchange.

---

## 6. Bar Data Model Deviations

**Spec Requirement** (SYSTEM_SPEC §4.3, SPEC_FLOWS §5.3):

- Bar model should include an `exchange: str` field
- Unique constraint should include `exchange` to support multi-exchange data

**Current Code**:

| Location                                           | Current State                                                      | Deviation               |
| -------------------------------------------------- | ------------------------------------------------------------------ | ----------------------- |
| `src/walle/models.py` BarRecord                    | Columns: `symbol`, `timeframe`, `timestamp`, OHLCV — no `exchange` | Missing exchange column |
| `src/walle/models.py` unique constraint            | `UniqueConstraint("symbol", "timeframe", "timestamp")`             | Should include exchange |
| `src/walle/repositories/bar_repository.py` Bar DTO | No `exchange` field                                                | Missing                 |
| `src/veda/models.py` veda.Bar                      | No `exchange` field                                                | Missing                 |
| `src/glados/schemas.py` CandleResponse             | No `exchange` field                                                | Missing                 |

**Impact**: Important — Cannot distinguish data for the same trading pair from different exchanges. Requires migration.

---

## 7. Backtest Engine Deviations

**Spec Requirement** (SYSTEM_SPEC §3.2, SPEC_FLOWS §5.3):

- Backtesting should support on-demand data fetching from exchanges (cache miss → ExchangeAdapter → bars table → return)
- BacktestClock's time range should be read from `run.config`, not Run top-level fields

**Current Code**:

| Location                                                | Current State                                                                              | Deviation                                              |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| `src/greta/greta_service.py` initialize()               | `bars = await self._bar_repo.get_bars(...)` — preloads all bars from DB at startup         | Should support on-demand fetching on cache miss        |
| `src/greta/greta_service.py` constructor                | Only accepts `bar_repository: BarRepository`                                               | Should also accept ExchangeAdapter for on-demand fetch |
| `src/greta/greta_service.py`                            | No ExchangeAdapter reference                                                               | Missing on-demand fetch logic                          |
| `src/glados/services/run_manager.py` \_start_backtest() | `BacktestClock(start_time=run.start_time, end_time=run.end_time, timeframe=run.timeframe)` | Should read from `run.config`                          |
| `src/glados/services/run_manager.py` validation         | `if run.start_time is None or run.end_time is None: raise ...`                             | Should validate from config                            |

**Impact**: Architecture-level — Backtesting currently requires preloading all data, cannot fetch on demand, and time range is read from wrong location.

---

## 8. Production Mode Resilience Deviations

**Spec Requirement** (SYSTEM_SPEC §4.1):

- `InMemoryEventLog` should only be used for unit tests, should not appear in production app lifespan
- In production mode, DB is a required dependency

**Current Code**:

| Location                                  | Current State                                                                                    | Deviation                                              |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| `src/glados/app.py` lifespan else branch  | When `DB_URL` is not set: creates `InMemoryEventLog()`, logs "no-DB mode", app continues running | Production mode should refuse to start or be test-only |
| `src/events/log.py` InMemoryEventLog docs | Docs say "Not suitable for production", but app.py uses it in production                         | Documentation contradicts usage                        |

**Impact**: Important — Production deployment silently enters non-persistent mode if DB_URL is not configured, losing all events.

---

## 9. Frontend Types & Component Deviations

### 9.1 Type Definitions

**Spec Requirement** (SPEC_FRONTEND §2.1, §2.2):

- `Run` type should not have top-level `symbols`, `timeframe`; `config` should be required `Record<string, unknown>`
- `RunCreate` should only be `{ strategy_id, mode, config }`

**Current Code**:

| Location                          | Current State                                                                                | Deviation                                   |
| --------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `haro/src/api/types.ts` Run       | `symbols: string[]`, `timeframe: string` as top-level fields; `config` optional              | Should not have top-level symbols/timeframe |
| `haro/src/api/types.ts` RunCreate | Contains `symbols`, `timeframe`, `start_time`, `end_time` as extra fields; `config` optional | Should be strategy_id + mode + config only  |

### 9.2 Create Run Form

**Spec Requirement** (SPEC_FRONTEND §5.1):

- Strategy selection should be a dropdown (`<select>`), data sourced from `GET /api/v1/strategies`
- After selecting a strategy, dynamically render config fields based on `config_schema`
- Should not have separate Symbols / Timeframe fields

**Current Code**:

| Location                                                   | Current State                             | Deviation                                       |
| ---------------------------------------------------------- | ----------------------------------------- | ----------------------------------------------- |
| `haro/src/components/CreateRunForm.tsx` strategy selection | `<input>` free text input                 | Should be `<select>` dropdown                   |
| `haro/src/components/CreateRunForm.tsx` form fields        | Has separate Symbols and Timeframe fields | Should remove, replace with dynamic config form |
| `haro/src/components/CreateRunForm.tsx` config             | No dynamic config rendering               | Should render based on config_schema            |

### 9.3 Strategy API Layer

**Spec Requirement** (SPEC_FRONTEND §3.3, §4.3):

- Should have a `fetchStrategies()` API function
- Should have a `useStrategies()` React Query hook

**Current Code**:

| Location          | Current State           | Deviation          |
| ----------------- | ----------------------- | ------------------ |
| `haro/src/api/`   | No `strategies.ts` file | Completely missing |
| `haro/src/hooks/` | No `useStrategies` hook | Completely missing |

### 9.4 Run List Display

**Spec Requirement** (SPEC_FRONTEND §5.2):

- Run table should show a "Config" column (config summary), not a "Symbols" column

**Current Code**:

| Location                                            | Current State                    | Deviation                  |
| --------------------------------------------------- | -------------------------------- | -------------------------- |
| `haro/src/pages/RunsPage.tsx` header (~L135, ~L180) | Shows "Symbols" column header    | Should be "Config"         |
| `haro/src/pages/RunsPage.tsx` cell (~L213)          | Renders `run.symbols.join(", ")` | Should show config summary |

### 9.5 Dashboard Activity Feed

**Spec Requirement** (SPEC_FRONTEND §5.3):

- Recent activity should show strategy name + mode, not symbols

**Current Code**:

| Location                                         | Current State              | Deviation                        |
| ------------------------------------------------ | -------------------------- | -------------------------------- |
| `haro/src/components/ActivityFeed.tsx` (~L88-91) | Shows `symbols.join(", ")` | Should show strategy name + mode |

**Impact**: Full-stack level — Frontend types, API layer, and components all need to be aligned with the new spec.

---

## 10. Pre-existing Functional Gaps (Retained)

> The following are functional gaps discovered during the original review, not spec deviations, but they affect system usability.

### Blocking Issues

| #   | Gap                           | Component                | Description                                                                               |
| --- | ----------------------------- | ------------------------ | ----------------------------------------------------------------------------------------- |
| B1  | **No Start Button**           | Frontend (RunsPage)      | `useStartRun()` hook exists, backend endpoint exists, but UI has no trigger element       |
| B2  | **bars table is empty**       | Data Pipeline            | No data import script, backtest has no data available                                     |
| B3  | **Live/Paper uses mock data** | Veda / MarketDataService | `MockMarketDataService` returns fake data, strategy places real orders based on fake data |

### Important Gaps

| #   | Gap                                | Component             | Description                                                           |
| --- | ---------------------------------- | --------------------- | --------------------------------------------------------------------- |
| I1  | No Order Sync UI                   | Frontend (OrdersPage) | Backend `POST /orders/{id}/sync` exists but no UI button              |
| I2  | No Cancel Order UI                 | Frontend (OrdersPage) | `useCancelOrder()` hook exists but no UI button                       |
| I3  | No Backtest Result API             | Backend               | `BacktestResult` is computed then discarded, no endpoint to return it |
| I4  | No Backtest Result UI              | Frontend              | No equity curve chart, statistics table, or trade list                |
| I5  | No Fill Confirmation Loop          | Veda                  | After submitting an order, no auto-polling/WebSocket to detect fills  |
| I6  | Candles endpoint returns fake data | Backend               | `GET /api/v1/candles` uses MockMarketDataService                      |

### Minor Issues

| #   | Gap                                    | Component        |
| --- | -------------------------------------- | ---------------- |
| N1  | Run detail page (orders/events/equity) | Frontend         |
| N2  | Settings page (credentials/DB status)  | Frontend         |
| N3  | Event log viewer                       | Frontend         |
| N4  | Candlestick chart component            | Frontend         |
| N5  | Strategy validation on Run creation    | Backend          |
| N6  | Configurable backtest initial capital  | Backend/Frontend |
| N7  | Exchange position sync                 | Veda             |

---

## 11. Full Deviation Summary Table

### Spec Deviations (Code vs Finalized Design)

| #   | Spec Decision                        | Status              | Core Gap                                                                           | Severity     |
| --- | ------------------------------------ | ------------------- | ---------------------------------------------------------------------------------- | ------------ |
| S1  | Run `config` structure refactor      | Violated            | `symbols`/`timeframe`/`start_time`/`end_time` still top-level; config optional     | Architecture |
| S2  | `initialize(config: dict)` signature | Violated            | Current signature is `initialize(symbols: list[str])`                              | Architecture |
| S3  | `STOP_RUN` action + `exchange` param | Violated            | No STOP_RUN; StrategyAction has no exchange field                                  | Architecture |
| S4  | `config_schema` metadata             | Violated            | StrategyMeta and all STRATEGY_META lack config_schema                              | Important    |
| S5  | Multi-exchange adapters              | Partially compliant | ABC correct; VedaService holds single adapter, factory hardcodes Alpaca            | Important    |
| S6  | `GET /api/v1/strategies` endpoint    | Violated            | Endpoint does not exist (backend capability exists but not exposed)                | Important    |
| S7  | Backtest on-demand data fetching     | Violated            | Greta only preloads from DB; no ExchangeAdapter fallback                           | Architecture |
| S8  | InMemoryEventLog test-only           | Violated            | app.py lifespan uses InMemoryEventLog when DB_URL is absent                        | Important    |
| S9  | Clock reads time range from config   | Partially compliant | RealtimeClock correct (never auto-stops); BacktestClock reads Run top-level fields | Important    |
| S10 | Bar model `exchange` field           | Violated            | BarRecord, Bar DTO, veda.Bar, CandleResponse all missing exchange                  | Important    |
| S11 | Frontend Run/RunCreate types         | Violated            | Contains extra top-level fields; config optional                                   | Full-stack   |
| S12 | Frontend strategy dropdown           | Violated            | Free text input instead of select dropdown                                         | Important    |
| S13 | Frontend Strategies API layer        | Violated            | fetchStrategies(), useStrategies() completely missing                              | Important    |
| S14 | Frontend Run table Config column     | Violated            | Shows "Symbols" instead of "Config" summary                                        | Important    |
| S15 | Frontend Dashboard activity display  | Violated            | Shows symbols instead of strategy name + mode                                      | Minor        |

### Recommended Fix Priority

**First Priority — Architecture-level Refactoring (S1 → S2 → S3 → S7)**:

1. **S1** Run config structure → all subsequent changes depend on this
2. **S2** initialize() signature → affected by S1
3. **S3** STOP_RUN + exchange → core strategy capability
4. **S7** Backtest on-demand fetching → makes backtesting truly usable

**Second Priority — Feature Completion (S4 → S6 → S12 → S13 → S11)**: 5. **S4** config_schema → prerequisite for S12 6. **S6** GET /strategies endpoint → prerequisite for S12/S13 7. **S13** Frontend Strategies API layer 8. **S12** Strategy dropdown selection 9. **S11** Frontend type alignment

**Third Priority — Multi-exchange & Data (S5 → S10 → S8 → S9 → S14 → S15)**: 10. **S5** VedaService multi-adapter 11. **S10** Bar exchange field (requires migration) 12. **S8** Remove production InMemoryEventLog 13. **S9** BacktestClock reads time from config 14. **S14** Frontend Run table Config column 15. **S15** Dashboard activity display
