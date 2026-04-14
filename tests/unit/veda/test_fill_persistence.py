"""
Tests for fill persistence wiring in VedaService.

N-03 (TDD): VedaService persists fills when orders are filled.
Tests written BEFORE implementation — expect RED initially.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.veda.interfaces import ExchangeOrder, TradeActivity
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from src.veda.veda_service import VedaService

# ============================================================================
# Helpers
# ============================================================================


def _make_intent(
    *,
    run_id: str = "run-001",
    client_order_id: str = "client-001",
    symbol: str = "AAPL",
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.MARKET,
    qty: Decimal = Decimal("10"),
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
    time_in_force: TimeInForce = TimeInForce.DAY,
    extended_hours: bool = False,
) -> OrderIntent:
    """Create a test OrderIntent with sensible defaults."""
    return OrderIntent(
        run_id=run_id,
        client_order_id=client_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        qty=qty,
        limit_price=limit_price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        extended_hours=extended_hours,
    )


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
        limit_price=intent.limit_price,
        stop_price=intent.stop_price,
        time_in_force=intent.time_in_force,
        status=OrderStatus.FILLED,
        filled_qty=intent.qty,
        filled_avg_price=Decimal("150.00"),
        exchange_order_id="exch-001",
        created_at=datetime.now(UTC),
        submitted_at=datetime.now(UTC),
        filled_at=datetime.now(UTC),
        cancelled_at=None,
        reject_reason=None,
        error_code=None,
    )


def _make_order_state(
    intent: OrderIntent,
    *,
    status: OrderStatus = OrderStatus.ACCEPTED,
    filled_qty: Decimal = Decimal("0"),
    filled_avg_price: Decimal | None = None,
    exchange_order_id: str = "exch-001",
) -> OrderState:
    """Create a non-terminal order state for reconciliation tests."""
    return OrderState(
        id="order-001",
        client_order_id=intent.client_order_id,
        run_id=intent.run_id,
        symbol=intent.symbol,
        side=intent.side,
        order_type=intent.order_type,
        qty=intent.qty,
        limit_price=intent.limit_price,
        stop_price=intent.stop_price,
        time_in_force=intent.time_in_force,
        status=status,
        filled_qty=filled_qty,
        filled_avg_price=filled_avg_price,
        exchange_order_id=exchange_order_id,
        created_at=datetime.now(UTC),
        submitted_at=datetime.now(UTC),
        filled_at=None,
        cancelled_at=None,
        reject_reason=None,
        error_code=None,
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
        repo.get_by_client_order_id = AsyncMock(return_value=None)
        repo.list_by_run_id = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def service(self, mock_fill_repo, mock_order_repo) -> VedaService:
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
    async def test_record_fill_persists_to_repository(self, service, mock_fill_repo) -> None:
        """record_fill() saves a FillRecord via FillRepository."""
        from src.walle.models import FillRecord

        fill = FillRecord(
            id="fill-001",
            order_id="order-001",
            price=Decimal("150.25"),
            quantity=Decimal("10"),
            side="buy",
            filled_at=datetime.now(UTC),
        )

        await service.record_fill(fill)

        mock_fill_repo.save.assert_awaited_once_with(fill)

    @pytest.mark.asyncio
    async def test_record_fill_noop_when_no_repository(self, mock_order_repo) -> None:
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
            filled_at=datetime.now(UTC),
        )

        # Should not raise
        await service.record_fill(fill)

    @pytest.mark.asyncio
    async def test_get_fills_delegates_to_repository(self, service, mock_fill_repo) -> None:
        """get_fills() delegates to FillRepository.list_by_order()."""
        from src.walle.models import FillRecord

        expected_fills = [
            FillRecord(
                id="fill-001",
                order_id="order-001",
                price=Decimal("150.25"),
                quantity=Decimal("10"),
                side="buy",
                filled_at=datetime.now(UTC),
            )
        ]
        mock_fill_repo.list_by_order.return_value = expected_fills

        result = await service.get_fills("order-001")

        mock_fill_repo.list_by_order.assert_awaited_once_with("order-001")
        assert result == expected_fills

    @pytest.mark.asyncio
    async def test_get_fills_returns_empty_when_no_repository(self, mock_order_repo) -> None:
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

    @pytest.mark.asyncio
    async def test_reconcile_run_fills_once_persists_new_fill(
        self,
        service: VedaService,
        mock_fill_repo: AsyncMock,
        mock_order_repo: AsyncMock,
    ) -> None:
        """reconcile_run_fills_once() saves a new fill activity."""
        adapter = cast(AsyncMock, service._adapter)
        intent = _make_intent(client_order_id="client-activity-1")
        persisted_order = _make_order_state(intent)
        mock_order_repo.list_by_run_id.return_value = [persisted_order]
        adapter.list_trade_activities.return_value = [
            TradeActivity(
                activity_id="activity-001",
                order_id="exch-001",
                symbol="AAPL",
                side=OrderSide.BUY,
                qty=Decimal("2"),
                price=Decimal("150.25"),
                transaction_time=datetime(2026, 4, 7, 10, 30, tzinfo=UTC),
                leaves_qty=Decimal("8"),
                cum_qty=Decimal("2"),
                order_status=OrderStatus.PARTIALLY_FILLED,
                activity_type="partial_fill",
            )
        ]
        adapter.get_order.return_value = ExchangeOrder(
            exchange_order_id="exch-001",
            client_order_id="client-activity-1",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("10"),
            filled_qty=Decimal("2"),
            filled_avg_price=Decimal("150.25"),
            status=OrderStatus.PARTIALLY_FILLED,
            created_at=datetime.now(UTC),
            updated_at=datetime(2026, 4, 7, 10, 30, tzinfo=UTC),
        )

        updated_after = await service.reconcile_run_fills_once(
            run_id="run-001",
            after=datetime(2026, 4, 7, 10, 0, tzinfo=UTC),
        )

        mock_fill_repo.save.assert_awaited_once()
        saved_fill = mock_fill_repo.save.await_args.args[0]
        assert saved_fill.id == "activity-001"
        assert saved_fill.exchange_fill_id == "activity-001"
        assert saved_fill.symbol == "AAPL"
        assert saved_fill.commission is None
        assert updated_after == datetime(2026, 4, 7, 10, 30, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_reconcile_run_fills_once_skips_duplicate_activity(
        self,
        service: VedaService,
        mock_fill_repo: AsyncMock,
        mock_order_repo: AsyncMock,
    ) -> None:
        """reconcile_run_fills_once() dedupes overlapping poll windows."""
        from src.walle.models import FillRecord

        adapter = cast(AsyncMock, service._adapter)
        event_log = cast(AsyncMock, service._event_log)
        intent = _make_intent(client_order_id="client-activity-2")
        persisted_order = _make_order_state(intent)
        mock_order_repo.get_by_client_order_id.return_value = persisted_order
        mock_order_repo.list_by_run_id.return_value = [persisted_order]
        mock_fill_repo.list_by_order.return_value = [
            FillRecord(
                id="activity-001",
                order_id="order-001",
                price=Decimal("150.25"),
                quantity=Decimal("2"),
                side="buy",
                filled_at=datetime(2026, 4, 7, 10, 30, tzinfo=UTC),
                exchange_fill_id="activity-001",
            )
        ]
        adapter.list_trade_activities.return_value = [
            TradeActivity(
                activity_id="activity-001",
                order_id="exch-001",
                symbol="AAPL",
                side=OrderSide.BUY,
                qty=Decimal("2"),
                price=Decimal("150.25"),
                transaction_time=datetime(2026, 4, 7, 10, 30, tzinfo=UTC),
                leaves_qty=Decimal("8"),
                cum_qty=Decimal("2"),
                order_status=OrderStatus.PARTIALLY_FILLED,
                activity_type="partial_fill",
            )
        ]

        await service.reconcile_run_fills_once(
            run_id="run-001",
            after=datetime(2026, 4, 7, 10, 0, tzinfo=UTC),
        )

        mock_fill_repo.save.assert_not_awaited()
        event_log.append.assert_not_awaited()
        adapter.get_order.assert_not_awaited()


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
