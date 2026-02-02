"""
Tests for Order Service

MVP-4: Order Queries
TDD: Write tests first, then implement.
"""

from __future__ import annotations


class TestOrderServiceGet:
    """Tests for OrderService.get()."""

    async def test_returns_order_by_id(self) -> None:
        """get() should return order with matching ID."""
        from src.glados.services.order_service import MockOrderService

        order_service = MockOrderService()

        order = await order_service.get("order-123")

        assert order is not None
        assert order.id == "order-123"

    async def test_returns_none_for_unknown_id(self) -> None:
        """get() should return None for non-existent ID."""
        from src.glados.services.order_service import MockOrderService

        order_service = MockOrderService()

        order = await order_service.get("non-existent-order")

        assert order is None


class TestOrderServiceList:
    """Tests for OrderService.list()."""

    async def test_returns_orders_list(self) -> None:
        """list() should return list of orders."""
        from src.glados.services.order_service import MockOrderService

        order_service = MockOrderService()

        orders, total = await order_service.list()

        assert isinstance(orders, list)
        assert total >= 0

    async def test_filters_by_run_id(self) -> None:
        """list() should filter by run_id."""
        from src.glados.services.order_service import MockOrderService

        order_service = MockOrderService()

        orders, _ = await order_service.list(run_id="run-123")

        for order in orders:
            assert order.run_id == "run-123"

    async def test_returns_empty_for_unknown_run(self) -> None:
        """list() should return empty for unknown run_id."""
        from src.glados.services.order_service import MockOrderService

        order_service = MockOrderService()

        orders, total = await order_service.list(run_id="unknown-run")

        assert orders == []
        assert total == 0
