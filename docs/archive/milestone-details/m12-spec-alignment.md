# M12: Spec Alignment — Design Framework & Decision Points

> **Document Charter**
> **Primary role**: M12 milestone design framework — options analysis for decision-making.
> **Status**: � DECISIONS LOCKED — All 10 decision points resolved. Ready for detailed planning.
> **Prerequisite**: M11 ✅ (1137 total tests)
> **Key Input**: `PROD_TEST_REVIEW.md` (15 spec deviations: S1–S15)
> **Branch**: `m12-spec-alignment`

---

## Table of Contents

1. [Current State Summary](#1-current-state-summary)
2. [Scope: M12 vs M13 Split](#2-scope-m12-vs-m13-split)
3. [Dependency Graph](#3-dependency-graph)
4. [Phase 1: Run Config Refactor (S1)](#4-phase-1-run-config-refactor-s1)
5. [Phase 2: Strategy Interface Refactor (S2 + S3)](#5-phase-2-strategy-interface-refactor-s2--s3)
6. [Phase 3: Strategy Metadata & API (S4 + S6)](#6-phase-3-strategy-metadata--api-s4--s6)
7. [Phase 4: Production Safety (S8)](#7-phase-4-production-safety-s8)
8. [Phase 5: Backtest Config Source (S9)](#8-phase-5-backtest-config-source-s9)
9. [Phase 6: Frontend Full-stack Alignment (S11–S15)](#9-phase-6-frontend-full-stack-alignment-s11-s15)
10. [Deferred to M13: Multi-Exchange & Bar Exchange (S5 + S10 + S7)](#10-deferred-to-m13-multi-exchange--bar-exchange-s5--s10--s7)
11. [TDD Execution Strategy](#11-tdd-execution-strategy)
12. [Risk Assessment](#12-risk-assessment)
13. [Estimated Test Impact](#13-estimated-test-impact)

---

## 1. Current State Summary

### 1.1 Test Totals (Post-M11)

| Category         | Tests    | Coverage |
| ---------------- | -------- | -------- |
| Backend unit     | 946      | ~90%     |
| Integration      | 50       | -        |
| Frontend unit    | 108      | ~95%     |
| E2E (Playwright) | 33       | -        |
| **Total**        | **1137** | -        |

### 1.2 Deviation Summary

15 spec deviations documented in `PROD_TEST_REVIEW.md`:

- **Architecture-level (4)**: S1, S2, S3, S7
- **Important (8)**: S4, S5, S6, S8, S9, S10, S12, S13
- **Full-stack (2)**: S11, S14
- **Minor (1)**: S15

### 1.3 Blast Radius Analysis

The Run config refactor (S1) is the foundation — it touches:

- **Backend**: 7 test files referencing `RunCreate` directly, 31 test files referencing `symbols`/`timeframe`
- **Frontend**: 5 test files referencing `symbols`
- **E2E**: 5 test files (backtest_flow, paper_flow, navigation, orders, sse)
- **Database**: Requires Alembic migration (6th migration)

---

## 2. Scope: M12 vs M13 Split

### What goes into M12 (this milestone)

| #   | Deviation                            | Rationale for M12                                |
| --- | ------------------------------------ | ------------------------------------------------ |
| S1  | Run `config` structure refactor      | Foundation — everything else depends on it       |
| S2  | `initialize(config: dict)` signature | Direct consequence of S1                         |
| S3  | `STOP_RUN` action + `exchange` param | Small additive change, no deps on multi-exchange |
| S4  | `config_schema` metadata             | Prerequisite for frontend strategy dropdown      |
| S6  | `GET /api/v1/strategies` endpoint    | Prerequisite for frontend strategy dropdown      |
| S8  | InMemoryEventLog test-only           | Small safety fix, no deps                        |
| S9  | BacktestClock reads from config      | Direct consequence of S1                         |
| S11 | Frontend Run/RunCreate types         | Direct consequence of S1                         |
| S12 | Frontend strategy dropdown           | Depends on S4+S6                                 |
| S13 | Frontend Strategies API layer        | Depends on S6                                    |
| S14 | Frontend Run table Config column     | Direct consequence of S11                        |
| S15 | Frontend Dashboard activity display  | Small UI tweak                                   |

### What is deferred to M13 — and why

| #   | Deviation                                  | Rationale for M13                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S5  | Multi-exchange adapters (VedaService dict) | **Reason**: This is a significant architectural change to VedaService, OrderManager, and the entire order routing pipeline. Currently only Alpaca is implemented. Changing VedaService from `adapter: ExchangeAdapter` to `adapters: dict[str, ExchangeAdapter]` cascades into order routing, position tracking, the factory, and app lifespan wiring. No user-facing feature depends on this in the current sprint. Also, the existing M12 backlog item "Multi-exchange support" was already marked as deferred. |
| S10 | Bar model `exchange` field                 | **Reason**: Tightly coupled with S5. Adding `exchange` to Bar is only useful once multi-exchange routing exists. Requires a DB migration that changes the unique constraint on the `bars` table. Without multi-exchange in VedaService, the field would always be a constant (e.g., "alpaca") — no value. Better to do S5+S10 together in M13.                                                                                                                                                                    |
| S7  | Backtest on-demand data fetching           | **Reason**: This requires GretaService to accept an `ExchangeAdapter` for fallback fetching. This is tightly coupled with S5 (multi-exchange) because the on-demand fetch needs to know _which_ exchange to query. Also requires network I/O during backtest (significant architectural shift from pure-local simulation). This was already flagged as "Requires Greta/WallE architectural changes" in the original backlog.                                                                                      |

### Backlog items shifted to M13+

The existing deferred backlog items (E-3, R-1, R-2) move behind M12:

- E-3: Pagination/filtering E2E → M13+
- R-1: Connection resilience → M13+
- R-2: Multi-symbol backtests → M13+

---

## 3. Dependency Graph

```
S1 (Run config refactor) ──────────────────────────────────────┐
    │                                                          │
    ├── S2 (initialize(config)) ─── depends on S1             │
    │                                                          │
    ├── S9 (BacktestClock from config) ─── depends on S1      │
    │                                                          │
    ├── S11 (Frontend types) ─── depends on S1                │
    │       │                                                  │
    │       ├── S14 (Run table Config column) ─── depends S11 │
    │       │                                                  │
    │       └── S15 (Dashboard activity) ─── depends S11      │
    │                                                          │
    S3 (STOP_RUN + exchange) ─── independent                  │
    │                                                          │
    S4 (config_schema) ─── independent                        │
    │                                                          │
    S6 (GET /strategies endpoint) ─── independent             │
    │       │                                                  │
    │       ├── S13 (Frontend Strategies API) ─── depends S6  │
    │       │                                                  │
    │       └── S12 (Strategy dropdown) ── depends S4+S6+S13  │
    │                                                          │
    S8 (InMemoryEventLog test-only) ─── independent           │
    │                                                          │
    └──────────────────────────────────────────────────────────┘

M13 (deferred):
    S5 (Multi-exchange VedaService)
    S10 (Bar exchange field) ─── depends S5
    S7 (Backtest on-demand fetch) ─── depends S5
```

### Proposed Execution Phases

```
Phase 1: S1 (Run config refactor)          ← foundation, highest blast radius
Phase 2: S2 + S3 (Strategy interface)      ← depends on S1
Phase 3: S4 + S6 (Metadata + API)          ← independent, can parallel with Phase 2
Phase 4: S8 (Production safety)            ← independent, small
Phase 5: S9 (BacktestClock config source)  ← depends on S1
Phase 6: S11-S15 (Frontend alignment)      ← depends on S1 + S6
```

---

## 4. Phase 1: Run Config Refactor (S1)

> This is the highest-impact change. Every other phase depends on this.

### 4.1 Current State (verified)

```python
# RunCreate schema
class RunCreate(BaseModel):
    strategy_id: str
    mode: RunMode
    symbols: list[str]           # ← move to config
    timeframe: str = "1m"        # ← move to config
    start_time: datetime | None  # ← move to config
    end_time: datetime | None    # ← move to config
    config: dict | None = None   # ← make required

# Run dataclass (RunManager)
@dataclass
class Run:
    symbols: list[str]           # ← move to config
    timeframe: str               # ← move to config
    config: dict | None          # ← make required
    start_time: datetime | None  # ← move to config
    end_time: datetime | None    # ← move to config

# RunRecord (DB model)
symbols: JSONB nullable          # ← remove column
timeframe: String nullable       # ← remove column
config: JSONB nullable           # ← make NOT NULL

# RunResponse
symbols: list[str]               # ← remove
timeframe: str                   # ← remove
config: dict | None              # ← make required
```

### 4.2 Decision Point D-1: Migration Strategy

**Option A: Big Bang (one migration, one commit)**

- Single Alembic migration: drop `symbols`/`timeframe` columns from `runs`, alter `config` to NOT NULL
- Update all Python code in one pass
- Update all tests in one pass

| Pros                           | Cons                                                       |
| ------------------------------ | ---------------------------------------------------------- |
| Clean, no transitional code    | High blast radius in single commit                         |
| No backward compatibility code | Have to update ~31 backend + 5 frontend test files at once |
| Simpler final state            | Harder to review / debug if something breaks               |

**Option B: Phased Migration (two migrations, backward-compatible intermediate step)**

1. **Migration 1**: Add `config` NOT NULL with server_default `'{}'::jsonb`. Keep `symbols`/`timeframe` columns. Write code that writes to BOTH places (dual-write).
2. **Migration 2** (same milestone, later phase): Drop `symbols`/`timeframe` columns, remove dual-write code.

| Pros                            | Cons                                      |
| ------------------------------- | ----------------------------------------- |
| Smaller per-commit blast radius | Extra transitional code that gets deleted |
| Can verify step-by-step         | Two migrations instead of one             |
| Safer rollback at each step     | More complexity during transition         |

**Option C: Shadow Migration (write to config, read from config, keep old columns as deprecated)**

- Add `config` as primary, keep `symbols`/`timeframe` columns populated but never read from them
- Drop them in a future M13 cleanup

| Pros                      | Cons                      |
| ------------------------- | ------------------------- |
| Very safe, nothing breaks | Dead columns in DB        |
| Can verify gradually      | Tech debt carried forward |

**Recommendation**: **Option A** — We're in a dev environment with no production data. There's no user base relying on the old schema. The blast radius is manageable because we have 1137 existing tests as a safety net. One clean cut is better than maintaining transitional code.

### 4.3 Decision Point D-2: Config Access Pattern

How do other parts of the code access `symbols`, `timeframe`, `start_time`, `end_time` from the Run?

**Option A: Direct dict access**

```python
symbols = run.config["symbols"]
timeframe = run.config["timeframe"]
```

| Pros                          | Cons                              |
| ----------------------------- | --------------------------------- |
| Simplest, no new abstractions | No type safety, KeyError possible |
| Matches spec literally        | Repeated dict access everywhere   |

**Option B: Helper methods on Run**

```python
@dataclass
class Run:
    config: dict[str, Any]

    @property
    def symbols(self) -> list[str]:
        return self.config.get("symbols", [])

    @property
    def timeframe(self) -> str:
        return self.config.get("timeframe", "1m")
```

| Pros                            | Cons                                              |
| ------------------------------- | ------------------------------------------------- |
| Type-safe convenience accessors | Looks like the old interface — could be confusing |
| Backward compatible callsites   | Extra code to maintain                            |
| IDE autocompletion works        | Hides the actual data location                    |

**Option C: Typed Config dataclass extracted at the callsite**

```python
# Each consumer extracts what it needs:
@dataclass
class BacktestConfig:
    symbols: list[str]
    timeframe: str
    start_time: datetime
    end_time: datetime
    initial_cash: Decimal = Decimal("100000")

    @classmethod
    def from_dict(cls, d: dict) -> "BacktestConfig":
        ...
```

| Pros                              | Cons                                      |
| --------------------------------- | ----------------------------------------- |
| Full type safety                  | Extra classes per consumer                |
| Validation at boundary            | More code                                 |
| Each consumer declares its schema | Slight over-engineering for current needs |

**Recommendation**: **Option A** — Direct dict access. The spec explicitly says config is an opaque `dict[str, Any]` that strategies own. Adding typed wrappers would contradict the design principle that config is strategy-controlled. If run_manager needs `start_time`/`end_time` for backtest, it can do `run.config["backtest_start"]`. Validation happens once (in create()) and that's sufficient.

### 4.4 Decision Point D-3: DB Migration — Column Handling

**Option A: Drop columns entirely**

- Remove `symbols` and `timeframe` from `RunRecord`
- Single `config JSONB NOT NULL` column holds everything

| Pros                 | Cons                       |
| -------------------- | -------------------------- |
| Clean schema         | Requires migration         |
| Matches spec exactly | Any existing dev data lost |

**Option B: Keep columns, mark deprecated, stop reading**

- Column stays in DB but is never written/read
- Remove from ORM model

| Pros                     | Cons                        |
| ------------------------ | --------------------------- |
| No migration needed      | Dead columns clutter schema |
| Zero risk of data issues | Confusing for future devs   |

**Recommendation**: **Option A** — Clean schema. This is a dev-only database, no production data at risk. The 5 existing migrations show the project has a healthy migration practice.

---

## 5. Phase 2: Strategy Interface Refactor (S2 + S3)

### 5.1 S2: initialize(config: dict)

**Current**: `async def initialize(self, symbols: list[str]) -> None`
**Target**: `async def initialize(self, config: dict) -> None`

### 5.2 Decision Point D-4: BaseStrategy.initialize() Signature

**Option A: Pure config dict**

```python
async def initialize(self, config: dict) -> None:
    self._symbols = config.get("symbols", [])
```

| Pros                 | Cons                                 |
| -------------------- | ------------------------------------ |
| Matches spec exactly | Strategies need to know config keys  |
| Maximum flexibility  | No autocompletion for config content |

**Option B: config dict + typed helper mixin**

```python
class ConfigMixin:
    def get_symbols(self, config: dict) -> list[str]: ...
    def get_timeframe(self, config: dict) -> str: ...
```

| Pros                          | Cons                   |
| ----------------------------- | ---------------------- |
| Convenience helpers available | Extra mixin class      |
| Still accepts raw dict        | Maintenance of helpers |

**Recommendation**: **Option A** — Pure config dict. Strategies are simple enough that `config["symbols"]` is clear. The `config_schema` metadata (S4) will document what keys each strategy expects.

### 5.3 S3: STOP_RUN Action + exchange Parameter

**Current**: ActionType has `FETCH_WINDOW`, `PLACE_ORDER`
**Target**: Add `STOP_RUN`; add `exchange: str | None = None` to `StrategyAction`

### 5.4 Decision Point D-5: STOP_RUN Implementation

**Option A: Strategy returns STOP_RUN action → StrategyRunner emits event → RunManager handles**

```python
# In StrategyRunner._emit_action():
elif action.type == ActionType.STOP_RUN:
    await self._event_log.append(Envelope(type="run.StopRequested", ...))

# RunManager subscribes to run.StopRequested → calls stop()
```

| Pros                                       | Cons                             |
| ------------------------------------------ | -------------------------------- |
| Event-driven, consistent with architecture | Extra event type to define       |
| Audit trail in outbox                      | Latency (event → handler → stop) |
| RunManager stays in control                | Slightly more complex            |

**Option B: Strategy returns STOP_RUN action → StrategyRunner directly calls a callback**

```python
# StrategyRunner accepts a stop_callback in initialize()
elif action.type == ActionType.STOP_RUN:
    await self._stop_callback(self._run_id)
```

| Pros                        | Cons                                     |
| --------------------------- | ---------------------------------------- |
| Simpler, fewer moving parts | No audit trail                           |
| Immediate effect            | Tight coupling StrategyRunner→RunManager |

**Recommendation**: **Option A** — Event-driven. This is consistent with Weaver's event-sourced architecture. The `run.StopRequested` event goes into the outbox, providing auditability. RunManager handles it like any other state transition.

### 5.5 Decision Point D-6: Exchange Parameter Scope

The `exchange` field on `StrategyAction` — what does it do before multi-exchange (S5) is implemented?

**Option A: Add field, validate but ignore until M13**

- Add `exchange: str | None = None` to `StrategyAction`
- If set, log a warning: "Multi-exchange routing not yet implemented, ignoring exchange parameter"
- Actual routing happens in M13 when VedaService supports multiple adapters

| Pros                    | Cons                          |
| ----------------------- | ----------------------------- |
| Interface ready for M13 | Warning may confuse users     |
| No fake implementation  | Field exists but doesn't work |

**Option B: Add field, route to default adapter if None, raise if explicit**

- If `exchange=None` → route to default adapter (current behavior)
- If `exchange="alpaca"` → route to default adapter (happens to be Alpaca)
- If `exchange="binance"` → raise `ExchangeNotConfigured` error

| Pros                 | Cons                                      |
| -------------------- | ----------------------------------------- |
| Validates early      | More code for error paths                 |
| Clear error messages | Still doesn't route to multiple exchanges |

**Option C: Add field to dataclass only, don't pass through to events yet**

- `StrategyAction.exchange` exists in the dataclass
- `_emit_fetch_window()` and `_emit_place_request()` don't include it in the event payload
- M13 adds it to event payload when routing is ready

| Pros              | Cons                              |
| ----------------- | --------------------------------- |
| Minimal change    | Field silently ignored            |
| No false promises | No error on invalid exchange name |

**Recommendation**: **Option C** — Add the field to the dataclass but don't wire it into event payloads yet. This matches the spec interface while avoiding half-implementations. M13 will wire it properly when multi-exchange routing lands.

---

## 6. Phase 3: Strategy Metadata & API (S4 + S6)

### 6.1 S4: config_schema in StrategyMeta

**Current**: StrategyMeta has no `config_schema` field.
**Target**: Add `config_schema: dict | None = None` to StrategyMeta.

### 6.2 Decision Point D-7: config_schema Format

**Option A: JSON Schema (standard)**

```python
"config_schema": {
    "type": "object",
    "properties": {
        "symbols": {"type": "array", "items": {"type": "string"}},
        "timeframe": {"type": "string", "default": "1h", "enum": ["1m","5m","15m","1h","4h","1d"]},
        "fast_period": {"type": "integer", "default": 10, "minimum": 1},
        "slow_period": {"type": "integer", "default": 20, "minimum": 1},
    },
    "required": ["symbols"]
}
```

| Pros                                        | Cons                              |
| ------------------------------------------- | --------------------------------- |
| Industry standard                           | Verbose                           |
| Libraries exist for validation (jsonschema) | Overkill for current 2 strategies |
| Frontend can use react-jsonschema-form      | Learning curve                    |

**Option B: Simple custom format (as shown in spec)**

```python
"config_schema": {
    "symbols": {"type": "list[str]", "required": True},
    "timeframe": {"type": "str", "default": "1h"},
    "fast_period": {"type": "int", "default": 10},
    "slow_period": {"type": "int", "default": 20},
}
```

| Pros                  | Cons                          |
| --------------------- | ----------------------------- |
| Matches spec exactly  | Non-standard format           |
| Simpler to read/write | Need custom frontend renderer |
| Minimal code          | No validation library support |

**Option C: Pydantic model reference**

```python
"config_schema": SMAConfig.model_json_schema()  # Auto-generate from Pydantic model
```

| Pros                           | Cons                                       |
| ------------------------------ | ------------------------------------------ |
| Auto-generated, always in sync | Strategies must define Pydantic models     |
| Full JSON Schema output        | Can't use AST extraction (needs import)    |
| Rich validation                | Breaks plugin loader's AST-only constraint |

**Decision**: **Option A — JSON Schema**. Although we currently only have 2 strategies, the project will scale. Using JSON Schema from the start means:

- No format migration later
- Backend can validate configs via the `jsonschema` library
- Frontend can use `react-jsonschema-form` (see D-10) — zero custom rendering code
- Each strategy's `STRATEGY_META` dict includes a standard `config_schema` in JSON Schema format

Example for SMA strategy:

```python
"config_schema": {
    "type": "object",
    "properties": {
        "symbols": {"type": "array", "items": {"type": "string"}},
        "timeframe": {"type": "string", "default": "1h",
                      "enum": ["1m","5m","15m","1h","4h","1d"]},
        "fast_period": {"type": "integer", "default": 10, "minimum": 1},
        "slow_period": {"type": "integer", "default": 20, "minimum": 1},
    },
    "required": ["symbols"]
}
```

**Implementation notes**:

- Add `jsonschema` to `requirements.txt` for backend config validation in `RunManager.create()`
- `StrategyMeta.config_schema` type: `dict | None = None` (None for strategies without schema)
- `StrategyMeta.from_dict()` reads `data.get("config_schema")` — no AST issue since it's a plain dict literal

### 6.3 S6: GET /api/v1/strategies Endpoint

Straightforward implementation:

1. Create `src/glados/routes/strategies.py`
2. Inject `PluginStrategyLoader` via FastAPI dependency
3. Return `list[StrategyMetaResponse]` (Pydantic schema with `config_schema: dict | None`)
4. Register router in `app.py`
5. Response includes `config_schema` so the frontend can render dynamic forms

No design alternatives needed — this is standard REST endpoint creation.

---

## 7. Phase 4: Production Safety (S8)

### 7.1 Decision Point D-8: How to Handle Missing DB_URL

**Option A: Refuse to start (hard fail)**

```python
if not db_url:
    raise RuntimeError("DB_URL environment variable is required")
```

| Pros                         | Cons                                      |
| ---------------------------- | ----------------------------------------- |
| Impossible to run without DB | Breaks developer quick-start              |
| Matches spec literally       | Need DB even for `--help` or health check |
| Clear error message          | E2E test startup may need adjustment      |

**Option B: Refuse to start in production, allow in dev mode**

```python
if not db_url:
    if os.environ.get("WEAVER_ENV") == "development":
        logger.warning("No DB — running in dev/test mode with InMemoryEventLog")
        ...
    else:
        raise RuntimeError("DB_URL required in production")
```

| Pros                        | Cons                  |
| --------------------------- | --------------------- |
| Safe in production          | New env var to manage |
| Still works for dev/testing | Slightly more complex |

**Option C: Always require DB, provide docker-compose dev DB**

- Remove InMemoryEventLog from app.py entirely
- Dev docker-compose always starts a PostgreSQL (already does)
- Unit tests continue to use InMemoryEventLog directly (not via app.py)

| Pros                                | Cons                                         |
| ----------------------------------- | -------------------------------------------- |
| Cleanest: prod code = dev code      | Must always have DB running                  |
| InMemoryEventLog stays test-only    | Docker required even for basic dev           |
| No conditional branches in lifespan | Already the case with docker-compose.dev.yml |

**Recommendation**: **Option C** — Always require DB in app.py. The dev environment already runs PostgreSQL via docker-compose.dev.yml. InMemoryEventLog is only needed in unit tests (which don't go through app.py). This is the cleanest separation.

---

## 8. Phase 5: Backtest Config Source (S9)

### 8.1 Current State

```python
# In _start_backtest():
BacktestClock(start_time=run.start_time, end_time=run.end_time, timeframe=run.timeframe)
```

### 8.2 Target (after S1)

```python
BacktestClock(
    start_time=datetime.fromisoformat(run.config["backtest_start"]),
    end_time=datetime.fromisoformat(run.config["backtest_end"]),
    timeframe=run.config.get("timeframe", "1m"),
)
```

No design decision needed — this is a direct consequence of S1. The config keys follow the spec's config examples (`backtest_start`, `backtest_end`).

### 8.3 Decision Point D-9: Config Key Names for Backtest Time Range

**Option A: `backtest_start` / `backtest_end`** (matches spec examples)
**Option B: `start_time` / `end_time`** (matches current field names)
**Option C: `start` / `end`** (shortest)

**Recommendation**: **Option A** — `backtest_start` / `backtest_end`. These are specific to backtest mode and should be clearly named to avoid confusion with other time fields a strategy might use.

---

## 9. Phase 6: Frontend Full-stack Alignment (S11–S15)

### 9.1 S11: Frontend Types

Direct consequence of S1. After backend API changes:

```typescript
// types.ts — new Run
export interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  config: Record<string, unknown>; // required, not optional
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

// types.ts — new RunCreate
export interface RunCreate {
  strategy_id: string;
  mode: RunMode;
  config: Record<string, unknown>; // required
}
```

### 9.2 S12: Strategy Dropdown

Depends on S6 (backend endpoint) + S4 (config_schema) + S13 (API layer).

### 9.3 Decision Point D-10: Dynamic Config Form Rendering

After selecting a strategy, the form should render config fields based on `config_schema`. How?

**Option A: Simple hardcoded renderer for known types**

```tsx
function ConfigField({ name, schema }: { name: string; schema: FieldSchema }) {
  if (schema.type === "list[str]")
    return <input placeholder="comma-separated" />;
  if (schema.type === "int") return <input type="number" />;
  if (schema.type === "str") return <input type="text" />;
  // etc.
}
```

| Pros                                                | Cons                       |
| --------------------------------------------------- | -------------------------- |
| Simple, no dependencies                             | Limited to known types     |
| Full control over rendering                         | Manual mapping code        |
| Works with custom schema format (Option B from D-7) | Needs update for new types |

**Option B: JSON Schema form library (react-jsonschema-form)**

| Pros                         | Cons                                            |
| ---------------------------- | ----------------------------------------------- |
| Feature-rich out of the box  | Heavy dependency                                |
| Handles validation, defaults | Requires JSON Schema format (Option A from D-7) |
| Well-maintained              | Styling integration effort                      |

**Decision**: **Option B — react-jsonschema-form (RJSF)**. Since D-7 chose JSON Schema, RJSF is the natural pairing:

- Zero custom rendering code — RJSF auto-generates forms from JSON Schema
- Built-in validation, defaults handling, required field markers
- Well-maintained: `@rjsf/core` + `@rjsf/utils` + `@rjsf/validator-ajv8`
- Theming: use `@rjsf/core` with custom widgets to match existing UI style

**Implementation notes**:

- Install: `npm install @rjsf/core @rjsf/utils @rjsf/validator-ajv8`
- In `CreateRunForm.tsx`: after strategy selection, fetch `config_schema` from the strategy, pass to `<Form schema={configSchema} validator={validator} />`
- RJSF outputs the config as a plain object → pass directly as `RunCreate.config`
- Custom widgets may be needed for `symbols` (array of strings → tag input or comma-separated)
- Tests: mock `config_schema` in tests, verify form renders correct fields

### 9.4 S13–S15: Remaining Frontend

- **S13**: Create `haro/src/api/strategies.ts` + `haro/src/hooks/useStrategies.ts` — standard pattern matching existing `runs.ts` / `useRuns.ts`. The `StrategyMeta` type includes `config_schema: Record<string, unknown> | null`.
- **S14**: Change RunsPage table column from "Symbols" → "Config" with summary (e.g., `JSON.stringify(config).slice(0, 50)`)
- **S15**: Change ActivityFeed from `symbols.join(",")` → `strategy_id (mode)`

No design decisions needed for these.

---

## 10. Deferred to M13: Multi-Exchange & Bar Exchange (S5 + S10 + S7)

### M13 Scope Preview

| #   | Task                       | Description                                                                               | Estimated Effort |
| --- | -------------------------- | ----------------------------------------------------------------------------------------- | ---------------- |
| S5  | Multi-exchange VedaService | Change `adapter` → `adapters: dict`, update OrderManager, update factory, update lifespan | 2-3 days         |
| S10 | Bar `exchange` field       | Add column + migration, update DTO, update unique constraint                              | 1 day            |
| S7  | Backtest on-demand fetch   | GretaService accepts ExchangeAdapter, cache-miss logic, async fetch during backtest       | 2-3 days         |
| E-3 | Pagination E2E tests       | Deferred from M11                                                                         | 0.5 day          |
| R-1 | Connection resilience      | Retry/circuit-breaker                                                                     | 2 days           |
| R-2 | Multi-symbol backtests     | Greta/WallE changes                                                                       | 2 days           |

---

---

---

# Part II: Detailed TDD Implementation Plan

> All decisions locked. Below is the step-by-step execution plan — follow in order.
> Notation: 🔴 = Red (write failing test) → 🟢 = Green (implement) → 🔵 = Blue (refactor/cleanup)

---

## Phase 1: Run Config Refactor (S1)

> **Goal**: Move `symbols`, `timeframe`, `start_time`, `end_time` from top-level fields into `config: dict`. Make `config` required (not optional). Drop DB columns.
> **Blast radius**: ~43 files (31 backend, 5 frontend, 5 E2E, 2 integration)

### Step 1.1 — Update `RunFactory` test helper

> This is the shared factory used by ~20 test files. Updating it first ensures all downstream tests use the new shape.

**File**: `tests/factories/runs.py` (317 lines)

**🔴 Red**: No new test file — RunFactory is a helper, not tested directly. Change the factory so it **produces** the new config-based shape. All existing callers will break (Red).

**🟢 Green — changes**:

```python
# Current RunFactory fields:
_timeframe: str = "1m"
_symbols: list[str] | None = None
_backtest_start: datetime | None = None
_backtest_end: datetime | None = None

# New: remove _timeframe, _symbols, _backtest_start, _backtest_end as separate fields.
# Replace with _config: dict[str, Any] that always contains symbols, timeframe, etc.
```

Exact changes to `RunFactory`:

1. Remove fields: `_timeframe`, `_symbols`, `_backtest_start`, `_backtest_end`
2. Keep `_config: dict[str, Any] | None = None`
3. `build()` → the returned dict puts symbols/timeframe/backtest into `config`:
   ```python
   def build(self) -> dict[str, Any]:
       config = dict(self._config or {})
       config.setdefault("symbols", ["AAPL"])
       config.setdefault("timeframe", "1m")
       return {
           "id": self._id or str(uuid4()),
           "strategy_name": self._strategy_name,
           "mode": self._mode,
           "status": self._status,
           "config": config,
           "started_at": self._started_at,
           "stopped_at": self._stopped_at,
           "created_at": self._created_at or now,
           "updated_at": self._updated_at or now,
       }
   ```
4. Keep `with_config()`, rename `with_symbols()`/`with_timeframe()` to write into config:
   ```python
   def with_symbols(self, symbols: list[str]) -> RunFactory:
       if self._config is None:
           self._config = {}
       self._config["symbols"] = symbols
       return self
   def with_timeframe(self, timeframe: str) -> RunFactory:
       if self._config is None:
           self._config = {}
       self._config["timeframe"] = timeframe
       return self
   def with_backtest_range(self, start: datetime, end: datetime) -> RunFactory:
       if self._config is None:
           self._config = {}
       self._config["backtest_start"] = start.isoformat()
       self._config["backtest_end"] = end.isoformat()
       return self
   ```
5. Update `create()`, `create_run()`, `create_live_run()`, `create_backtest_run()`, `create_sma_cross_backtest()` to match.
6. `create_run_manager_with_deps()` — no change needed (returns RunManager, not RunCreate).

### Step 1.2 — Update `RunCreate` schema

**File**: `src/glados/schemas.py` (lines 58–66)

**🔴 Red**: Write new test `tests/unit/glados/test_schemas.py` (new file):

```python
def test_run_create_requires_config():
    """config is required, not optional."""
    with pytest.raises(ValidationError):
        RunCreate(strategy_id="test", mode="paper")  # missing config

def test_run_create_accepts_config():
    rc = RunCreate(strategy_id="test", mode="paper", config={"symbols": ["BTC/USD"]})
    assert rc.config == {"symbols": ["BTC/USD"]}

def test_run_create_rejects_symbols_field():
    """symbols, timeframe, start_time, end_time are NOT top-level fields."""
    rc = RunCreate(strategy_id="test", mode="paper", config={"symbols": ["X"]}, symbols=["Y"])
    # Pydantic should reject unknown field 'symbols' (model_config forbid extra)

def test_run_create_no_extra_fields():
    """RunCreate only accepts strategy_id, mode, config."""
    with pytest.raises(ValidationError):
        RunCreate(strategy_id="test", mode="paper", config={}, timeframe="5m")

def test_run_response_has_config_not_symbols():
    resp = RunResponse(id="1", strategy_id="test", mode="paper", status="pending",
                       config={"symbols": ["BTC/USD"]}, created_at=datetime.now(UTC))
    assert resp.config == {"symbols": ["BTC/USD"]}
    assert not hasattr(resp, "symbols")
```

**🟢 Green — exact changes to `src/glados/schemas.py`**:

```python
# BEFORE (lines 58-66):
class RunCreate(BaseModel):
    strategy_id: str = Field(..., min_length=1)
    mode: RunMode
    symbols: list[str] = Field(..., min_length=1)
    timeframe: str = Field(default="1m")
    start_time: datetime | None = None
    end_time: datetime | None = None
    config: dict[str, Any] | None = None

# AFTER:
class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(..., min_length=1)
    mode: RunMode
    config: dict[str, Any] = Field(..., description="Strategy configuration containing symbols, timeframe, etc.")
```

```python
# BEFORE (lines 69-80):
class RunResponse(BaseModel):
    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    symbols: list[str]
    timeframe: str
    config: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None

# AFTER:
class RunResponse(BaseModel):
    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    config: dict[str, Any]
    created_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None
```

Add import at top: `from pydantic import BaseModel, ConfigDict, Field`

### Step 1.3 — Update `Run` dataclass and `RunManager`

**File**: `src/glados/services/run_manager.py`

**🔴 Red**: Update existing tests in `tests/unit/glados/services/test_run_manager.py`:

- `test_preserves_request_fields` → assert `run.config["symbols"] == ["BTC/USD"]` (not `run.symbols`)
- All `RunCreate(...)` calls → change to `RunCreate(strategy_id=..., mode=..., config={...})`

**🟢 Green — exact changes**:

1. **`Run` dataclass** (lines 42–55):

   ```python
   # BEFORE:
   @dataclass
   class Run:
       id: str
       strategy_id: str
       mode: RunMode
       status: RunStatus
       symbols: list[str]
       timeframe: str
       config: dict[str, Any] | None
       created_at: datetime
       start_time: datetime | None = None
       end_time: datetime | None = None
       started_at: datetime | None = None
       stopped_at: datetime | None = None

   # AFTER:
   @dataclass
   class Run:
       id: str
       strategy_id: str
       mode: RunMode
       status: RunStatus
       config: dict[str, Any]
       created_at: datetime
       started_at: datetime | None = None
       stopped_at: datetime | None = None
   ```

2. **`create()` method** (lines 156–175):

   ```python
   # BEFORE:
   run = Run(
       id=str(uuid4()),
       strategy_id=request.strategy_id,
       mode=request.mode,
       status=RunStatus.PENDING,
       symbols=request.symbols,
       timeframe=request.timeframe,
       config=request.config,
       created_at=datetime.now(UTC),
       start_time=request.start_time,
       end_time=request.end_time,
   )

   # AFTER:
   run = Run(
       id=str(uuid4()),
       strategy_id=request.strategy_id,
       mode=request.mode,
       status=RunStatus.PENDING,
       config=request.config,
       created_at=datetime.now(UTC),
   )
   ```

3. **`_persist_run()`** (lines 99–112):

   ```python
   # BEFORE:
   record = RunRecord(
       id=run.id,
       strategy_id=run.strategy_id,
       mode=run.mode.value,
       status=run.status.value,
       symbols=run.symbols,
       timeframe=run.timeframe,
       config=run.config,
       ...
   )

   # AFTER:
   record = RunRecord(
       id=run.id,
       strategy_id=run.strategy_id,
       mode=run.mode.value,
       status=run.status.value,
       config=run.config,
       ...
   )
   ```

4. **`_start_backtest()`** — read from config instead of top-level:

   ```python
   # BEFORE:
   if run.start_time is None or run.end_time is None:
       raise RuntimeError("start_time and end_time required for backtest")

   # AFTER:
   backtest_start = run.config.get("backtest_start")
   backtest_end = run.config.get("backtest_end")
   if backtest_start is None or backtest_end is None:
       raise RuntimeError("config must contain backtest_start and backtest_end for backtest")
   start_time = datetime.fromisoformat(backtest_start)
   end_time = datetime.fromisoformat(backtest_end)
   ```

   ```python
   # Clock creation — BEFORE:
   clock = BacktestClock(
       start_time=run.start_time,
       end_time=run.end_time,
       timeframe=run.timeframe,
   )
   # AFTER:
   clock = BacktestClock(
       start_time=start_time,
       end_time=end_time,
       timeframe=run.config.get("timeframe", "1m"),
   )
   ```

   ```python
   # Greta initialize — BEFORE:
   await greta.initialize(
       symbols=run.symbols,
       timeframe=run.timeframe,
       start=run.start_time,
       end=run.end_time,
       task_set=ctx.pending_tasks,
   )
   # AFTER:
   await greta.initialize(
       symbols=run.config.get("symbols", []),
       timeframe=run.config.get("timeframe", "1m"),
       start=start_time,
       end=end_time,
       task_set=ctx.pending_tasks,
   )
   ```

   ```python
   # Runner initialize — BEFORE:
   await runner.initialize(
       run_id=run.id,
       symbols=run.symbols,
       task_set=ctx.pending_tasks,
   )
   # AFTER:
   await runner.initialize(
       run_id=run.id,
       symbols=run.config.get("symbols", []),
       task_set=ctx.pending_tasks,
   )
   ```

5. **`_start_live()`** — similar changes:

   ```python
   # BEFORE:
   clock = RealtimeClock(timeframe=run.timeframe)

   # AFTER:
   clock = RealtimeClock(timeframe=run.config.get("timeframe", "1m"))
   ```

   ```python
   # BEFORE:
   await runner.initialize(run_id=run.id, symbols=run.symbols, task_set=ctx.pending_tasks)

   # AFTER:
   await runner.initialize(run_id=run.id, symbols=run.config.get("symbols", []), task_set=ctx.pending_tasks)
   ```

6. **`recover()`** — BEFORE builds Run with `symbols=symbols, timeframe=record.timeframe`. AFTER:

   ```python
   run = Run(
       id=record.id,
       strategy_id=record.strategy_id,
       mode=RunMode(record.mode),
       status=RunStatus(record.status),
       config=record.config or {},
       created_at=record.created_at,
       started_at=record.started_at,
       stopped_at=record.stopped_at,
   )
   ```

7. **`_emit_event()`** — payload builds `"run_id": run.id` etc. No change needed (doesn't emit symbols/timeframe).

8. **`on_live_fetch_window` in `app.py`** — currently reads `run.timeframe`:
   ```python
   # BEFORE (app.py ~L220):
   timeframe = run.timeframe
   # AFTER:
   timeframe = run.config.get("timeframe", "1m")
   ```

### Step 1.4 — Update `RunRecord` DB Model + Alembic Migration

**File**: `src/walle/models.py` (lines 167–191)

**🟢 Green — exact changes**:

```python
# BEFORE:
class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    symbols: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    ...

# AFTER:
class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    ...
```

**Alembic Migration** — new file `src/walle/migrations/versions/006_run_config_refactor.py`:

```python
def upgrade():
    # 1. Merge existing symbols/timeframe into config for any existing rows
    op.execute("""
        UPDATE runs SET config = jsonb_build_object(
            'symbols', COALESCE(symbols, '[]'::jsonb),
            'timeframe', COALESCE(timeframe, '1m')
        ) || COALESCE(config, '{}'::jsonb)
        WHERE config IS NULL OR NOT config ? 'symbols'
    """)
    # 2. Alter config to NOT NULL
    op.alter_column("runs", "config", nullable=False, server_default=text("'{}'::jsonb"))
    # 3. Drop old columns
    op.drop_column("runs", "symbols")
    op.drop_column("runs", "timeframe")

def downgrade():
    op.add_column("runs", sa.Column("symbols", JSONB, nullable=True))
    op.add_column("runs", sa.Column("timeframe", sa.String(20), nullable=True))
    op.alter_column("runs", "config", nullable=True, server_default=None)
```

### Step 1.5 — Update `routes/runs.py`

**File**: `src/glados/routes/runs.py` (lines 20–33)

```python
# BEFORE:
def _run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        strategy_id=run.strategy_id,
        mode=run.mode,
        status=run.status,
        symbols=run.symbols,
        timeframe=run.timeframe,
        config=run.config,
        created_at=run.created_at,
        started_at=run.started_at,
        stopped_at=run.stopped_at,
    )

# AFTER:
def _run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        strategy_id=run.strategy_id,
        mode=run.mode,
        status=run.status,
        config=run.config,
        created_at=run.created_at,
        started_at=run.started_at,
        stopped_at=run.stopped_at,
    )
```

### Step 1.6 — 🔵 Blue: Batch-update all existing test files

Every `RunCreate(...)` call across the codebase must change shape. Here is the complete file list with exact transformation:

**Pattern — all backend unit/integration tests**:

```python
# BEFORE (appears in ~14 critical test files):
RunCreate(
    strategy_id="sma_cross",
    mode=RunMode.BACKTEST,
    symbols=["BTC/USD"],
    timeframe="1m",
    start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
    end_time=datetime(2024, 1, 1, 9, 32, tzinfo=UTC),
)

# AFTER:
RunCreate(
    strategy_id="sma_cross",
    mode=RunMode.BACKTEST,
    config={
        "symbols": ["BTC/USD"],
        "timeframe": "1m",
        "backtest_start": "2024-01-01T09:30:00+00:00",
        "backtest_end": "2024-01-01T09:32:00+00:00",
    },
)
```

**Complete list of files to update (RunCreate / Run construction)**:

| #   | File                                                             | Lines to change                                                           | What changes                                                                                          |
| --- | ---------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | `tests/unit/glados/services/test_run_manager.py` (431L)          | All `RunCreate(...)` calls (~6), `run.symbols`/`run.timeframe` assertions | Change to `config={...}`, assert `run.config["symbols"]`                                              |
| 2   | `tests/unit/glados/services/test_run_lifecycle.py` (289L)        | All `RunCreate(...)` calls (~4)                                           | Change to `config={...}`                                                                              |
| 3   | `tests/unit/glados/services/test_run_persistence.py` (414L)      | `_make_run_create()` helper, all assertions                               | Config-based                                                                                          |
| 4   | `tests/unit/glados/services/test_run_mode_integration.py` (232L) | All `RunCreate(...)` calls (~3)                                           | Config-based                                                                                          |
| 5   | `tests/unit/glados/services/test_event_pipeline.py` (593L)       | `RunCreate(...)` and `Run(...)` constructions                             | Config-based                                                                                          |
| 6   | `tests/unit/glados/test_run_manager_backtest.py` (843L)          | All `RunCreate(...)` (~8)                                                 | Config-based                                                                                          |
| 7   | `tests/unit/glados/test_domain_router.py` (252L)                 | `Run(symbols=..., timeframe=..., config=None)` at L73, L138, L159, L223   | `Run(config={"symbols": [...], "timeframe": "1m"})` — remove `symbols`/`timeframe`/`config=None` args |
| 8   | `tests/unit/glados/routes/test_runs.py` (319L)                   | JSON payloads `{"symbols": [...], "timeframe": ...}`                      | `{"config": {...}}`                                                                                   |
| 9   | `tests/unit/walle/test_run_repository.py` (123L)                 | `test_has_required_columns` asserts `symbols`, `timeframe` columns        | Remove those assertions, assert `config` NOT NULL                                                     |
| 10  | `tests/integration/test_backtest_flow.py` (211L)                 | `RunCreate(...)` calls                                                    | Config-based                                                                                          |
| 11  | `tests/unit/glados/test_production_polish.py` (161L)             | May reference RunCreate in OpenAPI tests                                  | Check & update                                                                                        |
| 12  | `tests/unit/test_infrastructure.py` (177L)                       | Smoke test may use factories                                              | Check & update                                                                                        |

**Files with `run.symbols` / `run.timeframe` reads (not RunCreate but Run access)**:

| #     | File                                                    | What changes                                                                                                                                           |
| ----- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 13    | `tests/unit/greta/test_greta_service.py` (894L)         | `greta.initialize(symbols=..., timeframe=...)` — no change yet (S2 later), but `test_initialize_sets_symbols` asserts `service.symbols` — keep for now |
| 14    | `tests/unit/greta/test_greta_events.py` (309L)          | `greta.initialize(symbols=..., timeframe=...)` — no change yet                                                                                         |
| 15    | `tests/unit/marvin/test_strategy_runner.py` (341L)      | `runner.initialize(run_id=..., symbols=...)` — no change yet                                                                                           |
| 16-31 | Other files referencing `timeframe` as a string literal | Only change if they construct `RunCreate` or read `run.timeframe`                                                                                      |

**E2E test file updates**:

| #   | File                                        | What changes                                                                           |
| --- | ------------------------------------------- | -------------------------------------------------------------------------------------- |
| 32  | `tests/e2e/helpers.py` (67L)                | `create_run()` payload: remove `symbols`/`timeframe` from top level, put into `config` |
| 33  | `tests/e2e/test_backtest_flow.py` (167L)    | Assertions on response shape (no more `symbols` field)                                 |
| 34  | `tests/e2e/test_paper_flow.py` (85L)        | Same                                                                                   |
| 35  | `tests/e2e/test_orders_lifecycle.py` (155L) | Same                                                                                   |
| 36  | `tests/e2e/test_sse.py` (90L)               | Same                                                                                   |

**E2E helpers.py exact change**:

> **Type handling note**: The current `kwargs["start_time"]` / `kwargs["end_time"]` values may be `datetime` objects or ISO strings depending on the caller. The new code must ensure they are always stored as ISO strings in config, since `run_manager._start_backtest()` calls `datetime.fromisoformat()` on them.

```python
# BEFORE:
def create_run(self, **kwargs: Any) -> dict[str, Any]:
    payload = {
        "strategy_id": kwargs.get("strategy_id", "sample"),
        "mode": kwargs.get("mode", "backtest"),
        "symbols": kwargs.get("symbols", ["BTC/USD"]),
        "timeframe": kwargs.get("timeframe", "1m"),
    }
    if "start_time" in kwargs:
        payload["start_time"] = kwargs["start_time"]
    if "end_time" in kwargs:
        payload["end_time"] = kwargs["end_time"]
    if "config" in kwargs:
        payload["config"] = kwargs["config"]
    r = self.session.post(f"{self.base_url}/runs", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

# AFTER:
def create_run(self, **kwargs: Any) -> dict[str, Any]:
    config = dict(kwargs.get("config", {}))
    config.setdefault("symbols", kwargs.get("symbols", ["BTC/USD"]))
    config.setdefault("timeframe", kwargs.get("timeframe", "1m"))
    if "start_time" in kwargs:
        v = kwargs["start_time"]
        config["backtest_start"] = v.isoformat() if isinstance(v, datetime) else v
    if "end_time" in kwargs:
        v = kwargs["end_time"]
        config["backtest_end"] = v.isoformat() if isinstance(v, datetime) else v
    payload = {
        "strategy_id": kwargs.get("strategy_id", "sample"),
        "mode": kwargs.get("mode", "backtest"),
        "config": config,
    }
    r = self.session.post(f"{self.base_url}/runs", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()
```

> Add `from datetime import datetime` to imports if not present.

### Step 1.7 — Validate

```bash
# Run all backend tests
pytest tests/unit tests/integration -x -q
# Run frontend tests
cd haro && npm test
# Start E2E stack and run
docker compose -f docker/docker-compose.e2e.yml up -d --wait --build
pytest tests/e2e -x -q
```

---

## Phase 2: Strategy Interface Refactor (S2 + S3)

> **Goal**: Change `BaseStrategy.initialize(symbols)` → `initialize(config)`. Add `STOP_RUN` action type and `exchange` field to `StrategyAction`.

### Step 2.1 — S2: Update `BaseStrategy.initialize()` signature

**File**: `src/marvin/base_strategy.py` (lines 57–58)

**🔴 Red** — Update tests first:

`tests/unit/marvin/test_sample_strategy.py`:

```python
# BEFORE:
await strategy.initialize(["BTC/USD"])
# AFTER:
await strategy.initialize({"symbols": ["BTC/USD"], "timeframe": "1m"})
```

`tests/unit/marvin/test_sma_strategy.py`:

```python
# BEFORE:
await strategy.initialize(["BTC/USD"])
# AFTER:
await strategy.initialize({"symbols": ["BTC/USD"], "timeframe": "1m", "fast_period": 5, "slow_period": 20})
```

New tests in `tests/unit/marvin/test_base_strategy.py` (new file):

```python
def test_initialize_stores_config():
    strategy = ConcreteStrategy()
    await strategy.initialize({"symbols": ["AAPL"], "extra": 42})
    assert strategy._symbols == ["AAPL"]
    assert strategy._config == {"symbols": ["AAPL"], "extra": 42}

def test_initialize_default_symbols():
    strategy = ConcreteStrategy()
    await strategy.initialize({})
    assert strategy._symbols == []
```

**🟢 Green — exact changes**:

```python
# BEFORE (base_strategy.py L57-58):
async def initialize(self, symbols: list[str]) -> None:
    self._symbols = symbols

# AFTER:
async def initialize(self, config: dict[str, Any]) -> None:
    self._config = config
    self._symbols = config.get("symbols", [])
```

Add `from typing import Any` import.

### Step 2.2 — S2: Update `StrategyRunner.initialize()` propagation

**File**: `src/marvin/strategy_runner.py` (lines 51–61)

**🔴 Red** — Update `tests/unit/marvin/test_strategy_runner.py`:

```python
# BEFORE:
await runner.initialize(run_id="run-123", symbols=["BTC/USD"])
assert runner.symbols == ["BTC/USD"]

# AFTER:
await runner.initialize(run_id="run-123", config={"symbols": ["BTC/USD"], "timeframe": "1m"})
assert runner.symbols == ["BTC/USD"]
```

New test:

```python
def test_initialize_passes_config_to_strategy():
    config = {"symbols": ["ETH/USD"], "fast_period": 10}
    await runner.initialize(run_id="r1", config=config)
    strategy.initialize.assert_called_once_with(config)
```

**🟢 Green**:

```python
# BEFORE:
async def initialize(
    self, run_id: str, symbols: list[str], task_set: set[asyncio.Task[Any]] | None = None
) -> None:
    self._run_id = run_id
    self._symbols = symbols
    self._task_set = task_set
    await self._strategy.initialize(symbols)

# AFTER:
async def initialize(
    self, run_id: str, config: dict[str, Any], task_set: set[asyncio.Task[Any]] | None = None
) -> None:
    self._run_id = run_id
    self._config = config
    self._symbols = config.get("symbols", [])
    self._task_set = task_set
    await self._strategy.initialize(config)
```

Also add `from typing import Any` if not present.

### Step 2.3 — S2: Update strategy implementations

**File**: `src/marvin/strategies/sample_strategy.py`

Current `SampleStrategy` inherits `initialize()` from `BaseStrategy` — no override needed. The base class change in 2.1 handles it.

**File**: `src/marvin/strategies/sma_strategy.py`

> **Verified**: `SMAStrategy` does **NOT** override `initialize()`. It currently creates `SMAConfig` with hardcoded defaults in `__init__()`. After this change, strategy-specific params (fast_period, slow_period, qty) should be read from the config dict passed via the base class `initialize()`. Add an `initialize()` override:

**🔴 Red** — Add test in `tests/unit/marvin/test_sma_strategy.py`:

```python
async def test_initialize_reads_config_params():
    strategy = SMAStrategy()
    await strategy.initialize({
        "symbols": ["BTC/USD"],
        "fast_period": 8,
        "slow_period": 30,
        "qty": 2.5,
    })
    assert strategy._sma_config.fast_period == 8
    assert strategy._sma_config.slow_period == 30
    assert strategy._sma_config.qty == Decimal("2.5")

async def test_initialize_uses_defaults_when_no_params():
    strategy = SMAStrategy()
    await strategy.initialize({"symbols": ["BTC/USD"]})
    assert strategy._sma_config.fast_period == 5
    assert strategy._sma_config.slow_period == 20
    assert strategy._sma_config.qty == Decimal("1.0")
```

**🟢 Green** — Add `initialize()` override to `SMAStrategy`:

```python
async def initialize(self, config: dict[str, Any]) -> None:
    await super().initialize(config)
    self._sma_config = SMAConfig(
        fast_period=config.get("fast_period", 5),
        slow_period=config.get("slow_period", 20),
        qty=Decimal(str(config.get("qty", "1.0"))),
    )
```

> **Note**: Remove the `SMAConfig(...)` construction from `__init__()` since it now lives in `initialize()`. The `__init__` should only call `super().__init__()` and set `self._prev_fast_above_slow`.

### Step 2.4 — S2: Update `RunManager` callers

After Phase 1, `run_manager._start_backtest()` and `_start_live()` already pass `symbols=run.config.get("symbols", [])` to `runner.initialize()`. Now change to pass full config:

**File**: `src/glados/services/run_manager.py`

```python
# BEFORE (already changed in Phase 1):
await runner.initialize(
    run_id=run.id,
    symbols=run.config.get("symbols", []),
    task_set=ctx.pending_tasks,
)

# AFTER:
await runner.initialize(
    run_id=run.id,
    config=run.config,
    task_set=ctx.pending_tasks,
)
```

This change applies in both `_start_backtest()` and `_start_live()`.

### Step 2.5 — S3: Add `STOP_RUN` to `ActionType`

**File**: `src/marvin/base_strategy.py`

**🔴 Red** — New tests in `tests/unit/marvin/test_strategy_runner.py`:

```python
async def test_stop_run_action_emits_event():
    action = StrategyAction(type=ActionType.STOP_RUN)
    strategy.on_tick = AsyncMock(return_value=[action])
    await runner.on_tick(tick)
    event_log.append.assert_called()
    envelope = event_log.append.call_args[0][0]
    assert envelope.type == "run.StopRequested"
    assert envelope.run_id == runner.run_id

async def test_stop_run_action_payload():
    action = StrategyAction(type=ActionType.STOP_RUN)
    strategy.on_tick = AsyncMock(return_value=[action])
    await runner.on_tick(tick)
    envelope = event_log.append.call_args[0][0]
    assert envelope.payload == {"reason": "strategy_requested"}
```

**🟢 Green**:

```python
# base_strategy.py — add to ActionType enum:
class ActionType(StrEnum):
    FETCH_WINDOW = "fetch_window"
    PLACE_ORDER = "place_order"
    STOP_RUN = "stop_run"          # ← NEW
```

```python
# strategy_runner.py — add handler in _emit_action():
async def _emit_action(self, action: StrategyAction, tick: Any = None) -> None:
    if action.type == ActionType.FETCH_WINDOW:
        await self._emit_fetch_window(action, tick=tick)
    elif action.type == ActionType.PLACE_ORDER:
        if action.symbol is None or action.side is None or action.qty is None:
            raise ValueError("PLACE_ORDER requires symbol, side, qty")
        await self._emit_place_request(action)
    elif action.type == ActionType.STOP_RUN:       # ← NEW
        await self._emit_stop_run()                 # ← NEW

# NEW method:
async def _emit_stop_run(self) -> None:
    envelope = Envelope(
        type="run.StopRequested",
        payload={"reason": "strategy_requested"},
        run_id=self._run_id,
        producer="marvin.runner",
    )
    await self._event_log.append(envelope)
```

> **Verified**: `Envelope` (in `src/events/protocol.py`) is a frozen dataclass. `producer: str` is **required** (no default). `run_id: str | None` defaults to `None`. The construction above is correct.
>
> **Verified**: `run.StopRequested` already exists in `RunEvents` class in `src/events/types.py` (line: `STOP_REQUESTED = "run.StopRequested"`). No change needed there.

### Step 2.6 — S3: Add `exchange` field to `StrategyAction`

**File**: `src/marvin/base_strategy.py`

**🔴 Red**:

```python
def test_strategy_action_has_exchange_field():
    action = StrategyAction(type=ActionType.PLACE_ORDER, symbol="BTC/USD",
                           side=StrategyOrderSide.BUY, qty=Decimal("1"),
                           exchange="alpaca")
    assert action.exchange == "alpaca"

def test_strategy_action_exchange_defaults_none():
    action = StrategyAction(type=ActionType.FETCH_WINDOW, symbol="BTC/USD", lookback=10)
    assert action.exchange is None
```

**🟢 Green**:

```python
# BEFORE:
@dataclass(frozen=True)
class StrategyAction:
    type: ActionType
    symbol: str | None = None
    lookback: int | None = None
    side: StrategyOrderSide | None = None
    qty: Decimal | None = None
    order_type: StrategyOrderType = StrategyOrderType.MARKET
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None

# AFTER:
@dataclass(frozen=True)
class StrategyAction:
    type: ActionType
    symbol: str | None = None
    lookback: int | None = None
    side: StrategyOrderSide | None = None
    qty: Decimal | None = None
    order_type: StrategyOrderType = StrategyOrderType.MARKET
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    exchange: str | None = None     # ← NEW (D-6: field only, not wired to events yet)
```

**🔵 Blue**: No event payload changes (D-6 decision: field only, M13 wires it).

### Step 2.7 — Update remaining test files

| File                                                      | Change                                                                                                 |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `tests/unit/marvin/test_strategy_runner_events.py` (276L) | `runner.initialize("run-001", ["BTC/USD"])` → `runner.initialize("run-001", {"symbols": ["BTC/USD"]})` |
| `tests/unit/test_strategy_fixtures.py` (153L)             | `strategy.initialize(["BTC/USD"])` → `strategy.initialize({"symbols": ["BTC/USD"]})`                   |
| `tests/unit/greta/test_greta_events.py` (309L)            | No change — Greta's `initialize()` signature is different (takes symbols/timeframe as separate args)   |
| `tests/unit/greta/test_greta_service.py` (894L)           | No change — same reason                                                                                |

### Step 2.8 — Validate

```bash
pytest tests/unit/marvin -x -q
pytest tests/unit/glados -x -q
pytest tests/unit -x -q
```

---

## Phase 3: Strategy Metadata & API (S4 + S6)

> **Goal**: Add `config_schema` (JSON Schema) to StrategyMeta. Create `GET /api/v1/strategies` endpoint. Add `jsonschema` to requirements.

### Step 3.1 — Add `jsonschema` dependency

**File**: `docker/backend/requirements.txt`

```
jsonschema>=4.0.0
```

Run: `pip install jsonschema`

### Step 3.2 — S4: Add `config_schema` to `StrategyMeta`

**File**: `src/marvin/strategy_meta.py` (53L)

**🔴 Red** — New test `tests/unit/marvin/test_strategy_meta.py` (new file):

```python
def test_strategy_meta_has_config_schema():
    meta = StrategyMeta(id="test", class_name="Test", config_schema={"type": "object"})
    assert meta.config_schema == {"type": "object"}

def test_strategy_meta_config_schema_defaults_none():
    meta = StrategyMeta(id="test", class_name="Test")
    assert meta.config_schema is None

def test_from_dict_reads_config_schema():
    data = {"id": "x", "class": "X", "config_schema": {"type": "object", "properties": {}}}
    meta = StrategyMeta.from_dict(data)
    assert meta.config_schema == {"type": "object", "properties": {}}

def test_from_dict_missing_config_schema():
    data = {"id": "x", "class": "X"}
    meta = StrategyMeta.from_dict(data)
    assert meta.config_schema is None
```

**🟢 Green**:

```python
# BEFORE:
@dataclass(frozen=True)
class StrategyMeta:
    id: str
    class_name: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    module_path: Path | None = None

# AFTER:
@dataclass(frozen=True)
class StrategyMeta:
    id: str
    class_name: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    module_path: Path | None = None
    config_schema: dict | None = None       # ← NEW (JSON Schema format)
```

```python
# BEFORE from_dict():
@classmethod
def from_dict(cls, data: dict, module_path: Path | None = None) -> "StrategyMeta":
    return cls(
        id=data.get("id", ""),
        class_name=data.get("class", ""),
        ...
        dependencies=data.get("dependencies", []),
        module_path=module_path,
    )

# AFTER from_dict():
@classmethod
def from_dict(cls, data: dict, module_path: Path | None = None) -> "StrategyMeta":
    return cls(
        id=data.get("id", ""),
        class_name=data.get("class", ""),
        ...
        dependencies=data.get("dependencies", []),
        module_path=module_path,
        config_schema=data.get("config_schema"),   # ← NEW
    )
```

### Step 3.3 — S4: Add `config_schema` to strategy STRATEGY_META dicts

**File**: `src/marvin/strategies/sample_strategy.py`

```python
# BEFORE:
STRATEGY_META = {
    "id": "sample",
    "name": "Sample Mean-Reversion Strategy",
    "version": "1.0.0",
    "description": "Simple mean-reversion strategy for testing",
    "author": "weaver",
    "dependencies": [],
    "class": "SampleStrategy",
}

# AFTER:
STRATEGY_META = {
    "id": "sample",
    "name": "Sample Mean-Reversion Strategy",
    "version": "1.0.0",
    "description": "Simple mean-reversion strategy for testing",
    "author": "weaver",
    "dependencies": [],
    "class": "SampleStrategy",
    "config_schema": {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Trading symbols",
            },
            "timeframe": {
                "type": "string",
                "default": "1m",
                "enum": ["1m", "5m", "15m", "1h", "4h", "1d"],
            },
        },
        "required": ["symbols"],
    },
}
```

**File**: `src/marvin/strategies/sma_strategy.py`

```python
# AFTER:
STRATEGY_META = {
    "id": "sma-crossover",
    "name": "SMA Crossover Strategy",
    "version": "1.0.0",
    "description": "Simple Moving Average crossover strategy",
    "author": "weaver",
    "dependencies": [],
    "class": "SMAStrategy",
    "config_schema": {
        "type": "object",
        "properties": {
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Trading symbols",
            },
            "timeframe": {
                "type": "string",
                "default": "1m",
                "enum": ["1m", "5m", "15m", "1h", "4h", "1d"],
            },
            "fast_period": {
                "type": "integer",
                "default": 5,
                "minimum": 1,
                "description": "Fast SMA period",
            },
            "slow_period": {
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "description": "Slow SMA period",
            },
            "qty": {
                "type": "number",
                "default": 1.0,
                "minimum": 0,
                "description": "Quantity per trade",
            },
        },
        "required": ["symbols"],
    },
}
```

### Step 3.4 — S4: Add config validation in RunManager.create()

**File**: `src/glados/services/run_manager.py` — in `create()` method

**🔴 Red** — New test in `tests/unit/glados/services/test_run_manager.py`:

```python
async def test_create_validates_config_against_schema():
    """When strategy has config_schema, validate config on create."""
    # Setup loader to return strategy with schema
    meta = StrategyMeta(id="test", class_name="Test", config_schema={
        "type": "object",
        "properties": {"symbols": {"type": "array", "items": {"type": "string"}}},
        "required": ["symbols"],
    })
    loader.get_meta = MagicMock(return_value=meta)

    # Missing required "symbols"
    request = RunCreate(strategy_id="test", mode=RunMode.PAPER, config={"timeframe": "1m"})
    with pytest.raises(ValueError, match="symbols"):
        await manager.create(request)

async def test_create_skips_validation_when_no_schema():
    """Strategies without config_schema skip validation."""
    request = RunCreate(strategy_id="test", mode=RunMode.PAPER, config={"anything": True})
    run = await manager.create(request)
    assert run.config == {"anything": True}
```

**🟢 Green** — Add to `RunManager.create()`:

> **Design note**: `RunManager.__init__()` already accepts `strategy_loader` as a constructor arg. Since `get_meta()` is being added to the `StrategyLoader` ABC (with a default `return None`), there's no need for `hasattr` checks. The ABC guarantees the method exists.

```python
async def create(self, request: RunCreate) -> Run:
    # Validate config against strategy's config_schema (if available)
    meta = self._strategy_loader.get_meta(request.strategy_id)
    if meta and meta.config_schema:
        import jsonschema
        jsonschema.validate(instance=request.config, schema=meta.config_schema)

    run = Run(...)
    ...
```

> **Verified**: `PluginStrategyLoader._registry` is a `dict[str, StrategyMeta]` keyed by `strategy_id`. The `get_meta()` call `self._registry.get(strategy_id)` is correct.

Also add `get_meta()` method to `StrategyLoader` / `PluginStrategyLoader`:

```python
# strategy_loader.py — StrategyLoader ABC:
def get_meta(self, strategy_id: str) -> StrategyMeta | None:
    return None

# PluginStrategyLoader:
def get_meta(self, strategy_id: str) -> StrategyMeta | None:
    return self._registry.get(strategy_id)
```

### Step 3.5 — S6: Create `GET /api/v1/strategies` endpoint

**New file**: `src/glados/routes/strategies.py`

**🔴 Red** — New test `tests/unit/glados/routes/test_strategies.py`:

```python
async def test_list_strategies_returns_all():
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # sample + sma-crossover

async def test_strategy_response_includes_config_schema():
    response = client.get("/api/v1/strategies")
    data = response.json()
    sma = next(s for s in data if s["id"] == "sma-crossover")
    assert sma["config_schema"]["type"] == "object"
    assert "symbols" in sma["config_schema"]["properties"]

async def test_strategy_response_fields():
    response = client.get("/api/v1/strategies")
    item = response.json()[0]
    assert set(item.keys()) >= {"id", "name", "version", "description", "config_schema"}
```

**🟢 Green**:

```python
# src/glados/routes/strategies.py (NEW FILE):
"""Strategies Routes — strategy discovery endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from src.glados.dependencies import get_strategy_loader
from src.marvin.strategy_loader import PluginStrategyLoader

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


@router.get("")
async def list_strategies(
    loader: PluginStrategyLoader = Depends(get_strategy_loader),
) -> list[dict[str, Any]]:
    strategies = loader.list_available()
    return [
        {
            "id": s.id,
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "author": s.author,
            "config_schema": s.config_schema,
        }
        for s in strategies
    ]
```

**File**: `src/glados/dependencies.py` — add dependency:

```python
from src.marvin.strategy_loader import PluginStrategyLoader

def get_strategy_loader(request: Request) -> PluginStrategyLoader:
    return request.app.state.strategy_loader
```

**File**: `src/glados/app.py` — register router:

```python
# Add import:
from src.glados.routes.strategies import router as strategies_router

# Add router registration (after existing routers):
app.include_router(strategies_router)
```

### Step 3.6 — Validate

```bash
pytest tests/unit/marvin/test_strategy_meta.py -x -q
pytest tests/unit/glados/routes/test_strategies.py -x -q
pytest tests/unit -x -q
```

---

## Phase 4: Production Safety (S8)

> **Goal**: Remove `InMemoryEventLog` fallback from `app.py`. App requires `DB_URL` to start.

### Step 4.1 — Update app.py

**File**: `src/glados/app.py` (lines 82–140)

**🔴 Red** — New test `tests/unit/glados/test_app_requires_db.py`:

```python
async def test_app_raises_without_db_url(monkeypatch):
    """App must refuse to start when DB_URL is not set."""
    monkeypatch.delenv("DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="DB_URL"):
        async with lifespan(app):
            pass

async def test_app_starts_with_db_url(monkeypatch, mocker):
    """App starts normally when DB_URL is set (mock DB connection)."""
    monkeypatch.setenv("DB_URL", "postgresql://test@localhost/test")
    # Mock Database to avoid real connection attempt
    mocker.patch("src.glados.app.Database")
    # Should not raise RuntimeError — DB_URL is set
```

**🟢 Green** — Remove the `else` branch (lines ~128–143 in app.py):

```python
# BEFORE:
    else:
        logger.warning("DB_URL not set - running without database (in-memory mode)")
        app.state.database = None
        app.state.veda_service = None
        from src.events.log import InMemoryEventLog
        event_log = InMemoryEventLog()
        app.state.event_log = event_log
        logger.info("InMemoryEventLog initialized (no-DB mode)")
        ...SSE subscriber setup...

# AFTER:
    else:
        raise RuntimeError(
            "DB_URL environment variable is required. "
            "Use docker-compose.dev.yml to start a local PostgreSQL."
        )
```

### Step 4.2 — Validate

```bash
pytest tests/unit/glados/test_app_requires_db.py -x -q
# E2E always has DB — no changes needed
```

---

## Phase 5: Backtest Config Source (S9)

> **Goal**: (Already done in Phase 1 Step 1.3) BacktestClock reads `backtest_start`/`backtest_end` from `run.config`. This phase is a verification step.

### Step 5.1 — Verify

Phase 1 Step 1.3 already changed `_start_backtest()` to read:

```python
backtest_start = run.config.get("backtest_start")
backtest_end = run.config.get("backtest_end")
...
clock = BacktestClock(
    start_time=start_time,
    end_time=end_time,
    timeframe=run.config.get("timeframe", "1m"),
)
```

**🔴 Red** — Additional test in `tests/unit/glados/test_run_manager_backtest.py`:

```python
async def test_backtest_reads_config_keys():
    request = RunCreate(
        strategy_id="sample",
        mode=RunMode.BACKTEST,
        config={
            "symbols": ["BTC/USD"],
            "timeframe": "5m",
            "backtest_start": "2024-01-01T09:30:00+00:00",
            "backtest_end": "2024-01-01T10:30:00+00:00",
        },
    )
    run = await manager.create(request)
    await manager.start(run.id)
    # BacktestClock should have been created with timeframe="5m"
    # Verify via mock or by checking clock was constructed correctly

async def test_backtest_rejects_missing_backtest_start():
    request = RunCreate(
        strategy_id="sample",
        mode=RunMode.BACKTEST,
        config={"symbols": ["BTC/USD"], "timeframe": "1m"},
    )
    run = await manager.create(request)
    with pytest.raises(RuntimeError, match="backtest_start"):
        await manager.start(run.id)
```

### Step 5.2 — Validate

```bash
pytest tests/unit/glados/test_run_manager_backtest.py -x -q
```

---

## Phase 6: Frontend Full-stack Alignment (S11–S15)

> **Goal**: Update all frontend types, forms, pages, and API layer to match the new backend.

### Step 6.1 — Install RJSF dependencies

```bash
cd haro
npm install @rjsf/core @rjsf/utils @rjsf/validator-ajv8
```

### Step 6.2 — S11: Update `types.ts`

**File**: `haro/src/api/types.ts`

**🔴 Red** — Update `haro/tests/unit/api/runs.test.ts`:

```typescript
// BEFORE:
const data: RunCreate = {
  strategy_id: "test-strategy",
  mode: "paper",
  symbols: ["BTC/USD"],
  timeframe: "1h",
};

// AFTER:
const data: RunCreate = {
  strategy_id: "test-strategy",
  mode: "paper",
  config: { symbols: ["BTC/USD"], timeframe: "1h" },
};
```

**🟢 Green**:

```typescript
// BEFORE:
export interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  symbols: string[];
  timeframe: string;
  config?: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface RunCreate {
  strategy_id: string;
  mode: RunMode;
  symbols: string[];
  timeframe?: string;
  start_time?: string;
  end_time?: string;
  config?: Record<string, unknown>;
}

// AFTER:
export interface Run {
  id: string;
  strategy_id: string;
  mode: RunMode;
  status: RunStatus;
  config: Record<string, unknown>;
  created_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface RunCreate {
  strategy_id: string;
  mode: RunMode;
  config: Record<string, unknown>;
}
```

Add new types:

```typescript
export interface StrategyMeta {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  config_schema: Record<string, unknown> | null;
}
```

### Step 6.3 — S13: Create Strategies API layer

**New file**: `haro/src/api/strategies.ts`

```typescript
import { API_BASE } from "./runs";
import type { StrategyMeta } from "./types";

export async function fetchStrategies(): Promise<StrategyMeta[]> {
  const response = await fetch(`${API_BASE}/strategies`);
  if (!response.ok) throw new Error("Failed to fetch strategies");
  return response.json();
}
```

**New file**: `haro/src/hooks/useStrategies.ts`

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchStrategies } from "../api/strategies";

export function useStrategies() {
  return useQuery({ queryKey: ["strategies"], queryFn: fetchStrategies });
}
```

**🔴 Red** — New test `haro/tests/unit/hooks/useStrategies.test.tsx`:

```typescript
test("useStrategies fetches and returns strategies", async () => {
  const { result } = renderHook(() => useStrategies(), { wrapper });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toHaveLength(2);
  expect(result.current.data[0]).toHaveProperty("config_schema");
});
```

### Step 6.4 — S12: Update `CreateRunForm.tsx` with RJSF

**File**: `haro/src/components/runs/CreateRunForm.tsx` (142L)

**🔴 Red** — Update `haro/tests/unit/pages/RunsPage.test.tsx` (form tests):

```typescript
test('strategy dropdown shows available strategies', async () => {
  render(<RunsPage />, { wrapper });
  const select = await screen.findByLabelText(/strategy/i);
  expect(select).toBeInTheDocument();
  // Should show "Sample Mean-Reversion Strategy" and "SMA Crossover Strategy"
});

test('selecting strategy renders config form', async () => {
  render(<RunsPage />, { wrapper });
  // Select SMA strategy → RJSF renders fast_period, slow_period, symbols fields
  const select = await screen.findByLabelText(/strategy/i);
  await userEvent.selectOptions(select, 'sma-crossover');
  expect(await screen.findByLabelText(/fast_period/i)).toBeInTheDocument();
});
```

**🟢 Green** — Rewrite `CreateRunForm.tsx`:

```tsx
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import { useStrategies } from "../../hooks/useStrategies";

export function CreateRunForm({ onSubmit }: Props) {
  const { data: strategies } = useStrategies();
  const [strategyId, setStrategyId] = useState("");
  const [mode, setMode] = useState<RunMode>("backtest");
  const [configData, setConfigData] = useState<Record<string, unknown>>({});

  const selectedStrategy = strategies?.find((s) => s.id === strategyId);
  const configSchema = selectedStrategy?.config_schema;

  const handleSubmit = () => {
    onSubmit({
      strategy_id: strategyId,
      mode,
      config: configData,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Strategy dropdown */}
      <select
        value={strategyId}
        onChange={(e) => setStrategyId(e.target.value)}
      >
        <option value="">Select strategy...</option>
        {strategies?.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      {/* Mode selector */}
      <select value={mode} onChange={(e) => setMode(e.target.value as RunMode)}>
        <option value="backtest">Backtest</option>
        <option value="paper">Paper</option>
        <option value="live">Live</option>
      </select>

      {/* Backtest time range (only for backtest mode)
         NOTE: backtest_start/backtest_end are NOT in config_schema — they are
         platform-level fields managed by the form, not strategy-specific config.
         This avoids duplication: RJSF renders strategy params (symbols, timeframe,
         fast_period, etc.) while backtest time range is always a separate UI concern. */}
      {mode === "backtest" && (
        <>
          <label>
            Start Time
            <input
              type="datetime-local"
              onChange={(e) =>
                setConfigData((prev) => ({
                  ...prev,
                  backtest_start: e.target.value,
                }))
              }
            />
          </label>
          <label>
            End Time
            <input
              type="datetime-local"
              onChange={(e) =>
                setConfigData((prev) => ({
                  ...prev,
                  backtest_end: e.target.value,
                }))
              }
            />
          </label>
        </>
      )}

      {/* Dynamic config form from JSON Schema — renders strategy-specific fields */}
      {configSchema && (
        <Form
          schema={configSchema}
          validator={validator}
          formData={configData}
          onChange={(e) => setConfigData(e.formData)}
          uiSchema={{ "ui:submitButtonOptions": { norender: true } }}
        />
      )}

      <button type="submit">Create Run</button>
    </form>
  );
}
```

### Step 6.5 — S14: Update `RunsPage.tsx` table

**File**: `haro/src/pages/RunsPage.tsx` (255L)

> **UX note**: Instead of showing raw JSON truncation, extract the two most useful fields (symbols + timeframe) for display, with full config available on hover.

```tsx
// BEFORE:
<th>Symbols</th>
...
<td>{run.symbols.join(", ")}</td>

// AFTER:
<th>Symbols</th>
<th>Timeframe</th>
...
<td>{((run.config?.symbols as string[]) ?? []).join(", ")}</td>
<td>{(run.config?.timeframe as string) ?? "-"}</td>
```

> This keep the table readable while the underlying data source is now `run.config`. A tooltip or expandable row can show full config in a future iteration.

````

**🔴 Red** — Update test assertions in `haro/tests/unit/pages/RunsPage.test.tsx`:

```typescript
// BEFORE:
expect(screen.getByText("BTC/USD")).toBeInTheDocument();
// AFTER (symbols still renders as before, just sourced from config now):
expect(screen.getByText("BTC/USD")).toBeInTheDocument();
// Timeframe column now visible:
expect(screen.getByText("1h")).toBeInTheDocument();
````

### Step 6.6 — S15: Update `ActivityFeed.tsx`

**File**: `haro/src/components/dashboard/ActivityFeed.tsx` (103L)

```tsx
// BEFORE:
<span>{run.symbols.join(", ")}</span>

// AFTER:
<span>{run.strategy_id} ({run.mode})</span>
```

**🔴 Red** — Update `haro/tests/unit/components/ActivityFeed.test.tsx`:

```typescript
// BEFORE:
expect(screen.getByText("BTC/USD")).toBeInTheDocument();
// AFTER:
expect(screen.getByText(/sample.*backtest/i)).toBeInTheDocument();
```

### Step 6.7 — Update mock handlers

**File**: `haro/tests/mocks/handlers.ts` (193L)

```typescript
// BEFORE:
const mockRuns: Run[] = [
  {
    id: "run-1",
    strategy_id: "sma-crossover",
    mode: "backtest",
    status: "completed",
    symbols: ["BTC/USD"],
    timeframe: "1h",
    config: {},
    created_at: "2024-01-01T00:00:00Z",
  },
  ...
];

// AFTER:
const mockRuns: Run[] = [
  {
    id: "run-1",
    strategy_id: "sma-crossover",
    mode: "backtest",
    status: "completed",
    config: { symbols: ["BTC/USD"], timeframe: "1h" },
    created_at: "2024-01-01T00:00:00Z",
  },
  ...
];
```

Also add mock handler for `GET /api/v1/strategies`:

> **MSW version**: The project uses MSW v2 (`"^2.12.8"` in package.json). All handlers use `import { http, HttpResponse } from "msw"` — **NOT** the v1 `rest` API.

```typescript
http.get(`${API_BASE}/strategies`, () => {
  return HttpResponse.json([
    {
      id: "sample",
      name: "Sample Mean-Reversion Strategy",
      version: "1.0.0",
      description: "Simple mean-reversion strategy for testing",
      author: "weaver",
      config_schema: {
        type: "object",
        properties: {
          symbols: { type: "array", items: { type: "string" } },
          timeframe: { type: "string", default: "1m" },
        },
        required: ["symbols"],
      },
    },
    {
      id: "sma-crossover",
      name: "SMA Crossover Strategy",
      version: "1.0.0",
      description: "Simple Moving Average crossover strategy",
      author: "weaver",
      config_schema: {
        type: "object",
        properties: {
          symbols: { type: "array", items: { type: "string" } },
          timeframe: { type: "string", default: "1m" },
          fast_period: { type: "integer", default: 5 },
          slow_period: { type: "integer", default: 20 },
        },
        required: ["symbols"],
      },
    },
  ]);
}),
```

POST `/runs` handler:

```typescript
// BEFORE (MSW v2 syntax):
http.post(`${API_BASE}/runs`, async ({ request }) => {
  const body = await request.json();
  return HttpResponse.json(
    {
      ...body,
      id: "new-run-id",
      status: "pending",
      symbols: body.symbols,
      timeframe: body.timeframe || "1m",
    },
    { status: 201 },
  );
});

// AFTER:
http.post(`${API_BASE}/runs`, async ({ request }) => {
  const body = await request.json();
  return HttpResponse.json(
    {
      id: "new-run-id",
      strategy_id: body.strategy_id,
      mode: body.mode,
      status: "pending",
      config: body.config,
      created_at: new Date().toISOString(),
    },
    { status: 201 },
  );
});
```

### Step 6.8 — Validate

```bash
cd haro
npm test -- --run
npm run build  # verify no TypeScript errors
```

---

## Exit Gate

All criteria must pass before M12 is considered complete:

| #   | Criterion                                                                              | Verification                                                                                                                                                                          |
| --- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 1   | `RunCreate` schema only has `strategy_id`, `mode`, `config`                            | `pytest tests/unit/glados/test_schemas.py`                                                                                                                                            |
| 2   | `RunResponse` has `config` (not `symbols`/`timeframe`)                                 | Same                                                                                                                                                                                  |
| 3   | `Run` dataclass has `config: dict` (not `symbols`/`timeframe`/`start_time`/`end_time`) | `grep -Pn '\brun\.symbols\b\|\brun\.timeframe\b\|self\.symbols\b\|self\.timeframe\b' src/glados/services/run_manager.py` returns 0 (note: `run.config.get("symbols")` is expected/OK) |
| 4   | `RunRecord` has `config JSONB NOT NULL`, no `symbols`/`timeframe` columns              | Alembic migration passes; `test_has_required_columns` updated                                                                                                                         |
| 5   | `BaseStrategy.initialize()` takes `config: dict`                                       | `grep "def initialize" src/marvin/base_strategy.py` shows `config: dict`                                                                                                              |
| 6   | `StrategyRunner.initialize()` takes `config: dict`                                     | Same check                                                                                                                                                                            |
| 7   | `STOP_RUN` action type exists and emits `run.StopRequested` event                      | Test passes                                                                                                                                                                           |
| 8   | `StrategyAction.exchange` field exists (not wired)                                     | Test passes                                                                                                                                                                           |
| 9   | `StrategyMeta.config_schema` exists, strategies have JSON Schema                       | `test_strategy_meta.py` passes                                                                                                                                                        |
| 10  | `GET /api/v1/strategies` returns list with `config_schema`                             | `test_strategies.py` passes                                                                                                                                                           |
| 11  | App refuses to start without `DB_URL`                                                  | `test_app_requires_db.py` passes                                                                                                                                                      |
| 12  | `BacktestClock` reads `backtest_start`/`backtest_end` from `run.config`                | `test_run_manager_backtest.py` passes                                                                                                                                                 |
| 13  | Frontend `Run`/`RunCreate` types use `config` (not `symbols`)                          | `npm test` passes                                                                                                                                                                     |
| 14  | Frontend strategy dropdown with RJSF renders config form                               | Test passes                                                                                                                                                                           |
| 15  | Frontend Runs table shows Symbols + Timeframe columns (sourced from `config`)          | Test passes                                                                                                                                                                           |
| 16  | Frontend ActivityFeed shows `strategy_id (mode)`                                       | Test passes                                                                                                                                                                           |
| 17  | All 1137 existing tests pass (after updates)                                           | `pytest tests/ -x -q && cd haro && npm test`                                                                                                                                          |
| 18  | ~65 new tests added                                                                    | Count: `pytest --co -q \| wc -l`                                                                                                                                                      |
| 19  | E2E tests pass with new API shape                                                      | `pytest tests/e2e -x -q`                                                                                                                                                              |
| 20  | No `symbols` or `timeframe` as top-level fields on Run/RunCreate anywhere              | `grep -Pn '^\s+symbols:                                                                                                                                                               | ^\s+timeframe:' src/glados/schemas.py` returns 0 (ignores occurrences inside comments/descriptions) |

---

## Risk Assessment

| Risk                                    | Probability | Impact | Mitigation                                 |
| --------------------------------------- | ----------- | ------ | ------------------------------------------ |
| S1 blast radius breaks many tests       | Medium      | High   | TDD: update tests first, run incrementally |
| E2E tests break after API change        | High        | Medium | E2E helpers updated in Phase 1 Step 1.6    |
| Migration fails on existing dev data    | Low         | Low    | `docker compose down -v` to recreate       |
| Frontend build breaks during transition | Medium      | Medium | Phase 6 last — backend stable first        |
| RJSF styling doesn't match existing UI  | Medium      | Low    | Custom widgets / CSS override              |
| jsonschema validation too strict        | Low         | Low    | Schema is optional per strategy            |

---

## Summary of Decision Points

| #    | Decision                | Decision                     |
| ---- | ----------------------- | ---------------------------- |
| D-1  | Migration strategy (S1) | **A: Big bang**              |
| D-2  | Config access pattern   | **A: Direct dict**           |
| D-3  | DB column handling      | **A: Drop columns**          |
| D-4  | initialize() signature  | **A: Pure config dict**      |
| D-5  | STOP_RUN implementation | **A: Event-driven**          |
| D-6  | Exchange param scope    | **C: Field only**            |
| D-7  | config_schema format    | **A: JSON Schema**           |
| D-8  | Missing DB_URL handling | **C: Always require DB**     |
| D-9  | Backtest config keys    | **A: backtest_start/end**    |
| D-10 | Dynamic config form     | **B: react-jsonschema-form** |

---

_Status: DETAILED PLAN COMPLETE. All 6 phases specified to file-level with exact before/after code, TDD test specs, and validation commands. Ready for execution._
