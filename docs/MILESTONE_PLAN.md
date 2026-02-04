# Weaver Milestone Plan (2026-02-03)

> **Current State**: M4 Complete, 631 tests passing  
> **Remaining Work**: M5 → M6 → M7 → M8  
> **Estimated Total**: ~230 new tests, 7-8 weeks

---

## Executive Summary

All pending tasks have been consolidated and reorganized into 4 milestones:

| Milestone | Name | Core Objective | Est. Tests |
|-----------|------|----------------|------------|
| **M5** | Marvin Core | Strategy system + Plugin architecture | ~80 |
| **M6** | Live Trading | Paper/Live trading flow | ~60 |
| **M7** | Haro Frontend | React UI + SSE | ~50 |
| **M8** | Polish & E2E | Code quality + End-to-end tests | ~40 |

**Key Changes**:
1. M5 focuses on Marvin strategy system (excludes Live Trading)
2. New M6 dedicated to Live Trading flow
3. M7 changed to Frontend development
4. M8 for Polish + E2E testing

---

## 1. M5: Marvin Core (Strategy System)

> **Goal**: Complete strategy loading, execution, and backtest core flow  
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

### 2.1 Exit Gate (Definition of Done)

- [ ] PluginAdapterLoader implemented (exchange adapter plugins)
- [ ] AlpacaAdapter initialized with real clients
- [ ] VedaService routed to order endpoints
- [ ] Paper Trading orders can be submitted and filled
- [ ] Live Run uses RealtimeClock

### 2.2 MVP Breakdown

| MVP | Focus | Tests | Dependencies |
|-----|-------|-------|--------------|
| M6-1 | Plugin Adapter Loader | ~10 | - |
| M6-2 | AlpacaAdapter Init | ~12 | M6-1 |
| M6-3 | VedaService Routing | ~10 | - |
| M6-4 | Live Order Flow | ~15 | M6-2, M6-3 |
| M6-5 | Run Mode Integration | ~8 | M6-4 |

### 2.3 Detailed Tasks

#### M6-1: Plugin Adapter Loader (~10 tests)
```
- [ ] Create AdapterMeta dataclass
- [ ] Implement PluginAdapterLoader
- [ ] Add ADAPTER_META to alpaca_adapter.py
- [ ] Add ADAPTER_META to mock_adapter.py
- [ ] Remove hardcoded imports from adapters/__init__.py
- [ ] Test: discover adapters in directory
- [ ] Test: load by ID
- [ ] Test: deleted adapter = system works
- [ ] Test: feature support query
```

#### M6-2: AlpacaAdapter Init (~12 tests)
```
- [ ] Add connect() method
- [ ] Initialize TradingClient (stocks)
- [ ] Initialize CryptoHistoricalDataClient (crypto)
- [ ] Connection verification (ping/account query)
- [ ] Error handling: invalid credentials
- [ ] Error handling: network timeout
- [ ] Test: connection success
- [ ] Test: Paper vs Live mode
```

#### M6-3: VedaService Routing (~10 tests)
```
- [ ] Add get_veda_service to dependencies.py
- [ ] Order routes use VedaService
- [ ] Remove/deprecate MockOrderService
- [ ] Test: route correctly injects VedaService
- [ ] Test: order creation via VedaService
```

#### M6-4: Live Order Flow (~15 tests)
```
- [ ] VedaService subscribes to live.PlaceOrder
- [ ] DomainRouter routes to live.* in live mode
- [ ] Order status sync (submitted → filled)
- [ ] Test: paper order submit
- [ ] Test: paper order fill
- [ ] Test: order cancel
- [ ] Test: partial fill
```

#### M6-5: Run Mode Integration (~8 tests)
```
- [ ] RunManager supports Live Run (RealtimeClock)
- [ ] Live Run uses real market time
- [ ] Correct switch between Backtest/Live
- [ ] Test: create live run
- [ ] Test: live run uses RealtimeClock
- [ ] Test: stop live run
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
