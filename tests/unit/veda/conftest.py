"""
Veda Test Fixtures

Shared fixtures for Veda unit tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.veda.models import (
    Bar,
    Fill,
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    Quote,
    TimeInForce,
    Trade,
)


@pytest.fixture
def sample_order_intent() -> OrderIntent:
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


@pytest.fixture
def sample_limit_order_intent() -> OrderIntent:
    """Create sample limit order intent."""
    return OrderIntent(
        run_id="run-123",
        client_order_id="client-456",
        symbol="ETH/USD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        qty=Decimal("2.5"),
        limit_price=Decimal("2500.00"),
        stop_price=None,
        time_in_force=TimeInForce.GTC,
    )


@pytest.fixture
def sample_order_state() -> OrderState:
    """Create sample OrderState for tests."""
    now = datetime.now(UTC)
    return OrderState(
        id="order-001",
        client_order_id="client-123",
        exchange_order_id="exch-123",
        run_id="run-123",
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1.0"),
        limit_price=None,
        stop_price=None,
        time_in_force=TimeInForce.GTC,
        status=OrderStatus.FILLED,
        filled_qty=Decimal("1.0"),
        filled_avg_price=Decimal("42000.00"),
        fills=[],
        created_at=now,
        submitted_at=now,
        filled_at=now,
        cancelled_at=None,
        reject_reason=None,
        error_code=None,
    )


@pytest.fixture
def sample_bar() -> Bar:
    """Create sample OHLCV bar for tests."""
    return Bar(
        symbol="BTC/USD",
        timestamp=datetime(2026, 2, 2, 10, 0, 0, tzinfo=UTC),
        open=Decimal("42000.00"),
        high=Decimal("42500.00"),
        low=Decimal("41800.00"),
        close=Decimal("42200.00"),
        volume=Decimal("150.5"),
        trade_count=1234,
        vwap=Decimal("42100.00"),
    )


@pytest.fixture
def sample_quote() -> Quote:
    """Create sample quote for tests."""
    return Quote(
        symbol="BTC/USD",
        timestamp=datetime.now(UTC),
        bid_price=Decimal("42000.00"),
        bid_size=Decimal("1.5"),
        ask_price=Decimal("42010.00"),
        ask_size=Decimal("2.0"),
    )


@pytest.fixture
def sample_fill() -> Fill:
    """Create sample fill for tests."""
    return Fill(
        id="fill-001",
        order_id="order-001",
        qty=Decimal("0.5"),
        price=Decimal("42000.00"),
        commission=Decimal("0.42"),
        timestamp=datetime.now(UTC),
    )
