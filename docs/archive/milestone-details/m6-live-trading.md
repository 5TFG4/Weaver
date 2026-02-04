# M6: Live Trading (Paper/Live Flow)

> **Status**: ⏳ Planning Complete  
> **Prerequisite**: M5 (Marvin Core) ✅  
> **Estimated Effort**: 1.5-2 weeks  
> **Target Tests**: ~65 new tests (total: ~770)

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

M6 enables live trading through the Alpaca Paper Trading API. This milestone bridges the gap between backtesting (M4-M5) and real-world trading by completing the "last mile" of the trading system.

### Key Deliverables

| Deliverable | Description |
|-------------|-------------|
| PluginAdapterLoader | Auto-discovery adapter loader (mirrors PluginStrategyLoader) |
| AlpacaAdapter Connection | Real API client initialization with `connect()` |
| VedaService Routing | Wire VedaService to order routes (replace MockOrderService) |
| Live Order Flow | Paper trading flow with persistence and events |
| Run Mode Integration | Live runs use RealtimeClock |

### Success Criteria

- Paper trading order submits to Alpaca and returns success
- Orders persisted to database with Alpaca order ID
- Events emitted for order lifecycle (Created, Filled, Rejected)
- Live runs use RealtimeClock instead of BacktestClock
- ~65 new tests (total: ~770)

### Key Changes from Draft M6

The previous draft has been reorganized:

1. **MVP Reordering**: PluginAdapterLoader now first (matches M5 strategy pattern)
2. **Clearer Scope**: Focus only on paper trading (no real money)
3. **More Test Cases**: Expanded from ~52 to ~65 tests
4. **Audit Fixes**: Incorporates fixes for AUDIT items 1.3, 1.4, 1.6

---

## 2. Goals & Non-Goals

### Goals (M6 Scope)

| ID | Goal | MVP | Priority |
|----|------|-----|----------|
| G1 | PluginAdapterLoader with auto-discovery | M6-1 | P0 |
| G2 | Add ADAPTER_META to existing adapters | M6-1 | P0 |
| G3 | AlpacaAdapter `connect()` initializes real clients | M6-2 | P0 |
| G4 | AlpacaAdapter connection verification (account ping) | M6-2 | P0 |
| G5 | VedaService wired to /orders routes | M6-3 | P0 |
| G6 | Deprecate/remove MockOrderService from routes | M6-3 | P1 |
| G7 | Live order flow emits events to EventLog | M6-4 | P0 |
| G8 | Orders persisted with Alpaca order ID | M6-4 | P0 |
| G9 | Live Run uses RealtimeClock | M6-5 | P0 |
| G10 | Add missing `orders.Created` to `ALL_EVENT_TYPES` | M6-4 | P1 |

### Non-Goals (Deferred)

| Item | Reason | Target |
|------|--------|--------|
| Real money trading | Requires additional safety measures | M9+ |
| WebSocket streaming | Polling sufficient for MVP | M9+ |
| Advanced order types (OCO, bracket) | Market/Limit orders first | M8+ |
| Multiple exchange adapters | Complete Alpaca first | M9+ |
| Order cancellation flow | Focus on placement first | M7 |
| Automatic fill polling | Manual/event-based first | M7 |

### Deferred from M5 (Now in M6)

| Item | Original Source |
|------|-----------------|
| PluginAdapterLoader | M5 Section 2.1 |
| AlpacaAdapter init | AUDIT 1.4 |
| VedaService routing | AUDIT 1.3 |

---

## 3. Architecture Overview

### Live Trading Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Live Trading Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Client    │───►│  GLaDOS     │───►│ VedaService  │───►│OrderManager  │ │
│  │  (Haro/CLI)│    │ POST /orders│    │              │    │              │ │
│  └────────────┘    └─────────────┘    └──────────────┘    └──────┬───────┘ │
│                                                                   │         │
│                                                                   ▼         │
│  ┌────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  EventLog  │◄───│  VedaService│◄───│OrderManager  │◄───│PluginAdapter │ │
│  │  (events)  │    │  (emit)     │    │  (response)  │    │   Loader     │ │
│  └────────────┘    └─────────────┘    └──────────────┘    └──────┬───────┘ │
│       │                                                          │         │
│       │                                                          ▼         │
│       ▼                                                   ┌──────────────┐ │
│  ┌────────────┐                                           │AlpacaAdapter │ │
│  │    SSE     │                                           │  (connect)   │ │
│  │ Broadcast  │                                           └──────┬───────┘ │
│  └────────────┘                                                  │         │
│                                                                  ▼         │
│                                                          ┌───────────────┐ │
│                                                          │ Alpaca Paper  │ │
│                                                          │    API        │ │
│                                                          └───────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (M6 Changes)

| Component | Current State | M6 Target State |
|-----------|---------------|-----------------|
| `/orders` routes | Uses MockOrderService | Uses VedaService |
| VedaService | Created but not used | Wired to routes |
| AlpacaAdapter | Clients always None | `connect()` initializes real clients |
| adapters/ | Hardcoded imports | PluginAdapterLoader with ADAPTER_META |
| Live Run | No RealtimeClock | Uses RealtimeClock |

### Plugin Architecture (Matches M5 Strategy Pattern)

```
src/veda/
├── __init__.py              # Exports interfaces, NOT specific adapters
├── interfaces.py            # ExchangeAdapter ABC
├── adapter_loader.py        # NEW: PluginAdapterLoader
├── adapter_meta.py          # NEW: AdapterMeta dataclass
│
└── adapters/                # Plugin directory
    ├── __init__.py          # Empty (no imports)
    ├── alpaca_adapter.py    # + ADAPTER_META constant
    ├── mock_adapter.py      # + ADAPTER_META constant
    └── factory.py           # Update to use PluginAdapterLoader
```

---

## 4. Detailed Design

### 4.1 PluginAdapterLoader (G1, G2)

Mirrors the PluginStrategyLoader pattern from M5 for consistency.

