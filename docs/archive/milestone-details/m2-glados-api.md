## 9. GLaDOS API Implementation Plan (Current Focus)

> **Status**: ✅ COMPLETE | **Target**: M2 completion

This section follows the **Design-Complete, Execute-MVP** approach:
- **Part A**: Full Design (complete specification)
- **Part B**: MVP Execution Plan (incremental implementation)

---

## Part A: Full Design

### A.1 API Endpoints (Complete Specification)

```
┌─────────────────────────────────────────────────────────────────┐
│  REST API - Complete Endpoint Design                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Health & System                                                │
│  ├── GET  /healthz                    → Health check            │
│  └── GET  /api/v1/info                → System info             │
│                                                                 │
│  Run Management                                                 │
│  ├── GET    /api/v1/runs              → List runs (paginated)   │
│  ├── POST   /api/v1/runs              → Create new run          │
│  ├── GET    /api/v1/runs/{id}         → Get run details         │
│  ├── POST   /api/v1/runs/{id}/start   → Start a pending run     │
│  ├── POST   /api/v1/runs/{id}/stop    → Stop a running run      │
│  └── DELETE /api/v1/runs/{id}         → Delete a run            │
│                                                                 │
│  Order Queries                                                  │
│  ├── GET  /api/v1/orders              → List orders (filtered)  │
│  └── GET  /api/v1/orders/{id}         → Get order details       │
│                                                                 │
│  Market Data                                                    │
│  ├── GET  /api/v1/candles             → OHLCV data              │
│  └── GET  /api/v1/symbols             → Available symbols       │
│                                                                 │
│  Real-time Events                                               │
│  ├── GET  /api/v1/events/stream       → SSE event stream        │
│  └── GET  /api/v1/events/tail         → REST polling fallback   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### A.2 Data Models (Complete Schema Design)

#### Run Model
```python
class RunMode(str, Enum):
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"

class RunStatus(str, Enum):
    PENDING = "pending"        # Created, not started
    RUNNING = "running"        # Actively trading
    STOPPED = "stopped"        # Manually stopped
    COMPLETED = "completed"    # Finished (backtest end or strategy exit)
    ERROR = "error"            # Failed with error

class RunCreate(BaseModel):
    """Request body for creating a run."""
    strategy_id: str
    mode: RunMode
    symbols: list[str]
    timeframe: str = "1m"
    # Backtest-specific (required when mode=backtest)
    start_time: datetime | None = None
    end_time: datetime | None = None
    # Optional
    config: dict[str, Any] | None = None  # Strategy-specific config

class RunResponse(BaseModel):
    """Full run details."""
    id: str
    strategy_id: str
    mode: RunMode
    status: RunStatus
    symbols: list[str]
    timeframe: str
    config: dict[str, Any] | None
    # Timestamps
    created_at: datetime
    started_at: datetime | None
    stopped_at: datetime | None
    # Stats (populated during/after run)
    stats: RunStats | None

class RunStats(BaseModel):
    """Run performance statistics."""
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    max_drawdown: Decimal
    sharpe_ratio: float | None

class RunListResponse(BaseModel):
    """Paginated list of runs."""
    items: list[RunResponse]
    total: int
    page: int
    page_size: int
```

#### Order Model
```python
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, Enum):
    PENDING = "pending"              # Created, not submitted
    SUBMITTED = "submitted"          # Sent to exchange
    ACCEPTED = "accepted"            # Acknowledged by exchange
    PARTIALLY_FILLED = "partial"     # Some qty filled
    FILLED = "filled"                # Fully filled
    CANCELLED = "cancelled"          # Cancelled
    REJECTED = "rejected"            # Rejected by exchange
    EXPIRED = "expired"              # Time-in-force expired

class OrderResponse(BaseModel):
    """Full order details."""
    id: str
    run_id: str
    client_order_id: str          # Idempotency key
    exchange_order_id: str | None # Exchange's order ID
    # Order details
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Decimal | None         # Limit price
    stop_price: Decimal | None    # Stop trigger price
    time_in_force: str            # "day", "gtc", "ioc", "fok"
    # Fill info
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    # Status & timestamps
    status: OrderStatus
    created_at: datetime
    submitted_at: datetime | None
    filled_at: datetime | None
    # Error info
    reject_reason: str | None

class OrderListResponse(BaseModel):
    """Paginated list of orders."""
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
```

#### Candle Model
```python
class CandleResponse(BaseModel):
    """Single OHLCV candle."""
    symbol: str
    timeframe: str
    timestamp: datetime           # Bar open time (UTC)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int | None       # Number of trades in bar

class CandleListResponse(BaseModel):
    """List of candles."""
    symbol: str
    timeframe: str
    items: list[CandleResponse]
```

#### Error Model
```python
class ErrorCode(str, Enum):
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    BAD_REQUEST = "BAD_REQUEST"
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    # Domain errors
    RUN_NOT_STARTABLE = "RUN_NOT_STARTABLE"
    RUN_NOT_STOPPABLE = "RUN_NOT_STOPPABLE"
    INVALID_RUN_MODE = "INVALID_RUN_MODE"

class ErrorResponse(BaseModel):
    """Unified error response format."""
    code: ErrorCode
    message: str                  # Human-readable message
    details: dict[str, Any] | None  # Additional context
    correlation_id: str           # Request tracking ID
    timestamp: datetime
```

#### SSE Event Model
```python
class SSEEventType(str, Enum):
    # Run events
    RUN_STARTED = "run.started"
    RUN_STOPPED = "run.stopped"
    RUN_COMPLETED = "run.completed"
    RUN_ERROR = "run.error"
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_SUBMITTED = "order.submitted"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REJECTED = "order.rejected"
    # Clock events
    TICK = "tick"
    # System events
    HEARTBEAT = "heartbeat"

# SSE payload is minimal (thin events pattern)
# Frontend fetches full details via REST

class SSERunEvent(BaseModel):
    """Thin event for run status changes."""
    run_id: str
    status: RunStatus

class SSEOrderEvent(BaseModel):
    """Thin event for order updates."""
    order_id: str
    run_id: str
    status: OrderStatus

class SSETickEvent(BaseModel):
    """Tick notification."""
    run_id: str
    timestamp: datetime
    bar_index: int
```

### A.3 Service Interfaces (Complete Design)

```python
# src/glados/services/run_manager.py
class RunManager(ABC):
    """
    Manages trading run lifecycle.
    
    Responsibilities:
    - CRUD operations for runs
    - State transitions (pending → running → stopped)
    - Coordinating with Marvin (strategy) and Clock
    
    Note: Does NOT directly interact with Veda/Greta.
    Strategy decisions flow through events.
    """
    
    @abstractmethod
    async def create(self, request: RunCreate) -> Run:
        """Create a new run in PENDING status."""
    
    @abstractmethod
    async def get(self, run_id: str) -> Run | None:
        """Get run by ID."""
    
    @abstractmethod
    async def list(
        self,
        status: RunStatus | None = None,
        mode: RunMode | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Run], int]:
        """List runs with optional filters. Returns (runs, total_count)."""
    
    @abstractmethod
    async def start(self, run_id: str) -> Run:
        """Start a pending run. Raises if not startable."""
    
    @abstractmethod
    async def stop(self, run_id: str) -> Run:
        """Stop a running run. Idempotent if already stopped."""
    
    @abstractmethod
    async def delete(self, run_id: str) -> None:
        """Delete a run. Only allowed if not running."""
    
    @abstractmethod
    async def update_stats(self, run_id: str, stats: RunStats) -> Run:
        """Update run statistics."""


