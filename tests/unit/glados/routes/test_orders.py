"""
Tests for Orders Endpoint

MVP-4: Order Queries
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.veda.models import (
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# =============================================================================
# Helpers
# =============================================================================


def _make_order_state(
    client_order_id: str = "veda-order-1",
    run_id: str = "run-1",
    symbol: str = "AAPL",
    status: OrderStatus = OrderStatus.FILLED,
) -> OrderState:
    """Create a test OrderState for VedaService path tests."""
    return OrderState(
        id="internal-1",
        client_order_id=client_order_id,
        exchange_order_id="exch-1",
        run_id=run_id,
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("10"),
        limit_price=None,
        stop_price=None,
        time_in_force=TimeInForce.DAY,
        status=status,
        filled_qty=Decimal("10"),
        filled_avg_price=Decimal("150.50"),
        created_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
        filled_at=datetime.now(timezone.utc),
        cancelled_at=None,
        reject_reason=None,
        error_code=None,
    )


class TestListOrdersEndpoint:
    """Tests for GET /api/v1/orders."""

    def test_returns_200(self, client: TestClient) -> None:
        """GET /orders should return HTTP 200."""
        response = client.get("/api/v1/orders")

        assert response.status_code == 200

    def test_returns_items_list(self, client: TestClient) -> None:
        """Response should contain items list."""
        response = client.get("/api/v1/orders")
        data = response.json()

        assert "items" in data
        assert isinstance(data["items"], list)

    def test_returns_total_count(self, client: TestClient) -> None:
        """Response should contain total count."""
        response = client.get("/api/v1/orders")
        data = response.json()

        assert "total" in data
        assert isinstance(data["total"], int)

    def test_accepts_run_id_filter(self, client: TestClient) -> None:
        """GET /orders should accept run_id query param."""
        response = client.get("/api/v1/orders?run_id=test-run")

        assert response.status_code == 200


class TestGetOrderEndpoint:
    """Tests for GET /api/v1/orders/{id}."""

    def test_returns_order(self, client: TestClient) -> None:
        """GET /orders/{id} should return order details."""
        response = client.get("/api/v1/orders/order-123")

        assert response.status_code == 200
        assert response.json()["id"] == "order-123"

    def test_order_has_required_fields(self, client: TestClient) -> None:
        """Order response should have required fields."""
        response = client.get("/api/v1/orders/order-123")
        data = response.json()

        assert "id" in data
        assert "run_id" in data
        assert "symbol" in data
        assert "side" in data
        assert "order_type" in data
        assert "qty" in data
        assert "status" in data

    def test_not_found_returns_404(self, client: TestClient) -> None:
        """GET /orders/{id} with unknown ID returns 404."""
        response = client.get("/api/v1/orders/non-existent-order")

        assert response.status_code == 404


class TestListOrdersVedaPath:
    """C-04: GET /orders uses VedaService when available."""

    def test_list_returns_veda_orders_when_service_present(
        self, client: TestClient
    ) -> None:
        """When VedaService is configured, list_orders reads from it."""
        mock_veda = AsyncMock()
        mock_veda.list_orders.return_value = [
            _make_order_state("veda-1", run_id="run-a"),
            _make_order_state("veda-2", run_id="run-a"),
        ]
        # Inject VedaService onto the app
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get("/api/v1/orders")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["items"][0]["client_order_id"] == "veda-1"

        # Clean up
        client.app.state.veda_service = None  # type: ignore[union-attr]

    def test_list_passes_run_id_filter_to_veda(
        self, client: TestClient
    ) -> None:
        """run_id query param is forwarded to VedaService.list_orders."""
        mock_veda = AsyncMock()
        mock_veda.list_orders.return_value = []
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        client.get("/api/v1/orders?run_id=run-x")

        mock_veda.list_orders.assert_called_once_with(run_id="run-x")

        client.app.state.veda_service = None  # type: ignore[union-attr]

    def test_list_falls_back_to_mock_when_veda_absent(
        self, client: TestClient
    ) -> None:
        """Without VedaService, list_orders still returns from MockOrderService."""
        # veda_service is None by default in test config
        response = client.get("/api/v1/orders")
        assert response.status_code == 200


class TestGetOrderVedaPath:
    """C-04: GET /orders/{id} uses VedaService when available."""

    def test_get_returns_veda_order_when_service_present(
        self, client: TestClient
    ) -> None:
        """When VedaService is configured, get_order reads from it."""
        mock_veda = AsyncMock()
        mock_veda.get_order.return_value = _make_order_state("veda-order-42")
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get("/api/v1/orders/veda-order-42")

        assert response.status_code == 200
        assert response.json()["client_order_id"] == "veda-order-42"

        client.app.state.veda_service = None  # type: ignore[union-attr]

    def test_get_veda_not_found_returns_404(
        self, client: TestClient
    ) -> None:
        """When VedaService returns None, return 404."""
        mock_veda = AsyncMock()
        mock_veda.get_order.return_value = None
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get("/api/v1/orders/missing-order")

        assert response.status_code == 404

        client.app.state.veda_service = None  # type: ignore[union-attr]

    def test_get_falls_back_to_mock_when_veda_absent(
        self, client: TestClient
    ) -> None:
        """Without VedaService, get_order reads from MockOrderService."""
        response = client.get("/api/v1/orders/order-123")
        assert response.status_code == 200
