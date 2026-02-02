"""
Tests for Orders Endpoint

MVP-4: Order Queries
TDD: Write tests first, then implement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


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
