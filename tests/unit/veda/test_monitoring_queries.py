"""
Tests for monitoring-oriented VedaService queries.

M14 Phase 2: exchange positions and real bar accessors.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.veda.models import Bar, Position, PositionSide
from src.veda.veda_service import VedaService


@pytest.fixture
def service() -> VedaService:
    """Create a VedaService with mocked dependencies."""
    adapter = AsyncMock()
    adapter.is_connected = True
    return VedaService(
        adapter=adapter,
        event_log=AsyncMock(),
        repository=AsyncMock(),
        config=MagicMock(),
    )


class TestMonitoringQueries:
    """VedaService monitoring accessors delegate to the adapter."""

    @pytest.mark.asyncio
    async def test_get_exchange_positions_delegates_to_adapter(self, service: VedaService) -> None:
        """Open positions should come from the live adapter snapshot."""
        expected = [
            Position(
                symbol="AAPL",
                qty=Decimal("5"),
                side=PositionSide.LONG,
                avg_entry_price=Decimal("150.00"),
                market_value=Decimal("760.00"),
                unrealized_pnl=Decimal("10.00"),
                unrealized_pnl_percent=Decimal("1.33"),
            )
        ]
        service._adapter.get_positions.return_value = expected

        result = await service.get_exchange_positions()

        service._adapter.get_positions.assert_awaited_once_with()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_bars_delegates_to_adapter(self, service: VedaService) -> None:
        """Bar queries should flow through the exchange adapter."""
        start = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)
        end = datetime(2024, 1, 15, 14, 34, tzinfo=UTC)
        expected = [
            Bar(
                symbol="AAPL",
                timestamp=start,
                open=Decimal("100.00"),
                high=Decimal("101.00"),
                low=Decimal("99.50"),
                close=Decimal("100.50"),
                volume=Decimal("1234.00"),
            )
        ]
        service._adapter.get_bars.return_value = expected

        result = await service.get_bars(
            symbol="AAPL",
            timeframe="1m",
            start=start,
            end=end,
            limit=5,
        )

        service._adapter.get_bars.assert_awaited_once_with(
            symbol="AAPL",
            timeframe="1m",
            start=start,
            end=end,
            limit=5,
        )
        assert result == expected
