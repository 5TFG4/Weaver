"""
Tests for GretaService

Unit tests for the backtest execution service.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio

# These imports will fail until we implement GretaService
from src.greta.greta_service import GretaService
from src.greta.models import FillSimulationConfig
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
        cast(AsyncMock, service._bar_repo).get_bars.assert_called()

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

        cast(AsyncMock, initialized_service._event_log).append.assert_called()


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
        # Buy at 42100 (bar open at 9:31) + slippage
        await service_with_bars.place_order(
            make_order_intent(side=OrderSide.BUY, qty=Decimal("1.0"))
        )
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Price moved up at 9:32
        await service_with_bars.advance_to(datetime(2024, 1, 1, 9, 32, tzinfo=UTC))

        pos = service_with_bars.positions["BTC/USD"]
        # Entry ~42100 (9:31 open), marked to 9:32 bar close
        # Expected profit: ~200-250 depending on slippage config
        assert Decimal("150") < pos.unrealized_pnl <= Decimal("300")


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


class TestGretaServiceStatsComputation:
    """N-08: Tests for backtest statistics computation (Sharpe, drawdown, win_rate)."""

    @pytest_asyncio.fixture
    async def service_with_trades(self) -> GretaService:
        """
        Create a service with multiple trades for stats testing.

        Scenario: 3 round-trip trades (buy+sell) across 6 bars.
        Trade 1: Buy@100, Sell@110 → profit $10
        Trade 2: Buy@105, Sell@95  → loss  $10
        Trade 3: Buy@102, Sell@108 → profit $6
        """
        bar_repo = AsyncMock()
        event_log = AsyncMock()
        event_log.append = AsyncMock()
        event_log.subscribe_filtered = AsyncMock(return_value="sub-1")

        bars = [
            make_bar(timestamp=datetime(2024, 1, 1, 9, 30, tzinfo=UTC), open_=Decimal("100"), high=Decimal("112"), low=Decimal("98"), close=Decimal("110")),
            make_bar(timestamp=datetime(2024, 1, 1, 9, 31, tzinfo=UTC), open_=Decimal("110"), high=Decimal("115"), low=Decimal("108"), close=Decimal("112")),
            make_bar(timestamp=datetime(2024, 1, 1, 9, 32, tzinfo=UTC), open_=Decimal("105"), high=Decimal("107"), low=Decimal("93"), close=Decimal("95")),
            make_bar(timestamp=datetime(2024, 1, 1, 9, 33, tzinfo=UTC), open_=Decimal("95"), high=Decimal("100"), low=Decimal("90"), close=Decimal("98")),
            make_bar(timestamp=datetime(2024, 1, 1, 9, 34, tzinfo=UTC), open_=Decimal("102"), high=Decimal("110"), low=Decimal("100"), close=Decimal("108")),
            make_bar(timestamp=datetime(2024, 1, 1, 9, 35, tzinfo=UTC), open_=Decimal("108"), high=Decimal("112"), low=Decimal("106"), close=Decimal("109")),
        ]
        bar_repo.get_bars = AsyncMock(return_value=bars)

        service = GretaService(
            run_id="run-stats",
            bar_repository=bar_repo,
            event_log=event_log,
            initial_cash=Decimal("10000"),
        )
        await service.initialize(
            symbols=["BTC/USD"],
            timeframe="1m",
            start=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            end=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
        )

        # Trade 1: Buy at open=100, Sell at open=110 → profit $10
        await service.place_order(make_order_intent(
            client_order_id="buy-1", side=OrderSide.BUY, qty=Decimal("1"),
        ))
        await service.advance_to(datetime(2024, 1, 1, 9, 30, tzinfo=UTC))

        await service.place_order(make_order_intent(
            client_order_id="sell-1", side=OrderSide.SELL, qty=Decimal("1"),
        ))
        await service.advance_to(datetime(2024, 1, 1, 9, 31, tzinfo=UTC))

        # Trade 2: Buy at open=105, Sell at open=95 → loss $10
        await service.place_order(make_order_intent(
            client_order_id="buy-2", side=OrderSide.BUY, qty=Decimal("1"),
        ))
        await service.advance_to(datetime(2024, 1, 1, 9, 32, tzinfo=UTC))

        await service.place_order(make_order_intent(
            client_order_id="sell-2", side=OrderSide.SELL, qty=Decimal("1"),
        ))
        await service.advance_to(datetime(2024, 1, 1, 9, 33, tzinfo=UTC))

        # Trade 3: Buy at open=102, Sell at open=108 → profit $6
        await service.place_order(make_order_intent(
            client_order_id="buy-3", side=OrderSide.BUY, qty=Decimal("1"),
        ))
        await service.advance_to(datetime(2024, 1, 1, 9, 34, tzinfo=UTC))

        await service.place_order(make_order_intent(
            client_order_id="sell-3", side=OrderSide.SELL, qty=Decimal("1"),
        ))
        await service.advance_to(datetime(2024, 1, 1, 9, 35, tzinfo=UTC))

        return service

    async def test_sharpe_ratio_computed(self, service_with_trades: GretaService) -> None:
        """Sharpe ratio is computed from equity curve returns."""
        result = service_with_trades.get_result()
        assert result.stats.sharpe_ratio is not None
        # With mixed positive/negative returns, Sharpe should be a finite number
        assert result.stats.sharpe_ratio != Decimal("0")

    async def test_max_drawdown_computed(self, service_with_trades: GretaService) -> None:
        """Max drawdown is computed from equity curve."""
        result = service_with_trades.get_result()
        # Drawdown should be negative (loss from peak)
        assert result.stats.max_drawdown < Decimal("0")
        assert result.stats.max_drawdown_pct < Decimal("0")

    async def test_win_rate_computed(self, service_with_trades: GretaService) -> None:
        """Win rate is computed from round-trip trades."""
        result = service_with_trades.get_result()
        stats = result.stats
        # 2 winners out of 3 trades (buy-sell pairs)
        assert stats.winning_trades == 2
        assert stats.losing_trades == 1
        assert stats.win_rate > Decimal("0")
        assert stats.win_rate <= Decimal("100")

    async def test_profit_factor_computed(self, service_with_trades: GretaService) -> None:
        """Profit factor = gross profit / gross loss."""
        result = service_with_trades.get_result()
        stats = result.stats
        assert stats.profit_factor is not None
        assert stats.profit_factor > Decimal("0")