```python
# src/veda/adapter_meta.py

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterMeta:
    """Metadata for an exchange adapter plugin."""
    
    id: str                          # Unique identifier (e.g., "alpaca")
    name: str                        # Human-readable name
    version: str                     # Semantic version
    class_name: str                  # Class to instantiate
    module_path: str                 # Module path (auto-set by loader)
    supported_features: tuple[str, ...]  # e.g., ("stocks", "crypto", "paper")
    
    @classmethod
    def from_dict(cls, data: dict, module_path: str) -> "AdapterMeta":
        """Create AdapterMeta from ADAPTER_META dict."""
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            version=data.get("version", "1.0.0"),
            class_name=data["class"],
            module_path=module_path,
            supported_features=tuple(data.get("supported_features", [])),
        )
```

```python
# src/veda/adapter_loader.py

import ast
import importlib
import logging
from pathlib import Path
from typing import Any

from src.veda.adapter_meta import AdapterMeta
from src.veda.interfaces import ExchangeAdapter

logger = logging.getLogger(__name__)


class AdapterNotFoundError(Exception):
    """Raised when requested adapter is not found."""
    pass


class PluginAdapterLoader:
    """
    Plugin-based adapter loader with auto-discovery.
    
    Scans adapters/ directory for files with ADAPTER_META constant.
    Uses AST parsing to extract metadata without importing modules.
    
    Usage:
        loader = PluginAdapterLoader()
        available = loader.list_available()
        adapter = loader.load("alpaca", credentials)
    """
    
    def __init__(self, adapter_dir: Path | None = None) -> None:
        """
        Initialize loader.
        
        Args:
            adapter_dir: Directory to scan. Defaults to src/veda/adapters/
        """
        self._adapter_dir = adapter_dir or Path(__file__).parent / "adapters"
        self._metadata: dict[str, AdapterMeta] = {}
        self._scan_adapters()
    
    def _scan_adapters(self) -> None:
        """Scan adapter directory for plugins with ADAPTER_META."""
        if not self._adapter_dir.exists():
            logger.warning(f"Adapter directory not found: {self._adapter_dir}")
            return
        
        for file in self._adapter_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            
            meta = self._extract_metadata(file)
            if meta:
                self._metadata[meta.id] = meta
                logger.debug(f"Discovered adapter: {meta.id} ({meta.name})")
    
    def _extract_metadata(self, path: Path) -> AdapterMeta | None:
        """
        Extract ADAPTER_META from file without full module import.
        
        Uses AST parsing for safety - broken imports don't crash the loader.
        """
        try:
            source = path.read_text()
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "ADAPTER_META":
                            meta_dict = self._eval_dict_node(node.value)
                            if meta_dict and "id" in meta_dict and "class" in meta_dict:
                                module_name = path.stem
                                return AdapterMeta.from_dict(meta_dict, module_name)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {path}: {e}")
        
        return None
    
    def _eval_dict_node(self, node: ast.expr) -> dict | None:
        """Safely evaluate a dict AST node to a Python dict."""
        if not isinstance(node, ast.Dict):
            return None
        
        result = {}
        for key, value in zip(node.keys, node.values):
            if key is None:  # **spread operator
                continue
            
            # Only handle string keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                key_str = key.value
            else:
                continue
            
            # Handle various value types
            if isinstance(value, ast.Constant):
                result[key_str] = value.value
            elif isinstance(value, ast.List):
                result[key_str] = [
                    el.value for el in value.elts 
                    if isinstance(el, ast.Constant)
                ]
            elif isinstance(value, ast.Tuple):
                result[key_str] = tuple(
                    el.value for el in value.elts 
                    if isinstance(el, ast.Constant)
                )
        
        return result
    
    def list_available(self) -> list[AdapterMeta]:
        """List all discovered adapters."""
        return list(self._metadata.values())
    
    def get_metadata(self, adapter_id: str) -> AdapterMeta | None:
        """Get metadata for specific adapter."""
        return self._metadata.get(adapter_id)
    
    def supports_feature(self, adapter_id: str, feature: str) -> bool:
        """Check if adapter supports a specific feature."""
        meta = self._metadata.get(adapter_id)
        if not meta:
            return False
        return feature in meta.supported_features
    
    def load(self, adapter_id: str, credentials: Any = None) -> ExchangeAdapter:
        """
        Load and instantiate adapter by ID.
        
        Args:
            adapter_id: The adapter's declared ID
            credentials: Credentials to pass to adapter constructor
            
        Returns:
            Instantiated ExchangeAdapter
            
        Raises:
            AdapterNotFoundError: If adapter_id not found
        """
        if adapter_id not in self._metadata:
            available = [m.id for m in self._metadata.values()]
            raise AdapterNotFoundError(
                f"Adapter not found: {adapter_id}. Available: {available}"
            )
        
        meta = self._metadata[adapter_id]
        
        # Dynamic import
        module = importlib.import_module(f"src.veda.adapters.{meta.module_path}")
        adapter_class = getattr(module, meta.class_name)
        
        # Instantiate with credentials (if required)
        if credentials is not None:
            return adapter_class(credentials)
        else:
            return adapter_class()
```

### 4.2 ADAPTER_META Constants (G2)

Add metadata constants to existing adapters:

```python
# src/veda/adapters/alpaca_adapter.py (add at top, after docstring)

ADAPTER_META = {
    "id": "alpaca",
    "name": "Alpaca Markets",
    "version": "1.0.0",
    "class": "AlpacaAdapter",
    "supported_features": ["stocks", "crypto", "paper_trading", "live_trading"],
}
```

```python
# src/veda/adapters/mock_adapter.py (add at top, after docstring)

ADAPTER_META = {
    "id": "mock",
    "name": "Mock Exchange",
    "version": "1.0.0",
    "class": "MockExchangeAdapter",
    "supported_features": ["stocks", "crypto", "paper_trading", "testing"],
}
```

### 4.3 AlpacaAdapter Connection (G3, G4)

Update AlpacaAdapter to properly initialize Alpaca SDK clients:

