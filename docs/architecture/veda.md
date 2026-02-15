# Veda Trading Architecture

> Part of [Architecture Documentation](../ARCHITECTURE.md)  
> Last Updated: 2026-02-04 (M6 Complete)
>
> **Document Charter**  
> **Primary role**: Veda internals (adapter contract, order flow, domain models).  
> **Authoritative for**: Veda architecture and integration patterns inside trading subsystem.  
> **Not authoritative for**: global credential policy and security baseline (use `config.md`).

## 1. Overview

Veda is the live/paper trading subsystem. It handles:

- Exchange communication via adapters
- Order management and persistence
- Position tracking
- Connection lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Veda Architecture                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────┐     ┌────────────────┐               │
│  │ VedaService │────►│ OrderManager │────►│ ExchangeAdapter│               │
│  │ (facade)    │     │ (state)      │     │ (protocol)     │               │
│  └─────────────┘     └──────────────┘     └───────┬────────┘               │
│         │                   │                      │                        │
│         │                   ▼                      ▼                        │
│         │            ┌──────────────┐     ┌────────────────┐               │
│         │            │OrderRepository│     │  Alpaca API /  │               │
│         │            │ (persistence)│     │  Mock / Other  │               │
│         │            └──────────────┘     └────────────────┘               │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                           │
│  │  EventLog   │  ← orders.Created, orders.Rejected, etc.                  │
│  └─────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ExchangeAdapter Interface

All exchange adapters implement this protocol:

### 2.1 Connection Management

```python
class ExchangeAdapter(ABC):
    """Abstract interface for exchange communication."""

    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to the exchange.

        - Initialize API clients
        - Verify credentials (account ping)
        - Idempotent (safe to call multiple times)

        Raises:
            ExchangeConnectionError: If connection fails
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the exchange.

        - Release resources
        - Clear client references
        - Idempotent
        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently connected."""
```

### 2.2 Order Operations

```python
    @abstractmethod
    async def submit_order(self, intent: OrderIntent) -> OrderSubmitResult:
        """
        Submit order to exchange.

        Args:
            intent: Order intent with symbol, side, qty, type, etc.

        Returns:
            OrderSubmitResult:
                - success: bool
                - exchange_order_id: str | None
                - status: OrderStatus
                - error_code/error_message: if failed
        """

    @abstractmethod
    async def cancel_order(self, exchange_order_id: str) -> bool:
        """Cancel an order. Returns True if accepted."""

    @abstractmethod
    async def get_order(self, exchange_order_id: str) -> ExchangeOrder | None:
        """Get order status from exchange."""

    @abstractmethod
    async def list_orders(
        self,
        status: OrderStatus | None = None,
        symbols: list[str] | None = None,
        limit: int = 100,
    ) -> list[ExchangeOrder]:
        """List orders with optional filters."""
```

### 2.3 Account & Positions

```python
    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get account balance, buying power, etc."""

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all current positions."""

    @abstractmethod
    async def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol."""
```

### 2.4 Market Data

```python
    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        """Get historical OHLCV bars."""

    @abstractmethod
    async def get_latest_bar(self, symbol: str) -> Bar | None:
        """Get most recent bar."""

    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Quote | None:
        """Get most recent quote (bid/ask)."""

    @abstractmethod
    async def get_latest_trade(self, symbol: str) -> Trade | None:
        """Get most recent trade."""
```

---

## 3. Plugin Adapter System

### 3.1 AdapterMeta

Each adapter exports metadata for discovery:

```python
# In alpaca_adapter.py
ADAPTER_META = {
    "id": "alpaca",                    # Unique identifier
    "name": "Alpaca Markets",          # Display name
    "version": "1.0.0",                # Semantic version
    "class": "AlpacaAdapter",          # Class to instantiate
    "features": [                      # Capability flags
        "stocks",
        "crypto",
        "paper",
        "live",
    ],
}
```

### 3.2 PluginAdapterLoader

Discovers adapters via AST parsing (no imports until load):

```python
loader = PluginAdapterLoader(adapter_dir=Path("src/veda/adapters"))

# List all available adapters
adapters = loader.list_adapters()
# → [AdapterMeta(id="alpaca", ...), AdapterMeta(id="mock", ...)]

# Load specific adapter
adapter = loader.load("alpaca", api_key="...", api_secret="...")

# Check features
if loader.supports_feature("alpaca", "crypto"):
    # Use for crypto trading
```

