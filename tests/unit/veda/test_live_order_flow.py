"""
Tests for Live Order Flow.

M6-4: Complete order flow with persistence and events.
"""

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.veda.interfaces import OrderSubmitResult
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Create mock exchange adapter."""
    adapter = MagicMock()
    adapter.submit_order = AsyncMock()
    adapter.cancel_order = AsyncMock()
    adapter.get_order = AsyncMock()
    adapter.is_connected = True
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    return adapter


@pytest.fixture
def mock_event_log() -> MagicMock:
    """Create mock event log."""
    event_log = MagicMock()
    event_log.append = AsyncMock()
    event_log.subscribe = AsyncMock(return_value=lambda: None)
    return event_log


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create mock order repository."""
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_by_client_order_id = AsyncMock(return_value=None)
    repo.list_by_run_id = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def sample_intent() -> OrderIntent:
    """Create sample order intent."""
    return OrderIntent(
        run_id="run-123",
        client_order_id="order-abc",
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1.5"),
        limit_price=None,
        stop_price=None,
        time_in_force=TimeInForce.DAY,
        extended_hours=False,
    )


@pytest.fixture
def sample_limit_intent() -> OrderIntent:
    """Create sample limit order intent."""
    return OrderIntent(
        run_id="run-123",
        client_order_id="order-limit",
        symbol="AAPL",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        qty=Decimal("10"),
        limit_price=Decimal("150.00"),
        stop_price=None,
        time_in_force=TimeInForce.GTC,
        extended_hours=False,
    )


# =============================================================================
# Test: VedaService Connection
# =============================================================================


class TestVedaServiceConnection:
    """Tests for VedaService connection management."""

    def test_veda_service_has_connect_method(self) -> None:
        """VedaService should have connect() method."""
        from src.veda import VedaService
        assert hasattr(VedaService, "connect")

    def test_veda_service_has_disconnect_method(self) -> None:
        """VedaService should have disconnect() method."""
        from src.veda import VedaService
        assert hasattr(VedaService, "disconnect")

    def test_veda_service_has_is_connected_property(self) -> None:
        """VedaService should have is_connected property."""
        from src.veda import VedaService
        assert hasattr(VedaService, "is_connected")

    async def test_connect_calls_adapter_connect(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """connect() should call adapter.connect()."""
        from src.veda.veda_service import VedaService
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.connect()
        
        mock_adapter.connect.assert_called_once()

    async def test_disconnect_calls_adapter_disconnect(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """disconnect() should call adapter.disconnect()."""
        from src.veda.veda_service import VedaService
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.disconnect()
        
        mock_adapter.disconnect.assert_called_once()

    async def test_is_connected_returns_adapter_status(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """is_connected should return adapter.is_connected."""
        from src.veda.veda_service import VedaService
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        mock_adapter.is_connected = True
        assert service.is_connected is True
        
        mock_adapter.is_connected = False
        assert service.is_connected is False


# =============================================================================
# Test: Order Persistence
# =============================================================================


class TestOrderPersistence:
    """Tests for order persistence."""

    async def test_place_order_persists_to_repository(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """place_order() should persist order to repository."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.place_order(sample_intent)
        
        mock_repository.save.assert_called_once()
        saved_state = mock_repository.save.call_args[0][0]
        assert isinstance(saved_state, OrderState)
        assert saved_state.client_order_id == "order-abc"


# =============================================================================
# Test: Event Emission
# =============================================================================


class TestEventEmission:
    """Tests for event emission."""

    async def test_place_order_emits_created_event(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """place_order() should emit orders.Created event on success."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.place_order(sample_intent)
        
        mock_event_log.append.assert_called_once()
        envelope = mock_event_log.append.call_args[0][0]
        assert envelope.type == "orders.Created"
        assert envelope.run_id == "run-123"

    async def test_rejected_order_emits_rejected_event(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """place_order() should emit orders.Rejected for rejected orders."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=False,
            exchange_order_id=None,
            status=OrderStatus.REJECTED,
            error_code="INSUFFICIENT_FUNDS",
            error_message="Not enough buying power",
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.place_order(sample_intent)
        
        mock_event_log.append.assert_called_once()
        envelope = mock_event_log.append.call_args[0][0]
        assert envelope.type == "orders.Rejected"
        assert envelope.payload["reject_reason"] == "Not enough buying power"

    async def test_event_includes_exchange_order_id(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """Event payload should include exchange_order_id."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=True,
            exchange_order_id="alpaca-order-xyz",
            status=OrderStatus.ACCEPTED,
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.place_order(sample_intent)
        
        envelope = mock_event_log.append.call_args[0][0]
        assert envelope.payload["exchange_order_id"] == "alpaca-order-xyz"


# =============================================================================
# Test: Order Queries
# =============================================================================


class TestOrderQueries:
    """Tests for order query methods."""

    async def test_get_order_returns_from_local_state(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """get_order() should return order from local state first."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.place_order(sample_intent)
        
        # Should get from local state, not repository
        result = await service.get_order("order-abc")
        
        assert result is not None
        assert result.client_order_id == "order-abc"
        mock_repository.get_by_client_order_id.assert_not_called()

    async def test_get_order_falls_back_to_repository(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """get_order() should fall back to repository if not in local state."""
        from src.veda.veda_service import VedaService
        
        stored_state = OrderState(
            id="db-order-id",
            client_order_id="stored-order",
            exchange_order_id="exch-stored",
            run_id="run-123",
            symbol="ETH/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("2.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("2.0"),
            filled_avg_price=Decimal("3000.00"),
            created_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
            filled_at=datetime.now(UTC),
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        mock_repository.get_by_client_order_id.return_value = stored_state
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        result = await service.get_order("stored-order")
        
        assert result is not None
        assert result.client_order_id == "stored-order"
        mock_repository.get_by_client_order_id.assert_called_once_with("stored-order")

    async def test_list_orders_returns_local_orders(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """list_orders() without run_id should return local orders."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.place_order(sample_intent)
        
        orders = await service.list_orders()
        
        assert len(orders) == 1
        assert orders[0].client_order_id == "order-abc"

    async def test_list_orders_filters_by_run_id(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """list_orders(run_id=...) should query repository."""
        from src.veda.veda_service import VedaService
        
        mock_repository.list_by_run_id.return_value = []
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        await service.list_orders(run_id="run-456")
        
        mock_repository.list_by_run_id.assert_called_once_with("run-456")


# =============================================================================
# Test: Idempotency
# =============================================================================


class TestIdempotency:
    """Tests for idempotent order submission."""

    async def test_duplicate_client_order_id_returns_existing(
        self,
        mock_adapter: MagicMock,
        mock_event_log: MagicMock,
        mock_repository: MagicMock,
        sample_intent: OrderIntent,
    ) -> None:
        """Submitting same client_order_id twice should return existing order."""
        from src.veda.veda_service import VedaService
        
        mock_adapter.submit_order.return_value = OrderSubmitResult(
            success=True,
            exchange_order_id="exch-123",
            status=OrderStatus.SUBMITTED,
        )
        
        service = VedaService(
            adapter=mock_adapter,
            event_log=mock_event_log,
            repository=mock_repository,
            config=MagicMock(),
        )
        
        # Submit first time
        state1 = await service.place_order(sample_intent)
        
        # Submit again with same client_order_id
        state2 = await service.place_order(sample_intent)
        
        # Should return same state, adapter called only once
        assert state1.id == state2.id
        assert mock_adapter.submit_order.call_count == 1
        assert mock_repository.save.call_count == 1  # Saved only once
        assert mock_event_log.append.call_count == 1  # Event emitted once