# src/glados/services/order_service.py
class OrderService(ABC):
    """
    Provides order query capabilities.
    
    Note: Order creation happens through events (strategy → live/backtest).
    This service is READ-ONLY for the API layer.
    """
    
    @abstractmethod
    async def get(self, order_id: str) -> Order | None:
        """Get order by ID."""
    
    @abstractmethod
    async def list(
        self,
        run_id: str | None = None,
        status: OrderStatus | None = None,
        symbol: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Order], int]:
        """List orders with filters. Returns (orders, total_count)."""


# src/glados/services/market_data_service.py
class MarketDataService(ABC):
    """
    Provides market data queries.
    
    Delegates to Veda (live) or WallE (historical).
    """
    
    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[Candle]:
        """Get OHLCV candles."""
    
    @abstractmethod
    async def get_symbols(self) -> list[str]:
        """Get available trading symbols."""


# src/glados/sse_broadcaster.py
class SSEBroadcaster:
    """
    Manages SSE connections and broadcasts events to all clients.
    
    Features:
    - Multi-client support
    - Event ID tracking for reconnection
    - Heartbeat to keep connections alive
    - Graceful disconnect handling
    """
    
    async def subscribe(
        self,
        last_event_id: int | None = None,
    ) -> AsyncIterator[ServerSentEvent]:
        """Subscribe to event stream. Optionally resume from last_event_id."""
    
    async def publish(
        self,
        event_type: SSEEventType,
        data: dict,
    ) -> None:
        """Publish event to all connected clients."""
    
    async def start_heartbeat(self, interval: float = 30.0) -> None:
        """Start heartbeat task to keep connections alive."""
    
    async def stop(self) -> None:
        """Stop broadcaster and close all connections."""
    
    @property
    def client_count(self) -> int:
        """Number of connected clients."""
```

### A.4 Error Handling Strategy

```python
# All API errors follow this pattern:

# 1. Domain exceptions are raised in services
class RunNotFoundError(Exception):
    def __init__(self, run_id: str):
        self.run_id = run_id

class RunNotStartableError(Exception):
    def __init__(self, run_id: str, current_status: RunStatus):
        self.run_id = run_id
        self.current_status = current_status

# 2. Exception handlers convert to ErrorResponse
@app.exception_handler(RunNotFoundError)
async def run_not_found_handler(request: Request, exc: RunNotFoundError):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            code=ErrorCode.NOT_FOUND,
            message=f"Run {exc.run_id} not found",
            details={"run_id": exc.run_id},
            correlation_id=request.state.correlation_id,
            timestamp=datetime.utcnow(),
        ).model_dump(),
    )

# 3. Generic fallback for unexpected errors
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unexpected error", correlation_id=request.state.correlation_id)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            details=None,  # Don't leak internal details
            correlation_id=request.state.correlation_id,
            timestamp=datetime.utcnow(),
        ).model_dump(),
    )
```

### A.5 Middleware Stack

```python
# Order matters: first added = outermost
app.add_middleware(CorrelationIdMiddleware)  # Add X-Correlation-ID
app.add_middleware(RequestLoggingMiddleware)  # Log all requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### A.6 Dependency Injection

```python
# src/glados/dependencies.py

def get_settings(request: Request) -> Settings:
    """Get application settings."""
    return request.app.state.settings

def get_run_manager(request: Request) -> RunManager:
    """Get run manager instance."""
    return request.app.state.run_manager

def get_order_service(request: Request) -> OrderService:
    """Get order service instance."""
    return request.app.state.order_service

def get_market_data_service(request: Request) -> MarketDataService:
    """Get market data service instance."""
    return request.app.state.market_data_service

def get_broadcaster(request: Request) -> SSEBroadcaster:
    """Get SSE broadcaster instance."""
    return request.app.state.broadcaster

def get_event_log(request: Request) -> EventLog:
    """Get event log for persistence."""
    return request.app.state.event_log

# Usage in routes:
@router.get("/runs")
async def list_runs(
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    runs, total = await run_manager.list(page=page, page_size=page_size)
    return RunListResponse(items=runs, total=total, page=page, page_size=page_size)
```

### A.7 File Structure (Complete)

```
src/glados/
├── __init__.py
├── app.py                    # Application factory
├── dependencies.py           # DI providers
├── schemas.py                # All Pydantic models
├── exceptions.py             # Domain exceptions
├── middleware.py             # Custom middleware
├── sse_broadcaster.py        # SSE connection manager
├── services/
│   ├── __init__.py
│   ├── run_manager.py        # Run lifecycle management
│   ├── order_service.py      # Order queries
│   └── market_data_service.py # Candle/symbol queries
└── routes/
    ├── __init__.py           # Router aggregation
    ├── health.py             # /healthz
    ├── runs.py               # /api/v1/runs
    ├── orders.py             # /api/v1/orders
    ├── candles.py            # /api/v1/candles
    └── sse.py                # /api/v1/events/*
```

---

## Part B: MVP Execution Plan

Now that we have the complete design, here's how we implement it incrementally.

### B.1 MVP Overview

| MVP | What We Implement | What We Defer |
|-----|-------------------|---------------|
| **MVP-1** | app.py, /healthz, basic DI | Everything else |
| **MVP-2** | RunManager (in-memory), /runs CRUD | Pagination, /start, persistence |
| **MVP-3** | SSEBroadcaster, /events/stream | EventLog integration, /tail |
| **MVP-4** | OrderService (mock), /orders | Real data, complex filters |
| **MVP-5** | MarketDataService (mock), /candles | Real data, /symbols |
| **MVP-6** | Error handling, middleware, logging | Auth, rate limiting |

---

### B.2 TDD Test Specifications (Complete)

> **TDD Workflow**: Write test → Run (RED) → Implement → Run (GREEN) → Refactor
>
> All tests are designed against the Full Design (Part A), but implemented incrementally per MVP.

#### Test File Structure
```
tests/unit/glados/
├── test_app.py                      # MVP-1: App factory tests
├── test_schemas.py                  # MVP-1+: Schema validation tests
├── test_dependencies.py             # MVP-1+: DI tests
├── test_exceptions.py               # MVP-6: Exception tests
├── test_middleware.py               # MVP-6: Middleware tests
├── test_sse_broadcaster.py          # MVP-3: SSE broadcaster tests
├── services/
│   ├── __init__.py
│   ├── test_run_manager.py          # MVP-2: Run manager tests
│   ├── test_order_service.py        # MVP-4: Order service tests
│   └── test_market_data_service.py  # MVP-5: Market data tests
└── routes/
    ├── __init__.py
    ├── test_health.py               # MVP-1: Health endpoint tests
    ├── test_runs.py                 # MVP-2: Runs endpoint tests
    ├── test_orders.py               # MVP-4: Orders endpoint tests
    ├── test_candles.py              # MVP-5: Candles endpoint tests
    └── test_sse.py                  # MVP-3: SSE endpoint tests
```

