"""
Tests for FillSimulator

Unit tests for fill simulation logic (slippage, commission, limit fills).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

# These imports will fail until we implement
from src.greta.fill_simulator import DefaultFillSimulator
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
    time_in_force: TimeInForce = TimeInForce.DAY,
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
        time_in_force=time_in_force,
    )


class TestDefaultFillSimulator:
    """Tests for DefaultFillSimulator."""

    @pytest.fixture
    def simulator(self) -> DefaultFillSimulator:
        """Create simulator instance."""
        return DefaultFillSimulator()

    @pytest.fixture
    def default_config(self) -> FillSimulationConfig:
        """Create default config (no slippage/commission)."""
        return FillSimulationConfig()

    # =========================================================================
    # Market Order Tests
    # =========================================================================

    def test_market_buy_fills_at_open_by_default(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Market buy fills at bar open price by default."""
        intent = make_order_intent(side=OrderSide.BUY, order_type=OrderType.MARKET)
        bar = make_bar(open_=Decimal("42000.00"))

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.fill_price == Decimal("42000.00")
        assert fill.side == "buy"

    def test_market_sell_fills_at_open_by_default(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Market sell fills at bar open price by default."""
        intent = make_order_intent(side=OrderSide.SELL, order_type=OrderType.MARKET)
        bar = make_bar(open_=Decimal("42000.00"))

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.fill_price == Decimal("42000.00")
        assert fill.side == "sell"

    def test_market_buy_with_slippage(
        self, simulator: DefaultFillSimulator
    ) -> None:
        """Market buy includes unfavorable slippage (pays more)."""
        config = FillSimulationConfig(slippage_bps=Decimal("5"))  # 5 bps = 0.05%
        intent = make_order_intent(side=OrderSide.BUY, order_type=OrderType.MARKET)
        bar = make_bar(open_=Decimal("42000.00"))

        fill = simulator.simulate_fill(intent, bar, config)

        assert fill is not None
        # 5 bps of 42000 = 42000 * 0.0005 = 21
        expected_price = Decimal("42000.00") + Decimal("21.00")
        assert fill.fill_price == expected_price
        assert fill.slippage > Decimal("0")

    def test_market_sell_with_slippage(
        self, simulator: DefaultFillSimulator
    ) -> None:
        """Market sell includes unfavorable slippage (receives less)."""
        config = FillSimulationConfig(slippage_bps=Decimal("5"))  # 5 bps
        intent = make_order_intent(side=OrderSide.SELL, order_type=OrderType.MARKET)
        bar = make_bar(open_=Decimal("42000.00"))

        fill = simulator.simulate_fill(intent, bar, config)

        assert fill is not None
        # Sell with slippage = price goes DOWN (unfavorable)
        expected_price = Decimal("42000.00") - Decimal("21.00")
        assert fill.fill_price == expected_price

    def test_market_order_with_commission(
        self, simulator: DefaultFillSimulator
    ) -> None:
        """Commission is calculated correctly."""
        config = FillSimulationConfig(commission_bps=Decimal("10"))  # 10 bps = 0.1%
        intent = make_order_intent(
            side=OrderSide.BUY, 
            order_type=OrderType.MARKET, 
            qty=Decimal("1.0")
        )
        bar = make_bar(open_=Decimal("42000.00"))

        fill = simulator.simulate_fill(intent, bar, config)

        assert fill is not None
        # 10 bps of 42000 = 42000 * 0.001 = 42
        assert fill.commission == Decimal("42.00")

    def test_commission_minimum(
        self, simulator: DefaultFillSimulator
    ) -> None:
        """Minimum commission is enforced."""
        config = FillSimulationConfig(
            commission_bps=Decimal("1"),  # 1 bp of small order = tiny commission
            min_commission=Decimal("1.00"),  # But minimum is $1
        )
        intent = make_order_intent(
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("0.01"),  # Small order
        )
        bar = make_bar(open_=Decimal("100.00"))  # Notional = $1

        fill = simulator.simulate_fill(intent, bar, config)

        assert fill is not None
        # 1 bp of $1 = 0.0001, but min is $1
        assert fill.commission == Decimal("1.00")

    # =========================================================================
    # Limit Order Tests
    # =========================================================================

    def test_limit_buy_fills_when_low_touches_limit(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Limit buy fills if bar low <= limit price."""
        intent = make_order_intent(
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("41000.00"),
        )
        bar = make_bar(low=Decimal("40900.00"))  # Low below limit

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.fill_price == Decimal("41000.00")  # Fills at limit

    def test_limit_buy_no_fill_when_price_too_high(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Limit buy does NOT fill if bar low > limit price."""
        intent = make_order_intent(
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("40000.00"),
        )
        bar = make_bar(low=Decimal("41000.00"))  # Low above limit

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is None  # Cannot fill

    def test_limit_sell_fills_when_high_touches_limit(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Limit sell fills if bar high >= limit price."""
        intent = make_order_intent(
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("43000.00"),
        )
        bar = make_bar(high=Decimal("43100.00"))  # High above limit

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.fill_price == Decimal("43000.00")  # Fills at limit

    def test_limit_sell_no_fill_when_price_too_low(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Limit sell does NOT fill if bar high < limit price."""
        intent = make_order_intent(
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=Decimal("44000.00"),
        )
        bar = make_bar(high=Decimal("43000.00"))  # High below limit

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is None  # Cannot fill

    # =========================================================================
    # Stop Order Tests
    # =========================================================================

    def test_stop_buy_triggers_when_high_reaches_stop(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Stop buy triggers if bar high >= stop price."""
        intent = make_order_intent(
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            stop_price=Decimal("43000.00"),
        )
        bar = make_bar(high=Decimal("43100.00"))  # High above stop

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.fill_price == Decimal("43000.00")  # Fills at stop

    def test_stop_buy_no_fill_when_high_below_stop(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Stop buy does NOT trigger if bar high < stop price."""
        intent = make_order_intent(
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            stop_price=Decimal("44000.00"),
        )
        bar = make_bar(high=Decimal("43000.00"))  # High below stop

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is None  # Not triggered

    def test_stop_sell_triggers_when_low_reaches_stop(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Stop sell triggers if bar low <= stop price."""
        intent = make_order_intent(
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            stop_price=Decimal("41000.00"),
        )
        bar = make_bar(low=Decimal("40900.00"))  # Low below stop

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.fill_price == Decimal("41000.00")  # Fills at stop

    def test_stop_sell_no_fill_when_low_above_stop(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Stop sell does NOT trigger if bar low > stop price."""
        intent = make_order_intent(
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            stop_price=Decimal("40000.00"),
        )
        bar = make_bar(low=Decimal("41000.00"))  # Low above stop

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is None  # Not triggered

    # =========================================================================
    # Fill At Configuration Tests
    # =========================================================================

    def test_fill_at_close(
        self, simulator: DefaultFillSimulator
    ) -> None:
        """Can configure to fill at bar close."""
        config = FillSimulationConfig(fill_at="close")
        intent = make_order_intent(side=OrderSide.BUY, order_type=OrderType.MARKET)
        bar = make_bar(open_=Decimal("42000.00"), close=Decimal("42100.00"))

        fill = simulator.simulate_fill(intent, bar, config)

        assert fill is not None
        assert fill.fill_price == Decimal("42100.00")

    def test_fill_copies_order_info(
        self, simulator: DefaultFillSimulator, default_config: FillSimulationConfig
    ) -> None:
        """Fill includes order information."""
        intent = make_order_intent(
            client_order_id="my-order-123",
            symbol="ETH/USD",
            side=OrderSide.SELL,
            qty=Decimal("5.5"),
        )
        bar = make_bar(symbol="ETH/USD")

        fill = simulator.simulate_fill(intent, bar, default_config)

        assert fill is not None
        assert fill.client_order_id == "my-order-123"
        assert fill.symbol == "ETH/USD"
        assert fill.side == "sell"
        assert fill.qty == Decimal("5.5")