```python
# src/veda/adapters/alpaca_adapter.py

class AlpacaAdapter(ExchangeAdapter):
    """Alpaca Markets exchange adapter."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret are required")
        
        self._api_key = api_key
        self._api_secret = api_secret
        self._paper = paper
        
        # Clients (initialized by connect())
        self._trading_client: TradingClient | None = None
        self._crypto_data_client: CryptoHistoricalDataClient | None = None
        self._stock_data_client: StockHistoricalDataClient | None = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Whether adapter has active connection."""
        return self._connected
    
    async def connect(self) -> None:
        """
        Initialize API clients and verify connection.
        
        Creates:
        - TradingClient for order management
        - CryptoHistoricalDataClient for crypto bars
        - StockHistoricalDataClient for stock bars
        
        Raises:
            ConnectionError: If account not active or unreachable
        """
        if self._connected:
            return
        
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import (
                CryptoHistoricalDataClient,
                StockHistoricalDataClient,
            )
            
            # Initialize trading client
            self._trading_client = TradingClient(
                api_key=self._api_key,
                secret_key=self._api_secret,
                paper=self._paper,
            )
            
            # Initialize data clients
            self._crypto_data_client = CryptoHistoricalDataClient(
                api_key=self._api_key,
                secret_key=self._api_secret,
            )
            self._stock_data_client = StockHistoricalDataClient(
                api_key=self._api_key,
                secret_key=self._api_secret,
            )
            
            # Verify connection by fetching account
            account = self._trading_client.get_account()
            if account.status != "ACTIVE":
                raise ConnectionError(
                    f"Alpaca account not active: {account.status}"
                )
            
            self._connected = True
            logger.info(
                f"AlpacaAdapter connected (paper={self._paper}, "
                f"account={account.account_number})"
            )
            
        except ImportError as e:
            raise RuntimeError(
                "alpaca-py package not installed. "
                "Install with: pip install alpaca-py"
            ) from e
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Alpaca: {e}") from e
    
    async def disconnect(self) -> None:
        """Clean up clients."""
        self._trading_client = None
        self._crypto_data_client = None
        self._stock_data_client = None
        self._connected = False
        logger.info("AlpacaAdapter disconnected")
    
    def _require_connection(self) -> None:
        """Raise if not connected."""
        if not self._connected:
            raise RuntimeError(
                "AlpacaAdapter not connected. Call connect() first."
            )
```

### 4.4 VedaService Routing (G5, G6)

Update order routes to use VedaService instead of MockOrderService:

```python
# src/glados/routes/orders.py

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.glados.dependencies import get_veda_service
from src.glados.schemas import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
)
from src.veda import VedaService
from src.veda.models import OrderIntent, OrderSide, OrderType

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    veda_service: VedaService | None = Depends(get_veda_service),
) -> OrderResponse:
    """
    Create a new order.
    
    Submits order to exchange via VedaService:
    1. Validates order parameters
    2. Submits to exchange adapter
    3. Persists to database
    4. Emits orders.Created event
    """
    if veda_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trading service not available (no credentials configured)",
        )
    
    intent = OrderIntent(
        symbol=order.symbol,
        side=OrderSide(order.side),
        qty=order.qty,
        order_type=OrderType(order.order_type),
        limit_price=order.limit_price,
        client_order_id=order.client_order_id,
    )
    
    state = await veda_service.place_order(intent)
    
    return OrderResponse(
        id=state.order_id,
        client_order_id=state.client_order_id,
        exchange_order_id=state.exchange_order_id,
        symbol=intent.symbol,
        side=intent.side.value,
        order_type=intent.order_type.value,
        qty=str(intent.qty),
        price=str(intent.limit_price) if intent.limit_price else None,
        status=state.status.value,
        created_at=state.created_at,
    )
```

### 4.5 Live Order Flow (G7, G8, G10)

The order flow already exists in VedaService. Key updates needed:

1. **`orders.Created` already in ALL_EVENT_TYPES** (verified in types.py line 130)
2. **Ensure VedaService emits events correctly**
3. **Connect AlpacaAdapter before first order**

```python
# In app.py lifespan, after creating VedaService:

if settings.alpaca.has_paper_credentials:
    # Connect adapter on startup
    try:
        await veda_service.connect()
        logger.info("VedaService adapter connected")
    except ConnectionError as e:
        logger.warning(f"VedaService adapter connection failed: {e}")
```

### 4.6 Run Mode Integration (G9)

Update RunManager to use RealtimeClock for live runs:

```python
# src/glados/services/run_manager.py

from src.glados.clock.realtime import RealtimeClock
from src.glados.clock.backtest import BacktestClock

async def start(self, run_id: str) -> Run:
    """Start a run with appropriate clock."""
    run = self._runs.get(run_id)
    if not run:
        raise RunNotFoundError(run_id)
    
    # Create clock based on run mode
    if run.mode == RunMode.LIVE:
        clock = RealtimeClock(
            timeframe=run.timeframe,
            run_id=run_id,
        )
    else:  # BACKTEST
        clock = BacktestClock(
            timeframe=run.timeframe,
            start=run.start_time,
            end=run.end_time,
            run_id=run_id,
        )
    
    self._clocks[run_id] = clock
    # ... rest of start logic
```

---

## 5. MVP Implementation Plan

> **Methodology**: TDD (Test-Driven Development)  
> **Pattern**: RED → GREEN → REFACTOR

### MVP Overview

| MVP | Focus | Est. Tests | Priority | Dependencies |
|-----|-------|------------|----------|--------------|
| M6-1 | PluginAdapterLoader | 15 | P0 | M5 |
| M6-2 | AlpacaAdapter Connection | 14 | P0 | M6-1 |
| M6-3 | VedaService Routing | 12 | P0 | M6-2 |
| M6-4 | Live Order Flow | 15 | P0 | M6-3 |
| M6-5 | Run Mode Integration | 9 | P0 | M6-4 |

**Total: ~65 new tests**

---

### MVP 6-1: PluginAdapterLoader (~15 tests)

**Goal**: Create plugin-based adapter discovery that mirrors PluginStrategyLoader.

**Files to Create/Modify**:
- `src/veda/adapter_meta.py` (CREATE)
- `src/veda/adapter_loader.py` (CREATE)
- `src/veda/adapters/alpaca_adapter.py` (ADD ADAPTER_META)
- `src/veda/adapters/mock_adapter.py` (ADD ADAPTER_META)
- `src/veda/adapters/__init__.py` (CLEAR hardcoded imports)
- `tests/unit/veda/test_adapter_loader.py` (CREATE)
- `tests/unit/veda/test_adapter_meta.py` (CREATE)

