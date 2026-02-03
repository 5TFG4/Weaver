# M6 – Live Trading (Paper/Live Flow)

> **Status**: Planning  
> **Duration**: ~1.5-2 weeks  
> **Target**: ~60 new tests  
> **Prerequisites**: M5 Complete (Marvin Core)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Architecture Overview](#3-architecture-overview)
4. [Detailed Design](#4-detailed-design)
5. [MVP Implementation Plan](#5-mvp-implementation-plan)
6. [Test Strategy](#6-test-strategy)
7. [Entry & Exit Gates](#7-entry--exit-gates)
8. [Risk & Mitigations](#8-risk--mitigations)
9. [Appendix](#9-appendix)

---

## 1. Executive Summary

M6 adds live trading capability to Weaver through the Alpaca Paper Trading API. This milestone bridges the gap between backtesting (M4-M5) and real-world trading by:

1. **AlpacaAdapter Implementation**: Real API integration with Alpaca for order submission and market data
2. **VedaService Routing**: Wire VedaService to GLaDOS routes for live order management
3. **Live Order Flow**: Complete paper trading flow with event emission and persistence
4. **Plugin Adapter Loader**: Extensible adapter architecture for future exchange integrations

**Target**: Paper trading operational with SMA strategy

---

## 2. Goals & Non-Goals

### Goals (M6)

| ID | Goal | MVP |
|----|------|-----|
| G1 | AlpacaAdapter connects and submits orders | M6-1 |
| G2 | VedaService wired to /orders routes | M6-2 |
| G3 | Live order flow emits events and persists | M6-3 |
| G4 | Plugin adapter loader for extensibility | M6-4 |
| G5 | Paper trading E2E test passes | M6-3 |

### Non-Goals (Deferred to M7+)

- Frontend UI for trading
- Real money trading (live API keys)
- Multiple exchange support (beyond Alpaca)
- WebSocket streaming for live data
- Advanced order types (OCO, bracket, etc.)

---

## 3. Architecture Overview

### Live Trading Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Live Trading Architecture                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐ │
│  │ GLaDOS   │───►│ VedaService │───►│OrderManager │───►│AlpacaAdapter │ │
│  │ /orders  │    │             │    │             │    │              │ │
│  └──────────┘    └─────────────┘    └─────────────┘    └──────┬───────┘ │
│                                                               │         │
│                                                               ▼         │
│                                                    ┌──────────────────┐ │
│                                                    │  Alpaca Paper    │ │
│                                                    │  Trading API     │ │
│                                                    └──────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| GLaDOS /orders | REST API endpoint for order operations |
| VedaService | Order orchestration and validation |
| OrderManager | Order state machine and persistence |
| AlpacaAdapter | Alpaca API client wrapper |
| EventLog | Audit trail of all order events |

---

## 4. Detailed Design

### 4.1 AlpacaAdapter Implementation

```python
# src/veda/adapters/alpaca_adapter.py

from alpaca.trading.client import TradingClient
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient

ADAPTER_META = {
    "id": "alpaca",
    "name": "Alpaca Markets",
    "version": "1.0.0",
    "class": "AlpacaAdapter",
    "supported_features": ["stocks", "crypto", "paper_trading"],
}

class AlpacaAdapter(ExchangeAdapter):
    """Alpaca exchange adapter with real API clients."""
    
    def __init__(self, credentials: AlpacaCredentials) -> None:
        self._credentials = credentials
        self._trading_client: TradingClient | None = None
        self._crypto_data_client: CryptoHistoricalDataClient | None = None
        self._stock_data_client: StockHistoricalDataClient | None = None
        self._connected = False
    
    async def connect(self) -> None:
        """Initialize API clients."""
        if self._connected:
            return
        
        self._trading_client = TradingClient(
            api_key=self._credentials.api_key,
            secret_key=self._credentials.api_secret,
            paper=self._credentials.paper
        )
        
        self._crypto_data_client = CryptoHistoricalDataClient(
            api_key=self._credentials.api_key,
            secret_key=self._credentials.api_secret
        )
        
        self._stock_data_client = StockHistoricalDataClient(
            api_key=self._credentials.api_key,
            secret_key=self._credentials.api_secret
        )
        
        # Verify connection
        account = self._trading_client.get_account()
        if account.status != "ACTIVE":
            raise ConnectionError(f"Alpaca account not active: {account.status}")
        
        self._connected = True
    
    async def disconnect(self) -> None:
        """Clean up clients."""
        self._trading_client = None
        self._crypto_data_client = None
        self._stock_data_client = None
        self._connected = False
    
    async def submit_order(self, intent: OrderIntent) -> OrderResponse:
        """Submit order to Alpaca."""
        if not self._connected:
            raise RuntimeError("AlpacaAdapter not connected")
        
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        # Convert to Alpaca order request
        if intent.order_type == OrderType.MARKET:
            request = MarketOrderRequest(
                symbol=intent.symbol.replace("/", ""),  # BTC/USD -> BTCUSD
                qty=float(intent.qty),
                side=OrderSide.BUY if intent.side == VedaOrderSide.BUY else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
        else:
            request = LimitOrderRequest(
                symbol=intent.symbol.replace("/", ""),
                qty=float(intent.qty),
                side=OrderSide.BUY if intent.side == VedaOrderSide.BUY else OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                limit_price=float(intent.limit_price)
            )
        
        order = self._trading_client.submit_order(request)
        
        return OrderResponse(
            order_id=order.id,
            client_order_id=order.client_order_id,
            status=self._map_status(order.status),
            filled_qty=Decimal(str(order.filled_qty or 0)),
            filled_avg_price=Decimal(str(order.filled_avg_price or 0))
        )
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime
    ) -> list[Bar]:
        """Fetch historical bars from Alpaca."""
        if not self._connected:
            raise RuntimeError("AlpacaAdapter not connected")
        
        from alpaca.data.timeframe import TimeFrame
        from alpaca.data.requests import CryptoBarsRequest
        
        if "/" in symbol:  # Crypto uses / separator
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol.replace("/", ""),
                timeframe=self._map_timeframe(timeframe),
                start=start,
                end=end
            )
            bars_df = self._crypto_data_client.get_crypto_bars(request).df
        else:
            # Stock implementation...
            pass
        
        return [
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=idx,
                open=Decimal(str(row.open)),
                high=Decimal(str(row.high)),
                low=Decimal(str(row.low)),
                close=Decimal(str(row.close)),
                volume=Decimal(str(row.volume))
            )
            for idx, row in bars_df.iterrows()
        ]
```

### 4.2 VedaService Wiring to Routes

```python
# src/glados/routes/orders.py

from src.glados.dependencies import get_veda_service

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    veda_service: VedaService = Depends(get_veda_service)
) -> OrderResponse:
    """Create a new order via VedaService."""
    intent = OrderIntent(
        symbol=order.symbol,
        side=order.side,
        qty=order.qty,
        order_type=order.order_type,
        limit_price=order.limit_price,
        client_order_id=order.client_order_id or str(uuid4())
    )
    
    result = await veda_service.place_order(intent)
    
    return OrderResponse(
        order_id=result.order_id,
        client_order_id=result.client_order_id,
        status=result.status,
        symbol=order.symbol,
        side=order.side,
        qty=order.qty
    )
```

### 4.3 Live Order Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Live Order Flow (Paper Mode)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. POST /orders                                                        │
│     └──► OrderRoute.create_order()                                      │
│              │                                                          │
│  2.          └──► VedaService.place_order(intent)                       │
│                        │                                                │
│  3.                    └──► OrderManager.submit(intent)                 │
│                                  │                                      │
│  4.                              ├──► Persist to DB (pending)           │
│                                  │                                      │
│  5.                              └──► AlpacaAdapter.submit_order()      │
│                                            │                            │
│  6.                                        └──► Alpaca Paper API        │
│                                                     │                   │
│  7.                              ◄── OrderResponse ─┘                   │
│                                  │                                      │
│  8.                              ├──► Update DB (status)                │
│                                  │                                      │
│  9.                              └──► EventLog.append(orders.Created)   │
│                                                                         │
│  10. Return to client                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Plugin Adapter Loader

```python
# src/veda/adapter_loader.py

from pathlib import Path
import ast

class PluginAdapterLoader:
    """Plugin-based adapter loader with auto-discovery."""
    
    def __init__(self, adapter_dir: Path | None = None):
        self._adapter_dir = adapter_dir or Path(__file__).parent / "adapters"
        self._metadata: dict[str, AdapterMeta] = {}
        self._loaded: dict[str, ExchangeAdapter] = {}
        self._scan_adapters()
    
    def _scan_adapters(self) -> None:
        """Scan adapter directory for plugins."""
        for file in self._adapter_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            
            meta = self._extract_metadata(file)
            if meta:
                self._metadata[meta.id] = meta
    
    def _extract_metadata(self, path: Path) -> AdapterMeta | None:
        """Extract ADAPTER_META without importing module."""
        try:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "ADAPTER_META":
                            # Extract dict values
                            return self._parse_meta_dict(node.value, path)
        except Exception:
            return None
        return None
    
    def list_available(self) -> list[AdapterMeta]:
        """List all discovered adapters."""
        return list(self._metadata.values())
    
    def load(self, adapter_id: str, credentials: Any) -> ExchangeAdapter:
        """Load and instantiate adapter by ID."""
        if adapter_id not in self._metadata:
            raise AdapterNotFoundError(f"Adapter not found: {adapter_id}")
        
        meta = self._metadata[adapter_id]
        
        # Dynamic import
        module = importlib.import_module(f"src.veda.adapters.{meta.module_path}")
        adapter_class = getattr(module, meta.class_name)
        
        return adapter_class(credentials)
```

---

## 5. MVP Implementation Plan

> **Development Methodology**: TDD (Test-Driven Development)  
> **Pattern**: Write tests (RED) → Implement (GREEN) → Refactor (BLUE)

### MVP Overview

| MVP | Focus | Tests | Priority | Dependencies |
|-----|-------|-------|----------|--------------|
| M6-1 | AlpacaAdapter Init | ~15 | P0 | M5 |
| M6-2 | VedaService Routing | ~12 | P0 | M6-1 |
| M6-3 | Live Order Flow | ~15 | P0 | M6-2 |
| M6-4 | Plugin Adapter Loader | ~10 | P1 | M6-1 |

**Estimated Total: ~52 new tests** (allowing for ~8 integration tests)

---

### M6-1: AlpacaAdapter Init (~15 tests)

**Goal**: Initialize AlpacaAdapter with real API clients.

#### TDD Test Cases

```python
# tests/unit/veda/test_alpaca_adapter.py

class TestAlpacaAdapterInit:
    """Tests for AlpacaAdapter initialization."""
    
    async def test_connect_creates_trading_client(self, mock_alpaca_api):
        """connect() creates TradingClient."""
        adapter = AlpacaAdapter(credentials)
        await adapter.connect()
        assert adapter._trading_client is not None
    
    async def test_connect_creates_crypto_data_client(self, mock_alpaca_api):
        """connect() creates CryptoHistoricalDataClient."""
        ...
    
    async def test_connect_verifies_account_status(self, mock_alpaca_api):
        """connect() verifies account is active."""
        ...
    
    async def test_connect_inactive_account_raises(self, mock_alpaca_api):
        """connect() raises if account not ACTIVE."""
        mock_alpaca_api.account.status = "INACTIVE"
        adapter = AlpacaAdapter(credentials)
        
        with pytest.raises(ConnectionError, match="not active"):
            await adapter.connect()
    
    async def test_disconnect_clears_clients(self):
        """disconnect() sets all clients to None."""
        ...
    
    async def test_submit_order_requires_connection(self):
        """submit_order() raises RuntimeError if not connected."""
        adapter = AlpacaAdapter(credentials)
        
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.submit_order(OrderIntent(...))
    
    async def test_submit_market_order(self, mock_alpaca_api):
        """submit_order() sends market order correctly."""
        ...
    
    async def test_submit_limit_order(self, mock_alpaca_api):
        """submit_order() sends limit order correctly."""
        ...
    
    async def test_symbol_conversion(self, mock_alpaca_api):
        """BTC/USD converted to BTCUSD for Alpaca."""
        ...
    
    async def test_paper_mode_flag(self, mock_alpaca_api):
        """paper=True passed to TradingClient."""
        ...
    
    async def test_get_bars_crypto(self, mock_alpaca_api):
        """get_bars() fetches crypto bars correctly."""
        ...
    
    async def test_get_bars_requires_connection(self):
        """get_bars() raises RuntimeError if not connected."""
        ...


# tests/fixtures/http.py - Add Alpaca mocks

@pytest.fixture
def mock_alpaca_api(mocker):
    """Mock Alpaca API clients."""
    mock_trading = mocker.patch("alpaca.trading.client.TradingClient")
    mock_trading.return_value.get_account.return_value = MockAccount(status="ACTIVE")
    
    mock_crypto = mocker.patch("alpaca.data.historical.CryptoHistoricalDataClient")
    
    return SimpleNamespace(trading=mock_trading, crypto=mock_crypto)
```

---

### M6-2: VedaService Routing (~12 tests)

**Goal**: Wire VedaService to order routes.

#### TDD Test Cases

```python
# tests/unit/glados/routes/test_order_routes_veda.py

class TestOrderRoutesWithVeda:
    """Tests for order routes using VedaService."""
    
    async def test_create_order_calls_veda_service(self, client, mock_veda):
        """POST /orders calls VedaService.place_order."""
        response = await client.post("/orders", json={...})
        
        mock_veda.place_order.assert_called_once()
    
    async def test_create_order_passes_intent_correctly(self, client, mock_veda):
        """Order intent fields mapped correctly."""
        ...
    
    async def test_create_order_returns_response(self, client, mock_veda):
        """Response includes order_id and status."""
        ...
    
    async def test_create_order_validation_error(self, client):
        """Invalid order returns 422."""
        response = await client.post("/orders", json={"invalid": "data"})
        assert response.status_code == 422
    
    async def test_order_persisted_to_db(self, client, mock_veda, db_session):
        """Order record created in database."""
        ...
    
    async def test_order_created_event_emitted(self, client, mock_veda, event_log):
        """orders.Created event emitted."""
        ...
    
    async def test_get_order_by_id(self, client, mock_veda):
        """GET /orders/{id} returns order details."""
        ...
    
    async def test_cancel_order(self, client, mock_veda):
        """DELETE /orders/{id} cancels order."""
        ...
```

---

### M6-3: Live Order Flow (~15 tests)

**Goal**: Complete live order flow with paper mode.

#### TDD Test Cases

```python
# tests/integration/test_live_order_flow.py

class TestLiveOrderFlow:
    """Integration tests for live order flow."""
    
    async def test_live_run_creates_realtime_clock(self, run_manager):
        """Live run uses RealtimeClock."""
        run = await run_manager.create_run(mode=RunMode.LIVE, ...)
        assert isinstance(run.clock, RealtimeClock)
    
    async def test_strategy_place_request_routes_to_veda(self, event_log, mock_veda):
        """strategy.PlaceRequest routes to live.PlaceOrder → VedaService."""
        ...
    
    async def test_order_submitted_to_alpaca(self, mock_alpaca):
        """Order submitted to Alpaca paper API."""
        ...
    
    async def test_fill_event_emitted_after_alpaca_response(self, mock_alpaca, event_log):
        """orders.Filled event emitted after Alpaca response."""
        ...
    
    async def test_order_persisted_with_alpaca_id(self, mock_alpaca, db_session):
        """Order persisted with Alpaca order ID."""
        ...
    
    async def test_full_live_order_flow(self, mock_alpaca, event_log, db_session):
        """E2E: POST /orders → Alpaca → Event → DB."""
        ...
    
    async def test_alpaca_error_handled_gracefully(self, mock_alpaca):
        """Alpaca API error returns appropriate error response."""
        mock_alpaca.submit_order.side_effect = AlpacaAPIError("Insufficient funds")
        ...
    
    async def test_order_status_updates_on_fill(self, mock_alpaca):
        """Order status updated when Alpaca reports fill."""
        ...
```

---

### M6-4: Plugin Adapter Loader (~10 tests)

**Goal**: Implement plugin architecture for exchange adapters.

#### TDD Test Cases

```python
# tests/unit/veda/test_adapter_loader.py

class TestPluginAdapterLoader:
    """Tests for plugin-based adapter loading."""
    
    @pytest.fixture
    def temp_adapter_dir(self, tmp_path):
        """Create temp directory with test adapter files."""
        adapter_dir = tmp_path / "adapters"
        adapter_dir.mkdir()
        
        (adapter_dir / "test_adapter.py").write_text('''
ADAPTER_META = {
    "id": "test-exchange",
    "name": "Test Exchange",
    "class": "TestAdapter",
}

class TestAdapter:
    def __init__(self, credentials): pass
    async def connect(self): pass
''')
        return adapter_dir
    
    def test_discovers_adapters_in_directory(self, temp_adapter_dir):
        """Scans adapters/ directory and finds all plugins."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        available = loader.list_available()
        
        assert len(available) >= 1
        assert any(a.id == "test-exchange" for a in available)
    
    def test_load_adapter_by_id(self, temp_adapter_dir):
        """Loads adapter by its declared ID."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        adapter = loader.load("test-exchange", credentials=None)
        
        assert adapter is not None
    
    def test_unknown_adapter_raises_not_found(self, temp_adapter_dir):
        """AdapterNotFoundError for unknown adapter_id."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        
        with pytest.raises(AdapterNotFoundError):
            loader.load("nonexistent", credentials=None)
    
    def test_extracts_metadata_without_importing(self, temp_adapter_dir):
        """Reads ADAPTER_META without full module import."""
        # Add file with import error
        (temp_adapter_dir / "broken.py").write_text('''
ADAPTER_META = {"id": "broken", "class": "Broken"}
import nonexistent_module
''')
        
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        available = loader.list_available()
        
        assert any(a.id == "broken" for a in available)
    
    def test_list_available_adapters(self, temp_adapter_dir):
        """list_available() returns all discovered adapters."""
        ...
    
    def test_deleted_adapter_not_discovered(self, temp_adapter_dir):
        """Deleted .py file is not in available list."""
        ...
    
    def test_adapter_supports_feature_check(self, temp_adapter_dir):
        """Can query adapter for supported features."""
        ...
```

---

## 6. Test Strategy

### Test Pyramid

```
              ┌─────────────────┐
              │  E2E Tests (3)  │  ← Full live trading flow
              │  test_e2e/      │
              └────────┬────────┘
                       │
        ┌──────────────┴──────────────┐
        │  Integration Tests (~15)    │  ← Multi-component tests
        │  test_integration/          │
        └──────────────┬──────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │         Unit Tests (~35)            │  ← Single component
    │  tests/unit/veda/, glados/routes/   │
    └─────────────────────────────────────┘
```

### Test Coverage Targets (M6)

| Module | Current (Post-M5) | Target |
|--------|-------------------|--------|
| Veda | ~197 | 230+ |
| GLaDOS | ~201 | 215+ |

---

## 7. Entry & Exit Gates

### Entry Gate (Before Starting M6)

- [ ] M5 complete (~60 tests, ~690 total)
- [ ] EventLog subscription works
- [ ] SMA strategy backtests successfully
- [ ] Plugin strategy loader implemented

### Exit Gate (M6 Complete)

| Requirement | Verification |
|-------------|--------------|
| AlpacaAdapter connects | Connection test with mock passes |
| AlpacaAdapter submits orders | Order submission test passes |
| VedaService wired to routes | Route integration test passes |
| Live order flow works | E2E paper trading test passes |
| Plugin adapter loader works | Auto-discovery tests pass |
| ~60 new tests | Test count ≥ 750 |

---

## 8. Risk & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Alpaca API changes | High | Low | Mock in tests, version pin |
| API rate limits | Medium | Medium | Implement rate limiting |
| Network failures | Medium | Medium | Retry logic with backoff |
| Paper/Live mode confusion | High | Low | Clear mode indicators |

---

## 9. Appendix

### A. File Change Summary

| Category | Files | Action |
|----------|-------|--------|
| Veda | adapters/alpaca_adapter.py | Modify |
| Veda | adapter_loader.py, adapter_meta.py | Create |
| GLaDOS | routes/orders.py | Modify |
| GLaDOS | dependencies.py | Modify |
| Tests | ~6 new test files | Create |

### B. Dependency Additions

```toml
# pyproject.toml additions
dependencies = [
    "alpaca-py>=0.10.0",
]
```

### C. Related Documents

| Document | Link |
|----------|------|
| M5 Design (Marvin Core) | [m5-marvin.md](m5-marvin.md) |
| M7 Design (Haro Frontend) | [m7-haro.md](m7-haro.md) |
| Veda Interfaces | [../../architecture/api.md](../../architecture/api.md) |
| Roadmap | [../../architecture/roadmap.md](../../architecture/roadmap.md) |
| Milestone Plan | [../../MILESTONE_PLAN.md](../../MILESTONE_PLAN.md) |

---

*Last Updated: 2025-02-03 (M6 design document created)*
