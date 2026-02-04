# Weaver Milestone Plan (2026-02-04)

> **Current State**: M6-3 Complete, 781 tests passing  
> **Remaining Work**: M6-4 → M6-5 → M7 → M8  
> **Estimated Total**: ~75 new tests remaining, 3-4 weeks

---

## Executive Summary

All pending tasks have been consolidated and reorganized into 4 milestones:

| Milestone | Name | Core Objective | Est. Tests | Status |
|-----------|------|----------------|------------|--------|
| **M5** | Marvin Core | Strategy system + Plugin architecture | 74 | ✅ DONE |
| **M6** | Live Trading | Paper/Live trading flow | ~65 | ⏳ M6-2 done (63 tests) |
| **M7** | Haro Frontend | React UI + SSE | ~50 | ⏳ |
| **M8** | Polish & E2E | Code quality + End-to-end tests | ~40 | ⏳ |

**M6-1 & M6-2 Complete**:
1. ✅ PluginAdapterLoader (mirrors PluginStrategyLoader pattern)
2. ✅ AdapterMeta dataclass with features support
3. ✅ ADAPTER_META added to AlpacaAdapter and MockExchangeAdapter
4. ✅ AST-based discovery without importing
5. ✅ AlpacaAdapter connect()/disconnect()/is_connected
6. ✅ _require_connection() guard on all methods

**M6 Remaining**:
- M6-3: VedaService wired to order routes
- M6-4: Live order flow with events + persistence
- M6-5: RealtimeClock for live runs

---

## 1. M5: Marvin Core (Strategy System) ✅ COMPLETE

> **Goal**: Complete strategy loading, execution, and backtest core flow  
> **Status**: ✅ COMPLETE (74 tests, 705 total)
> **Prerequisite**: M4 ✅  
> **Estimated Effort**: 2-3 weeks

### 1.1 Exit Gate (Definition of Done)

- [ ] EventLog subscription mechanism completed
- [ ] data.WindowReady event flow completed
- [ ] SMA strategy implemented and backtested successfully
- [ ] PluginStrategyLoader implemented (auto-discovery)
- [ ] System works after deleting strategy files

### 1.2 MVP Breakdown

| MVP | Focus | Tests | Dependencies |
|-----|-------|-------|--------------|
| M5-1 | EventLog Subscription | ~10 | - |
| M5-2 | data.WindowReady Flow | ~15 | M5-1 |
| M5-3 | SMA Strategy | ~12 | M5-2 |
| M5-4 | Plugin Strategy Loader | ~15 | M5-3 |
| M5-5 | Code Quality (Marvin) | ~8 | - |

### 1.3 Detailed Tasks

#### M5-1: EventLog Subscription (~10 tests)
```
- [ ] Add subscribe()/unsubscribe() to EventLog protocol
- [ ] Implement subscription in InMemoryEventLog
- [ ] Implement subscription in PostgresEventLog
- [ ] Test: multiple subscribers receive events
- [ ] Test: unsubscribed consumer stops receiving
```

#### M5-2: data.WindowReady Flow (~15 tests)
```
- [ ] StrategyRunner subscribes to data.WindowReady
- [ ] GretaService subscribes to backtest.FetchWindow (M4 deferred)
- [ ] GretaService emits data.WindowReady
- [ ] Test: complete FetchWindow → WindowReady chain
- [ ] Test: error handling when no data available
```

#### M5-3: SMA Strategy (~12 tests)
```
- [ ] Create src/marvin/strategies/ directory
- [ ] Implement SMAStrategy (dual moving average crossover)
- [ ] Configurable parameters: fast_period, slow_period
- [ ] Test: SMA calculation correctness
- [ ] Test: crossover signal generation
- [ ] Integration test: SMA backtest produces trades
```

#### M5-4: Plugin Strategy Loader (~15 tests)
```
- [ ] Create StrategyMeta dataclass
- [ ] Create @strategy decorator (optional)
- [ ] Implement PluginStrategyLoader (directory scanning)
- [ ] Dependency resolution (topological sort)
- [ ] Add STRATEGY_META to sample_strategy.py
- [ ] Remove hardcoded imports from __init__.py
- [ ] Test: discover strategies in directory
- [ ] Test: load by ID
- [ ] Test: dependency resolution
- [ ] Test: deleted strategy = system works
- [ ] Test: missing dependency error
```