**Build**:
- AdapterMeta dataclass with from_dict factory
- PluginAdapterLoader with AST-based metadata extraction
- Directory scanning without module import
- list_available(), get_metadata(), supports_feature(), load()

**Defer**:
- Hot reloading (adapter files can change at runtime)
- Remote adapter loading
- Adapter versioning/conflicts

#### TDD Test Cases (M6-1)

```python
# tests/unit/veda/test_adapter_meta.py

class TestAdapterMeta:
    """Tests for AdapterMeta dataclass."""
    
    def test_from_dict_with_all_fields(self):
        """Create AdapterMeta from complete dict."""
        data = {
            "id": "test",
            "name": "Test Adapter",
            "version": "2.0.0",
            "class": "TestAdapter",
            "supported_features": ["feature1", "feature2"],
        }
        meta = AdapterMeta.from_dict(data, "test_module")
        
        assert meta.id == "test"
        assert meta.name == "Test Adapter"
        assert meta.version == "2.0.0"
        assert meta.class_name == "TestAdapter"
        assert meta.module_path == "test_module"
        assert meta.supported_features == ("feature1", "feature2")
    
    def test_from_dict_with_minimal_fields(self):
        """Create AdapterMeta with only required fields."""
        data = {"id": "minimal", "class": "MinimalAdapter"}
        meta = AdapterMeta.from_dict(data, "minimal_module")
        
        assert meta.id == "minimal"
        assert meta.name == "minimal"  # defaults to id
        assert meta.version == "1.0.0"  # default version
        assert meta.supported_features == ()  # empty tuple
    
    def test_adapter_meta_is_frozen(self):
        """AdapterMeta is immutable."""
        meta = AdapterMeta.from_dict({"id": "x", "class": "X"}, "m")
        
        with pytest.raises(FrozenInstanceError):
            meta.id = "changed"


# tests/unit/veda/test_adapter_loader.py

class TestPluginAdapterLoader:
    """Tests for PluginAdapterLoader."""
    
    @pytest.fixture
    def temp_adapter_dir(self, tmp_path):
        """Create temp directory with test adapter files."""
        adapter_dir = tmp_path / "adapters"
        adapter_dir.mkdir()
        
        # Valid adapter
        (adapter_dir / "valid_adapter.py").write_text('''
ADAPTER_META = {
    "id": "valid-test",
    "name": "Valid Test Adapter",
    "version": "1.0.0",
    "class": "ValidAdapter",
    "supported_features": ["testing"],
}

class ValidAdapter:
    def __init__(self, credentials=None): pass
''')
        
        # Adapter without meta (should be skipped)
        (adapter_dir / "no_meta.py").write_text('''
class NoMetaAdapter:
    pass
''')
        
        return adapter_dir
    
    def test_discovers_adapters_in_directory(self, temp_adapter_dir):
        """Scans directory and finds adapters with ADAPTER_META."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        available = loader.list_available()
        
        assert len(available) == 1
        assert available[0].id == "valid-test"
    
    def test_skips_files_without_adapter_meta(self, temp_adapter_dir):
        """Files without ADAPTER_META are not discovered."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        ids = [m.id for m in loader.list_available()]
        
        assert "no_meta" not in ids
    
    def test_skips_private_files(self, temp_adapter_dir):
        """Files starting with _ are skipped."""
        (temp_adapter_dir / "_private.py").write_text('''
ADAPTER_META = {"id": "private", "class": "Private"}
class Private: pass
''')
        
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        ids = [m.id for m in loader.list_available()]
        
        assert "private" not in ids
    
    def test_load_adapter_by_id(self, temp_adapter_dir):
        """Loads adapter by its declared ID."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        adapter = loader.load("valid-test")
        
        assert adapter is not None
        assert adapter.__class__.__name__ == "ValidAdapter"
    
    def test_load_adapter_with_credentials(self, temp_adapter_dir):
        """Passes credentials to adapter constructor."""
        (temp_adapter_dir / "cred_adapter.py").write_text('''
ADAPTER_META = {"id": "cred", "class": "CredAdapter"}

class CredAdapter:
    def __init__(self, credentials):
        self.creds = credentials
''')
        
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        loader._scan_adapters()  # Rescan
        adapter = loader.load("cred", credentials={"key": "secret"})
        
        assert adapter.creds == {"key": "secret"}
    
    def test_unknown_adapter_raises_not_found(self, temp_adapter_dir):
        """AdapterNotFoundError for unknown adapter_id."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        
        with pytest.raises(AdapterNotFoundError, match="nonexistent"):
            loader.load("nonexistent")
    
    def test_error_includes_available_adapters(self, temp_adapter_dir):
        """Error message lists available adapters."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        
        with pytest.raises(AdapterNotFoundError, match="valid-test"):
            loader.load("nonexistent")
    
    def test_extracts_metadata_without_importing(self, temp_adapter_dir):
        """Reads ADAPTER_META via AST, not import."""
        # Add file with import error
        (temp_adapter_dir / "broken_import.py").write_text('''
ADAPTER_META = {"id": "broken", "class": "Broken"}
import nonexistent_module_xyz
class Broken: pass
''')
        
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        available = loader.list_available()
        
        # Should discover metadata even though import would fail
        assert any(m.id == "broken" for m in available)
    
    def test_get_metadata_by_id(self, temp_adapter_dir):
        """get_metadata() returns AdapterMeta for known ID."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        meta = loader.get_metadata("valid-test")
        
        assert meta is not None
        assert meta.id == "valid-test"
    
    def test_get_metadata_returns_none_for_unknown(self, temp_adapter_dir):
        """get_metadata() returns None for unknown ID."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        meta = loader.get_metadata("unknown")
        
        assert meta is None
    
    def test_supports_feature_true(self, temp_adapter_dir):
        """supports_feature() returns True for supported feature."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        
        assert loader.supports_feature("valid-test", "testing") is True
    
    def test_supports_feature_false(self, temp_adapter_dir):
        """supports_feature() returns False for unsupported feature."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        
        assert loader.supports_feature("valid-test", "live_trading") is False
    
    def test_supports_feature_unknown_adapter(self, temp_adapter_dir):
        """supports_feature() returns False for unknown adapter."""
        loader = PluginAdapterLoader(adapter_dir=temp_adapter_dir)
        
        assert loader.supports_feature("unknown", "testing") is False
    
    def test_empty_directory_returns_empty_list(self, tmp_path):
        """Empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        loader = PluginAdapterLoader(adapter_dir=empty_dir)
        
        assert loader.list_available() == []
```

