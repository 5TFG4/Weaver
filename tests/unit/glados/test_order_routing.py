"""
Tests for VedaService routing in order endpoints.

M6-3: Wire VedaService to order routes.
"""

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.glados.routes.orders import router
from src.glados.schemas import OrderCreate


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_veda_service() -> MagicMock:
    """Create mock VedaService."""
    service = MagicMock()
    service.place_order = AsyncMock()
    service.get_order = AsyncMock()
    service.cancel_order = AsyncMock()
    return service


@pytest.fixture
def mock_order_service() -> MagicMock:
    """Create mock OrderService (legacy)."""
    service = MagicMock()
    service.list = AsyncMock(return_value=([], 0))
    service.get = AsyncMock(return_value=None)
    return service


@pytest.fixture
def app_with_veda(mock_veda_service: MagicMock, mock_order_service: MagicMock) -> FastAPI:
    """Create FastAPI app with VedaService configured."""
    app = FastAPI()
    app.include_router(router)
    app.state.veda_service = mock_veda_service
    app.state.order_service = mock_order_service
    return app


@pytest.fixture
def app_without_veda(mock_order_service: MagicMock) -> FastAPI:
    """Create FastAPI app WITHOUT VedaService (not configured)."""
    app = FastAPI()
    app.include_router(router)
    app.state.veda_service = None
    app.state.order_service = mock_order_service
    return app


@pytest.fixture
def client_with_veda(app_with_veda: FastAPI) -> TestClient:
    """Test client with VedaService."""
    return TestClient(app_with_veda)


@pytest.fixture
def client_without_veda(app_without_veda: FastAPI) -> TestClient:
    """Test client without VedaService."""
    return TestClient(app_without_veda)


# =============================================================================
# Test: OrderCreate Schema
# =============================================================================


class TestOrderCreateSchema:
    """Tests for OrderCreate schema validation."""

    def test_schema_exists(self) -> None:
        """OrderCreate schema should exist."""
        from src.glados.schemas import OrderCreate
        assert OrderCreate is not None

    def test_valid_market_order(self) -> None:
        """Valid market order should pass validation."""
        order = OrderCreate(
            run_id="run-123",
            client_order_id="order-abc",
            symbol="BTC/USD",
            side="buy",
            order_type="market",
            qty="1.5",
        )
        assert order.run_id == "run-123"
        assert order.qty == "1.5"
        assert order.time_in_force == "day"

    def test_valid_limit_order(self) -> None:
        """Valid limit order with price should pass."""
        order = OrderCreate(
            run_id="run-123",
            client_order_id="order-abc",
            symbol="BTC/USD",
            side="sell",
            order_type="limit",
            qty="2.0",
            limit_price="50000.00",
        )
        assert order.limit_price == "50000.00"

    def test_missing_required_field_raises(self) -> None:
        """Missing required field should raise ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OrderCreate(
                run_id="run-123",
                # Missing client_order_id
                symbol="BTC/USD",
                side="buy",
                order_type="market",
                qty="1.0",
            )

    def test_empty_run_id_raises(self) -> None:
        """Empty run_id should raise ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OrderCreate(
                run_id="",  # Empty not allowed
                client_order_id="order-abc",
                symbol="BTC/USD",
                side="buy",
                order_type="market",
                qty="1.0",
            )


# =============================================================================
# Test: POST /orders
# =============================================================================