#### M5-5: Code Quality - Marvin (~8 tests)
```
- [ ] SimulatedFill.side: str → OrderSide enum
- [ ] Extract SimpleTestStrategy to fixtures
- [ ] Extract MockStrategyLoader to fixtures
- [ ] Fix ClockTick duplicate definition
- [ ] Clock Union type (BacktestClock | RealtimeClock)
```

---

## 2. M6: Live Trading

> **Goal**: Complete paper/live trading full flow  
> **Prerequisite**: M5 ✅  
> **Estimated Effort**: 1.5-2 weeks  
> **Design Doc**: [m6-live-trading.md](archive/milestone-details/m6-live-trading.md)

### 2.1 Exit Gate (Definition of Done)

- [x] PluginAdapterLoader with auto-discovery (mirrors strategy pattern) ✅ 2026-02-04
- [x] AlpacaAdapter `connect()` initializes real clients ✅ 2026-02-04
- [x] VedaService wired to order routes (replaces MockOrderService) ✅ 2026-02-04
- [ ] Paper Trading orders persist + emit events
- [ ] Live Run uses RealtimeClock
- [ ] ~65 new tests (target: 770+)

### 2.2 MVP Breakdown

| MVP | Focus | Tests | Dependencies |
|-----|-------|-------|--------------|
| M6-1 | PluginAdapterLoader | 40 ✅ | - |
| M6-2 | AlpacaAdapter Connection | 23 ✅ | M6-1 ✅ |
| M6-3 | VedaService Routing | 13 ✅ | M6-2 ✅ |
| M6-4 | Live Order Flow | ~15 | M6-3 ✅ |
| M6-5 | Run Mode Integration | ~9 | M6-4 |

### 2.3 Detailed Tasks

#### M6-1: PluginAdapterLoader ✅ COMPLETE (40 tests)