---

### MVP 6-2: AlpacaAdapter Connection (~14 tests)

**Goal**: Initialize AlpacaAdapter with real Alpaca SDK clients.

**Files to Modify**:
- `src/veda/adapters/alpaca_adapter.py` (ADD connect(), disconnect(), is_connected)
- `tests/unit/veda/test_alpaca_adapter_connection.py` (CREATE)
- `tests/fixtures/http.py` (ADD mock_alpaca_api fixture)

**Build**:
- `connect()` method initializing TradingClient, CryptoHistoricalDataClient, StockHistoricalDataClient
- Connection verification via account status check
- `disconnect()` cleanup method
- `is_connected` property
- `_require_connection()` guard for API methods

**Defer**:
- WebSocket streaming connections
- Connection retry/backoff
- Connection pooling

#### TDD Test Cases (M6-2)

```python
# tests/unit/veda/test_alpaca_adapter_connection.py

class TestAlpacaAdapterConnection:
    """Tests for AlpacaAdapter connection management."""
    
    @pytest.fixture
    def mock_alpaca_api(self, mocker):
        """Mock Alpaca SDK clients."""
        # Mock TradingClient
        mock_trading = mocker.patch(
            "src.veda.adapters.alpaca_adapter.TradingClient"
        )
        mock_account = mocker.MagicMock()
        mock_account.status = "ACTIVE"
        mock_account.account_number = "PA123456"
        mock_trading.return_value.get_account.return_value = mock_account
        
        # Mock data clients
        mock_crypto = mocker.patch(
            "src.veda.adapters.alpaca_adapter.CryptoHistoricalDataClient"
        )
        mock_stock = mocker.patch(
            "src.veda.adapters.alpaca_adapter.StockHistoricalDataClient"
        )
        
        return SimpleNamespace(
            trading=mock_trading,
            crypto=mock_crypto,
            stock=mock_stock,
            account=mock_account,
        )
    
    @pytest.fixture
    def adapter(self):
        """Create unconnected adapter."""
        return AlpacaAdapter(
            api_key="test-key",
            api_secret="test-secret",
            paper=True,
        )
    
    async def test_connect_creates_trading_client(self, adapter, mock_alpaca_api):
        """connect() creates TradingClient with correct params."""
        await adapter.connect()
        
        mock_alpaca_api.trading.assert_called_once_with(
            api_key="test-key",
            secret_key="test-secret",
            paper=True,
        )
    
    async def test_connect_creates_crypto_data_client(self, adapter, mock_alpaca_api):
        """connect() creates CryptoHistoricalDataClient."""
        await adapter.connect()
        
        mock_alpaca_api.crypto.assert_called_once_with(
            api_key="test-key",
            secret_key="test-secret",
        )
    
    async def test_connect_creates_stock_data_client(self, adapter, mock_alpaca_api):
        """connect() creates StockHistoricalDataClient."""
        await adapter.connect()
        
        mock_alpaca_api.stock.assert_called_once_with(
            api_key="test-key",
            secret_key="test-secret",
        )
    
    async def test_connect_verifies_account_status(self, adapter, mock_alpaca_api):
        """connect() verifies account is ACTIVE."""
        await adapter.connect()
        
        mock_alpaca_api.trading.return_value.get_account.assert_called_once()
    
    async def test_connect_sets_is_connected(self, adapter, mock_alpaca_api):
        """connect() sets is_connected to True."""
        assert adapter.is_connected is False
        
        await adapter.connect()
        
        assert adapter.is_connected is True
    
    async def test_connect_inactive_account_raises(self, adapter, mock_alpaca_api):
        """connect() raises ConnectionError if account not ACTIVE."""
        mock_alpaca_api.account.status = "INACTIVE"
        
        with pytest.raises(ConnectionError, match="not active"):
            await adapter.connect()
        
        assert adapter.is_connected is False
    
    async def test_connect_api_error_raises(self, adapter, mock_alpaca_api):
        """connect() raises ConnectionError on API failure."""
        mock_alpaca_api.trading.return_value.get_account.side_effect = Exception(
            "API Error"
        )
        
        with pytest.raises(ConnectionError, match="Failed to connect"):
            await adapter.connect()
    
    async def test_connect_idempotent(self, adapter, mock_alpaca_api):
        """Multiple connect() calls don't re-initialize."""
        await adapter.connect()
        await adapter.connect()
        
        # Should only be called once
        assert mock_alpaca_api.trading.call_count == 1
    
    async def test_disconnect_clears_clients(self, adapter, mock_alpaca_api):
        """disconnect() sets all clients to None."""
        await adapter.connect()
        await adapter.disconnect()
        
        assert adapter._trading_client is None
        assert adapter._crypto_data_client is None
        assert adapter._stock_data_client is None
        assert adapter.is_connected is False
    
    async def test_submit_order_requires_connection(self, adapter):
        """submit_order() raises RuntimeError if not connected."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.submit_order(intent)
    
    async def test_get_bars_requires_connection(self, adapter):
        """get_bars() raises RuntimeError if not connected."""
        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.get_bars("BTC/USD", "1m", datetime.now(), datetime.now())
    
    async def test_paper_mode_flag_passed(self, adapter, mock_alpaca_api):
        """paper=True passed to TradingClient."""
        await adapter.connect()
        
        call_kwargs = mock_alpaca_api.trading.call_args.kwargs
        assert call_kwargs["paper"] is True
    
    async def test_live_mode_flag_passed(self, mock_alpaca_api):
        """paper=False passed for live trading."""
        adapter = AlpacaAdapter(
            api_key="key",
            api_secret="secret",
            paper=False,
        )
        await adapter.connect()
        
        call_kwargs = mock_alpaca_api.trading.call_args.kwargs
        assert call_kwargs["paper"] is False
```

---

### MVP 6-3: VedaService Routing (~12 tests)

