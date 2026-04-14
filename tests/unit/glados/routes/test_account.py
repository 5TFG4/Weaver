"""
Tests for account monitoring endpoints.

M14 Phase 2: account snapshot + positions snapshot.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.veda.models import AccountInfo, Position, PositionSide


def _make_account() -> AccountInfo:
    """Create a deterministic account snapshot."""
    return AccountInfo(
        account_id="acct-001",
        buying_power=Decimal("25000.50"),
        cash=Decimal("12000.25"),
        portfolio_value=Decimal("30123.75"),
        currency="USD",
        status="ACTIVE",
    )


def _make_position(symbol: str, side: PositionSide = PositionSide.LONG) -> Position:
    """Create a deterministic position snapshot."""
    return Position(
        symbol=symbol,
        qty=Decimal("10"),
        side=side,
        avg_entry_price=Decimal("150.25"),
        market_value=Decimal("1520.00"),
        unrealized_pnl=Decimal("17.50"),
        unrealized_pnl_percent=Decimal("1.16"),
    )


class TestAccountEndpoint:
    """Tests for GET /api/v1/account."""

    def test_requires_veda_service(self, client: TestClient) -> None:
        """Returns 503 when live trading is not configured."""
        response = client.get("/api/v1/account")

        assert response.status_code == 503
        assert response.json()["detail"] == "Trading service not configured"

    def test_returns_account_snapshot_from_veda(self, client: TestClient) -> None:
        """Routes account queries through VedaService."""
        mock_veda = AsyncMock()
        mock_veda.get_account.return_value = _make_account()
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get("/api/v1/account")

        assert response.status_code == 200
        data = response.json()
        assert data == {
            "account_id": "acct-001",
            "buying_power": "25000.50",
            "cash": "12000.25",
            "portfolio_value": "30123.75",
            "currency": "USD",
            "status": "ACTIVE",
        }
        mock_veda.get_account.assert_awaited_once_with()


class TestAccountPositionsEndpoint:
    """Tests for GET /api/v1/account/positions."""

    def test_requires_veda_service(self, client: TestClient) -> None:
        """Returns 503 when live trading is not configured."""
        response = client.get("/api/v1/account/positions")

        assert response.status_code == 503
        assert response.json()["detail"] == "Trading service not configured"

    def test_returns_exchange_positions_snapshot(self, client: TestClient) -> None:
        """Reads open positions from the exchange-backed Veda path."""
        mock_veda = AsyncMock()
        mock_veda.get_exchange_positions.return_value = [
            _make_position("AAPL"),
            _make_position("TSLA", side=PositionSide.SHORT),
        ]
        client.app.state.veda_service = mock_veda  # type: ignore[union-attr]

        response = client.get("/api/v1/account/positions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["items"][0]["symbol"] == "AAPL"
        assert data["items"][0]["qty"] == "10"
        assert data["items"][0]["side"] == "long"
        assert data["items"][1]["side"] == "short"
        mock_veda.get_exchange_positions.assert_awaited_once_with()
