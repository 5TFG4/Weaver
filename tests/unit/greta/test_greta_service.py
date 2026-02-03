"""
Tests for GretaService

Unit tests for the backtest execution service.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# These imports will fail until we implement GretaService
from src.greta.greta_service import GretaService
from src.greta.models import FillSimulationConfig, SimulatedFill
from src.veda.models import OrderIntent, OrderSide, OrderType, TimeInForce
from src.walle.repositories.bar_repository import Bar


def make_bar(
    symbol: str = "BTC/USD",
    timeframe: str = "1m",
    timestamp: datetime | None = None,
    open_: Decimal = Decimal("42000.00"),
    high: Decimal = Decimal("42100.00"),
    low: Decimal = Decimal("41900.00"),
    close: Decimal = Decimal("42050.00"),
    volume: Decimal = Decimal("100.00"),
) -> Bar:
    """Factory for test bars."""
    return Bar(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp or datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def make_order_intent(
    run_id: str = "run-123",
    client_order_id: str = "order-456",
    symbol: str = "BTC/USD",
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.MARKET,
    qty: Decimal = Decimal("1.0"),
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
) -> OrderIntent:
    """Factory for test order intents."""
    return OrderIntent(
        run_id=run_id,
        client_order_id=client_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        qty=qty,
        limit_price=limit_price,
        stop_price=stop_price,
        time_in_force=TimeInForce.DAY,
    )


class TestGretaServiceInit:
    """Tests for GretaService initialization."""

    def test_requires_run_id(self) -> None:
        """GretaService requires run_id at construction."""
        mock_bar_repo = MagicMock()
        mock_event_log = MagicMock()

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
        )

        assert service.run_id == "run-123"

    def test_accepts_custom_fill_config(self) -> None:
        """Can customize fill simulation config."""
        mock_bar_repo = MagicMock()
        mock_event_log = MagicMock()
        config = FillSimulationConfig(slippage_bps=Decimal("10"))

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
            fill_config=config,
        )

        assert service._fill_config.slippage_bps == Decimal("10")

    def test_starts_with_no_positions(self) -> None:
        """Service starts with empty positions."""
        mock_bar_repo = MagicMock()
        mock_event_log = MagicMock()

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
        )

        assert service.positions == {}
        assert service.pending_orders == {}


class TestGretaServiceInitialize:
    """Tests for GretaService.initialize()."""

    @pytest_asyncio.fixture
    async def service(self) -> GretaService:
        """Create service with mocked dependencies."""
        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])
        mock_event_log = AsyncMock()

        return GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
        )

    async def test_initialize_sets_symbols(self, service: GretaService) -> None:
        """Initialize sets up symbols for backtest."""
        await service.initialize(
            symbols=["BTC/USD", "ETH/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        assert service.symbols == ["BTC/USD", "ETH/USD"]
        assert service.timeframe == "1m"

    async def test_initialize_preloads_bars(self, service: GretaService) -> None:
        """Initialize calls bar repository to preload data."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)

        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=start,
            end=end,
        )

        # Should have called get_bars to preload
        service._bar_repo.get_bars.assert_called()

    async def test_initialize_resets_state(self, service: GretaService) -> None:
        """Initialize clears any previous state."""
        # Set some state
        service._positions["BTC/USD"] = MagicMock()
        service._fills.append(MagicMock())

        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        assert service.positions == {}
        assert service.fills == []


class TestGretaServicePlaceOrder:
    """Tests for GretaService.place_order()."""

    @pytest_asyncio.fixture
    async def initialized_service(self) -> GretaService:
        """Create and initialize service."""
        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
        )

        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        )

        return service

    async def test_place_order_queues_for_fill(
        self, initialized_service: GretaService
    ) -> None:
        """Place order adds to pending orders."""
        intent = make_order_intent()

        await initialized_service.place_order(intent)

        assert len(initialized_service.pending_orders) == 1

    async def test_place_order_emits_event(
        self, initialized_service: GretaService
    ) -> None:
        """Place order emits orders.Placed event."""
        intent = make_order_intent()

        await initialized_service.place_order(intent)

        initialized_service._event_log.append.assert_called()