**Goal**: Wire VedaService to order routes, deprecate MockOrderService.

**Files to Modify**:
- `src/glados/routes/orders.py` (REWRITE to use VedaService)
- `src/glados/schemas.py` (ADD OrderCreate schema if needed)
- `tests/unit/glados/routes/test_orders_veda.py` (CREATE)

**Build**:
- POST /orders endpoint using VedaService
- GET /orders/{id} using OrderRepository
- GET /orders with filters
- Proper error responses (503 when VedaService unavailable)

**Defer**:
- DELETE /orders/{id} (cancel)
- PUT /orders/{id} (modify)
- Advanced filtering (date range, status)

#### TDD Test Cases (M6-3)

```python
# tests/unit/glados/routes/test_orders_veda.py

class TestOrderRoutesWithVeda:
    """Tests for order routes using VedaService."""
    
    @pytest.fixture
    def mock_veda_service(self, mocker):
        """Mock VedaService."""
        mock = mocker.MagicMock(spec=VedaService)
        mock.place_order = mocker.AsyncMock(return_value=OrderState(
            order_id="ord-123",
            client_order_id="client-456",
            exchange_order_id="alpaca-789",
            status=OrderStatus.ACCEPTED,
            created_at=datetime.now(UTC),
        ))
        return mock
    
    @pytest.fixture
    def app_with_veda(self, mock_veda_service):
        """Create app with mocked VedaService."""
        app = create_app()
        app.state.veda_service = mock_veda_service
        return app
    
    @pytest.fixture
    async def client(self, app_with_veda):
        """Async test client."""
        async with AsyncClient(app=app_with_veda, base_url="http://test") as ac:
            yield ac
    
    async def test_create_order_calls_veda_service(self, client, mock_veda_service):
        """POST /orders calls VedaService.place_order."""
        response = await client.post("/api/v1/orders", json={
            "symbol": "BTC/USD",
            "side": "buy",
            "qty": "1.5",
            "order_type": "market",
        })
        
        assert response.status_code == 201
        mock_veda_service.place_order.assert_called_once()
    
    async def test_create_order_passes_intent_correctly(self, client, mock_veda_service):
        """Order intent fields mapped correctly to VedaService."""
        await client.post("/api/v1/orders", json={
            "symbol": "ETH/USD",
            "side": "sell",
            "qty": "2.0",
            "order_type": "limit",
            "limit_price": "2500.00",
            "client_order_id": "my-order-1",
        })
        
        call_args = mock_veda_service.place_order.call_args
        intent = call_args[0][0]
        
        assert intent.symbol == "ETH/USD"
        assert intent.side == OrderSide.SELL
        assert intent.qty == Decimal("2.0")
        assert intent.order_type == OrderType.LIMIT
        assert intent.limit_price == Decimal("2500.00")
        assert intent.client_order_id == "my-order-1"
    
    async def test_create_order_returns_response(self, client):
        """Response includes order_id and status."""
        response = await client.post("/api/v1/orders", json={
            "symbol": "BTC/USD",
            "side": "buy",
            "qty": "1",
            "order_type": "market",
        })
        
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert data["symbol"] == "BTC/USD"
    
    async def test_create_order_validation_error(self, client):
        """Invalid order returns 422."""
        response = await client.post("/api/v1/orders", json={
            "invalid": "data"
        })
        
        assert response.status_code == 422
    
    async def test_create_order_missing_veda_service(self):
        """503 when VedaService not configured."""
        app = create_app()
        app.state.veda_service = None
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/v1/orders", json={
                "symbol": "BTC/USD",
                "side": "buy",
                "qty": "1",
                "order_type": "market",
            })
        
        assert response.status_code == 503
        assert "not available" in response.json()["detail"]
    
    async def test_get_order_by_id(self, client, mock_veda_service):
        """GET /orders/{id} returns order details."""
        mock_veda_service.get_order = mocker.AsyncMock(return_value=OrderState(...))
        
        response = await client.get("/api/v1/orders/ord-123")
        
        assert response.status_code == 200
        mock_veda_service.get_order.assert_called_once_with("ord-123")
    
    async def test_get_order_not_found(self, client, mock_veda_service):
        """GET /orders/{id} returns 404 for unknown order."""
        mock_veda_service.get_order = mocker.AsyncMock(return_value=None)
        
        response = await client.get("/api/v1/orders/unknown")
        
        assert response.status_code == 404
    
    async def test_list_orders(self, client, mock_veda_service):
        """GET /orders returns order list."""
        mock_veda_service.list_orders = mocker.AsyncMock(return_value=[])
        
        response = await client.get("/api/v1/orders")
        
        assert response.status_code == 200
        assert "items" in response.json()
    
    async def test_list_orders_with_run_id_filter(self, client, mock_veda_service):
        """GET /orders?run_id= filters by run."""
        mock_veda_service.list_orders = mocker.AsyncMock(return_value=[])
        
        response = await client.get("/api/v1/orders?run_id=run-123")
        
        mock_veda_service.list_orders.assert_called_once_with(run_id="run-123")
```

---

### MVP 6-4: Live Order Flow (~15 tests)

**Goal**: Complete live order flow with event emission and persistence.

**Files to Modify**:
- `src/veda/veda_service.py` (ADD connect(), get_order(), list_orders())
- `src/glados/app.py` (CONNECT adapter on startup)
- `tests/integration/test_live_order_flow.py` (CREATE)

**Build**:
- VedaService.connect() to initialize adapter
- Event emission for orders.Created, orders.Filled, orders.Rejected
- Order persistence to database
- Order retrieval methods

**Defer**:
- Order status polling
- WebSocket fill notifications
- Partial fill handling

#### TDD Test Cases (M6-4)