### 3.3 Discovery Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  PluginAdapterLoader.list_adapters()                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Scan adapter_dir for *.py files                             │
│  2. For each file:                                              │
│     a. Parse with ast.parse() (no import/execution)             │
│     b. Find ADAPTER_META = {...} assignment                      │
│     c. Extract dict literal values                              │
│     d. Create AdapterMeta dataclass                             │
│  3. Return list of AdapterMeta                                  │
│                                                                  │
│  Benefits:                                                       │
│  - No side effects from importing                               │
│  - Fast (no module loading)                                     │
│  - Safe (can't execute malicious code)                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. VedaService Facade

VedaService provides a high-level API over OrderManager + Adapter:

### 4.1 Order Flow

```python
class VedaService:
    async def place_order(self, intent: OrderIntent) -> OrderState:
        """
        Place order with idempotency and event emission.

        Flow:
        1. Check idempotency (by client_order_id)
        2. Submit to adapter
        3. Persist to database
        4. Emit orders.Created or orders.Rejected
        5. Return OrderState
        """
```

### 4.2 Idempotency Pattern

```python
async def place_order(self, intent: OrderIntent) -> OrderState:
    # 1. Check if order already exists
    existing = await self._order_manager.get_order(intent.client_order_id)
    if existing:
        return existing  # Return existing, don't resubmit

    # 2. Submit to exchange
    result = await self._adapter.submit_order(intent)

    # 3. Create order state
    order = OrderState(
        id=str(uuid4()),
        client_order_id=intent.client_order_id,
        exchange_order_id=result.exchange_order_id,
        status=result.status,
        ...
    )

    # 4. Persist
    await self._order_manager.save_order(order)

    # 5. Emit event
    if result.success:
        await self._emit_event("orders.Created", order)
    else:
        await self._emit_event("orders.Rejected", order)

    return order
```

### 4.3 Connection Delegation

```python
class VedaService:
    async def connect(self) -> None:
        """Delegate to adapter."""
        await self._adapter.connect()

    async def disconnect(self) -> None:
        """Delegate to adapter."""
        await self._adapter.disconnect()

    @property
    def is_connected(self) -> bool:
        """Delegate to adapter."""
        return self._adapter.is_connected
```

---

## 5. Data Models

### 5.1 OrderIntent (Input)

```python
@dataclass
class OrderIntent:
    """Order request from strategy."""
    run_id: str
    client_order_id: str
    symbol: str
    side: OrderSide          # BUY | SELL
    order_type: OrderType    # MARKET | LIMIT | STOP | STOP_LIMIT
    qty: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    time_in_force: TimeInForce  # DAY | GTC | IOC | FOK
    extended_hours: bool = False
```

### 5.2 OrderState (Internal)

```python
@dataclass
class OrderState:
    """Order tracked by OrderManager."""
    id: str
    run_id: str
    client_order_id: str
    exchange_order_id: str | None
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

### 5.3 OrderStatus Enum

```python
class OrderStatus(str, Enum):
    PENDING = "pending"           # Created locally, not yet sent
    ACCEPTED = "accepted"         # Exchange accepted
    PARTIALLY_FILLED = "partial"  # Some qty filled
    FILLED = "filled"             # Fully filled
    CANCELLED = "cancelled"       # User cancelled
    REJECTED = "rejected"         # Exchange rejected
    EXPIRED = "expired"           # Time expired
```

---

## 6. Implemented Adapters

### 6.1 AlpacaAdapter

| Feature               | Status                    |
| --------------------- | ------------------------- |
| Paper trading         | ✅                        |
| Live trading          | ✅ (credentials required) |
| Stocks                | ✅                        |
| Crypto                | ✅                        |
| Connection management | ✅                        |
| Historical bars       | ✅                        |
| Latest quote/trade    | ✅                        |
| WebSocket streaming   | ❌ (planned)              |

### 6.2 MockExchangeAdapter

For testing without real API:

| Feature            | Behavior                         |
| ------------------ | -------------------------------- |
| submit_order       | Always succeeds (configurable)   |
| get_bars           | Returns empty or configured data |
| Latency simulation | Optional delays                  |

---

## 7. Error Handling

### 7.1 Exception Hierarchy

```
VedaError
├── ExchangeConnectionError    # Connection/auth failures
├── OrderError
│   ├── OrderNotFoundError     # Order doesn't exist
│   ├── OrderRejectedError     # Exchange rejected
│   └── InsufficientFundsError # Not enough buying power
├── RateLimitError             # API rate limit hit
└── AdapterNotFoundError       # Unknown adapter ID
```

### 7.2 Connection Guard Pattern

```python
class AlpacaAdapter:
    def _require_connection(self) -> None:
        """Guard method - call at start of each operation."""
        if not self._connected:
            raise ExchangeConnectionError(
                "Not connected to Alpaca. Call connect() first."
            )

    async def submit_order(self, intent: OrderIntent) -> OrderSubmitResult:
        self._require_connection()  # Guard
        # ... rest of method
```

---

## 8. Configuration

### 8.1 Alpaca Credentials

```python
# In config.py
@dataclass
class AlpacaConfig:
    paper_key: str | None = None
    paper_secret: str | None = None
    live_key: str | None = None
    live_secret: str | None = None

    @property
    def has_paper_credentials(self) -> bool:
        return self.paper_key and self.paper_secret

    def get_credentials(self, mode: str) -> dict:
        if mode == "paper":
            return {"api_key": self.paper_key, "api_secret": self.paper_secret, "paper": True}
        return {"api_key": self.live_key, "api_secret": self.live_secret, "paper": False}
```

### 8.2 Environment Variables

| Variable              | Description           | Required          |
| --------------------- | --------------------- | ----------------- |
| `ALPACA_PAPER_KEY`    | Paper trading API key | For paper trading |
| `ALPACA_PAPER_SECRET` | Paper trading secret  | For paper trading |
| `ALPACA_LIVE_KEY`     | Live trading API key  | For live trading  |
| `ALPACA_LIVE_SECRET`  | Live trading secret   | For live trading  |

---

## 9. Testing Patterns

### 9.1 Mock Adapter in Tests

```python
@pytest.fixture
def mock_adapter():
    adapter = MockExchangeAdapter()
    adapter.configure_response(
        "submit_order",
        OrderSubmitResult(success=True, exchange_order_id="test-123", status=OrderStatus.ACCEPTED)
    )
    return adapter
```

### 9.2 Integration with Real Alpaca (Sandbox)

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ALPACA_PAPER_KEY"), reason="No Alpaca credentials")
async def test_real_alpaca_connection():
    adapter = AlpacaAdapter(
        api_key=os.getenv("ALPACA_PAPER_KEY"),
        api_secret=os.getenv("ALPACA_PAPER_SECRET"),
        paper=True
    )
    await adapter.connect()
    assert adapter.is_connected
```

---

_See also: [Events](events.md) for order event details, [API](api.md) for REST endpoints_
