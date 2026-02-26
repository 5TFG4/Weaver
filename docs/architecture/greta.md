# Greta (Backtest Engine)

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: backtest execution model, simulated fills, and per-run lifecycle.  
> **Authoritative for**: Greta runtime behavior, state isolation, and output artifacts.  
> **Not authoritative for**: live-trading order submission path (see `veda.md`).

## 1. Responsibility & Boundary

Greta is Weaver's backtest execution engine. It replays historical bars, simulates order fills, tracks positions/equity, and emits domain events used by Marvin and GLaDOS.

Core boundary:

- **Input**: routed `backtest.*` requests + clock ticks
- **State**: per-run simulation state only
- **Output**: `data.WindowReady` and `orders.*` events + `BacktestResult`

## 2. Instance Model (Per-Run)

`GretaService` is a **per-run instance**, not a singleton.

Each run gets an isolated instance because the following state is run-scoped:

- positions
- pending orders
- fills
- equity curve
- current bar cache and timeline cursor

Shared dependencies:

- `BarRepository` (singleton, immutable historical data)
- `EventLog` (singleton event bus)

## 3. Backtest Lifecycle

### 3.1 Initialize

`GretaService.initialize(symbols, timeframe, start, end)`:

1. resets per-run mutable state,
2. preloads bars from `BarRepository` into in-memory cache,
3. subscribes to `backtest.FetchWindow` filtered by `run_id`.

### 3.2 Tick Advancement

`GretaService.advance_to(timestamp)`:

1. updates current bars,
2. processes pending orders for potential fills,
3. marks positions to market,
4. appends equity point.

### 3.3 Completion

At run stop/completion:

- service returns `BacktestResult` (stats/equity/fills),
- subscriptions are removed,
- instance is discarded by `RunManager`.

## 4. Data Window Flow

For strategy data requests:

1. Marvin emits `strategy.FetchWindow`.
2. DomainRouter rewrites to `backtest.FetchWindow` for backtest mode.
3. Greta receives run-filtered request, reads from preloaded cache, emits `data.WindowReady`.
4. Marvin consumes `data.WindowReady` and continues strategy logic.

## 5. Fill Simulation

`DefaultFillSimulator` supports:

- `market` (open/close/vwap behavior by config)
- `limit` (buy: `low <= limit`; sell: `high >= limit`)
- `stop` (buy: `high >= stop`; sell: `low <= stop`)

Simulation controls (`FillSimulationConfig`):

- slippage model + basis points
- commission basis points + minimum commission
- fill reference price (`open|close|vwap|worst`)

`SimulatedFill` records immutable audit fields:

- order/client IDs, symbol/side/qty
- fill price, commission, slippage
- timestamp and bar index

## 6. Position & Equity Accounting

Greta tracks:

- per-symbol `SimulatedPosition` (qty, avg entry, unrealized/realized PnL),
- cash balance,
- equity curve (timestamp, equity),
- cumulative fill history.

Output `BacktestResult` includes summary stats (`BacktestStats`) and full fill/equity artifacts.

## 7. Event Contract (Backtest Path)

Common events in Greta flow:

- inbound: `backtest.FetchWindow`, `backtest.PlaceOrder`
- outbound data: `data.WindowReady`
- outbound order lifecycle: `orders.Created`, `orders.Filled`, `orders.Rejected`, `orders.Cancelled`

Event names are case-sensitive and forwarded to SSE as `event: <Envelope.type>`.

## 8. Key Files

- `src/greta/greta_service.py`
- `src/greta/fill_simulator.py`
- `src/greta/models.py`

---

_Last updated: 2026-02-26 (M8-D)_