```python
# tests/integration/test_live_order_flow.py

class TestLiveOrderFlow:
    """Integration tests for live order flow."""
    
    @pytest.fixture
    def mock_alpaca(self, mocker):
        """Mock Alpaca API for integration tests."""
        # Setup mocks...
        pass
    
    @pytest.fixture
    async def veda_service(self, mock_alpaca, event_log, db_session):
        """Create VedaService with mocked adapter."""
        adapter = MockExchangeAdapter()
        service = VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=OrderRepository(db_session),
            config=get_config(),
        )
        return service
    
    async def test_place_order_persists_to_db(self, veda_service, db_session):
        """Placed order is persisted to database."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        
        state = await veda_service.place_order(intent)
        
        # Verify in database
        order = await db_session.get(OrderModel, state.order_id)
        assert order is not None
        assert order.symbol == "BTC/USD"
    
    async def test_place_order_emits_created_event(self, veda_service, event_log):
        """Placed order emits orders.Created event."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        
        await veda_service.place_order(intent)
        
        events = await event_log.query(types=["orders.Created"])
        assert len(events) == 1
        assert events[0].payload["symbol"] == "BTC/USD"
    
    async def test_rejected_order_emits_rejected_event(self, veda_service, event_log):
        """Rejected order emits orders.Rejected event."""
        veda_service._adapter.set_reject_next_order(True, "Insufficient funds")
        
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1000000"),
            order_type=OrderType.MARKET,
        )
        
        state = await veda_service.place_order(intent)
        
        assert state.status == OrderStatus.REJECTED
        events = await event_log.query(types=["orders.Rejected"])
        assert len(events) == 1
    
    async def test_order_includes_exchange_order_id(self, veda_service):
        """Order state includes exchange order ID."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        
        state = await veda_service.place_order(intent)
        
        assert state.exchange_order_id is not None
    
    async def test_market_order_fills_immediately(self, veda_service):
        """Market order with MockAdapter fills immediately."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        
        state = await veda_service.place_order(intent)
        
        assert state.status == OrderStatus.FILLED
    
    async def test_limit_order_stays_pending(self, veda_service):
        """Limit order stays in ACCEPTED state."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.LIMIT,
            limit_price=Decimal("40000"),
        )
        
        state = await veda_service.place_order(intent)
        
        assert state.status == OrderStatus.ACCEPTED
    
    async def test_get_order_by_id(self, veda_service):
        """Can retrieve order by ID."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        state = await veda_service.place_order(intent)
        
        retrieved = await veda_service.get_order(state.order_id)
        
        assert retrieved is not None
        assert retrieved.order_id == state.order_id
    
    async def test_list_orders(self, veda_service):
        """Can list all orders."""
        # Create multiple orders
        for _ in range(3):
            await veda_service.place_order(OrderIntent(
                symbol="BTC/USD",
                side=OrderSide.BUY,
                qty=Decimal("1"),
                order_type=OrderType.MARKET,
            ))
        
        orders = await veda_service.list_orders()
        
        assert len(orders) == 3
    
    async def test_list_orders_filter_by_run_id(self, veda_service):
        """Can filter orders by run_id."""
        # Create orders with different run_ids
        await veda_service.place_order(OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
            run_id="run-1",
        ))
        await veda_service.place_order(OrderIntent(
            symbol="ETH/USD",
            side=OrderSide.SELL,
            qty=Decimal("2"),
            order_type=OrderType.MARKET,
            run_id="run-2",
        ))
        
        orders = await veda_service.list_orders(run_id="run-1")
        
        assert len(orders) == 1
        assert orders[0].symbol == "BTC/USD"
    
    async def test_idempotent_order_submission(self, veda_service):
        """Same client_order_id returns same order."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
            client_order_id="idempotent-123",
        )
        
        state1 = await veda_service.place_order(intent)
        state2 = await veda_service.place_order(intent)
        
        assert state1.order_id == state2.order_id
    
    async def test_connect_initializes_adapter(self, mock_alpaca):
        """VedaService.connect() calls adapter.connect()."""
        adapter = AlpacaAdapter("key", "secret", paper=True)
        service = VedaService(adapter=adapter, ...)
        
        await service.connect()
        
        mock_alpaca.trading.assert_called()
    
    async def test_event_includes_correlation_id(self, veda_service, event_log):
        """Events include correlation_id for tracing."""
        intent = OrderIntent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1"),
            order_type=OrderType.MARKET,
        )
        
        await veda_service.place_order(intent)
        
        events = await event_log.query(types=["orders.Created"])
        assert events[0].correlation_id is not None
```

---

### MVP 6-5: Run Mode Integration (~9 tests)

**Goal**: Live runs use RealtimeClock, proper mode switching.

**Files to Modify**:
- `src/glados/services/run_manager.py` (ADD clock creation logic)
- `tests/unit/glados/services/test_run_manager_modes.py` (CREATE)

**Build**:
- RunManager creates RealtimeClock for live runs
- RunManager creates BacktestClock for backtest runs
- Proper mode detection and switching

**Defer**:
- Clock synchronization with exchange
- Multi-timezone support
- Clock drift detection

#### TDD Test Cases (M6-5)

```python
# tests/unit/glados/services/test_run_manager_modes.py

class TestRunManagerModes:
    """Tests for RunManager mode-specific behavior."""
    
    @pytest.fixture
    def run_manager(self, event_log):
        """Create RunManager with event log."""
        return RunManager(event_log=event_log)
    
    async def test_live_run_uses_realtime_clock(self, run_manager):
        """Live run creates RealtimeClock."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.LIVE,
            config={"symbol": "BTC/USD"},
        )
        
        await run_manager.start(run.id)
        
        clock = run_manager._clocks.get(run.id)
        assert isinstance(clock, RealtimeClock)
    
    async def test_backtest_run_uses_backtest_clock(self, run_manager):
        """Backtest run creates BacktestClock."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.BACKTEST,
            config={
                "symbol": "BTC/USD",
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z",
            },
        )
        
        await run_manager.start(run.id)
        
        clock = run_manager._clocks.get(run.id)
        assert isinstance(clock, BacktestClock)
    
    async def test_realtime_clock_uses_current_time(self, run_manager):
        """RealtimeClock starts from current time."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.LIVE,
            config={"symbol": "BTC/USD"},
        )
        
        before = datetime.now(UTC)
        await run_manager.start(run.id)
        after = datetime.now(UTC)
        
        clock = run_manager._clocks[run.id]
        assert before <= clock.current_time <= after
    
    async def test_backtest_clock_uses_config_times(self, run_manager):
        """BacktestClock uses configured start/end times."""
        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 2, tzinfo=UTC)
        
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.BACKTEST,
            config={
                "symbol": "BTC/USD",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        )
        
        await run_manager.start(run.id)
        
        clock = run_manager._clocks[run.id]
        assert clock.start_time == start
        assert clock.end_time == end
    
    async def test_stop_run_stops_clock(self, run_manager):
        """Stopping run stops the clock."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.LIVE,
            config={"symbol": "BTC/USD"},
        )
        await run_manager.start(run.id)
        
        await run_manager.stop(run.id)
        
        clock = run_manager._clocks.get(run.id)
        assert clock is None or not clock.is_running
    
    async def test_run_mode_persisted(self, run_manager):
        """Run mode is persisted in run state."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.LIVE,
            config={"symbol": "BTC/USD"},
        )
        
        retrieved = await run_manager.get(run.id)
        
        assert retrieved.mode == RunMode.LIVE
    
    async def test_cannot_start_already_running(self, run_manager):
        """Cannot start an already running run."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.LIVE,
            config={"symbol": "BTC/USD"},
        )
        await run_manager.start(run.id)
        
        with pytest.raises(RunAlreadyRunningError):
            await run_manager.start(run.id)
    
    async def test_live_run_emits_started_event(self, run_manager, event_log):
        """Live run start emits run.Started event."""
        run = await run_manager.create(
            strategy_id="sma",
            mode=RunMode.LIVE,
            config={"symbol": "BTC/USD"},
        )
        
        await run_manager.start(run.id)
        
        events = await event_log.query(types=["run.Started"])
        assert len(events) == 1
        assert events[0].payload["mode"] == "live"
```