#### MVP-1 Tests (~8 tests)

```python
# tests/unit/glados/test_app.py
class TestCreateApp:
    """Tests for application factory."""
    
    def test_returns_fastapi_instance(self):
        """create_app() should return a FastAPI instance."""
        app = create_app()
        assert isinstance(app, FastAPI)
    
    def test_app_has_configured_title(self):
        """App should have title 'Weaver API'."""
        app = create_app()
        assert app.title == "Weaver API"
    
    def test_app_has_configured_version(self):
        """App should have version from settings."""
        app = create_app()
        assert app.version == "0.1.0"
    
    def test_accepts_custom_settings(self):
        """create_app() should accept custom Settings."""
        settings = Settings(api_version="0.2.0")
        app = create_app(settings=settings)
        assert app.state.settings == settings
    
    def test_healthz_route_registered(self):
        """App should have /healthz route."""
        app = create_app()
        routes = [r.path for r in app.routes]
        assert "/healthz" in routes


# tests/unit/glados/routes/test_health.py
class TestHealthEndpoint:
    """Tests for GET /healthz endpoint."""
    
    def test_returns_200_ok(self, client: TestClient):
        """GET /healthz should return HTTP 200."""
        response = client.get("/healthz")
        assert response.status_code == 200
    
    def test_returns_status_ok(self, client: TestClient):
        """Response should contain status: ok."""
        response = client.get("/healthz")
        assert response.json()["status"] == "ok"
    
    def test_returns_version(self, client: TestClient):
        """Response should contain version string."""
        response = client.get("/healthz")
        assert "version" in response.json()
        assert response.json()["version"] == "0.1.0"
```

#### MVP-2 Tests (~12 tests)

```python
# tests/unit/glados/services/test_run_manager.py
class TestRunManagerCreate:
    """Tests for RunManager.create()."""
    
    async def test_creates_run_with_id(self, run_manager: RunManager):
        """create() should return Run with generated UUID."""
        request = RunCreate(strategy_id="test", mode=RunMode.PAPER, symbols=["BTC/USD"])
        run = await run_manager.create(request)
        assert run.id is not None
        assert len(run.id) == 36  # UUID format
    
    async def test_initial_status_is_pending(self, run_manager: RunManager):
        """New run should have status=PENDING."""
        request = RunCreate(strategy_id="test", mode=RunMode.PAPER, symbols=["BTC/USD"])
        run = await run_manager.create(request)
        assert run.status == RunStatus.PENDING
    
    async def test_preserves_request_fields(self, run_manager: RunManager):
        """Run should contain all fields from request."""
        request = RunCreate(
            strategy_id="my_strategy",
            mode=RunMode.BACKTEST,
            symbols=["BTC/USD", "ETH/USD"],
            timeframe="5m",
        )
        run = await run_manager.create(request)
        assert run.strategy_id == "my_strategy"
        assert run.mode == RunMode.BACKTEST
        assert run.symbols == ["BTC/USD", "ETH/USD"]
        assert run.timeframe == "5m"


class TestRunManagerGet:
    """Tests for RunManager.get()."""
    
    async def test_returns_existing_run(self, run_manager: RunManager):
        """get() should return run by ID."""
        request = RunCreate(strategy_id="test", mode=RunMode.PAPER, symbols=["BTC/USD"])
        created = await run_manager.create(request)
        fetched = await run_manager.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
    
    async def test_returns_none_for_unknown_id(self, run_manager: RunManager):
        """get() should return None for non-existent ID."""
        result = await run_manager.get("non-existent-id")
        assert result is None


class TestRunManagerList:
    """Tests for RunManager.list()."""
    
    async def test_empty_returns_empty_list(self, run_manager: RunManager):
        """list() should return empty list when no runs exist."""
        runs, total = await run_manager.list()
        assert runs == []
        assert total == 0
    
    async def test_returns_all_runs(self, run_manager: RunManager):
        """list() should return all created runs."""
        for i in range(3):
            await run_manager.create(
                RunCreate(strategy_id=f"test_{i}", mode=RunMode.PAPER, symbols=["BTC/USD"])
            )
        runs, total = await run_manager.list()
        assert len(runs) == 3
        assert total == 3


class TestRunManagerStop:
    """Tests for RunManager.stop()."""
    
    async def test_transitions_to_stopped(self, run_manager: RunManager):
        """stop() should change status to STOPPED."""
        request = RunCreate(strategy_id="test", mode=RunMode.PAPER, symbols=["BTC/USD"])
        run = await run_manager.create(request)
        # Simulate running state
        run.status = RunStatus.RUNNING
        stopped = await run_manager.stop(run.id)
        assert stopped.status == RunStatus.STOPPED
    
    async def test_already_stopped_is_idempotent(self, run_manager: RunManager):
        """stop() on stopped run should not raise."""
        request = RunCreate(strategy_id="test", mode=RunMode.PAPER, symbols=["BTC/USD"])
        run = await run_manager.create(request)
        run.status = RunStatus.STOPPED
        stopped = await run_manager.stop(run.id)
        assert stopped.status == RunStatus.STOPPED
    
    async def test_not_found_raises_error(self, run_manager: RunManager):
        """stop() on non-existent run should raise RunNotFoundError."""
        with pytest.raises(RunNotFoundError):
            await run_manager.stop("non-existent-id")


# tests/unit/glados/routes/test_runs.py
class TestListRunsEndpoint:
    """Tests for GET /api/v1/runs."""
    
    def test_returns_200(self, client: TestClient):
        """GET /runs should return HTTP 200."""
        response = client.get("/api/v1/runs")
        assert response.status_code == 200
    
    def test_empty_returns_empty_items(self, client: TestClient):
        """GET /runs with no runs returns empty items list."""
        response = client.get("/api/v1/runs")
        assert response.json()["items"] == []


class TestCreateRunEndpoint:
    """Tests for POST /api/v1/runs."""
    
    def test_returns_201(self, client: TestClient):
        """POST /runs with valid data returns HTTP 201."""
        response = client.post("/api/v1/runs", json={
            "strategy_id": "test",
            "mode": "paper",
            "symbols": ["BTC/USD"],
        })
        assert response.status_code == 201
    
    def test_validates_required_fields(self, client: TestClient):
        """POST /runs without required fields returns 422."""
        response = client.post("/api/v1/runs", json={})
        assert response.status_code == 422
    
    def test_validates_mode_enum(self, client: TestClient):
        """POST /runs with invalid mode returns 422."""
        response = client.post("/api/v1/runs", json={
            "strategy_id": "test",
            "mode": "invalid_mode",
            "symbols": ["BTC/USD"],
        })
        assert response.status_code == 422


class TestGetRunEndpoint:
    """Tests for GET /api/v1/runs/{id}."""
    
    def test_returns_run(self, client: TestClient):
        """GET /runs/{id} returns the run details."""
        # Create a run first
        create_resp = client.post("/api/v1/runs", json={
            "strategy_id": "test",
            "mode": "paper",
            "symbols": ["BTC/USD"],
        })
        run_id = create_resp.json()["id"]
        # Get it
        response = client.get(f"/api/v1/runs/{run_id}")
        assert response.status_code == 200
        assert response.json()["id"] == run_id
    
    def test_not_found_returns_404(self, client: TestClient):
        """GET /runs/{id} with unknown ID returns 404."""
        response = client.get("/api/v1/runs/non-existent-id")
        assert response.status_code == 404


class TestStopRunEndpoint:
    """Tests for POST /api/v1/runs/{id}/stop."""
    
    def test_stops_running_run(self, client: TestClient):
        """POST /runs/{id}/stop changes status to stopped."""
        # Create and start a run
        create_resp = client.post("/api/v1/runs", json={
            "strategy_id": "test",
            "mode": "paper",
            "symbols": ["BTC/USD"],
        })
        run_id = create_resp.json()["id"]
        # Stop it
        response = client.post(f"/api/v1/runs/{run_id}/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
```

