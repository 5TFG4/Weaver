## 10. Veda Trading Implementation Plan (M3: Trading Works)

> **Status**: ⏳ PENDING | **Target**: M3 completion
> 
> **Definition of Done**: Veda tests pass with mocked exchange; Order idempotency proven

This section follows the **Design-Complete, Execute-MVP** approach:
- **Part A**: Full Design (complete specification)
- **Part B**: MVP Execution Plan (incremental implementation)

---

## Part A: Full Design

### A.1 Module Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│  Veda - Live Data & Trading Module                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RESPONSIBILITIES:                                              │
│  ├── Handle live.* events from GLaDOS routing                   │
│  ├── Submit orders to exchange (Alpaca)                         │
│  ├── Fetch real-time and historical market data                 │
│  ├── Manage order lifecycle (submit → ack → fill/reject)        │
│  ├── Enforce idempotency via client_order_id                    │
│  └── Emit orders.* events for status updates                    │
│                                                                 │
│  DOES NOT:                                                      │
│  ├── Handle backtest logic (that's Greta)                       │
│  ├── Make strategy decisions (that's Marvin)                    │
│  ├── Expose APIs (that's GLaDOS)                                │
│  └── Persist business data directly (that's WallE)              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### A.2 Architecture Integration

```
                          ┌─────────────────────┐
                          │       GLaDOS        │
                          │  (Domain Routing)   │
                          └─────────┬───────────┘
                                    │
           strategy.PlaceRequest    │    live.PlaceOrder
           ─────────────────────────┼────────────────────►
                                    │
                          ┌─────────▼───────────┐
                          │        Veda         │
                          │  (Live Trading)     │
                          └─────────┬───────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
            │   Exchange   │ │   Events    │ │   Cache    │
            │   Adapter    │ │   Emitter   │ │   Layer    │
            │   (Alpaca)   │ │             │ │            │
            └───────┬──────┘ └──────┬──────┘ └────────────┘
                    │               │
                    ▼               ▼
            ┌──────────────┐  ┌──────────────┐
            │   Alpaca     │  │   EventLog   │
            │     API      │  │   (Outbox)   │
            └──────────────┘  └──────────────┘
```

### A.3 Data Models (Complete Schema Design)

#### Order Domain Models

```python
# src/veda/models.py

@dataclass(frozen=True)
class OrderIntent:
    """
    Strategy's order intent - what the strategy WANTS to do.
    
    This is the INPUT to Veda, coming from strategy.PlaceRequest events.
    """
    run_id: str
    client_order_id: str          # Idempotency key (strategy-generated)
    symbol: str
    side: OrderSide               # BUY | SELL
    order_type: OrderType         # MARKET | LIMIT | STOP | STOP_LIMIT
    qty: Decimal
    limit_price: Decimal | None   # Required for LIMIT, STOP_LIMIT
    stop_price: Decimal | None    # Required for STOP, STOP_LIMIT
    time_in_force: TimeInForce    # DAY | GTC | IOC | FOK
    extended_hours: bool = False


class TimeInForce(str, Enum):
    """Order time-in-force options."""
    DAY = "day"      # Valid until end of regular trading hours
    GTC = "gtc"      # Good til cancelled (crypto: valid until cancelled)
    IOC = "ioc"      # Immediate or cancel
    FOK = "fok"      # Fill or kill


@dataclass
class OrderState:
    """
    Full order state tracked by Veda.
    
    Combines the original intent with exchange response and fill status.
    """
    # Identity
    id: str                        # Veda's internal order ID
    client_order_id: str           # From intent (idempotency key)
    exchange_order_id: str | None  # Exchange's order ID (after submit)
    run_id: str
    
    # Order details (from intent)
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    time_in_force: TimeInForce
    
    # Status
    status: OrderStatus
    
    # Fill info
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    fills: list[Fill]              # Individual fill records
    
    # Timestamps
    created_at: datetime
    submitted_at: datetime | None
    filled_at: datetime | None     # When fully filled
    cancelled_at: datetime | None
    
    # Error handling
    reject_reason: str | None
    error_code: str | None


@dataclass(frozen=True)
class Fill:
    """Individual fill record."""
    id: str
    order_id: str
    qty: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime


class OrderStatus(str, Enum):
    """Order lifecycle status."""
    # Initial states
    PENDING = "pending"           # Created locally, not yet submitted
    SUBMITTING = "submitting"     # Being sent to exchange
    
    # Exchange acknowledged states
    SUBMITTED = "submitted"       # Sent, awaiting exchange ack
    ACCEPTED = "accepted"         # Exchange accepted, in order book
    PARTIALLY_FILLED = "partial"  # Some quantity filled
    
    # Terminal states
    FILLED = "filled"             # Fully filled
    CANCELLED = "cancelled"       # Cancelled (by user or system)
    REJECTED = "rejected"         # Rejected by exchange
    EXPIRED = "expired"           # Time-in-force expired


@dataclass(frozen=True)
class AccountInfo:
    """Account information from exchange."""
    account_id: str
    buying_power: Decimal
    cash: Decimal
    portfolio_value: Decimal
    currency: str
    status: str                   # ACTIVE, INACTIVE, etc.


@dataclass(frozen=True) 
class Position:
    """Current position for a symbol."""
    symbol: str
    qty: Decimal
    side: PositionSide
    avg_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"
```

#### Market Data Models

```python
# src/veda/models.py (continued)

@dataclass(frozen=True)
class Bar:
    """OHLCV bar (candle) data."""
    symbol: str
    timestamp: datetime           # Bar open time (UTC)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int | None
    vwap: Decimal | None          # Volume-weighted average price


@dataclass(frozen=True)
class Quote:
    """Real-time quote data."""
    symbol: str
    timestamp: datetime
    bid_price: Decimal
    bid_size: Decimal
    ask_price: Decimal
    ask_size: Decimal
    

@dataclass(frozen=True)
class Trade:
    """Real-time trade data."""
    symbol: str
    timestamp: datetime
    price: Decimal
    size: Decimal
    exchange: str
```

### A.4 Service Interfaces (Complete Design)

```python
# src/veda/interfaces.py

from abc import ABC, abstractmethod
from typing import AsyncIterator


class ExchangeAdapter(ABC):
    """
    Abstract interface for exchange communication.
    
    Implementations:
    - AlpacaAdapter: Real Alpaca API
    - MockExchangeAdapter: For testing
    """
    
    # =========================================================================
    # Order Management
    # =========================================================================
    
    @abstractmethod
    async def submit_order(self, intent: OrderIntent) -> OrderSubmitResult:
        """
        Submit order to exchange.
        
        Args:
            intent: Order intent from strategy
            
        Returns:
            OrderSubmitResult with exchange_order_id or error
            
        Raises:
            ExchangeConnectionError: If exchange unreachable
            RateLimitError: If rate limit exceeded
        """
    
    @abstractmethod
    async def cancel_order(self, exchange_order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            exchange_order_id: Exchange's order ID
            
        Returns:
            True if cancel request accepted, False if order not found
        """
    
    @abstractmethod
    async def get_order(self, exchange_order_id: str) -> ExchangeOrder | None:
        """
        Get current order status from exchange.
        
        Args:
            exchange_order_id: Exchange's order ID
            
        Returns:
            ExchangeOrder if found, None otherwise
        """
    
    @abstractmethod
    async def list_orders(
        self,
        status: OrderStatus | None = None,
        symbols: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExchangeOrder]:
        """List orders from exchange."""
    
    # =========================================================================
    # Account & Positions
    # =========================================================================
    
    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get account information."""
    
    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all current positions."""
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Position | None:
        """Get position for a specific symbol."""
    
    # =========================================================================
    # Market Data
    # =========================================================================
    
    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """
        Get historical OHLCV bars.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USD")
            timeframe: Bar timeframe (e.g., "1m", "5m", "1h", "1d")
            start: Start datetime (UTC)
            end: End datetime (UTC), defaults to now
            limit: Max bars to return
            
        Returns:
            List of Bar objects, oldest first
        """
    
    @abstractmethod
    async def get_latest_bar(self, symbol: str) -> Bar | None:
        """Get the most recent bar for a symbol."""
    
    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get the most recent quote for a symbol."""
    
    @abstractmethod
    async def get_latest_trade(self, symbol: str) -> Trade | None:
        """Get the most recent trade for a symbol."""
    
    # =========================================================================
    # Streaming (Future)
    # =========================================================================
    
    @abstractmethod
    async def stream_bars(
        self,
        symbols: list[str],
    ) -> AsyncIterator[Bar]:
        """Stream real-time bars (future implementation)."""
    
    @abstractmethod
    async def stream_quotes(
        self,
        symbols: list[str],
    ) -> AsyncIterator[Quote]:
        """Stream real-time quotes (future implementation)."""


@dataclass(frozen=True)
class OrderSubmitResult:
    """Result of order submission to exchange."""
    success: bool
    exchange_order_id: str | None
    status: OrderStatus
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class ExchangeOrder:
    """Order as represented by the exchange."""
    exchange_order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
```

```python
# src/veda/order_manager.py

class OrderManager:
    """
    Manages order lifecycle within Veda.
    
    Responsibilities:
    - Track all orders by client_order_id (idempotency)
    - Coordinate with ExchangeAdapter
    - Emit order events
    - Handle order state transitions
    """
    
    def __init__(
        self,
        adapter: ExchangeAdapter,
        event_log: EventLog,
        config: TradingConfig,
    ) -> None:
        self._adapter = adapter
        self._event_log = event_log
        self._config = config
        self._orders: dict[str, OrderState] = {}  # client_order_id → OrderState
        self._pending_cancels: set[str] = set()
    
    async def place_order(self, intent: OrderIntent) -> OrderState:
        """
        Place an order based on strategy intent.
        
        Idempotency: If client_order_id already exists, return existing order.
        
        Flow:
        1. Check idempotency (return existing if duplicate)
        2. Validate intent
        3. Create local OrderState (PENDING)
        4. Emit orders.Created event
        5. Submit to exchange
        6. Update state based on result
        7. Emit orders.Submitted or orders.Rejected
        
        Args:
            intent: Order intent from strategy
            
        Returns:
            OrderState (current state of the order)
            
        Raises:
            ValidationError: If intent is invalid
        """
    
    async def cancel_order(self, client_order_id: str) -> OrderState:
        """
        Request order cancellation.
        
        Args:
            client_order_id: The client order ID to cancel
            
        Returns:
            Updated OrderState
            
        Raises:
            OrderNotFoundError: If order doesn't exist
            OrderNotCancellableError: If order in terminal state
        """
    
    async def sync_order(self, client_order_id: str) -> OrderState:
        """
        Sync order state with exchange.
        
        Fetches latest status from exchange and updates local state.
        
        Args:
            client_order_id: The client order ID
            
        Returns:
            Updated OrderState
        """
    
    async def get_order(self, client_order_id: str) -> OrderState | None:
        """Get order by client_order_id."""
    
    async def list_orders(
        self,
        run_id: str | None = None,
        status: OrderStatus | None = None,
    ) -> list[OrderState]:
        """List orders with optional filters."""
    
    def is_duplicate(self, client_order_id: str) -> bool:
        """Check if client_order_id already exists (idempotency check)."""
```

```python
# src/veda/market_data_provider.py

class MarketDataProvider:
    """
    Provides market data with caching.
    
    Features:
    - Automatic caching of recent bars
    - Rate limit management
    - Batch request optimization
    """
    
    def __init__(
        self,
        adapter: ExchangeAdapter,
        cache_ttl_seconds: int = 60,
    ) -> None:
        self._adapter = adapter
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = cache_ttl_seconds
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """Get historical bars with caching."""
    
    async def get_latest_bar(self, symbol: str) -> Bar | None:
        """Get latest bar with caching."""
    
    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get latest quote (no caching for real-time data)."""
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
```

```python
# src/veda/veda_service.py

class VedaService:
    """
    Main Veda service - entry point for live trading.
    
    Orchestrates:
    - OrderManager for order lifecycle
    - MarketDataProvider for market data
    - Event handling for live.* events
    """
    
    def __init__(
        self,
        adapter: ExchangeAdapter,
        event_log: EventLog,
        config: WeaverConfig,
    ) -> None:
        self._adapter = adapter
        self._order_manager = OrderManager(adapter, event_log, config.trading)
        self._market_data = MarketDataProvider(adapter)
        self._event_log = event_log
    
    # =========================================================================
    # Event Handlers (called by GLaDOS routing)
    # =========================================================================
    
    async def handle_place_order(self, event: Envelope) -> None:
        """
        Handle live.PlaceOrder event.
        
        Extracts OrderIntent from payload and delegates to OrderManager.
        """
    
    async def handle_cancel_order(self, event: Envelope) -> None:
        """Handle live.CancelOrder event."""
    
    async def handle_fetch_window(self, event: Envelope) -> None:
        """
        Handle live.FetchWindow event.
        
        Fetches market data and emits data.WindowReady event.
        """
    
    # =========================================================================
    # Direct API (for GLaDOS services)
    # =========================================================================
    
    async def get_account(self) -> AccountInfo:
        """Get account information."""
    
    async def get_positions(self) -> list[Position]:
        """Get all positions."""
    
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
    ) -> list[Bar]:
        """Get historical bars."""
```

### A.5 Event Types (M3 Additions)

```python
# src/events/types.py additions

class OrderEvents:
    """Order lifecycle events."""
    
    # Commands (requests)
    PLACE_REQUEST: Final[str] = "orders.PlaceRequest"
    CANCEL_REQUEST: Final[str] = "orders.CancelRequest"
    
    # Status events
    CREATED: Final[str] = "orders.Created"          # Order created locally
    SUBMITTED: Final[str] = "orders.Submitted"      # Sent to exchange
    ACCEPTED: Final[str] = "orders.Accepted"        # Exchange accepted
    REJECTED: Final[str] = "orders.Rejected"        # Exchange rejected
    FILLED: Final[str] = "orders.Filled"            # Fully filled
    PARTIALLY_FILLED: Final[str] = "orders.PartialFill"
    CANCELLED: Final[str] = "orders.Cancelled"
    EXPIRED: Final[str] = "orders.Expired"
    
    # Error events
    SUBMIT_FAILED: Final[str] = "orders.SubmitFailed"  # Network/system error


# Event payload schemas
ORDER_PLACE_REQUEST_PAYLOAD = {
    "run_id": str,
    "client_order_id": str,
    "symbol": str,
    "side": str,           # "buy" | "sell"
    "order_type": str,     # "market" | "limit" | "stop" | "stop_limit"
    "qty": str,            # Decimal as string
    "limit_price": str | None,
    "stop_price": str | None,
    "time_in_force": str,  # "day" | "gtc" | "ioc" | "fok"
}

ORDER_STATUS_PAYLOAD = {
    "order_id": str,
    "client_order_id": str,
    "exchange_order_id": str | None,
    "run_id": str,
    "status": str,
    "filled_qty": str,
    "filled_avg_price": str | None,
    "reject_reason": str | None,
}
```

### A.6 Error Handling Strategy

```python
# src/veda/exceptions.py

class VedaError(Exception):
    """Base exception for Veda module."""
    pass


class ExchangeConnectionError(VedaError):
    """Failed to connect to exchange."""
    pass


class RateLimitError(VedaError):
    """Exchange rate limit exceeded."""
    def __init__(self, retry_after_seconds: int | None = None):
        self.retry_after = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s")


class OrderNotFoundError(VedaError):
    """Order not found."""
    def __init__(self, client_order_id: str):
        self.client_order_id = client_order_id
        super().__init__(f"Order not found: {client_order_id}")


class OrderNotCancellableError(VedaError):
    """Order cannot be cancelled (already in terminal state)."""
    def __init__(self, client_order_id: str, status: OrderStatus):
        self.client_order_id = client_order_id
        self.status = status
        super().__init__(f"Order {client_order_id} cannot be cancelled (status: {status})")


class InsufficientFundsError(VedaError):
    """Insufficient funds for order."""
    def __init__(self, required: Decimal, available: Decimal):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient funds: need {required}, have {available}")


class InvalidOrderError(VedaError):
    """Order validation failed."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid order: {reason}")


class SymbolNotFoundError(VedaError):
    """Trading symbol not found."""
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Symbol not found: {symbol}")
```

### A.7 File Structure (Complete)

```
src/veda/
├── __init__.py
├── interfaces.py             # ExchangeAdapter ABC, result types
├── models.py                 # OrderIntent, OrderState, Bar, etc.
├── exceptions.py             # VedaError hierarchy
├── order_manager.py          # Order lifecycle management
├── market_data_provider.py   # Market data with caching
├── veda_service.py           # Main service (event handlers)
├── adapters/
│   ├── __init__.py
│   ├── alpaca_adapter.py     # Real Alpaca implementation
│   └── mock_adapter.py       # Mock for testing
└── utils/
    ├── __init__.py
    └── rate_limiter.py       # Rate limit handling
```

### A.8 Idempotency Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Order Idempotency via client_order_id                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PROBLEM: Network failures can cause duplicate order submission │
│                                                                 │
│  SOLUTION: client_order_id (UUID generated by strategy)         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Marvin (Strategy)                                       │   │
│  │  ────────────────────────────────────────────────────── │   │
│  │  client_order_id = uuid4()  # Strategy generates this    │   │
│  │  emit(strategy.PlaceRequest, {client_order_id, ...})     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Veda (OrderManager)                                     │   │
│  │  ────────────────────────────────────────────────────── │   │
│  │  if client_order_id in self._orders:                     │   │
│  │      return self._orders[client_order_id]  # IDEMPOTENT  │   │
│  │  else:                                                   │   │
│  │      order = create_and_submit(intent)                   │   │
│  │      self._orders[client_order_id] = order               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Alpaca API                                              │   │
│  │  ────────────────────────────────────────────────────── │   │
│  │  Also tracks client_order_id for their idempotency       │   │
│  │  Duplicate submission → returns existing order           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  GUARANTEES:                                                    │
│  • Same client_order_id always returns same order               │
│  • No duplicate orders even with retries                        │
│  • Safe to replay events during recovery                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part B: MVP Execution Plan

### B.1 MVP Overview

| MVP | What We Implement | What We Defer |
|-----|-------------------|---------------|
| **MVP-1** | Models, interfaces, exceptions | Real implementations |
| **MVP-2** | MockExchangeAdapter | Real Alpaca adapter |
| **MVP-3** | OrderManager core (place, idempotency) | Cancel, sync, streaming |
| **MVP-4** | MarketDataProvider (basic) | Caching, streaming |
| **MVP-5** | AlpacaAdapter (orders) | Market data streaming |
| **MVP-6** | VedaService + GLaDOS integration | Full event routing |

---

### B.2 TDD Test Specifications (Complete)

#### Test File Structure

```
tests/unit/veda/
├── __init__.py
├── conftest.py                    # Veda test fixtures
├── test_models.py                 # MVP-1: Model tests
├── test_interfaces.py             # MVP-1: Interface contract tests
├── test_exceptions.py             # MVP-1: Exception tests
├── test_mock_adapter.py           # MVP-2: Mock adapter tests
├── test_order_manager.py          # MVP-3: Order manager tests
├── test_market_data_provider.py   # MVP-4: Market data tests
├── test_alpaca_adapter.py         # MVP-5: Alpaca adapter tests (mocked HTTP)
└── test_veda_service.py           # MVP-6: Service integration tests

tests/integration/veda/
├── __init__.py
├── conftest.py
└── test_alpaca_integration.py     # Optional: Real API tests (manual/CI-skip)
```

#### MVP-1 Tests (~20 tests)

```python
# tests/unit/veda/test_models.py

class TestOrderIntent:
    """Tests for OrderIntent dataclass."""
    
    def test_creates_with_required_fields(self):
        """OrderIntent requires all order details."""
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.5"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        assert intent.symbol == "BTC/USD"
        assert intent.qty == Decimal("1.5")
    
    def test_is_immutable(self):
        """OrderIntent should be frozen."""
        intent = OrderIntent(...)
        with pytest.raises(FrozenInstanceError):
            intent.qty = Decimal("2.0")
    
    def test_limit_order_requires_price(self):
        """Limit orders should have limit_price set."""
        intent = OrderIntent(
            order_type=OrderType.LIMIT,
            limit_price=Decimal("50000.00"),
            ...
        )
        assert intent.limit_price is not None


class TestOrderState:
    """Tests for OrderState dataclass."""
    
    def test_initial_status_is_pending(self):
        """New OrderState should start as PENDING."""
        state = OrderState(
            id="order-1",
            client_order_id="client-1",
            status=OrderStatus.PENDING,
            ...
        )
        assert state.status == OrderStatus.PENDING
    
    def test_tracks_fill_information(self):
        """OrderState should track fills."""
        state = OrderState(
            filled_qty=Decimal("0.5"),
            filled_avg_price=Decimal("42000.00"),
            fills=[Fill(...)],
            ...
        )
        assert state.filled_qty == Decimal("0.5")
        assert len(state.fills) == 1


class TestBar:
    """Tests for Bar (OHLCV) dataclass."""
    
    def test_has_ohlcv_fields(self):
        """Bar should have all OHLCV fields."""
        bar = Bar(
            symbol="BTC/USD",
            timestamp=datetime.now(UTC),
            open=Decimal("42000"),
            high=Decimal("42500"),
            low=Decimal("41800"),
            close=Decimal("42200"),
            volume=Decimal("100.5"),
            trade_count=1234,
            vwap=Decimal("42100"),
        )
        assert bar.high > bar.low
    
    def test_is_immutable(self):
        """Bar should be frozen."""
        bar = Bar(...)
        with pytest.raises(FrozenInstanceError):
            bar.close = Decimal("50000")


class TestOrderStatus:
    """Tests for OrderStatus enum."""
    
    def test_terminal_states(self):
        """Identify terminal states."""
        terminal = {OrderStatus.FILLED, OrderStatus.CANCELLED, 
                   OrderStatus.REJECTED, OrderStatus.EXPIRED}
        assert OrderStatus.FILLED in terminal
        assert OrderStatus.PENDING not in terminal
    
    def test_can_cancel_states(self):
        """Identify states that can be cancelled."""
        cancellable = {OrderStatus.PENDING, OrderStatus.SUBMITTED, 
                      OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}
        assert OrderStatus.ACCEPTED in cancellable
        assert OrderStatus.FILLED not in cancellable


# tests/unit/veda/test_exceptions.py

class TestVedaExceptions:
    """Tests for Veda exception classes."""
    
    def test_order_not_found_error_stores_id(self):
        """OrderNotFoundError should store client_order_id."""
        exc = OrderNotFoundError("client-123")
        assert exc.client_order_id == "client-123"
    
    def test_rate_limit_error_stores_retry(self):
        """RateLimitError should store retry_after."""
        exc = RateLimitError(retry_after_seconds=60)
        assert exc.retry_after == 60
    
    def test_order_not_cancellable_stores_status(self):
        """OrderNotCancellableError should store current status."""
        exc = OrderNotCancellableError("client-123", OrderStatus.FILLED)
        assert exc.status == OrderStatus.FILLED
    
    def test_insufficient_funds_stores_amounts(self):
        """InsufficientFundsError should store required and available."""
        exc = InsufficientFundsError(
            required=Decimal("10000"),
            available=Decimal("5000"),
        )
        assert exc.required == Decimal("10000")
        assert exc.available == Decimal("5000")
```

#### MVP-2 Tests (~15 tests)

```python
# tests/unit/veda/test_mock_adapter.py

class TestMockExchangeAdapter:
    """Tests for MockExchangeAdapter."""
    
    async def test_submit_order_returns_success(self, mock_adapter):
        """Submit order should return success result."""
        intent = OrderIntent(
            client_order_id="test-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            ...
        )
        result = await mock_adapter.submit_order(intent)
        assert result.success is True
        assert result.exchange_order_id is not None
    
    async def test_submit_order_uses_client_order_id(self, mock_adapter):
        """Mock should track client_order_id for idempotency."""
        intent = OrderIntent(client_order_id="test-123", ...)
        result1 = await mock_adapter.submit_order(intent)
        result2 = await mock_adapter.submit_order(intent)
        # Same client_order_id should return same exchange_order_id
        assert result1.exchange_order_id == result2.exchange_order_id
    
    async def test_get_order_returns_submitted(self, mock_adapter):
        """Get order should return previously submitted order."""
        intent = OrderIntent(client_order_id="test-123", ...)
        result = await mock_adapter.submit_order(intent)
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.client_order_id == "test-123"
    
    async def test_cancel_order_changes_status(self, mock_adapter):
        """Cancel should change order status to CANCELLED."""
        intent = OrderIntent(client_order_id="test-123", ...)
        result = await mock_adapter.submit_order(intent)
        cancelled = await mock_adapter.cancel_order(result.exchange_order_id)
        assert cancelled is True
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order.status == OrderStatus.CANCELLED
    
    async def test_get_account_returns_mock_data(self, mock_adapter):
        """Get account should return mock account info."""
        account = await mock_adapter.get_account()
        assert account.buying_power > 0
        assert account.status == "ACTIVE"
    
    async def test_get_bars_returns_mock_data(self, mock_adapter):
        """Get bars should return mock OHLCV data."""
        bars = await mock_adapter.get_bars(
            symbol="BTC/USD",
            timeframe="1m",
            start=datetime.now(UTC) - timedelta(hours=1),
        )
        assert len(bars) > 0
        assert all(isinstance(b, Bar) for b in bars)
    
    async def test_simulate_fill_triggers_fill(self, mock_adapter):
        """Mock can simulate order fills."""
        intent = OrderIntent(
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            ...
        )
        result = await mock_adapter.submit_order(intent)
        # Market orders should fill immediately in mock
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == Decimal("1.0")
    
    async def test_limit_order_stays_pending(self, mock_adapter):
        """Limit orders should not auto-fill."""
        intent = OrderIntent(
            order_type=OrderType.LIMIT,
            limit_price=Decimal("30000"),  # Below market
            qty=Decimal("1.0"),
            ...
        )
        result = await mock_adapter.submit_order(intent)
        order = await mock_adapter.get_order(result.exchange_order_id)
        assert order.status == OrderStatus.ACCEPTED
        assert order.filled_qty == Decimal("0")
```

#### MVP-3 Tests (~18 tests)

```python
# tests/unit/veda/test_order_manager.py

class TestOrderManagerPlace:
    """Tests for OrderManager.place_order()."""
    
    async def test_creates_order_state(self, order_manager, mock_adapter):
        """place_order should create OrderState."""
        intent = OrderIntent(client_order_id="test-123", ...)
        state = await order_manager.place_order(intent)
        assert state is not None
        assert state.client_order_id == "test-123"
    
    async def test_generates_internal_id(self, order_manager):
        """place_order should generate internal order ID."""
        intent = OrderIntent(client_order_id="test-123", ...)
        state = await order_manager.place_order(intent)
        assert state.id is not None
        assert len(state.id) == 36  # UUID format
    
    async def test_submits_to_exchange(self, order_manager, mock_adapter):
        """place_order should submit to exchange adapter."""
        intent = OrderIntent(client_order_id="test-123", ...)
        state = await order_manager.place_order(intent)
        assert state.exchange_order_id is not None
    
    async def test_idempotent_with_same_client_order_id(self, order_manager):
        """Duplicate client_order_id should return existing order."""
        intent = OrderIntent(client_order_id="test-123", ...)
        state1 = await order_manager.place_order(intent)
        state2 = await order_manager.place_order(intent)
        assert state1.id == state2.id
        assert state1.exchange_order_id == state2.exchange_order_id
    
    async def test_different_client_order_ids_create_different_orders(self, order_manager):
        """Different client_order_ids should create different orders."""
        intent1 = OrderIntent(client_order_id="test-123", ...)
        intent2 = OrderIntent(client_order_id="test-456", ...)
        state1 = await order_manager.place_order(intent1)
        state2 = await order_manager.place_order(intent2)
        assert state1.id != state2.id


class TestOrderManagerIdempotency:
    """Tests for order idempotency guarantees."""
    
    async def test_concurrent_same_order_returns_same(self, order_manager):
        """Concurrent submissions with same client_order_id return same order."""
        intent = OrderIntent(client_order_id="test-123", ...)
        # Simulate concurrent calls
        results = await asyncio.gather(
            order_manager.place_order(intent),
            order_manager.place_order(intent),
            order_manager.place_order(intent),
        )
        # All should return the same order
        ids = {r.id for r in results}
        assert len(ids) == 1
    
    async def test_is_duplicate_returns_true_for_existing(self, order_manager):
        """is_duplicate should return True for existing client_order_id."""
        intent = OrderIntent(client_order_id="test-123", ...)
        await order_manager.place_order(intent)
        assert order_manager.is_duplicate("test-123") is True
    
    async def test_is_duplicate_returns_false_for_new(self, order_manager):
        """is_duplicate should return False for new client_order_id."""
        assert order_manager.is_duplicate("non-existent") is False


class TestOrderManagerCancel:
    """Tests for OrderManager.cancel_order()."""
    
    async def test_cancels_pending_order(self, order_manager):
        """cancel_order should work for pending orders."""
        intent = OrderIntent(
            client_order_id="test-123",
            order_type=OrderType.LIMIT,
            ...
        )
        state = await order_manager.place_order(intent)
        cancelled = await order_manager.cancel_order("test-123")
        assert cancelled.status == OrderStatus.CANCELLED
    
    async def test_raises_for_unknown_order(self, order_manager):
        """cancel_order should raise for unknown client_order_id."""
        with pytest.raises(OrderNotFoundError):
            await order_manager.cancel_order("non-existent")
    
    async def test_raises_for_filled_order(self, order_manager):
        """cancel_order should raise for already-filled orders."""
        intent = OrderIntent(
            client_order_id="test-123",
            order_type=OrderType.MARKET,  # Will fill immediately
            ...
        )
        await order_manager.place_order(intent)
        with pytest.raises(OrderNotCancellableError):
            await order_manager.cancel_order("test-123")


class TestOrderManagerList:
    """Tests for OrderManager.list_orders()."""
    
    async def test_returns_all_orders(self, order_manager):
        """list_orders should return all orders."""
        for i in range(3):
            intent = OrderIntent(client_order_id=f"test-{i}", ...)
            await order_manager.place_order(intent)
        orders = await order_manager.list_orders()
        assert len(orders) == 3
    
    async def test_filters_by_run_id(self, order_manager):
        """list_orders should filter by run_id."""
        intent1 = OrderIntent(run_id="run-1", client_order_id="test-1", ...)
        intent2 = OrderIntent(run_id="run-2", client_order_id="test-2", ...)
        await order_manager.place_order(intent1)
        await order_manager.place_order(intent2)
        orders = await order_manager.list_orders(run_id="run-1")
        assert len(orders) == 1
        assert orders[0].run_id == "run-1"
```

#### MVP-4 Tests (~10 tests)

```python
# tests/unit/veda/test_market_data_provider.py

class TestMarketDataProviderBars:
    """Tests for MarketDataProvider.get_bars()."""
    
    async def test_returns_bars_from_adapter(self, market_data, mock_adapter):
        """get_bars should return bars from adapter."""
        bars = await market_data.get_bars(
            symbol="BTC/USD",
            timeframe="1m",
            start=datetime.now(UTC) - timedelta(hours=1),
        )
        assert len(bars) > 0
        assert all(isinstance(b, Bar) for b in bars)
    
    async def test_caches_recent_requests(self, market_data, mock_adapter):
        """Repeated requests should use cache."""
        start = datetime.now(UTC) - timedelta(hours=1)
        bars1 = await market_data.get_bars("BTC/USD", "1m", start)
        bars2 = await market_data.get_bars("BTC/USD", "1m", start)
        # Mock adapter call count should be 1 (cached)
        assert mock_adapter.get_bars_call_count == 1
    
    async def test_cache_expires(self, market_data):
        """Cache should expire after TTL."""
        # Use short TTL for test
        market_data._cache_ttl = 0.1
        start = datetime.now(UTC) - timedelta(hours=1)
        await market_data.get_bars("BTC/USD", "1m", start)
        await asyncio.sleep(0.2)  # Wait for expiry
        await market_data.get_bars("BTC/USD", "1m", start)
        # Should have called adapter twice
        assert mock_adapter.get_bars_call_count == 2


class TestMarketDataProviderQuotes:
    """Tests for MarketDataProvider quote methods."""
    
    async def test_get_latest_quote(self, market_data):
        """get_latest_quote should return quote from adapter."""
        quote = await market_data.get_latest_quote("BTC/USD")
        assert quote is not None
        assert quote.symbol == "BTC/USD"
        assert quote.bid_price > 0
    
    async def test_quotes_not_cached(self, market_data, mock_adapter):
        """Quotes should not be cached (real-time data)."""
        await market_data.get_latest_quote("BTC/USD")
        await market_data.get_latest_quote("BTC/USD")
        assert mock_adapter.get_quote_call_count == 2
```

#### MVP-5 Tests (~15 tests)

```python
# tests/unit/veda/test_alpaca_adapter.py

class TestAlpacaAdapterSubmitOrder:
    """Tests for AlpacaAdapter.submit_order() with mocked HTTP."""
    
    @pytest.fixture
    def mock_alpaca_api(self, respx_mock):
        """Mock Alpaca API responses."""
        respx_mock.post("https://paper-api.alpaca.markets/v2/orders").mock(
            return_value=Response(
                200,
                json={
                    "id": "exch-123",
                    "client_order_id": "test-123",
                    "status": "accepted",
                    "filled_qty": "0",
                    ...
                }
            )
        )
        return respx_mock
    
    async def test_submit_market_order(self, alpaca_adapter, mock_alpaca_api):
        """Submit market order to Alpaca."""
        intent = OrderIntent(
            client_order_id="test-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            ...
        )
        result = await alpaca_adapter.submit_order(intent)
        assert result.success is True
        assert result.exchange_order_id == "exch-123"
    
    async def test_submit_limit_order_includes_price(self, alpaca_adapter, mock_alpaca_api):
        """Limit order should include limit_price."""
        intent = OrderIntent(
            order_type=OrderType.LIMIT,
            limit_price=Decimal("50000.00"),
            ...
        )
        await alpaca_adapter.submit_order(intent)
        # Verify request included limit_price
        request = mock_alpaca_api.calls[0].request
        body = json.loads(request.content)
        assert body["limit_price"] == "50000.00"
    
    async def test_handles_rejection(self, alpaca_adapter, respx_mock):
        """Handle order rejection from Alpaca."""
        respx_mock.post("https://paper-api.alpaca.markets/v2/orders").mock(
            return_value=Response(403, json={"message": "Insufficient funds"})
        )
        intent = OrderIntent(...)
        result = await alpaca_adapter.submit_order(intent)
        assert result.success is False
        assert result.error_message == "Insufficient funds"
    
    async def test_handles_rate_limit(self, alpaca_adapter, respx_mock):
        """Handle rate limit from Alpaca."""
        respx_mock.post("https://paper-api.alpaca.markets/v2/orders").mock(
            return_value=Response(429, headers={"Retry-After": "60"})
        )
        intent = OrderIntent(...)
        with pytest.raises(RateLimitError) as exc:
            await alpaca_adapter.submit_order(intent)
        assert exc.value.retry_after == 60


class TestAlpacaAdapterMarketData:
    """Tests for AlpacaAdapter market data methods."""
    
    async def test_get_bars_parses_response(self, alpaca_adapter, respx_mock):
        """get_bars should parse Alpaca bar response."""
        respx_mock.get(
            "https://data.alpaca.markets/v1beta3/crypto/us/bars"
        ).mock(return_value=Response(200, json={
            "bars": {
                "BTC/USD": [
                    {"t": "2026-02-02T10:00:00Z", "o": "42000", ...},
                    {"t": "2026-02-02T10:01:00Z", "o": "42100", ...},
                ]
            }
        }))
        bars = await alpaca_adapter.get_bars(
            symbol="BTC/USD",
            timeframe="1m",
            start=datetime(2026, 2, 2, 10, 0, tzinfo=UTC),
        )
        assert len(bars) == 2
        assert bars[0].symbol == "BTC/USD"
        assert bars[0].open == Decimal("42000")
```

#### MVP-6 Tests (~12 tests)

```python
# tests/unit/veda/test_veda_service.py

class TestVedaServiceOrderHandling:
    """Tests for VedaService order event handling."""
    
    async def test_handle_place_order_event(self, veda_service, mock_adapter):
        """handle_place_order should process live.PlaceOrder event."""
        event = Envelope(
            type="live.PlaceOrder",
            producer="glados",
            run_id="run-123",
            payload={
                "client_order_id": "test-123",
                "symbol": "BTC/USD",
                "side": "buy",
                "order_type": "market",
                "qty": "1.0",
                "time_in_force": "gtc",
            },
        )
        await veda_service.handle_place_order(event)
        # Verify order was placed
        order = await veda_service._order_manager.get_order("test-123")
        assert order is not None
        assert order.symbol == "BTC/USD"
    
    async def test_emits_order_created_event(self, veda_service, mock_event_log):
        """handle_place_order should emit orders.Created event."""
        event = Envelope(type="live.PlaceOrder", payload={...})
        await veda_service.handle_place_order(event)
        # Verify event was logged
        events = mock_event_log.get_events_by_type("orders.Created")
        assert len(events) == 1
    
    async def test_emits_order_filled_event(self, veda_service, mock_event_log):
        """Market order should emit orders.Filled event."""
        event = Envelope(
            type="live.PlaceOrder",
            payload={"order_type": "market", ...}
        )
        await veda_service.handle_place_order(event)
        events = mock_event_log.get_events_by_type("orders.Filled")
        assert len(events) == 1


class TestVedaServiceMarketData:
    """Tests for VedaService market data handling."""
    
    async def test_handle_fetch_window(self, veda_service, mock_adapter):
        """handle_fetch_window should fetch and emit data."""
        event = Envelope(
            type="live.FetchWindow",
            producer="glados",
            run_id="run-123",
            payload={
                "symbol": "BTC/USD",
                "timeframe": "1m",
                "start": "2026-02-02T09:00:00Z",
                "end": "2026-02-02T10:00:00Z",
            },
        )
        await veda_service.handle_fetch_window(event)
        # Verify data.WindowReady event emitted
        events = mock_event_log.get_events_by_type("data.WindowReady")
        assert len(events) == 1
    
    async def test_get_bars_returns_data(self, veda_service):
        """get_bars should return market data."""
        bars = await veda_service.get_bars(
            symbol="BTC/USD",
            timeframe="1m",
            start=datetime.now(UTC) - timedelta(hours=1),
        )
        assert len(bars) > 0


class TestVedaServiceAccount:
    """Tests for VedaService account methods."""
    
    async def test_get_account(self, veda_service):
        """get_account should return account info."""
        account = await veda_service.get_account()
        assert account.buying_power > 0
    
    async def test_get_positions(self, veda_service):
        """get_positions should return positions list."""
        positions = await veda_service.get_positions()
        assert isinstance(positions, list)
```

#### Test Fixtures

```python
# tests/unit/veda/conftest.py

import pytest
from decimal import Decimal
from datetime import datetime, UTC

from src.veda.models import OrderIntent, OrderSide, OrderType, TimeInForce
from src.veda.adapters.mock_adapter import MockExchangeAdapter
from src.veda.order_manager import OrderManager
from src.veda.market_data_provider import MarketDataProvider
from src.veda.veda_service import VedaService
from src.events.log import InMemoryEventLog


@pytest.fixture
def mock_adapter():
    """Create mock exchange adapter."""
    return MockExchangeAdapter()


@pytest.fixture
def mock_event_log():
    """Create in-memory event log for testing."""
    return InMemoryEventLog()


@pytest.fixture
def order_manager(mock_adapter, mock_event_log):
    """Create OrderManager with mock dependencies."""
    return OrderManager(
        adapter=mock_adapter,
        event_log=mock_event_log,
        config=TradingConfig(),
    )


@pytest.fixture
def market_data(mock_adapter):
    """Create MarketDataProvider with mock adapter."""
    return MarketDataProvider(adapter=mock_adapter)


@pytest.fixture
def veda_service(mock_adapter, mock_event_log):
    """Create VedaService with mock dependencies."""
    return VedaService(
        adapter=mock_adapter,
        event_log=mock_event_log,
        config=get_test_config(),
    )


@pytest.fixture
def sample_order_intent():
    """Create sample OrderIntent for tests."""
    return OrderIntent(
        run_id="run-123",
        client_order_id="client-123",
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1.0"),
        limit_price=None,
        stop_price=None,
        time_in_force=TimeInForce.GTC,
    )
```

---

### B.3 MVP-1: Models, Interfaces, Exceptions

> **Implements**: Core data structures and contracts
> 
> **Deliverables**:
> ```
> src/veda/
> ├── models.py         # OrderIntent, OrderState, Bar, etc.
> ├── interfaces.py     # ExchangeAdapter ABC, result types
> └── exceptions.py     # VedaError hierarchy
> ```

**Completion Criteria**:
- [ ] All model dataclasses defined and immutable where appropriate
- [ ] ExchangeAdapter ABC with all methods
- [ ] All exception classes with proper attributes
- [ ] ~20 tests passing

---

### B.4 MVP-2: MockExchangeAdapter

> **Implements**: Mock adapter for testing
> 
> **Deliverables**:
> ```
> src/veda/adapters/
> ├── __init__.py
> └── mock_adapter.py   # MockExchangeAdapter
> ```

**Features**:
- Submit orders (market orders fill immediately)
- Track orders by exchange_order_id
- Idempotency via client_order_id
- Cancel orders
- Mock account and position data
- Generate mock OHLCV bars

**Completion Criteria**:
- [ ] MockExchangeAdapter passes all interface tests
- [ ] Market orders auto-fill
- [ ] Limit orders stay pending
- [ ] ~15 tests passing

---

### B.5 MVP-3: OrderManager Core

> **Implements**: Order lifecycle management
> 
> **Deliverables**:
> ```
> src/veda/
> └── order_manager.py  # OrderManager class
> ```

**Features**:
- `place_order()` with idempotency
- `cancel_order()` with state validation
- `get_order()` and `list_orders()`
- Event emission (orders.Created, orders.Filled, etc.)

**Completion Criteria**:
- [ ] Idempotency proven with concurrent test
- [ ] All state transitions validated
- [ ] Events emitted correctly
- [ ] ~18 tests passing

---

### B.6 MVP-4: MarketDataProvider

> **Implements**: Market data with caching
> 
> **Deliverables**:
> ```
> src/veda/
> └── market_data_provider.py  # MarketDataProvider class
> ```

**Features**:
- `get_bars()` with caching
- `get_latest_bar()`, `get_latest_quote()`
- Cache TTL expiration
- `clear_cache()`

**Completion Criteria**:
- [ ] Caching reduces adapter calls
- [ ] Cache expires after TTL
- [ ] Real-time data not cached
- [ ] ~10 tests passing

---

### B.7 MVP-5: AlpacaAdapter

> **Implements**: Real Alpaca API integration
> 
> **Deliverables**:
> ```
> src/veda/adapters/
> └── alpaca_adapter.py  # AlpacaAdapter class
> ```

**Features**:
- Submit orders via Alpaca Trading API
- Get order status
- Cancel orders
- Get account info
- Get historical bars via Alpaca Data API
- Handle rate limits and errors

**Test Strategy**:
- Use `respx` to mock HTTP requests
- No real API calls in unit tests

**Completion Criteria**:
- [ ] All order types supported
- [ ] Error handling (rejection, rate limit)
- [ ] HTTP requests properly formatted
- [ ] ~15 tests passing

---

### B.8 MVP-6: VedaService + GLaDOS Integration

> **Implements**: Service orchestration and event handling
> 
> **Deliverables**:
> ```
> src/veda/
> └── veda_service.py  # VedaService class
> 
> # Updates to GLaDOS
> src/glados/services/
> └── order_service.py  # Update to use Veda
> ```

**Features**:
- Handle `live.PlaceOrder` events
- Handle `live.FetchWindow` events
- Emit `orders.*` and `data.*` events
- Direct API methods for GLaDOS

**Completion Criteria**:
- [ ] Event handlers work end-to-end
- [ ] Events properly emitted
- [ ] GLaDOS integration tested
- [ ] ~12 tests passing

---

### B.9 Success Criteria (M3 Overall)

- [ ] All MVP-1 through MVP-6 complete
- [ ] `pytest tests/unit/veda/ -v` all passing (~90 tests)
- [ ] Coverage ≥85% for `src/veda/`
- [ ] Order idempotency proven with tests
- [ ] Mock exchange passes all scenarios
- [ ] Alpaca adapter works with mocked HTTP

**Test Count Estimate**:
| MVP | Tests |
|-----|-------|
| MVP-1 | ~20 |
| MVP-2 | ~15 |
| MVP-3 | ~18 |
| MVP-4 | ~10 |
| MVP-5 | ~15 |
| MVP-6 | ~12 |
| **Total** | **~90** |

---

### B.10 What Remains for M4+

| Feature | Full Design | M3 Status | M4+ |
|---------|-------------|-----------|-----|
| Streaming quotes | ✅ Designed | ❌ Deferred | Implement WebSocket |
| Real-time bar updates | ✅ Designed | ❌ Deferred | Implement |
| Order sync on startup | ✅ Designed | ❌ Deferred | Recovery logic |
| Position tracking | ✅ Designed | ⚠️ Basic | Full tracking |
| Multiple exchanges | ✅ Interface ready | ❌ Alpaca only | Add more adapters |
| Rate limiter util | ✅ Designed | ❌ Basic | Token bucket |

---

### B.11 Development Notes

1. **HTTP Mocking**: Use `respx` for mocking Alpaca HTTP calls
2. **Async Testing**: All tests use `pytest-asyncio`
3. **Decimal Precision**: Use `Decimal` for all monetary values
4. **Timestamps**: All times in UTC
5. **Idempotency Key**: `client_order_id` is the single source of truth
6. **Event Flow**: `live.PlaceOrder` → OrderManager → Alpaca → `orders.Filled`
7. **No Real API in Tests**: Unit tests never call real Alpaca API

---
