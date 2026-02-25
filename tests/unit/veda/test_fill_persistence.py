"""
Tests for fill persistence wiring in VedaService.

N-03 (TDD): VedaService persists fills when orders are filled.
Tests written BEFORE implementation — expect RED initially.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_intent(**overrides) -> OrderIntent:
    """Create a test OrderIntent with sensible defaults."""
    defaults = dict(
        run_id="run-001",
        client_order_id="client-001",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("10"),
        time_in_force=TimeInForce.DAY,
    )
    defaults.update(overrides)
    return OrderIntent(**defaults)


def _make_filled_state(intent: OrderIntent) -> OrderState:
    """Create a filled order state from an intent."""
    return OrderState(
        id="order-001",
        client_order_id=intent.client_order_id,
        run_id=intent.run_id,
        symbol=intent.symbol,
        side=intent.side,
        order_type=intent.order_type,
        qty=intent.qty,
        time_in_force=intent.time_in_force,
        status=OrderStatus.FILLED,
        filled_qty=intent.qty,
        filled_avg_price=Decimal("150.00"),
        exchange_order_id="exch-001",
        created_at=datetime.now(timezone.utc),
        filled_at=datetime.now(timezone.utc),
    )


# ============================================================================
# Test: VedaService accepts FillRepository
# ============================================================================


class TestVedaServiceFillRepositoryWiring:
    """VedaService can be created with an optional FillRepository."""

    def test_accepts_fill_repository_parameter(self) -> None:
        """VedaService constructor accepts fill_repository keyword."""
        from src.veda.veda_service import VedaService

        adapter = MagicMock()
        event_log = MagicMock()
        repository = MagicMock()
        config = MagicMock()
        fill_repository = MagicMock()

        service = VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=repository,
            config=config,
            fill_repository=fill_repository,
        )
        assert service is not None

    def test_fill_repository_defaults_to_none(self) -> None:
        """VedaService works without fill_repository (backward compatible)."""
        from src.veda.veda_service import VedaService

        adapter = MagicMock()
        event_log = MagicMock()
        repository = MagicMock()
        config = MagicMock()

        service = VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=repository,
            config=config,
        )
        assert service is not None


# ============================================================================
# Test: VedaService persists fills
# ============================================================================


class TestVedaServiceFillPersistence:
    """VedaService saves fill records when orders are filled."""

    @pytest.fixture
    def mock_fill_repo(self) -> AsyncMock:
        """Create a mock FillRepository."""
        repo = AsyncMock()
        repo.save = AsyncMock()
        repo.list_by_order = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_order_repo(self) -> AsyncMock:
        """Create a mock OrderRepository."""
        repo = AsyncMock()
        repo.save = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_fill_repo, mock_order_repo) -> "VedaService":
        """Create VedaService with mock fills repo."""
        from src.veda.veda_service import VedaService

        adapter = AsyncMock()
        adapter.is_connected = True
        event_log = AsyncMock()
        event_log.append = AsyncMock()
        config = MagicMock()

        return VedaService(
            adapter=adapter,
            event_log=event_log,
            repository=mock_order_repo,
            config=config,
            fill_repository=mock_fill_repo,
        )

    @pytest.mark.asyncio
    async def test_record_fill_persists_to_repository(
        self, service, mock_fill_repo
    ) -> None:
        """record_fill() saves a FillRecord via FillRepository."""
        from src.walle.models import FillRecord

        fill = FillRecord(
            id="fill-001",
            order_id="order-001",
            price=Decimal("150.25"),
            quantity=Decimal("10"),
            side="buy",
            filled_at=datetime.now(timezone.utc),
        )

        await service.record_fill(fill)

        mock_fill_repo.save.assert_awaited_once_with(fill)

    @pytest.mark.asyncio
    async def test_record_fill_noop_when_no_repository(
        self, mock_order_repo
    ) -> None:
        """record_fill() is a no-op when fill_repository is None."""
        from src.veda.veda_service import VedaService
        from src.walle.models import FillRecord

        service = VedaService(
            adapter=AsyncMock(),
            event_log=AsyncMock(),
            repository=mock_order_repo,
            config=MagicMock(),
            # No fill_repository
        )

        fill = FillRecord(
            id="fill-002",
            order_id="order-001",
            price=Decimal("150.25"),
            quantity=Decimal("10"),
            side="buy",
            filled_at=datetime.now(timezone.utc),
        )

        # Should not raise
        await service.record_fill(fill)

    @pytest.mark.asyncio
    async def test_get_fills_delegates_to_repository(
        self, service, mock_fill_repo
    ) -> None:
        """get_fills() delegates to FillRepository.list_by_order()."""
        from src.walle.models import FillRecord

        expected_fills = [
            FillRecord(
                id="fill-001",
                order_id="order-001",
                price=Decimal("150.25"),
                quantity=Decimal("10"),
                side="buy",
                filled_at=datetime.now(timezone.utc),
            )
        ]
        mock_fill_repo.list_by_order.return_value = expected_fills

        result = await service.get_fills("order-001")

        mock_fill_repo.list_by_order.assert_awaited_once_with("order-001")
        assert result == expected_fills

    @pytest.mark.asyncio
    async def test_get_fills_returns_empty_when_no_repository(
        self, mock_order_repo
    ) -> None:
        """get_fills() returns empty list when fill_repository is None."""
        from src.veda.veda_service import VedaService

        service = VedaService(
            adapter=AsyncMock(),
            event_log=AsyncMock(),
            repository=mock_order_repo,
            config=MagicMock(),
        )

        result = await service.get_fills("order-001")
        assert result == []


# ============================================================================
# Test: Factory function includes FillRepository
# ============================================================================


class TestCreateVedaServiceFactory:
    """create_veda_service factory includes FillRepository when session available."""

    def test_factory_creates_service_with_fill_repository(self) -> None:
        """create_veda_service wires FillRepository from session_factory."""
        from src.veda.veda_service import create_veda_service

        adapter = MagicMock()
        event_log = MagicMock()
        session_factory = MagicMock()
        config = MagicMock()

        service = create_veda_service(
            adapter=adapter,
            event_log=event_log,
            session_factory=session_factory,
            config=config,
        )

        # Service should have a fill_repository set
        assert service._fill_repository is not None