#### MVP-3 Tests (~10 tests)

```python
# tests/unit/glados/test_sse_broadcaster.py
class TestSSEBroadcasterSubscribe:
    """Tests for SSEBroadcaster.subscribe()."""
    
    async def test_returns_async_iterator(self, broadcaster: SSEBroadcaster):
        """subscribe() should return an async iterator."""
        subscription = broadcaster.subscribe()
        assert hasattr(subscription, "__anext__")
    
    async def test_receives_published_events(self, broadcaster: SSEBroadcaster):
        """Subscriber should receive published events."""
        received = []
        
        async def collect():
            async for event in broadcaster.subscribe():
                received.append(event)
                if len(received) >= 1:
                    break
        
        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)  # Let subscriber connect
        await broadcaster.publish("test.event", {"data": "hello"})
        await asyncio.wait_for(task, timeout=1.0)
        
        assert len(received) == 1
        assert received[0].event == "test.event"


class TestSSEBroadcasterPublish:
    """Tests for SSEBroadcaster.publish()."""
    
    async def test_increments_event_id(self, broadcaster: SSEBroadcaster):
        """publish() should increment event ID."""
        # Publish multiple events
        await broadcaster.publish("event1", {})
        await broadcaster.publish("event2", {})
        assert broadcaster._event_id == 2
    
    async def test_sends_to_all_clients(self, broadcaster: SSEBroadcaster):
        """publish() should send to all connected clients."""
        received_1 = []
        received_2 = []
        
        async def collect_1():
            async for event in broadcaster.subscribe():
                received_1.append(event)
                if len(received_1) >= 1:
                    break
        
        async def collect_2():
            async for event in broadcaster.subscribe():
                received_2.append(event)
                if len(received_2) >= 1:
                    break
        
        task1 = asyncio.create_task(collect_1())
        task2 = asyncio.create_task(collect_2())
        await asyncio.sleep(0.01)
        
        await broadcaster.publish("broadcast", {"msg": "to all"})
        await asyncio.gather(task1, task2, return_exceptions=True)
        
        assert len(received_1) == 1
        assert len(received_2) == 1
    
    async def test_event_has_correct_format(self, broadcaster: SSEBroadcaster):
        """Published event should have id, event, and data fields."""
        received = []
        
        async def collect():
            async for event in broadcaster.subscribe():
                received.append(event)
                break
        
        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)
        await broadcaster.publish("test.type", {"key": "value"})
        await asyncio.wait_for(task, timeout=1.0)
        
        event = received[0]
        assert event.id is not None
        assert event.event == "test.type"
        assert '"key": "value"' in event.data or '"key":"value"' in event.data


class TestSSEBroadcasterClientManagement:
    """Tests for SSE client connection management."""
    
    async def test_client_count_increases_on_subscribe(self, broadcaster: SSEBroadcaster):
        """Client count should increase when subscribing."""
        assert broadcaster.client_count == 0
        
        async def hold_connection():
            async for _ in broadcaster.subscribe():
                break
        
        task = asyncio.create_task(hold_connection())
        await asyncio.sleep(0.01)
        assert broadcaster.client_count == 1
        
        await broadcaster.publish("close", {})
        await task
    
    async def test_client_count_decreases_on_disconnect(self, broadcaster: SSEBroadcaster):
        """Client count should decrease when client disconnects."""
        async def short_lived():
            async for _ in broadcaster.subscribe():
                break  # Disconnect immediately after first event
        
        task = asyncio.create_task(short_lived())
        await asyncio.sleep(0.01)
        assert broadcaster.client_count == 1
        
        await broadcaster.publish("trigger", {})
        await task
        await asyncio.sleep(0.01)
        assert broadcaster.client_count == 0


# tests/unit/glados/routes/test_sse.py
class TestSSEStreamEndpoint:
    """Tests for GET /api/v1/events/stream."""
    
    async def test_returns_event_stream_content_type(self, async_client: AsyncClient):
        """SSE endpoint should return text/event-stream content type."""
        async with async_client.stream("GET", "/api/v1/events/stream") as response:
            assert response.headers["content-type"].startswith("text/event-stream")
    
    async def test_receives_events(self, async_client: AsyncClient, broadcaster: SSEBroadcaster):
        """SSE endpoint should receive published events."""
        events = []
        
        async def read_stream():
            async with async_client.stream("GET", "/api/v1/events/stream") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        events.append(line)
                        break
        
        task = asyncio.create_task(read_stream())
        await asyncio.sleep(0.1)
        await broadcaster.publish("test", {"hello": "world"})
        await asyncio.wait_for(task, timeout=2.0)
        
        assert len(events) == 1
    
    async def test_supports_last_event_id(self, async_client: AsyncClient):
        """SSE endpoint should accept Last-Event-ID header."""
        headers = {"Last-Event-ID": "42"}
        async with async_client.stream(
            "GET", "/api/v1/events/stream", headers=headers
        ) as response:
            assert response.status_code == 200
```

#### MVP-4 Tests (~8 tests)

```python
# tests/unit/glados/services/test_order_service.py
class TestOrderServiceGet:
    """Tests for OrderService.get()."""
    
    async def test_returns_order_by_id(self, order_service: OrderService):
        """get() should return order with matching ID."""
        order = await order_service.get("order-123")
        assert order is not None
        assert order.id == "order-123"
    
    async def test_returns_none_for_unknown_id(self, order_service: OrderService):
        """get() should return None for non-existent ID."""
        order = await order_service.get("non-existent")
        assert order is None


class TestOrderServiceList:
    """Tests for OrderService.list()."""
    
    async def test_returns_orders_list(self, order_service: OrderService):
        """list() should return list of orders."""
        orders, total = await order_service.list()
        assert isinstance(orders, list)
        assert total >= 0
    
    async def test_filters_by_run_id(self, order_service: OrderService):
        """list() should filter by run_id."""
        orders, _ = await order_service.list(run_id="run-123")
        for order in orders:
            assert order.run_id == "run-123"


# tests/unit/glados/routes/test_orders.py
class TestListOrdersEndpoint:
    """Tests for GET /api/v1/orders."""
    
    def test_returns_200(self, client: TestClient):
        """GET /orders should return HTTP 200."""
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
    
    def test_returns_items_list(self, client: TestClient):
        """Response should contain items list."""
        response = client.get("/api/v1/orders")
        assert "items" in response.json()
        assert isinstance(response.json()["items"], list)
    
    def test_accepts_run_id_filter(self, client: TestClient):
        """GET /orders should accept run_id query param."""
        response = client.get("/api/v1/orders?run_id=test-run")
        assert response.status_code == 200


class TestGetOrderEndpoint:
    """Tests for GET /api/v1/orders/{id}."""
    
    def test_returns_order(self, client: TestClient):
        """GET /orders/{id} should return order details."""
        response = client.get("/api/v1/orders/order-123")
        assert response.status_code == 200
        assert response.json()["id"] == "order-123"
    
    def test_not_found_returns_404(self, client: TestClient):
        """GET /orders/{id} with unknown ID returns 404."""
        response = client.get("/api/v1/orders/non-existent")
        assert response.status_code == 404
```