class TestCreateOrder:
    """Tests for POST /orders endpoint."""

    def test_create_order_calls_veda_service(
        self,
        client_with_veda: TestClient,
        mock_veda_service: MagicMock,
    ) -> None:
        """POST /orders should call VedaService.place_order."""
        from src.veda.models import OrderState, OrderStatus
        
        # Setup mock response
        mock_state = MagicMock(spec=OrderState)
        mock_state.intent = MagicMock()
        mock_state.intent.run_id = "run-123"
        mock_state.intent.client_order_id = "order-abc"
        mock_state.intent.symbol = "BTC/USD"
        mock_state.intent.side.value = "buy"
        mock_state.intent.order_type.value = "market"
        mock_state.intent.qty = Decimal("1.5")
        mock_state.intent.limit_price = None
        mock_state.intent.stop_price = None
        mock_state.intent.time_in_force.value = "day"
        mock_state.exchange_order_id = "exch-123"
        mock_state.filled_qty = Decimal("0")
        mock_state.filled_avg_price = None
        mock_state.status = OrderStatus.SUBMITTED
        mock_state.created_at = datetime.now(UTC)
        mock_state.submitted_at = datetime.now(UTC)
        mock_state.filled_at = None
        mock_state.reject_reason = None
        mock_veda_service.place_order.return_value = mock_state

        response = client_with_veda.post(
            "/api/v1/orders",
            json={
                "run_id": "run-123",
                "client_order_id": "order-abc",
                "symbol": "BTC/USD",
                "side": "buy",
                "order_type": "market",
                "qty": "1.5",
            },
        )

        assert response.status_code == 201
        mock_veda_service.place_order.assert_called_once()

    def test_create_order_maps_intent_correctly(
        self,
        client_with_veda: TestClient,
        mock_veda_service: MagicMock,
    ) -> None:
        """POST /orders should map request fields to OrderIntent correctly."""
        from src.veda.models import OrderIntent, OrderState, OrderStatus, OrderSide, OrderType, TimeInForce
        
        # Setup mock
        mock_state = MagicMock(spec=OrderState)
        mock_state.intent = MagicMock()
        mock_state.intent.run_id = "run-123"
        mock_state.intent.client_order_id = "order-abc"
        mock_state.intent.symbol = "AAPL"
        mock_state.intent.side.value = "sell"
        mock_state.intent.order_type.value = "limit"
        mock_state.intent.qty = Decimal("10")
        mock_state.intent.limit_price = Decimal("150.00")
        mock_state.intent.stop_price = None
        mock_state.intent.time_in_force.value = "gtc"
        mock_state.exchange_order_id = None
        mock_state.filled_qty = Decimal("0")
        mock_state.filled_avg_price = None
        mock_state.status = OrderStatus.PENDING
        mock_state.created_at = datetime.now(UTC)
        mock_state.submitted_at = None
        mock_state.filled_at = None
        mock_state.reject_reason = None
        mock_veda_service.place_order.return_value = mock_state

        client_with_veda.post(
            "/api/v1/orders",
            json={
                "run_id": "run-123",
                "client_order_id": "order-abc",
                "symbol": "AAPL",
                "side": "sell",
                "order_type": "limit",
                "qty": "10",
                "limit_price": "150.00",
                "time_in_force": "gtc",
            },
        )

        # Verify intent was created correctly
        call_args = mock_veda_service.place_order.call_args
        intent = call_args[0][0]  # First positional argument
        
        assert isinstance(intent, OrderIntent)
        assert intent.run_id == "run-123"
        assert intent.client_order_id == "order-abc"
        assert intent.symbol == "AAPL"
        assert intent.side == OrderSide.SELL
        assert intent.order_type == OrderType.LIMIT
        assert intent.qty == Decimal("10")
        assert intent.limit_price == Decimal("150.00")
        assert intent.time_in_force == TimeInForce.GTC

    def test_create_order_returns_order_response(
        self,
        client_with_veda: TestClient,
        mock_veda_service: MagicMock,
    ) -> None:
        """POST /orders should return OrderResponse."""
        from src.veda.models import OrderState, OrderStatus
        
        mock_state = MagicMock(spec=OrderState)
        mock_state.intent = MagicMock()
        mock_state.intent.run_id = "run-123"
        mock_state.intent.client_order_id = "order-abc"
        mock_state.intent.symbol = "BTC/USD"
        mock_state.intent.side.value = "buy"
        mock_state.intent.order_type.value = "market"
        mock_state.intent.qty = Decimal("1.5")
        mock_state.intent.limit_price = None
        mock_state.intent.stop_price = None
        mock_state.intent.time_in_force.value = "day"
        mock_state.exchange_order_id = "exch-123"
        mock_state.filled_qty = Decimal("0")
        mock_state.filled_avg_price = None
        mock_state.status = OrderStatus.SUBMITTED
        mock_state.created_at = datetime.now(UTC)
        mock_state.submitted_at = datetime.now(UTC)
        mock_state.filled_at = None
        mock_state.reject_reason = None
        mock_veda_service.place_order.return_value = mock_state

        response = client_with_veda.post(
            "/api/v1/orders",
            json={
                "run_id": "run-123",
                "client_order_id": "order-abc",
                "symbol": "BTC/USD",
                "side": "buy",
                "order_type": "market",
                "qty": "1.5",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "order-abc"  # client_order_id as id
        assert data["run_id"] == "run-123"
        assert data["symbol"] == "BTC/USD"
        assert data["status"] == "submitted"

    def test_create_order_invalid_input_returns_422(
        self,
        client_with_veda: TestClient,
    ) -> None:
        """POST /orders with invalid input should return 422."""
        response = client_with_veda.post(
            "/api/v1/orders",
            json={
                "run_id": "run-123",
                # Missing required fields
            },
        )

        assert response.status_code == 422

    def test_create_order_without_veda_returns_503(
        self,
        client_without_veda: TestClient,
    ) -> None:
        """POST /orders without VedaService should return 503."""
        response = client_without_veda.post(
            "/api/v1/orders",
            json={
                "run_id": "run-123",
                "client_order_id": "order-abc",
                "symbol": "BTC/USD",
                "side": "buy",
                "order_type": "market",
                "qty": "1.5",
            },
        )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()


# =============================================================================
# Test: DELETE /orders/{id}
# =============================================================================


class TestCancelOrder:
    """Tests for DELETE /orders/{id} endpoint."""

    def test_cancel_order_calls_veda_service(
        self,
        client_with_veda: TestClient,
        mock_veda_service: MagicMock,
    ) -> None:
        """DELETE /orders/{id} should call VedaService.cancel_order."""
        mock_veda_service.cancel_order.return_value = True

        response = client_with_veda.delete("/api/v1/orders/order-abc")

        assert response.status_code == 204
        mock_veda_service.cancel_order.assert_called_once_with("order-abc")

    def test_cancel_nonexistent_order_returns_404(
        self,
        client_with_veda: TestClient,
        mock_veda_service: MagicMock,
    ) -> None:
        """DELETE /orders/{id} for non-existent order should return 404."""
        mock_veda_service.cancel_order.return_value = False

        response = client_with_veda.delete("/api/v1/orders/nonexistent")

        assert response.status_code == 404

    def test_cancel_order_without_veda_returns_503(
        self,
        client_without_veda: TestClient,
    ) -> None:
        """DELETE /orders/{id} without VedaService should return 503."""
        response = client_without_veda.delete("/api/v1/orders/order-abc")

        assert response.status_code == 503
