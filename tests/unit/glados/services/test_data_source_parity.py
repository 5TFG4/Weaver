"""
Tests for Data Source Unification — M8-P1 Package C

Integration tests for write → read parity via VedaService.
Ensures orders placed through VedaService are visible via list/get.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.events.log import InMemoryEventLog
from src.veda.interfaces import OrderSubmitResult
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)


class TestOrderWriteReadParity:
    """C.1-C.2: Orders written via VedaService must be readable."""

    async def test_place_order_then_list_returns_it(self) -> None:
        """Integration: place_order → list_orders returns the placed order."""
        from src.veda.veda_service import VedaService

        # Mock adapter accepts all orders
        adapter = MagicMock()
        adapter.submit_order = AsyncMock(return_value=OrderSubmitResult(
            success=True,
            exchange_order_id="exch-001",
            status=OrderStatus.SUBMITTED,
        ))

        # Mock repository that stores orders in memory
        stored = {}

        async def mock_save(state):
            stored[state.client_order_id] = state

        def mock_list_by_run(rid):
            return [s for s in stored.values() if s.run_id == rid]

        repo = MagicMock()
        repo.save = AsyncMock(side_effect=mock_save)
        repo.list_by_run_id = AsyncMock(side_effect=mock_list_by_run)
        repo.get_by_client_order_id = AsyncMock(side_effect=lambda cid: stored.get(cid))

        event_log = InMemoryEventLog()
        service = VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=repo,
            config=MagicMock(),
        )

        # Place an order
        intent = OrderIntent(
            run_id="run-1",
            client_order_id="order-abc",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("10"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.DAY,
        )
        placed_state = await service.place_order(intent)
        assert placed_state.status == OrderStatus.SUBMITTED

        # List orders → should include the placed order
        orders = await service.list_orders(run_id="run-1")
        # list_orders with run_id uses repository.list_by_run_id
        assert any(o.client_order_id == "order-abc" for o in orders)

    async def test_place_order_then_get_returns_it(self) -> None:
        """Integration: place_order → get_order returns the placed order."""
        from src.veda.veda_service import VedaService

        adapter = MagicMock()
        adapter.submit_order = AsyncMock(return_value=OrderSubmitResult(
            success=True,
            exchange_order_id="exch-002",
            status=OrderStatus.SUBMITTED,
        ))

        repo = MagicMock()
        repo.save = AsyncMock()
        repo.get_by_client_order_id = AsyncMock(return_value=None)

        event_log = InMemoryEventLog()
        service = VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=repo,
            config=MagicMock(),
        )

        intent = OrderIntent(
            run_id="run-2",
            client_order_id="order-xyz",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            qty=Decimal("0.5"),
            limit_price=Decimal("30000.00"),
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        await service.place_order(intent)

        # get_order checks local state first (OrderManager), then repository
        result = await service.get_order("order-xyz")
        assert result is not None
        assert result.client_order_id == "order-xyz"
        assert result.symbol == "BTC/USD"

    async def test_cancel_order_then_list_shows_cancelled(self) -> None:
        """Integration: cancel_order → list shows cancelled status."""
        from src.veda.veda_service import VedaService

        adapter = MagicMock()
        adapter.submit_order = AsyncMock(return_value=OrderSubmitResult(
            success=True,
            exchange_order_id="exch-003",
            status=OrderStatus.SUBMITTED,
        ))
        adapter.cancel_order = AsyncMock(return_value=True)

        stored = {}

        async def mock_save(state):
            stored[state.client_order_id] = state

        repo = MagicMock()
        repo.save = AsyncMock(side_effect=mock_save)
        repo.get_by_client_order_id = AsyncMock(return_value=None)

        event_log = InMemoryEventLog()
        service = VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=repo,
            config=MagicMock(),
        )

        # Place then cancel
        intent = OrderIntent(
            run_id="run-3",
            client_order_id="order-cancel-me",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("5"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.DAY,
        )
        await service.place_order(intent)
        cancelled = await service.cancel_order("order-cancel-me")
        assert cancelled is True

        # Get should show cancelled status
        result = await service.get_order("order-cancel-me")
        assert result is not None
        assert result.status == OrderStatus.CANCELLED