#### MVP-5 Tests (~6 tests)

```python
# tests/unit/glados/services/test_market_data_service.py
class TestMarketDataServiceGetCandles:
    """Tests for MarketDataService.get_candles()."""
    
    async def test_returns_candle_list(self, market_data_service: MarketDataService):
        """get_candles() should return list of candles."""
        candles = await market_data_service.get_candles("BTC/USD", "1m")
        assert isinstance(candles, list)
        assert len(candles) > 0
    
    async def test_candle_has_ohlcv_fields(self, market_data_service: MarketDataService):
        """Each candle should have OHLCV fields."""
        candles = await market_data_service.get_candles("BTC/USD", "1m")
        candle = candles[0]
        assert hasattr(candle, "open")
        assert hasattr(candle, "high")
        assert hasattr(candle, "low")
        assert hasattr(candle, "close")
        assert hasattr(candle, "volume")


# tests/unit/glados/routes/test_candles.py
class TestCandlesEndpoint:
    """Tests for GET /api/v1/candles."""
    
    def test_returns_200(self, client: TestClient):
        """GET /candles should return HTTP 200."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m")
        assert response.status_code == 200
    
    def test_requires_symbol_param(self, client: TestClient):
        """GET /candles without symbol should return 422."""
        response = client.get("/api/v1/candles?timeframe=1m")
        assert response.status_code == 422
    
    def test_requires_timeframe_param(self, client: TestClient):
        """GET /candles without timeframe should return 422."""
        response = client.get("/api/v1/candles?symbol=BTC/USD")
        assert response.status_code == 422
    
    def test_returns_items_with_ohlcv(self, client: TestClient):
        """Response should contain OHLCV data."""
        response = client.get("/api/v1/candles?symbol=BTC/USD&timeframe=1m")
        data = response.json()
        assert "items" in data
        if len(data["items"]) > 0:
            candle = data["items"][0]
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle
```

#### MVP-6 Tests (~10 tests)

```python
# tests/unit/glados/test_exceptions.py
class TestDomainExceptions:
    """Tests for domain exception classes."""
    
    def test_run_not_found_error_has_run_id(self):
        """RunNotFoundError should store run_id."""
        exc = RunNotFoundError("test-id")
        assert exc.run_id == "test-id"
    
    def test_run_not_startable_error_has_details(self):
        """RunNotStartableError should store run_id and status."""
        exc = RunNotStartableError("test-id", RunStatus.COMPLETED)
        assert exc.run_id == "test-id"
        assert exc.current_status == RunStatus.COMPLETED


# tests/unit/glados/test_middleware.py
class TestCorrelationIdMiddleware:
    """Tests for CorrelationIdMiddleware."""
    
    def test_adds_correlation_id_to_response(self, client: TestClient):
        """Response should have X-Correlation-ID header."""
        response = client.get("/healthz")
        assert "x-correlation-id" in response.headers
    
    def test_uses_provided_correlation_id(self, client: TestClient):
        """Should use X-Correlation-ID from request if provided."""
        response = client.get(
            "/healthz",
            headers={"X-Correlation-ID": "my-custom-id"}
        )
        assert response.headers["x-correlation-id"] == "my-custom-id"
    
    def test_generates_uuid_if_not_provided(self, client: TestClient):
        """Should generate UUID if no correlation ID provided."""
        response = client.get("/healthz")
        correlation_id = response.headers["x-correlation-id"]
        # Should be valid UUID format
        assert len(correlation_id) == 36


class TestErrorHandling:
    """Tests for global error handling."""
    
    def test_not_found_returns_error_response(self, client: TestClient):
        """404 should return ErrorResponse format."""
        response = client.get("/api/v1/runs/non-existent")
        assert response.status_code == 404
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "correlation_id" in data
    
    def test_validation_error_returns_422(self, client: TestClient):
        """Validation error should return 422 with details."""
        response = client.post("/api/v1/runs", json={"invalid": "data"})
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
    
    def test_error_includes_timestamp(self, client: TestClient):
        """Error response should include timestamp."""
        response = client.get("/api/v1/runs/non-existent")
        data = response.json()
        assert "timestamp" in data


# tests/unit/glados/test_app.py (additions for MVP-6)
class TestAppErrorHandlers:
    """Tests for app-level error handlers."""
    
    def test_unhandled_exception_returns_500(self, client: TestClient):
        """Unhandled exceptions should return 500."""
        # This would require a route that raises an unexpected exception
        # Typically done with a test-only route
        pass
    
    def test_internal_error_hides_details(self, client: TestClient):
        """500 errors should not leak internal details."""
        # details field should be None for 500 errors
        pass
```

#### Test Fixtures (Shared)

```python
# tests/unit/glados/conftest.py
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.glados.app import create_app
from src.glados.services.run_manager import RunManager
from src.glados.sse_broadcaster import SSEBroadcaster


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncClient:
    """Async test client for SSE testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def run_manager() -> RunManager:
    """Fresh RunManager instance."""
    return RunManager()


@pytest.fixture
def broadcaster() -> SSEBroadcaster:
    """Fresh SSEBroadcaster instance."""
    return SSEBroadcaster()


@pytest.fixture
def order_service() -> OrderService:
    """Mock OrderService instance."""
    return MockOrderService()


@pytest.fixture
def market_data_service() -> MarketDataService:
    """Mock MarketDataService instance."""
    return MockMarketDataService()
```

---

### B.3 MVP-1: Bootable Skeleton

> **Implements**: app.py, dependencies.py (partial), schemas.py (partial), /healthz
> 
> **From Full Design**: HealthResponse, basic app factory

**Deliverables**:
```
src/glados/
├── app.py              # create_app() - minimal version
├── dependencies.py     # get_settings() only
├── schemas.py          # HealthResponse only
└── routes/
    └── health.py       # GET /healthz
```

**Completion Criteria**:
- [x] `uvicorn src.glados.app:app` starts
- [x] `curl localhost:8000/healthz` → `{"status": "ok", "version": "0.1.0"}`
- [x] 13 tests passing

---

### B.4 MVP-2: Run Lifecycle

> **Implements**: RunManager, /runs endpoints (partial)
> 
> **From Full Design**: RunCreate, RunResponse, RunStatus, RunMode

**What we build**:
- `RunManager` with in-memory storage (interface matches full design)
- `POST /runs` - create
- `GET /runs` - list (no pagination yet)
- `GET /runs/{id}` - get details
- `POST /runs/{id}/stop` - stop

**What we defer**:
- `POST /runs/{id}/start` - MVP-2 runs start immediately on create
- `DELETE /runs/{id}` - not critical for MVP
- Pagination in list
- Status/mode filters
- RunStats population

