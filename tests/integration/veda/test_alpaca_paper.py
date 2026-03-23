"""Integration tests for AlpacaAdapter against real Alpaca Paper API.

These tests validate that our adapter correctly communicates with
the real Alpaca API. They require paper trading credentials.

Safety constraints:
- Uses crypto (BTC/USD) only — trades 24/7, no market hours dependency
- Tiny quantities (0.001 BTC) to preserve paper account balance
- Cleanup runs in fixture teardown (cancel orders + close positions)

Prerequisites:
    ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET env vars must be set.
    Tests are skipped when credentials are not available.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest

from src.veda.adapters.alpaca_adapter import AlpacaAdapter
from src.veda.models import OrderIntent, OrderSide, OrderStatus, OrderType, TimeInForce

_PLACEHOLDER_VALUES = {"your_paper_api_key", "your_paper_api_secret", ""}


def _has_real_alpaca_creds() -> bool:
    """Check if real (non-placeholder) Alpaca credentials are available."""
    key = os.environ.get("ALPACA_PAPER_API_KEY", "")
    secret = os.environ.get("ALPACA_PAPER_API_SECRET", "")
    return key not in _PLACEHOLDER_VALUES and secret not in _PLACEHOLDER_VALUES


pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not _has_real_alpaca_creds(),
        reason="Real ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET required",
    ),
]

# Crypto symbol for 24/7 testing
SYMBOL = "BTC/USD"
# Tiny quantity to preserve paper balance
QTY = Decimal("0.001")


@pytest.fixture(scope="module")
def api_key() -> str:
    return os.environ["ALPACA_PAPER_API_KEY"]


@pytest.fixture(scope="module")
def api_secret() -> str:
    return os.environ["ALPACA_PAPER_API_SECRET"]


@pytest.fixture
async def adapter(api_key: str, api_secret: str) -> AsyncGenerator[AlpacaAdapter]:
    """Create a connected adapter with post-test cleanup."""
    a = AlpacaAdapter(api_key=api_key, api_secret=api_secret, paper=True)
    await a.connect()
    yield a  # type: ignore[misc]
    # Cleanup: cancel open orders and close positions
    try:
        await a.cancel_all_orders()
        # Small delay for cancellations to propagate
        await asyncio.sleep(1)
        await a.close_all_positions()
        await asyncio.sleep(1)
    except Exception:
        pass  # Best-effort cleanup
    await a.disconnect()


class TestAlpacaConnection:
    """Tests for connection and account access."""

    async def test_connect_succeeds(self, api_key: str, api_secret: str) -> None:
        """connect() should establish connection and verify account is ACTIVE."""
        adapter = AlpacaAdapter(api_key=api_key, api_secret=api_secret, paper=True)
        await adapter.connect()

        assert adapter.is_connected is True
        assert adapter.paper is True

        await adapter.disconnect()
        assert adapter.is_connected is False

    async def test_get_account_returns_real_data(self, adapter: AlpacaAdapter) -> None:
        """get_account() should return real account with numeric fields."""
        account = await adapter.get_account()

        assert account.status == "ACTIVE"
        assert account.buying_power > 0
        assert account.portfolio_value > 0
        assert account.currency == "USD"
        assert account.account_id is not None


class TestAlpacaOrderLifecycle:
    """Tests for order submission, retrieval, and cancellation."""

    async def test_submit_and_get_order_roundtrip(self, adapter: AlpacaAdapter) -> None:
        """Submit a market order and retrieve it by ID."""
        client_order_id = f"weaver-test-{uuid.uuid4().hex[:12]}"
        intent = OrderIntent(
            run_id="integration-test",
            client_order_id=client_order_id,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=QTY,
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )

        result = await adapter.submit_order(intent)
        assert result.success is True
        assert result.exchange_order_id is not None

        # Retrieve the order
        order = await adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.symbol == SYMBOL  # Alpaca preserves slash for crypto
        assert order.side == OrderSide.BUY
        assert order.qty == QTY

    async def test_cancel_pending_order(self, adapter: AlpacaAdapter) -> None:
        """Submit a limit order far from market, then cancel it."""
        client_order_id = f"weaver-cancel-{uuid.uuid4().hex[:12]}"
        intent = OrderIntent(
            run_id="integration-test",
            client_order_id=client_order_id,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=QTY,
            limit_price=Decimal("15000.00"),  # Far below market — will never fill
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )

        result = await adapter.submit_order(intent)
        assert result.success is True
        assert result.exchange_order_id is not None

        # Cancel it
        cancelled = await adapter.cancel_order(result.exchange_order_id)
        assert cancelled is True

        # Verify cancellation (may take a moment to propagate)
        await asyncio.sleep(1)
        order = await adapter.get_order(result.exchange_order_id)
        assert order is not None
        assert order.status in (OrderStatus.CANCELLED, OrderStatus.ACCEPTED)

    async def test_list_orders_includes_submitted(self, adapter: AlpacaAdapter) -> None:
        """Submitted order should appear in list_orders()."""
        client_order_id = f"weaver-list-{uuid.uuid4().hex[:12]}"
        intent = OrderIntent(
            run_id="integration-test",
            client_order_id=client_order_id,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=QTY,
            limit_price=Decimal("15000.00"),
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )

        result = await adapter.submit_order(intent)
        assert result.success is True

        orders = await adapter.list_orders()
        order_ids = [o.exchange_order_id for o in orders]
        assert result.exchange_order_id in order_ids


class TestAlpacaPositions:
    """Tests for position tracking after fills."""

    async def test_get_positions_after_fill(self, adapter: AlpacaAdapter) -> None:
        """After a market buy fills, get_positions() should show the position."""
        client_order_id = f"weaver-pos-{uuid.uuid4().hex[:12]}"
        intent = OrderIntent(
            run_id="integration-test",
            client_order_id=client_order_id,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=QTY,
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )

        result = await adapter.submit_order(intent)
        assert result.success is True

        # Wait for fill (crypto market orders fill quickly)
        await asyncio.sleep(3)

        positions = await adapter.get_positions()
        symbols = [p.symbol for p in positions]
        # BTC/USD may appear as BTCUSD in positions
        assert any("BTC" in s for s in symbols), f"Expected BTC position, got: {symbols}"

        # Verify position details
        btc_pos = next(p for p in positions if "BTC" in p.symbol)
        assert btc_pos.qty > 0
        assert btc_pos.avg_entry_price > 0
