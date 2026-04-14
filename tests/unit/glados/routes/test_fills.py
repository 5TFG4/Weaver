"""
Tests for run fill history endpoint.

M14 Phase 2: expose persisted fills by run.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.walle.models import FillRecord


def _make_fill(
    fill_id: str,
    *,
    order_id: str = "order-001",
    symbol: str | None = "AAPL",
    commission: Decimal | None = Decimal("1.25"),
) -> FillRecord:
    """Create a deterministic persisted fill."""
    return FillRecord(
        id=fill_id,
        order_id=order_id,
        price=Decimal("150.25"),
        quantity=Decimal("2"),
        side="buy",
        filled_at=datetime(2026, 4, 8, 14, 30, tzinfo=UTC),
        exchange_fill_id=f"ex-{fill_id}",
        commission=commission,
        symbol=symbol,
    )


class TestRunFillsEndpoint:
    """Tests for GET /api/v1/runs/{run_id}/fills."""

    def test_returns_503_when_fill_history_unavailable(self, client: TestClient) -> None:
        """Missing fill repository should fail explicitly."""
        client.app.state.fill_repository = None  # type: ignore[union-attr]

        response = client.get("/api/v1/runs/run-123/fills")

        assert response.status_code == 503
        assert response.json()["detail"] == "Fill history not configured"

    def test_returns_run_fill_history(self, client: TestClient) -> None:
        """Maps persisted fills into the API response."""
        mock_fill_repo = AsyncMock()
        mock_fill_repo.list_by_run_id.return_value = [
            _make_fill("fill-001"),
            _make_fill("fill-002", commission=None, symbol=None),
        ]
        client.app.state.fill_repository = mock_fill_repo  # type: ignore[union-attr]

        response = client.get("/api/v1/runs/run-123/fills")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["items"][0]["id"] == "fill-001"
        assert data["items"][0]["price"] == "150.25000000"
        assert data["items"][0]["commission"] == "1.25000000"
        assert data["items"][0]["symbol"] == "AAPL"
        assert data["items"][1]["commission"] is None
        assert data["items"][1]["symbol"] is None
        mock_fill_repo.list_by_run_id.assert_awaited_once_with("run-123")