**Completion Criteria**:
- [x] Full Run CRUD via curl
- [x] 25 tests passing

---

### B.5 MVP-3: SSE Real-time Push

> **Implements**: SSEBroadcaster, /events/stream
> 
> **From Full Design**: SSEEventType, thin event models

**What we build**:
- `SSEBroadcaster` class (full implementation)
- `GET /events/stream` endpoint
- Manual publish capability

**What we defer**:
- EventLog integration (SSE reads from Outbox)
- `/events/tail` REST polling
- Heartbeat (nice to have, add if time permits)

**Completion Criteria**:
- [x] SSE connection works with curl -N
- [x] Events broadcast to multiple clients
- [x] 12 tests passing

---

### B.6 MVP-4: Order Queries

> **Implements**: OrderService (mock), /orders endpoints
> 
> **From Full Design**: OrderResponse, OrderStatus, OrderSide, OrderType

**What we build**:
- `MockOrderService` returning fake data
- `GET /orders` with `run_id` filter
- `GET /orders/{id}`

**What we defer**:
- Real data from Veda/WallE
- Complex filters (status, date range)
- Pagination

**Completion Criteria**:
- [x] Orders endpoint returns mock data
- [x] 12 tests passing

---

### B.7 MVP-5: Candle Queries

> **Implements**: MarketDataService (mock), /candles endpoint
> 
> **From Full Design**: CandleResponse

**What we build**:
- `MockMarketDataService` returning fake OHLCV
- `GET /candles?symbol=X&timeframe=Y`

**What we defer**:
- Real data from Veda/WallE
- `/symbols` endpoint
- Date range filters

**Completion Criteria**:
- [x] Candles endpoint returns mock OHLCV
- [x] 10 tests passing

---

### B.8 MVP-6: Production Polish

> **Implements**: Error handling, middleware, logging
> 
> **From Full Design**: ErrorResponse, ErrorCode, middleware stack

**What we build**:
- `exceptions.py` with domain exceptions
- Exception handlers in app.py
- `CorrelationIdMiddleware`
- Structured logging with structlog

**What we defer**:
- Authentication
- Rate limiting
- Request logging middleware (if time permits)

**Completion Criteria**:
- [x] CORS middleware configured
- [x] Lifespan context manager
- [x] OpenAPI docs available at /docs and /redoc
- [x] 13 tests passing
- [x] **M2 Complete** ✅

---

### B.9 Test Strategy

**Each MVP has its own test file**:
```
tests/unit/glados/
├── test_app.py                    # MVP-1
├── test_sse_broadcaster.py        # MVP-3
├── services/
│   ├── test_run_manager.py        # MVP-2
│   ├── test_order_service.py      # MVP-4
│   └── test_market_data_service.py # MVP-5
└── routes/
    ├── test_health.py             # MVP-1
    ├── test_runs.py               # MVP-2
    ├── test_orders.py             # MVP-4
    ├── test_candles.py            # MVP-5
    └── test_sse.py                # MVP-3
```

### B.10 Success Criteria (M2 Overall)

- [x] All MVP-1 through MVP-6 complete
- [x] `pytest tests/unit/glados/ -v` all passing (85 tests)
- [x] Coverage ≥85% for `src/glados/`
- [x] Full design documented, MVP implementation complete
- [x] Clear path to completing remaining features in M3+

**Final Test Count (M2)**:
| MVP | Tests |
|-----|-------|
| MVP-1 | 13 |
| MVP-2 | 25 |
| MVP-3 | 12 |
| MVP-4 | 12 |
| MVP-5 | 10 |
| MVP-6 | 13 |
| **Total** | **85** |

---

### B.11 What Remains for M3+

| Feature | Full Design | MVP Status | M3+ |
|---------|-------------|------------|-----|
| Run persistence | ✅ Designed | ❌ In-memory | Store in PostgreSQL |
| Run /start endpoint | ✅ Designed | ❌ Skipped | Implement |
| Run pagination | ✅ Designed | ❌ Returns all | Implement |
| Order real data | ✅ Designed | ❌ Mock | Integrate Veda |
| Order pagination | ✅ Designed | ❌ Returns all | Implement |
| Candle real data | ✅ Designed | ❌ Mock | Integrate Veda/WallE |
| /symbols endpoint | ✅ Designed | ❌ Skipped | Implement |
| EventLog → SSE | ✅ Designed | ❌ Manual publish | Integrate |
| /events/tail | ✅ Designed | ❌ Skipped | Implement |
| Authentication | ✅ Designed | ❌ Skipped | When needed |

---

### B.12 Development Notes

1. **Design First**: Full schema/interface design is complete BEFORE coding
2. **MVP Execution**: Implement in small, runnable increments
3. **Interface Stability**: Service interfaces won't change; only implementations
4. **TDD**: Write tests against the full design, implement minimal code to pass
5. **Defer, Don't Delete**: Features not in MVP are documented, not forgotten
4. **Mock Backend**: Routes don't call real Veda/Greta yet, just manage state
5. **SSE Testing**: Use `sse-starlette` for server, `httpx-sse` for client testing
6. **Error Codes**: Use consistent codes like `NOT_FOUND`, `VALIDATION_ERROR`, `INTERNAL_ERROR`
7. **Correlation ID**: Generate UUID per request, include in all logs and error responses
8. **OpenAPI**: FastAPI auto-generates `/docs` (Swagger) and `/redoc`

---

## Changelog

### 2026-02-02 — M3: Veda Trading Implementation Complete 🎉

**M3: Trading Works — DONE** (196 new tests, 493 total):

All 6 MVPs implemented via TDD:
- ✅ MVP-1: Core Models & Interfaces (42 tests)
- ✅ MVP-2: MockExchangeAdapter (27 tests)
- ✅ MVP-3: OrderManager (35 tests)
- ✅ MVP-4: PositionTracker (28 tests)
- ✅ MVP-5: Persistence Layer (24 tests)
- ✅ MVP-6: AlpacaAdapter (19 tests) + Exceptions (21 tests)

**Files Created** (`src/veda/`):
```
src/veda/
├── __init__.py
├── models.py              # OrderIntent, OrderState, Position, Bar, Quote, Trade, etc.
├── interfaces.py          # ExchangeAdapter ABC, OrderSubmitResult, ExchangeOrder
├── exceptions.py          # VedaError, OrderError, AdapterError hierarchy
├── order_manager.py       # Order lifecycle, idempotency, state tracking
├── position_tracker.py    # Position tracking, P&L calculation
├── persistence.py         # VedaOrder model, OrderRepository
└── adapters/
    ├── __init__.py
    ├── mock_adapter.py    # Full MockExchangeAdapter for testing/backtesting
    └── alpaca_adapter.py  # AlpacaAdapter for paper/live trading
```

**Test Files** (`tests/unit/veda/`):
```
tests/unit/veda/
├── conftest.py            # Shared fixtures (sample_order_intent, etc.)
├── test_models.py         # 42 tests - all data models
├── test_interfaces.py     # 20 tests - ExchangeAdapter ABC
├── test_mock_adapter.py   # 27 tests - MockExchangeAdapter
├── test_order_manager.py  # 35 tests - OrderManager
├── test_position_tracker.py # 28 tests - PositionTracker
├── test_persistence.py    # 24 tests (20 unit + 4 integration)
├── test_alpaca_adapter.py # 19 tests - AlpacaAdapter
└── test_exceptions.py     # 21 tests - Exception hierarchy
```