class TestGretaServiceAdvanceTo:
    """Tests for GretaService.advance_to() - tick processing."""

    @pytest_asyncio.fixture
    async def service_with_bars(self) -> GretaService:
        """Create service with preloaded bar data with rising prices."""
        bars = [
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                open_=Decimal("42000.00"),
                close=Decimal("42050.00"),
            ),
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 31, tzinfo=UTC),
                open_=Decimal("42100.00"),
                close=Decimal("42150.00"),
            ),
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 32, tzinfo=UTC),
                open_=Decimal("42200.00"),
                close=Decimal("42300.00"),
            ),
        ]

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=bars)
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
        )

        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            end=datetime(2024, 1, 1, 9, 32, tzinfo=UTC),
        )

        return service

    async def test_advance_to_updates_current_bar(
        self, service_with_bars: GretaService
    ) -> None:
        """advance_to() updates current bar for symbols."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)

        await service_with_bars.advance_to(ts)

        assert "BTC/USD" in service_with_bars.current_bars
        assert service_with_bars.current_bars["BTC/USD"].timestamp == ts

    async def test_advance_to_fills_market_order(
        self, service_with_bars: GretaService
    ) -> None:
        """advance_to() fills pending market orders."""
        intent = make_order_intent(order_type=OrderType.MARKET)
        await service_with_bars.place_order(intent)

        # Advance to next tick
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Order should be filled
        assert len(service_with_bars.fills) == 1
        assert len(service_with_bars.pending_orders) == 0

    async def test_advance_to_creates_position_on_fill(
        self, service_with_bars: GretaService
    ) -> None:
        """Fill creates or updates position."""
        intent = make_order_intent(
            symbol="BTC/USD",
            side=OrderSide.BUY,
            qty=Decimal("1.0"),
        )
        await service_with_bars.place_order(intent)
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        assert "BTC/USD" in service_with_bars.positions
        assert service_with_bars.positions["BTC/USD"].qty == Decimal("1.0")

    async def test_advance_to_records_equity(
        self, service_with_bars: GretaService
    ) -> None:
        """advance_to() records equity curve point."""
        ts = datetime(2024, 1, 1, 9, 30, tzinfo=UTC)

        await service_with_bars.advance_to(ts)

        assert len(service_with_bars.equity_curve) == 1

    async def test_limit_order_fills_when_price_reached(
        self, service_with_bars: GretaService
    ) -> None:
        """Limit order fills when bar touches limit price."""
        # Place limit buy below current market
        intent = make_order_intent(
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            limit_price=Decimal("41900.00"),  # Below bar low
        )
        await service_with_bars.place_order(intent)

        # Bar has low=41900, so limit should fill
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        assert len(service_with_bars.fills) == 1
        assert service_with_bars.fills[0].fill_price == Decimal("41900.00")

    async def test_limit_order_stays_pending_when_not_reached(
        self, service_with_bars: GretaService
    ) -> None:
        """Limit order stays pending when price not reached."""
        # Place limit buy way below market
        intent = make_order_intent(
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            limit_price=Decimal("40000.00"),  # Far below bar low
        )
        await service_with_bars.place_order(intent)

        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Order should still be pending
        assert len(service_with_bars.fills) == 0
        assert len(service_with_bars.pending_orders) == 1


class TestGretaServicePositionTracking:
    """Tests for position tracking logic."""

    @pytest_asyncio.fixture
    async def service_with_bars(self) -> GretaService:
        """Create service with bar data with rising prices."""
        bars = [
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                open_=Decimal("42000"),
                close=Decimal("42050"),
            ),
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 31, tzinfo=UTC),
                open_=Decimal("42100"),
                close=Decimal("42200"),
            ),
            make_bar(
                timestamp=datetime(2024, 1, 1, 9, 32, tzinfo=UTC),
                open_=Decimal("42200"),
                close=Decimal("42350"),
            ),
        ]

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=bars)
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
        )

        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            end=datetime(2024, 1, 1, 9, 32, tzinfo=UTC),
        )

        return service

    async def test_buy_increases_position(
        self, service_with_bars: GretaService
    ) -> None:
        """Buying increases position qty."""
        # First buy
        await service_with_bars.place_order(
            make_order_intent(side=OrderSide.BUY, qty=Decimal("1.0"))
        )
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Second buy
        await service_with_bars.place_order(
            make_order_intent(
                client_order_id="order-789", side=OrderSide.BUY, qty=Decimal("0.5")
            )
        )
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 32, tzinfo=UTC))

        assert service_with_bars.positions["BTC/USD"].qty == Decimal("1.5")

    async def test_sell_decreases_position(
        self, service_with_bars: GretaService
    ) -> None:
        """Selling decreases position qty."""
        # Buy first
        await service_with_bars.place_order(
            make_order_intent(side=OrderSide.BUY, qty=Decimal("2.0"))
        )
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Sell some
        await service_with_bars.place_order(
            make_order_intent(
                client_order_id="order-789", side=OrderSide.SELL, qty=Decimal("1.0")
            )
        )
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 32, tzinfo=UTC))

        assert service_with_bars.positions["BTC/USD"].qty == Decimal("1.0")

    async def test_position_unrealized_pnl_updates(
        self, service_with_bars: GretaService
    ) -> None:
        """Position unrealized P&L updates with price."""
        # Buy at 42000 (bar open at 9:31)
        await service_with_bars.place_order(
            make_order_intent(side=OrderSide.BUY, qty=Decimal("1.0"))
        )
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Price moved to 42200 (bar open at 9:32)
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 32, tzinfo=UTC))

        pos = service_with_bars.positions["BTC/USD"]
        # Bought at ~42100 (9:31 open), now at 42200 open = ~100 profit
        assert pos.unrealized_pnl > Decimal("0")


class TestGretaServiceGetResult:
    """Tests for GretaService.get_result()."""

    @pytest_asyncio.fixture
    async def completed_service(self) -> GretaService:
        """Create service that has completed a backtest."""
        bars = [
            make_bar(timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC)),
            make_bar(timestamp=datetime(2024, 1, 1, 9, 31, tzinfo=UTC)),
        ]

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=bars)
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        service = GretaService(
            run_id="run-123",
            bar_repository=mock_bar_repo,
            event_log=mock_event_log,
            initial_cash=Decimal("100000"),
        )

        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            end=datetime(2024, 1, 1, 9, 31, tzinfo=UTC),
        )

        # Run through ticks
        await service.advance_to(datetime(2024, 1, 1, 9, 30, tzinfo=UTC))
        await service.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        return service

    async def test_get_result_returns_backtest_result(
        self, completed_service: GretaService
    ) -> None:
        """get_result() returns BacktestResult."""
        from src.greta.models import BacktestResult

        result = completed_service.get_result()

        assert isinstance(result, BacktestResult)
        assert result.run_id == "run-123"

    async def test_get_result_includes_equity_curve(
        self, completed_service: GretaService
    ) -> None:
        """Result includes equity curve."""
        result = completed_service.get_result()

        assert len(result.equity_curve) > 0

    async def test_get_result_includes_fills(
        self, completed_service: GretaService
    ) -> None:
        """Result includes all fills."""
        # Place an order first
        await completed_service.place_order(make_order_intent())
        await completed_service.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        result = completed_service.get_result()

        assert result.fills == completed_service.fills