---

## 6. Test Strategy

### Test Pyramid

```
                  ┌─────────────────┐
                  │  E2E Tests (3)  │  ← Full API flow
                  └────────┬────────┘
                           │
          ┌────────────────┴────────────────┐
          │    Integration Tests (~15)      │  ← Multi-component
          └────────────────┬────────────────┘
                           │
    ┌──────────────────────┴──────────────────────┐
    │            Unit Tests (~47)                 │  ← Single component
    └─────────────────────────────────────────────┘
```

### Test Files Summary

| File | Category | Tests |
|------|----------|-------|
| `tests/unit/veda/test_adapter_meta.py` | Unit | 3 |
| `tests/unit/veda/test_adapter_loader.py` | Unit | 12 |
| `tests/unit/veda/test_alpaca_adapter_connection.py` | Unit | 14 |
| `tests/unit/glados/routes/test_orders_veda.py` | Unit | 10 |
| `tests/unit/glados/services/test_run_manager_modes.py` | Unit | 9 |
| `tests/integration/test_live_order_flow.py` | Integration | 14 |
| `tests/e2e/test_live_trading.py` | E2E | 3 |

**Total: ~65 tests**

### Coverage Targets

| Module | Before M6 | Target |
|--------|-----------|--------|
| veda/ | ~197 | 230+ |
| glados/ | ~201 | 215+ |
| **Overall** | 705 | 770+ |

---

## 7. Entry & Exit Gates

### Entry Gate (Before Starting M6)

All items verified ✅:

- [x] M5 Complete (705 tests)
- [x] EventLog subscription works
- [x] PluginStrategyLoader implemented
- [x] SMA strategy backtests successfully
- [x] Clock module complete
- [x] VedaService exists (unused)

### Exit Gate (M6 Complete)

| Requirement | Verification |
|-------------|--------------|
| PluginAdapterLoader discovers adapters | Unit tests pass |
| ADAPTER_META in alpaca/mock adapters | Code review |
| AlpacaAdapter.connect() works | Unit tests with mocks pass |
| VedaService wired to routes | Integration tests pass |
| Orders persisted to database | Integration tests pass |
| Events emitted (Created/Rejected/Filled) | Integration tests pass |
| Live runs use RealtimeClock | Unit tests pass |
| ~65 new tests | Total ≥ 770 |

---

## 8. Risk & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Alpaca SDK changes | Low | High | Version pin, mock in tests |
| API rate limits in tests | Medium | Medium | Use MockExchangeAdapter for unit tests |
| Network failures | Medium | Medium | Proper error handling, timeouts |
| Paper/Live mode confusion | Low | High | Clear logging, mode indicators |
| Database connection issues | Low | Medium | Graceful degradation (in-memory mode) |

---

## 9. Appendix

### A. File Change Summary

| Category | File | Action |
|----------|------|--------|
| **Veda** | `adapter_meta.py` | CREATE |
| **Veda** | `adapter_loader.py` | CREATE |
| **Veda** | `adapters/alpaca_adapter.py` | MODIFY (add META + connect) |
| **Veda** | `adapters/mock_adapter.py` | MODIFY (add META) |
| **Veda** | `adapters/__init__.py` | MODIFY (clear imports) |
| **Veda** | `veda_service.py` | MODIFY (add connect, get, list) |
| **GLaDOS** | `routes/orders.py` | MODIFY (use VedaService) |
| **GLaDOS** | `schemas.py` | MODIFY (add OrderCreate) |
| **GLaDOS** | `app.py` | MODIFY (connect adapter on startup) |
| **GLaDOS** | `services/run_manager.py` | MODIFY (clock creation) |
| **Tests** | 7 new test files | CREATE |

### B. Dependency Additions

```toml
# pyproject.toml - already present, verify version
dependencies = [
    "alpaca-py>=0.10.0",  # Verify installed
]
```

### C. Environment Variables

```bash
# Required for live/paper trading
ALPACA_PAPER_API_KEY=xxx
ALPACA_PAPER_API_SECRET=xxx

# Optional for live trading (M9+)
ALPACA_LIVE_API_KEY=xxx
ALPACA_LIVE_API_SECRET=xxx
```

### D. Related Documents

| Document | Purpose |
|----------|---------|
| [M5 Marvin](m5-marvin.md) | Strategy plugin pattern reference |
| [M7 Haro](m7-haro.md) | Frontend that will consume these APIs |
| [AUDIT_FINDINGS.md](../../AUDIT_FINDINGS.md) | Issues being resolved |
| [roadmap.md](../../architecture/roadmap.md) | Milestone tracking |
| [api.md](../../architecture/api.md) | API design reference |

---

*Created: 2026-02-04*  
*Last Updated: 2026-02-04*