**Key Features**:
- **Idempotency**: Orders tracked by `client_order_id` (strategy-generated UUID)
- **Adapter Pattern**: `ExchangeAdapter` ABC allows swapping exchanges
- **Mock-First Testing**: All unit tests use mocks, no real API calls needed
- **Paper Trading**: AlpacaAdapter supports paper mode for safe testing
- **Position Tracking**: Real-time P&L with unrealized/realized gains
- **Persistence Ready**: OrderRepository for database storage (integration tests)

**Test Strategy**:
- Unit tests: 192 passing (all use mocks)
- Integration tests: 4 (require database, skipped without DB_URL)
- Type safety: All Pylance errors resolved with proper type annotations

**Next**: M4 (Backtest Works) - Greta simulation with historical data

---

### 2026-02-02 — M3: Veda Trading Design Complete 📋

**M3 Full Design (Section 10)**:
- Part A: Complete specification for Veda live trading module
  - A.1: Module responsibilities and architecture
  - A.2: Integration diagram (GLaDOS → Veda → Alpaca)
  - A.3: Data models (OrderIntent, OrderState, Bar, Quote, Fill, etc.)
  - A.4: Service interfaces (ExchangeAdapter ABC, OrderManager, MarketDataProvider, VedaService)
  - A.5: Event types (orders.Created, orders.Filled, etc.)
  - A.6: Error handling (VedaError hierarchy)
  - A.7: File structure
  - A.8: Idempotency design via client_order_id

- Part B: MVP execution plan
  - 6 MVPs: Models → MockAdapter → OrderManager → MarketData → AlpacaAdapter → Integration
  - ~90 tests specified
  - TDD test specifications for all components

**Key Design Decisions**:
- Idempotency via `client_order_id` (strategy-generated UUID)
- MockExchangeAdapter for comprehensive testing without real API
- ExchangeAdapter ABC allows future exchange integrations
- Event-driven: `live.PlaceOrder` → `orders.Filled`

---

### 2026-02-02 — M2: GLaDOS API Complete 🎉

**M2: API Live — DONE**:
- ✅ FastAPI application factory with lifespan context
- ✅ REST endpoints: /healthz, /api/v1/runs, /api/v1/orders, /api/v1/candles
- ✅ SSE streaming: /api/v1/events/stream with SSEBroadcaster
- ✅ CORS middleware for frontend development
- ✅ OpenAPI docs at /docs and /redoc

**Files Created**:
```
src/glados/
├── app.py                    # Application factory with lifespan & CORS
├── schemas.py                # All Pydantic models (Run, Order, Candle, etc.)
├── dependencies.py           # DI providers
├── exceptions.py             # Domain exceptions
├── sse_broadcaster.py        # SSE connection manager
├── services/
│   ├── run_manager.py        # Run lifecycle (in-memory MVP)
│   ├── order_service.py      # Mock order queries
│   └── market_data_service.py # Mock candle data
└── routes/
    ├── health.py             # GET /healthz
    ├── runs.py               # /api/v1/runs CRUD
    ├── orders.py             # /api/v1/orders queries
    ├── candles.py            # /api/v1/candles queries
    └── sse.py                # /api/v1/events/stream
```

**Test Summary**:
| MVP | Feature | Tests |
|-----|---------|-------|
| MVP-1 | Bootable skeleton | 13 |
| MVP-2 | Run lifecycle | 25 |
| MVP-3 | SSE broadcaster | 12 |
| MVP-4 | Order queries | 12 |
| MVP-5 | Candle queries | 10 |
| MVP-6 | Production polish | 13 |
| **Total M2** | | **85** |

**Total Project Tests**: 274 (189 before M2 + 85 new)

**Next**: M3 (Trading Works) - Veda integration with mocked exchange

---

### 2026-02-02 — Development Methodology Formalized 📚

**New Section 0: Development Methodology**:
- Documented "Design-Complete, Execute-MVP" framework
- Added rationale: why this approach vs traditional MVP
- Defined milestone document structure template
- Added pre-implementation checklist
- Added TDD workflow with commit patterns

**New Appendix A: Quick Reference**:
- Pre-implementation checklist (copy-paste ready)
- TDD commit pattern examples
- MVP naming conventions
- Documentation template
- Key principles summary table
- Anti-patterns to avoid

**M2 Plan (Section 9) Restructured**:
- Part A: Full Design (complete specification)
  - All 14 endpoints documented
  - All schemas (Run, Order, Candle, Error, SSE)
  - All service interfaces
  - Error handling strategy
  - Middleware and DI design
- Part B: MVP Execution Plan
  - B.2: Complete TDD test specifications (~54 tests)
  - B.3-B.8: Six MVP iterations with clear scope
  - B.11: What remains for M3+

**Philosophy Captured**:
> "MVP is about HOW we implement, not WHAT we design."
> Design: Think comprehensively. Execute: Deliver incrementally.

---

### 2026-02-02 — M2 Plan Refactored to MVP Model 📋

**Changes**:
- Refactored M2 plan from "phase-by-feature" to "MVP iteration model"
- 6 MVP iterations, each produces a runnable system
- MVP-1: Bootable skeleton → MVP-2: Run management → MVP-3: SSE → MVP-4: Orders → MVP-5: Candles → MVP-6: Production ready
- Clear scope for each iteration: what to do and what to defer

**Principles**:
- Vertical slice first: End-to-end before horizontal expansion
- Design for future, implement for now
- Defer non-essential features to later iterations

**Project-Wide**: Added TDD + MVP development philosophy to Section 0

---

### 2026-01-30 (Late Night) — M1 Complete, M2 Started 🎉

**M1: Foundation Complete**:
- ✅ Clock module: 93 tests, 93% coverage
- ✅ Events DB integration: PostgresEventLog, PostgresOffsetStore
- ✅ Alembic migrations: outbox + consumer_offsets tables
- ✅ Integration tests: 23 tests (skipped without DB_URL)

**M2: API Live Started**:
- Created detailed implementation plan (Section 9)
- 6 MVP iterations
- Estimated: 5 days, ~54 tests
- Target: 85% coverage for `src/glados/`

**Tests**: 212 total (189 unit + 23 integration)

---

### 2026-01-30 — Database/Alembic Setup Complete 🎉

**Phase A-E Implementation Summary**:

| Phase | Description | Tests |
|-------|-------------|-------|
| A | Alembic initialization | N/A |
| B | Model unit tests | 12 |
| C | Session management | 13 |
| D | PostgresEventLog/OffsetStore refactor | N/A |
| E | Integration tests | 23 (skipped w/o DB_URL) |

**Files Created/Modified**:
- `alembic.ini`: Alembic configuration pointing to `src/walle/migrations`
- `src/walle/models.py`: SQLAlchemy 2.0 models (`OutboxEvent`, `ConsumerOffset` with BigInteger)
- `src/walle/database.py`: Async session factory and connection management
- `src/walle/migrations/env.py`: Supports `DB_URL` environment variable override
- `src/walle/migrations/versions/001_initial.py`: Creates `outbox` and `consumer_offsets` tables
- `docker/docker-compose.yml`: Added `DB_URL`, healthcheck, `depends_on`, pinned `postgres:16-alpine`
- `docker/docker-compose.dev.yml`: Same improvements as prod
- `docker/example.env` & `example.env.dev`: Added `POSTGRES_DB` variable

