# Marvin (Strategy Runtime)

> Part of [Architecture Documentation](../ARCHITECTURE.md)
>
> **Document Charter**  
> **Primary role**: strategy plugin model, strategy execution loop, and action-to-event translation.  
> **Authoritative for**: Marvin lifecycle and strategy integration contract.  
> **Not authoritative for**: exchange adapter behavior (see `veda.md`).

## 1. Responsibility & Boundary

Marvin hosts strategy logic in a mode-agnostic way. Strategies never call live/backtest services directly; they emit intent through typed actions, which are translated into domain events.

Boundary:

- **Input**: clock ticks + `data.WindowReady`
- **Output**: `strategy.FetchWindow` / `strategy.PlaceRequest`
- **Isolation key**: `run_id`

## 2. Strategy Contract

Strategies implement `BaseStrategy`:

- `initialize(symbols)`
- `on_tick(tick) -> list[StrategyAction]`
- `on_data(data) -> list[StrategyAction]`

Action model (`StrategyAction`):

- `FETCH_WINDOW`
- `PLACE_ORDER`

Order intents carry side/type/qty and optional limit/stop prices.

## 3. StrategyRunner Lifecycle

`StrategyRunner` is created per run and bound to one strategy instance.

Lifecycle:

1. `initialize(run_id, symbols)` calls strategy initialize and subscribes to `data.WindowReady` filtered by run.
2. `on_tick()` executes strategy logic and emits translated events.
3. `on_data_ready()` feeds data payload back into strategy and emits follow-up actions.
4. `cleanup()` unsubscribes from EventLog.

`cleanup()` is invoked explicitly by `RunManager` during stop/completion/error teardown,
so per-run subscriptions are not left behind across run lifecycle transitions.

## 4. Action → Event Translation

`StrategyRunner` emits:

- `strategy.FetchWindow` from `FETCH_WINDOW`
- `strategy.PlaceRequest` from `PLACE_ORDER`

Payload rules:

- decimals are serialized as strings to preserve precision,
- all emitted events carry the run's `run_id`,
- producer is `marvin.runner`.

## 5. Plugin Strategy Loading

`PluginStrategyLoader` provides auto-discovery and lazy loading:

- scans `src/marvin/strategies/` for `STRATEGY_META`,
- extracts metadata via AST without importing broken modules,
- resolves dependencies with cycle detection,
- imports strategy class only when loaded.

Failure modes include:

- missing strategy (`StrategyNotFoundError`),
- missing dependency (`DependencyError`),
- circular dependency (`CircularDependencyError`).

## 6. Integration Pattern

Marvin does not know run mode. Mode-specific routing is delegated to DomainRouter:

`strategy.* -> live.*` for paper/live runs,
`strategy.* -> backtest.*` for backtest runs.

This keeps strategy code shared across live and simulation paths.

## 7. Key Files

- `src/marvin/base_strategy.py`
- `src/marvin/strategy_runner.py`
- `src/marvin/strategy_loader.py`
- `src/marvin/strategies/` (plugins)

---

_Last updated: 2026-02-26 (M8-D)_
