"""
Veda Models Tests

TDD tests for Veda data models.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.veda.models import (
    AccountInfo,
    Bar,
    Fill,
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Quote,
    TimeInForce,
    Trade,
)


# =============================================================================
# OrderIntent Tests
# =============================================================================


class TestOrderIntent:
    """Tests for OrderIntent dataclass."""

    def test_creates_with_required_fields(self, sample_order_intent: OrderIntent) -> None:
        """OrderIntent requires all order details."""
        assert sample_order_intent.run_id == "run-123"
        assert sample_order_intent.client_order_id == "client-123"
        assert sample_order_intent.symbol == "BTC/USD"
        assert sample_order_intent.side == OrderSide.BUY
        assert sample_order_intent.order_type == OrderType.MARKET
        assert sample_order_intent.qty == Decimal("1.0")
        assert sample_order_intent.time_in_force == TimeInForce.GTC

    def test_is_immutable(self, sample_order_intent: OrderIntent) -> None:
        """OrderIntent should be frozen."""
        with pytest.raises(FrozenInstanceError):
            sample_order_intent.qty = Decimal("2.0")  # type: ignore

    def test_limit_order_has_price(self, sample_limit_order_intent: OrderIntent) -> None:
        """Limit orders should have limit_price set."""
        assert sample_limit_order_intent.order_type == OrderType.LIMIT
        assert sample_limit_order_intent.limit_price == Decimal("2500.00")

    def test_market_order_no_limit_price(self, sample_order_intent: OrderIntent) -> None:
        """Market orders should not have limit_price."""
        assert sample_order_intent.order_type == OrderType.MARKET
        assert sample_order_intent.limit_price is None

    def test_extended_hours_default_false(self, sample_order_intent: OrderIntent) -> None:
        """extended_hours should default to False."""
        assert sample_order_intent.extended_hours is False

    def test_stop_order_has_stop_price(self) -> None:
        """Stop orders should have stop_price set."""
        intent = OrderIntent(
            run_id="run-123",
            client_order_id="client-789",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=Decimal("40000.00"),
            time_in_force=TimeInForce.GTC,
        )
        assert intent.stop_price == Decimal("40000.00")


# =============================================================================
# OrderState Tests
# =============================================================================


class TestOrderState:
    """Tests for OrderState dataclass."""

    def test_has_all_identity_fields(self, sample_order_state: OrderState) -> None:
        """OrderState should have all identity fields."""
        assert sample_order_state.id == "order-001"
        assert sample_order_state.client_order_id == "client-123"
        assert sample_order_state.exchange_order_id == "exch-123"
        assert sample_order_state.run_id == "run-123"

    def test_tracks_order_details(self, sample_order_state: OrderState) -> None:
        """OrderState should track order details from intent."""
        assert sample_order_state.symbol == "BTC/USD"
        assert sample_order_state.side == OrderSide.BUY
        assert sample_order_state.order_type == OrderType.MARKET
        assert sample_order_state.qty == Decimal("1.0")

    def test_tracks_status(self, sample_order_state: OrderState) -> None:
        """OrderState should track status."""
        assert sample_order_state.status == OrderStatus.FILLED

    def test_tracks_fill_information(self, sample_order_state: OrderState) -> None:
        """OrderState should track fills."""
        assert sample_order_state.filled_qty == Decimal("1.0")
        assert sample_order_state.filled_avg_price == Decimal("42000.00")

    def test_tracks_timestamps(self, sample_order_state: OrderState) -> None:
        """OrderState should track timestamps."""
        assert sample_order_state.created_at is not None
        assert sample_order_state.submitted_at is not None
        assert sample_order_state.filled_at is not None

    def test_mutable_for_state_updates(self) -> None:
        """OrderState should be mutable for status updates."""
        now = datetime.now(UTC)
        state = OrderState(
            id="order-002",
            client_order_id="client-002",
            exchange_order_id=None,
            run_id="run-123",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.PENDING,
            filled_qty=Decimal("0"),
            filled_avg_price=None,
            fills=[],
            created_at=now,
            submitted_at=None,
            filled_at=None,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        # Should be able to update status
        state.status = OrderStatus.SUBMITTED
        assert state.status == OrderStatus.SUBMITTED


# =============================================================================
# OrderStatus Tests
# =============================================================================


class TestOrderStatus:
    """Tests for OrderStatus enum."""

    def test_has_all_statuses(self) -> None:
        """OrderStatus should have all defined statuses."""
        expected = {
            "pending",
            "submitting",
            "submitted",
            "accepted",
            "partial",
            "filled",
            "cancelled",
            "rejected",
            "expired",
        }
        actual = {s.value for s in OrderStatus}
        assert actual == expected

    def test_terminal_states(self) -> None:
        """Identify terminal states that cannot transition further."""
        terminal = {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        }
        assert OrderStatus.FILLED in terminal
        assert OrderStatus.PENDING not in terminal
        assert OrderStatus.ACCEPTED not in terminal

    def test_cancellable_states(self) -> None:
        """Identify states that can be cancelled."""
        cancellable = {
            OrderStatus.PENDING,
            OrderStatus.SUBMITTING,
            OrderStatus.SUBMITTED,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
        }
        assert OrderStatus.ACCEPTED in cancellable
        assert OrderStatus.FILLED not in cancellable
        assert OrderStatus.CANCELLED not in cancellable


# =============================================================================
# Bar Tests
# =============================================================================


class TestBar:
    """Tests for Bar (OHLCV) dataclass."""

    def test_has_ohlcv_fields(self, sample_bar: Bar) -> None:
        """Bar should have all OHLCV fields."""
        assert sample_bar.open == Decimal("42000.00")
        assert sample_bar.high == Decimal("42500.00")
        assert sample_bar.low == Decimal("41800.00")
        assert sample_bar.close == Decimal("42200.00")
        assert sample_bar.volume == Decimal("150.5")

    def test_has_metadata(self, sample_bar: Bar) -> None:
        """Bar should have symbol and timestamp."""
        assert sample_bar.symbol == "BTC/USD"
        assert sample_bar.timestamp.tzinfo == UTC

    def test_has_optional_fields(self, sample_bar: Bar) -> None:
        """Bar should have optional trade_count and vwap."""
        assert sample_bar.trade_count == 1234
        assert sample_bar.vwap == Decimal("42100.00")

    def test_is_immutable(self, sample_bar: Bar) -> None:
        """Bar should be frozen."""
        with pytest.raises(FrozenInstanceError):
            sample_bar.close = Decimal("50000")  # type: ignore

    def test_high_gte_low(self, sample_bar: Bar) -> None:
        """High should be >= low (data integrity)."""
        assert sample_bar.high >= sample_bar.low


# =============================================================================
# Quote Tests
# =============================================================================


class TestQuote:
    """Tests for Quote dataclass."""

    def test_has_bid_ask(self, sample_quote: Quote) -> None:
        """Quote should have bid and ask prices/sizes."""
        assert sample_quote.bid_price == Decimal("42000.00")
        assert sample_quote.bid_size == Decimal("1.5")
        assert sample_quote.ask_price == Decimal("42010.00")
        assert sample_quote.ask_size == Decimal("2.0")

    def test_has_symbol_and_timestamp(self, sample_quote: Quote) -> None:
        """Quote should have symbol and timestamp."""
        assert sample_quote.symbol == "BTC/USD"
        assert sample_quote.timestamp is not None

    def test_is_immutable(self, sample_quote: Quote) -> None:
        """Quote should be frozen."""
        with pytest.raises(FrozenInstanceError):
            sample_quote.bid_price = Decimal("41000")  # type: ignore


# =============================================================================
# Trade Tests
# =============================================================================


class TestTrade:
    """Tests for Trade dataclass."""

    def test_has_trade_fields(self) -> None:
        """Trade should have price, size, exchange."""
        trade = Trade(
            symbol="BTC/USD",
            timestamp=datetime.now(UTC),
            price=Decimal("42000.00"),
            size=Decimal("0.5"),
            exchange="CBSE",
        )
        assert trade.price == Decimal("42000.00")
        assert trade.size == Decimal("0.5")
        assert trade.exchange == "CBSE"

    def test_is_immutable(self) -> None:
        """Trade should be frozen."""
        trade = Trade(
            symbol="BTC/USD",
            timestamp=datetime.now(UTC),
            price=Decimal("42000.00"),
            size=Decimal("0.5"),
            exchange="CBSE",
        )
        with pytest.raises(FrozenInstanceError):
            trade.price = Decimal("50000")  # type: ignore


# =============================================================================
# Fill Tests
# =============================================================================


class TestFill:
    """Tests for Fill dataclass."""

    def test_has_fill_fields(self, sample_fill: Fill) -> None:
        """Fill should have qty, price, commission."""
        assert sample_fill.id == "fill-001"
        assert sample_fill.order_id == "order-001"
        assert sample_fill.qty == Decimal("0.5")
        assert sample_fill.price == Decimal("42000.00")
        assert sample_fill.commission == Decimal("0.42")

    def test_is_immutable(self, sample_fill: Fill) -> None:
        """Fill should be frozen."""
        with pytest.raises(FrozenInstanceError):
            sample_fill.qty = Decimal("1.0")  # type: ignore


# =============================================================================
# AccountInfo Tests
# =============================================================================


class TestAccountInfo:
    """Tests for AccountInfo dataclass."""

    def test_has_account_fields(self) -> None:
        """AccountInfo should have all account fields."""
        account = AccountInfo(
            account_id="acc-123",
            buying_power=Decimal("100000.00"),
            cash=Decimal("50000.00"),
            portfolio_value=Decimal("150000.00"),
            currency="USD",
            status="ACTIVE",
        )
        assert account.account_id == "acc-123"
        assert account.buying_power == Decimal("100000.00")
        assert account.cash == Decimal("50000.00")
        assert account.portfolio_value == Decimal("150000.00")
        assert account.currency == "USD"
        assert account.status == "ACTIVE"

    def test_is_immutable(self) -> None:
        """AccountInfo should be frozen."""
        account = AccountInfo(
            account_id="acc-123",
            buying_power=Decimal("100000.00"),
            cash=Decimal("50000.00"),
            portfolio_value=Decimal("150000.00"),
            currency="USD",
            status="ACTIVE",
        )
        with pytest.raises(FrozenInstanceError):
            account.cash = Decimal("0")  # type: ignore


# =============================================================================
# Position Tests
# =============================================================================


class TestPosition:
    """Tests for Position dataclass."""

    def test_has_position_fields(self) -> None:
        """Position should have all position fields."""
        position = Position(
            symbol="BTC/USD",
            qty=Decimal("2.5"),
            side=PositionSide.LONG,
            avg_entry_price=Decimal("40000.00"),
            market_value=Decimal("105000.00"),
            unrealized_pnl=Decimal("5000.00"),
            unrealized_pnl_percent=Decimal("5.0"),
        )
        assert position.symbol == "BTC/USD"
        assert position.qty == Decimal("2.5")
        assert position.side == PositionSide.LONG
        assert position.avg_entry_price == Decimal("40000.00")
        assert position.unrealized_pnl == Decimal("5000.00")

    def test_is_immutable(self) -> None:
        """Position should be frozen."""
        position = Position(
            symbol="BTC/USD",
            qty=Decimal("2.5"),
            side=PositionSide.LONG,
            avg_entry_price=Decimal("40000.00"),
            market_value=Decimal("105000.00"),
            unrealized_pnl=Decimal("5000.00"),
            unrealized_pnl_percent=Decimal("5.0"),
        )
        with pytest.raises(FrozenInstanceError):
            position.qty = Decimal("0")  # type: ignore


# =============================================================================
# Enum Tests
# =============================================================================


class TestOrderSide:
    """Tests for OrderSide enum."""

    def test_has_buy_and_sell(self) -> None:
        """OrderSide should have BUY and SELL."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"


class TestOrderType:
    """Tests for OrderType enum."""

    def test_has_all_types(self) -> None:
        """OrderType should have all order types."""
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"


class TestTimeInForce:
    """Tests for TimeInForce enum."""

    def test_has_all_tifs(self) -> None:
        """TimeInForce should have all options."""
        assert TimeInForce.DAY.value == "day"
        assert TimeInForce.GTC.value == "gtc"
        assert TimeInForce.IOC.value == "ioc"
        assert TimeInForce.FOK.value == "fok"


class TestPositionSide:
    """Tests for PositionSide enum."""

    def test_has_long_and_short(self) -> None:
        """PositionSide should have LONG and SHORT."""
        assert PositionSide.LONG.value == "long"
        assert PositionSide.SHORT.value == "short"