**Infrastructure Alignment**:
- Dev and prod docker-compose now consistent
- All use `${POSTGRES_DB}` environment variable (not hardcoded)
- Integration tests use `alembic upgrade head` (not `Base.metadata.create_all`)

**Tests**: 212 total (189 unit + 23 integration)
**Integration Tests**: Auto-skipped when `DB_URL` not set

---

### 2026-01-30 (Night) — Clock Factory Complete 🎉

**Clock Factory TDD** (`src/glados/clock/factory.py`):
- `ClockConfig` frozen dataclass with validation
- `create_clock()` factory function
- 18 unit tests, 100% coverage
- Automatic mode detection: has backtest times → BacktestClock, otherwise → RealtimeClock

**Tests**: 145 → 163 tests passing (+18)
**Clock Module**: 92 tests total, 93% coverage

---

### 2026-01-30 (Evening) — Clock Module Complete 🎉

**RealtimeClock TDD** (`src/glados/clock/realtime.py`):
- 24 unit tests covering all functionality
- 89% code coverage
- Drift compensation with two-phase sleep (long sleep + precision busy-wait)
- `_sleep_until()` method for precise bar alignment
- Tick timestamp is bar start time, not emission time

**BaseClock Refactoring** (`src/glados/clock/base.py`):
- Extracted shared state: `_run_id`, `_task`, `_bar_index`
- Moved `stop()` from abstract to concrete method
- Added `wait()` method with proper `CancelledError` handling
- DRY: removed duplicate code from both subclasses

**Tests**: 121 → 145 tests passing (+24)
**Clock Module**: 74 tests total, 93% coverage

---

### 2026-01-30 (PM) — BacktestClock Complete

**BacktestClock TDD** (`src/glados/clock/backtest.py`):
- 33 unit tests covering all functionality
- 92% code coverage
- Fixed bug: `_running` not reset when tick loop completes naturally
- Added `wait()` method for clean async API (replaces direct `_task` access)
- Backpressure mechanism fully tested
- Progress tracking fully tested
- Edge cases: single tick, multiple timeframes, callback exceptions

**ClockTick** (`src/glados/clock/base.py`):
- 98% coverage
- `to_dict()` serialization tested
- Immutability (frozen dataclass) tested

**Tests**: 88 → 121 tests passing (+33)

---

### 2026-01-30 — Phase 1.1 Complete (M0.5)

**Project Restructure**:
- Renamed all module directories to lowercase (`GLaDOS` → `glados`, `Veda` → `veda`, etc.)
- Deleted legacy `archive/` and `archive2/` folders
- Updated all import statements throughout the codebase

**Events Module** (`src/events/`):
- `protocol.py`: Envelope and ErrorResponse dataclasses (immutable)
- `types.py`: Event type constants organized by namespace
- `registry.py`: EventSchema and EventRegistry for payload validation
- `log.py`: InMemoryEventLog for unit testing (PostgresEventLog pending)
- `offsets.py`: ConsumerOffset tracking for at-least-once delivery

**Clock Module** (`src/glados/clock/`):
- `base.py`: BaseClock ABC and ClockTick dataclass
- `utils.py`: Bar alignment utilities (17 tests)
- `realtime.py`: RealtimeClock stub
- `backtest.py`: BacktestClock stub

**Configuration** (`src/config.py`):
- AlpacaCredentials frozen dataclass
- AlpacaConfig with dual credential support (Live + Paper in parallel)
- DatabaseConfig, ServerConfig, EventConfig, TradingConfig
- WeaverConfig as root configuration

**Tests**: 88 tests passing

### 2026-01-29 — M0 Complete

- Test infrastructure established
- Python upgraded to 3.13
- pytest, fixtures, factories all working
- 14 smoke tests passing

---

## Appendix A: Development Methodology Quick Reference

> **Copy this checklist when starting any new milestone or feature.**

### A.1 Pre-Implementation Checklist

```
□ STEP 1: COMPLETE DESIGN
  □ All endpoints/APIs documented
  □ All request/response schemas defined
  □ All data models with all fields
  □ All service interfaces (abstract methods)
  □ All error cases enumerated
  □ File structure planned
  □ Integration points identified

□ STEP 2: MVP BREAKDOWN
  □ Full design split into N MVPs
  □ MVP-1 is the minimal runnable thing
  □ Each MVP has "implement" vs "defer" list
  □ Each MVP has completion criteria
  □ Deferred features documented

□ STEP 3: TDD SPECS
  □ All test cases written (against full design)
  □ Tests organized by MVP
  □ Fixtures planned
  □ Test file structure matches src/ structure

□ STEP 4: IMPLEMENTATION
  □ Start with MVP-1
  □ For each test: RED → GREEN → REFACTOR
  □ Commit after each passing test
  □ Complete all tests for MVP-N before MVP-N+1
  □ Run full test suite before marking MVP complete
```

### A.2 TDD Commit Pattern

```bash
# Pattern: test_<what>_<expected_behavior>
git commit -m "test: RunManager.create returns run with UUID"
git commit -m "feat: implement RunManager.create"
git commit -m "refactor: extract ID generation to helper"
```

### A.3 MVP Naming Convention

```
MVP-1: Always "Bootable Skeleton" or "Minimal Runnable"
MVP-2 to N-1: Core features, one per MVP
MVP-N: Always "Production Polish" (error handling, logging, etc.)
```

### A.4 Documentation Template

When documenting a new milestone, use this structure:

```markdown
## Part A: Full Design

### A.1 [Endpoints / Commands / APIs]
### A.2 [Data Models / Schemas]
### A.3 [Service Interfaces]
### A.4 [Error Handling]
### A.5 [File Structure]

---

## Part B: MVP Execution Plan

### B.1 MVP Overview Table
### B.2 TDD Test Specifications
### B.3 MVP-1: [Name]
### B.4 MVP-2: [Name]
...
### B.N Success Criteria
### B.N+1 What Remains for Next Milestone
```

### A.5 Key Principles Summary

| Principle | Description |
|-----------|-------------|
| **Design Complete** | Know the full scope before writing code |
| **Execute MVP** | Implement in small, working increments |
| **TDD** | Tests define the contract, code fulfills it |
| **Interface Stability** | Design interfaces upfront, implementations evolve |
| **Defer, Don't Delete** | Track what's not built, don't forget it |
| **Vertical Slices** | Each MVP is end-to-end, not layer-by-layer |

### A.6 Anti-Patterns to Avoid

```
❌ "Let's just build the API first, we'll figure out errors later"
   → Design ALL error cases upfront

❌ "We don't need pagination for MVP"
   → DESIGN pagination, DEFER implementation

❌ "I'll write tests after the code works"
   → Write tests FIRST (TDD)

❌ "Let's redesign this endpoint"
   → Design should be stable; if changing, update FULL DESIGN first

❌ "This MVP is taking too long, let's skip some tests"
   → Tests ARE the deliverable; reduce MVP scope instead
```

