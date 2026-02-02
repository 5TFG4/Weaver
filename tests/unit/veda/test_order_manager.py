"""
Unit tests for OrderManager

MVP-3: OrderManager Core
- Wraps ExchangeAdapter
- Manages local OrderState instances  
- Emits OrderEvent when state changes
- Idempotent submit (tracks by client_order_id)
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.veda.adapters.mock_adapter import MockExchangeAdapter
from src.veda.interfaces import ExchangeAdapter, OrderSubmitResult
from src.veda.models import (
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    TimeInForce,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_adapter() -> MockExchangeAdapter:
    """Create a fresh mock adapter."""
    return MockExchangeAdapter()


@pytest.fixture
def sample_intent() -> OrderIntent:
    """Create a sample order intent."""
    return OrderIntent(
        run_id="test-run-001",
        client_order_id=str(uuid4()),
        symbol="BTC/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1.0"),
        limit_price=None,
        stop_price=None,
        time_in_force=TimeInForce.GTC,
    )


@pytest.fixture
def limit_order_intent() -> OrderIntent:
    """Create a limit order intent."""
    return OrderIntent(
        run_id="test-run-001",
        client_order_id=str(uuid4()),
        symbol="ETH/USD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        qty=Decimal("10.0"),
        limit_price=Decimal("3000.00"),
        stop_price=None,
        time_in_force=TimeInForce.GTC,
    )


# ============================================================================
# Test: OrderManager Interface
# ============================================================================

class TestOrderManagerInterface:
    """Test that OrderManager has the expected interface."""

    def test_order_manager_exists(self) -> None:
        """OrderManager class exists."""
        from src.veda.order_manager import OrderManager
        assert OrderManager is not None

    def test_accepts_adapter_in_constructor(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """OrderManager accepts an adapter in constructor."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        assert manager is not None

    def test_has_submit_order_method(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """OrderManager has submit_order method."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        assert hasattr(manager, "submit_order")
        assert callable(manager.submit_order)

    def test_has_cancel_order_method(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """OrderManager has cancel_order method."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        assert hasattr(manager, "cancel_order")

    def test_has_get_order_method(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """OrderManager has get_order method."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        assert hasattr(manager, "get_order")

    def test_has_list_orders_method(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """OrderManager has list_orders method."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        assert hasattr(manager, "list_orders")


# ============================================================================
# Test: Order Submission
# ============================================================================

class TestOrderManagerSubmit:
    """Test order submission through OrderManager."""

    async def test_submit_order_returns_order_state(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """submit_order returns an OrderState."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        
        assert isinstance(result, OrderState)

    async def test_submit_order_populates_client_order_id(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Returned OrderState has correct client_order_id."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        
        assert result.client_order_id == sample_intent.client_order_id

    async def test_submit_order_populates_exchange_order_id(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Returned OrderState has exchange_order_id set."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        
        assert result.exchange_order_id is not None
        assert len(result.exchange_order_id) > 0

    async def test_submit_order_populates_symbol_and_side(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Returned OrderState has symbol and side from intent."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        
        assert result.symbol == sample_intent.symbol
        assert result.side == sample_intent.side

    async def test_submit_order_populates_qty_and_type(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Returned OrderState has qty and order_type from intent."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        
        assert result.qty == sample_intent.qty
        assert result.order_type == sample_intent.order_type

    async def test_submit_market_order_has_filled_status(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Market order gets FILLED status (mock fills immediately)."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        
        assert result.status == OrderStatus.FILLED

    async def test_submit_limit_order_has_accepted_status(
        self,
        mock_adapter: MockExchangeAdapter,
        limit_order_intent: OrderIntent,
    ) -> None:
        """Limit order gets ACCEPTED status (mock doesn't fill)."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(limit_order_intent)
        
        assert result.status == OrderStatus.ACCEPTED

    async def test_submit_order_has_timestamps(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Returned OrderState has created_at and submitted_at."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        before = datetime.now(UTC)
        
        result = await manager.submit_order(sample_intent)
        
        after = datetime.now(UTC)
        assert before <= result.created_at <= after
        assert result.submitted_at is not None
        assert before <= result.submitted_at <= after


# ============================================================================
# Test: Order Idempotency
# ============================================================================

class TestOrderManagerIdempotency:
    """Test idempotent order submission."""

    async def test_submit_same_order_twice_returns_same_state(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Submitting same client_order_id returns same OrderState."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result1 = await manager.submit_order(sample_intent)
        result2 = await manager.submit_order(sample_intent)
        
        assert result1.exchange_order_id == result2.exchange_order_id
        assert result1.client_order_id == result2.client_order_id

    async def test_submit_different_orders_returns_different_states(
        self,
        mock_adapter: MockExchangeAdapter,
    ) -> None:
        """Different client_order_ids produce different states."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        intent1 = OrderIntent(
            run_id="test-run-001",
            client_order_id=str(uuid4()),
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        intent2 = OrderIntent(
            run_id="test-run-001",
            client_order_id=str(uuid4()),
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
        )
        
        result1 = await manager.submit_order(intent1)
        result2 = await manager.submit_order(intent2)
        
        assert result1.exchange_order_id != result2.exchange_order_id

    async def test_orders_tracked_locally(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Submitted orders are tracked in manager's local state."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.submit_order(sample_intent)
        local_state = manager.get_order(sample_intent.client_order_id)
        
        assert local_state is not None
        assert local_state.client_order_id == result.client_order_id


# ============================================================================
# Test: Order Query
# ============================================================================

class TestOrderManagerQuery:
    """Test order queries through OrderManager."""

    async def test_get_order_returns_tracked_state(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """get_order returns the tracked OrderState."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        submitted = await manager.submit_order(sample_intent)
        result = manager.get_order(sample_intent.client_order_id)
        
        assert result is not None
        assert result.exchange_order_id == submitted.exchange_order_id

    async def test_get_order_returns_none_for_unknown(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """get_order returns None for unknown client_order_id."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = manager.get_order("unknown-id")
        
        assert result is None

    async def test_list_orders_returns_all_tracked(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """list_orders returns all tracked orders."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        intents = [
            OrderIntent(
                run_id="test-run-001",
                client_order_id=str(uuid4()),
                symbol="BTC/USD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=Decimal("1.0"),
                limit_price=None,
                stop_price=None,
                time_in_force=TimeInForce.GTC,
            )
            for _ in range(3)
        ]
        
        for intent in intents:
            await manager.submit_order(intent)
        
        result = manager.list_orders()
        
        assert len(result) == 3

    async def test_list_orders_empty_initially(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """list_orders returns empty list when no orders."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = manager.list_orders()
        
        assert result == []


# ============================================================================
# Test: Order Cancellation
# ============================================================================

class TestOrderManagerCancel:
    """Test order cancellation through OrderManager."""

    async def test_cancel_pending_order_returns_true(
        self,
        mock_adapter: MockExchangeAdapter,
        limit_order_intent: OrderIntent,
    ) -> None:
        """cancel_order returns True for pending order."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        await manager.submit_order(limit_order_intent)
        result = await manager.cancel_order(limit_order_intent.client_order_id)
        
        assert result is True

    async def test_cancel_updates_local_state(
        self,
        mock_adapter: MockExchangeAdapter,
        limit_order_intent: OrderIntent,
    ) -> None:
        """cancel_order updates local OrderState to CANCELLED."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        await manager.submit_order(limit_order_intent)
        await manager.cancel_order(limit_order_intent.client_order_id)
        
        state = manager.get_order(limit_order_intent.client_order_id)
        assert state is not None
        assert state.status == OrderStatus.CANCELLED

    async def test_cancel_unknown_order_returns_false(
        self, mock_adapter: MockExchangeAdapter
    ) -> None:
        """cancel_order returns False for unknown order."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        result = await manager.cancel_order("unknown-id")
        
        assert result is False

    async def test_cancel_filled_order_returns_false(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """cancel_order returns False for filled order."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        # Market orders fill immediately in mock
        await manager.submit_order(sample_intent)
        result = await manager.cancel_order(sample_intent.client_order_id)
        
        assert result is False


# ============================================================================
# Test: Rejection Handling
# ============================================================================

class TestOrderManagerRejection:
    """Test order rejection handling."""

    async def test_rejected_order_has_rejected_status(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Rejected order has REJECTED status in local state."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        mock_adapter.set_reject_next_order(True, "Insufficient funds")
        result = await manager.submit_order(sample_intent)
        
        assert result.status == OrderStatus.REJECTED

    async def test_rejected_order_tracked_locally(
        self,
        mock_adapter: MockExchangeAdapter,
        sample_intent: OrderIntent,
    ) -> None:
        """Rejected orders are tracked in local state."""
        from src.veda.order_manager import OrderManager
        manager = OrderManager(adapter=mock_adapter)
        
        mock_adapter.set_reject_next_order(True, "Insufficient funds")
        await manager.submit_order(sample_intent)
        
        local_state = manager.get_order(sample_intent.client_order_id)
        assert local_state is not None
        assert local_state.status == OrderStatus.REJECTED