**Files**: `adapter_meta.py`, `adapter_loader.py` (CREATED), adapters/*.py (MODIFIED)

```
- [x] Create AdapterMeta dataclass (id, name, version, class_name, features)
- [x] Implement PluginAdapterLoader with AST-based metadata extraction
- [x] Add ADAPTER_META to alpaca_adapter.py
- [x] Add ADAPTER_META to mock_adapter.py
- [x] Test: discover adapters in directory
- [x] Test: load adapter by ID
- [x] Test: pass credentials to adapter constructor
- [x] Test: unknown adapter raises AdapterNotFoundError
- [x] Test: extracts metadata without importing (AST)
- [x] Test: get_metadata(), supports_feature()
- [x] Test: empty directory returns empty list
- [x] Test: skip private files (_*)
```

#### M6-2: AlpacaAdapter Connection ✅ COMPLETE (23 tests)

**Files**: `adapters/alpaca_adapter.py` (MODIFIED)

```
- [x] Add connect() method
- [x] Initialize TradingClient with api_key, secret_key, paper
- [x] Initialize CryptoHistoricalDataClient
- [x] Initialize StockHistoricalDataClient
- [x] Verify connection via account status check
- [x] Add is_connected property
- [x] Add disconnect() method
- [x] Add _require_connection() guard
- [x] Test: connect creates all clients
- [x] Test: connect verifies account ACTIVE
- [x] Test: inactive account raises ConnectionError
- [x] Test: connect idempotent
- [x] Test: disconnect clears clients
- [x] Test: submit_order requires connection
- [ ] Test: paper/live mode flag passed correctly
```

#### M6-3: VedaService Routing ✅ COMPLETE (13 tests)

**Files**: `routes/orders.py` (MODIFIED), `schemas.py` (MODIFIED)

```
- [x] Add OrderCreate schema to schemas.py
- [x] Add POST /orders endpoint using VedaService
- [x] Add DELETE /orders/{id} endpoint for cancel
- [x] Handle 503 when VedaService not configured
- [x] _state_to_response() converter
- [x] _require_veda_service() dependency
- [x] Test: create_order calls VedaService.place_order
- [x] Test: intent fields mapped correctly
- [x] Test: returns OrderResponse
- [x] Test: 422 for invalid input
- [x] Test: 503 when no VedaService
- [x] Test: cancel_order calls VedaService
- [x] Test: cancel nonexistent returns 404
```

#### M6-4: Live Order Flow (~15 tests)

**Files**: `veda_service.py` (MODIFY), `app.py` (MODIFY), `test_live_order_flow.py` (CREATE)

```
- [ ] Add VedaService.connect() to initialize adapter
- [ ] Add VedaService.get_order() method
- [ ] Add VedaService.list_orders() method
- [ ] Connect adapter on app startup (in lifespan)
- [ ] Test: place_order persists to database
- [ ] Test: place_order emits orders.Created event
- [ ] Test: rejected order emits orders.Rejected event
- [ ] Test: order includes exchange_order_id
- [ ] Test: market order fills immediately (mock)
- [ ] Test: limit order stays ACCEPTED
- [ ] Test: get_order retrieves by ID
- [ ] Test: list_orders returns all
- [ ] Test: list_orders filters by run_id
- [ ] Test: idempotent submission (same client_order_id)
- [ ] Test: event includes correlation_id
```

#### M6-5: Run Mode Integration (~9 tests)

**Files**: `services/run_manager.py` (MODIFY)

```
- [ ] Create RealtimeClock for live runs
- [ ] Create BacktestClock for backtest runs
- [ ] RunManager.start() selects clock by mode
- [ ] Test: live run uses RealtimeClock
- [ ] Test: backtest run uses BacktestClock
- [ ] Test: realtime clock uses current time
- [ ] Test: backtest clock uses config times
- [ ] Test: stop run stops clock
- [ ] Test: run mode persisted
- [ ] Test: cannot start already running
- [ ] Test: live run emits run.Started with mode
```

---

## 3. M7: Haro Frontend

> **Goal**: React frontend to display trading status and data  
> **Prerequisite**: M6 ✅  
> **Estimated Effort**: 1.5-2 weeks

### 3.1 Exit Gate (Definition of Done)

- [ ] React app running in standalone container
- [ ] Dashboard page displays system status
- [ ] Runs page with list and details
- [ ] Orders page displays order status
- [ ] SSE real-time updates

### 3.2 MVP Breakdown

| MVP | Focus | Tests | Dependencies |
|-----|-------|-------|--------------|
| M7-1 | React App Scaffold | ~10 | - |
| M7-2 | Dashboard Page | ~10 | M7-1 |
| M7-3 | Runs Page | ~12 | M7-2 |
| M7-4 | Orders Page | ~10 | M7-3 |
| M7-5 | SSE Integration | ~8 | M7-4 |

### 3.3 Detailed Tasks

#### M7-1: React App Scaffold (~10 tests)
```
- [ ] Create src/haro/ React project
- [ ] Configure Vite + TypeScript
- [ ] Setup Docker build
- [ ] API client configuration
- [ ] Routing setup (React Router)
```

#### M7-2: Dashboard Page (~10 tests)
```
- [ ] System health status display
- [ ] Active run count
- [ ] Recent orders summary
- [ ] API connection status indicator
```

#### M7-3: Runs Page (~12 tests)
```
- [ ] Run list (paginated)
- [ ] Run detail page
- [ ] Create new run form
- [ ] Start/Stop actions
- [ ] Run status badges
```

#### M7-4: Orders Page (~10 tests)
```
- [ ] Order list (filter by run)
- [ ] Order details
- [ ] Status filter
- [ ] Time range filter
```

#### M7-5: SSE Integration (~8 tests)
```
- [ ] SSE client wrapper
- [ ] Auto-reconnection mechanism
- [ ] Event dispatch to components
- [ ] Optimistic updates + rollback
```

---

## 4. M8: Polish & E2E

> **Goal**: Code quality improvement + full E2E testing  
> **Prerequisite**: M7 ✅  
> **Estimated Effort**: 1-1.5 weeks

### 4.1 Exit Gate (Definition of Done)

- [ ] E2E tests pass (Playwright)
- [ ] Code coverage ≥80%
- [ ] All TODO/FIXME cleaned up
- [ ] Documentation complete

### 4.2 MVP Breakdown

| MVP | Focus | Tests | Dependencies |
|-----|-------|-------|--------------|
| M8-1 | E2E Test Setup | ~5 | - |
| M8-2 | E2E Backtest Flow | ~8 | M8-1 |
| M8-3 | E2E Live Flow | ~8 | M8-2 |
| M8-4 | Code Quality | ~10 | - |
| M8-5 | Documentation | - | M8-4 |

### 4.3 Detailed Tasks

#### M8-1: E2E Test Setup (~5 tests)
```
- [ ] Configure Playwright
- [ ] Setup test database
- [ ] Docker Compose for E2E
- [ ] Basic page load tests
```

#### M8-2: E2E Backtest Flow (~8 tests)
```
- [ ] Create backtest run
- [ ] View backtest progress
- [ ] View backtest results
- [ ] View generated orders
```

#### M8-3: E2E Live Flow (~8 tests)
```
- [ ] Create paper run
- [ ] Monitor real-time status
- [ ] Manually stop run
- [ ] Verify order status updates
```

#### M8-4: Code Quality (~10 tests)
```
- [ ] Clean all TODO/FIXME
- [ ] Fix Pylance/mypy warnings
- [ ] Add missing docstrings
- [ ] Configure strict type checking
- [ ] Remove unused code
- [ ] Advanced backtest stats (Sharpe, Drawdown)
- [ ] LISTEN/NOTIFY activation (optional)
```

#### M8-5: Documentation
```
- [ ] Update README with usage instructions
- [ ] Complete API documentation
- [ ] Deployment guide
- [ ] Strategy development guide
- [ ] Exchange adapter development guide
```

---

## 5. Backlog (Deferred Tasks)

The following tasks have been incorporated into milestones or deferred:

### Incorporated into Milestones

| Task | Source | Assigned To |
|------|--------|-------------|
| EventLog subscription | AUDIT 1.7 | M5-1 |
| GretaService subscribe FetchWindow | M4 defer | M5-2 |
| SimulatedFill.side enum | M4 note #4 | M5-5 |
| ClockTick duplicate | M4 note #5 | M5-5 |
| AlpacaAdapter init | AUDIT 1.4 | M6-2 |
| VedaService routing | AUDIT 1.3 | M6-3 |
| Sharpe ratio | greta TODO | M8-4 |
| Max drawdown | greta TODO | M8-4 |

### Deferred (M9+)

| Task | Reason |
|------|--------|
| Multiple simultaneous strategies | High complexity, future enhancement |
| Strategy optimization | Requires more infrastructure |
| Real money trading | Requires more security measures |
| WebSocket streaming | Polling sufficient for MVP |
| Multi-exchange support | Complete Alpaca first |

---

## 6. Timeline

```
Week 1-2   │██████████████████████│ M5: Marvin Core
Week 3-4   │██████████████████│     M6: Live Trading
Week 5-6   │██████████████████│     M7: Haro Frontend
Week 7     │████████████│           M8: Polish & E2E
```

### Key Dependencies

```
M4 (Done)
    │
    ▼
M5: Marvin Core ─────┐
    │                │
    ▼                ▼
M6: Live Trading ────┤
    │                │
    ▼                ▼
M7: Haro Frontend ───┤
    │                │
    ▼                ▼
M8: Polish & E2E
```

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Alpaca API changes | Low | High | Abstraction layer isolation, quick adaptation |
| Frontend development delay | Medium | Medium | Backend can complete first, CLI as fallback |
| Flaky E2E tests | Medium | Low | Retry mechanism, isolated test environment |
| Plugin architecture complexity | Low | Medium | AST parsing has mature solutions |

---

## 8. Success Metrics

### Test Count

| Milestone | New Tests | Cumulative |
|-----------|-----------|------------|
| M4 (Done) | - | 631 |
| M5 | ~80 | ~711 |
| M6 | ~60 | ~771 |
| M7 | ~50 | ~821 |
| M8 | ~40 | ~861 |

### Coverage Targets

| Module | Target |
|--------|--------|
| events/ | 90% |
| glados/ | 85% |
| veda/ | 85% |
| greta/ | 90% |
| marvin/ | 85% |
| walle/ | 80% |
| haro/ | 75% |

---

*Last Updated: 2026-02-03*
*Total Estimated New Tests: ~230*
*Total Estimated Timeline: 7-8 weeks*
