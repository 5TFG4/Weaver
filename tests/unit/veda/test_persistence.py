"""
Unit tests for VedaOrderRepository

MVP-4: OrderState Persistence
- SQLAlchemy model for order storage
- Repository pattern for CRUD operations
- Support for query by various criteria
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.veda.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)


# ============================================================================
# Test: VedaOrder SQLAlchemy Model
# ============================================================================


class TestVedaOrderModel:
    """Test VedaOrder SQLAlchemy model."""

    def test_veda_order_model_exists(self) -> None:
        """VedaOrder model exists."""
        from src.veda.persistence import VedaOrder
        assert VedaOrder is not None

    def test_veda_order_has_tablename(self) -> None:
        """VedaOrder has correct tablename."""
        from src.veda.persistence import VedaOrder
        assert VedaOrder.__tablename__ == "veda_orders"

    def test_veda_order_has_id_column(self) -> None:
        """VedaOrder has id primary key."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "id")

    def test_veda_order_has_client_order_id_column(self) -> None:
        """VedaOrder has client_order_id column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "client_order_id")

    def test_veda_order_has_exchange_order_id_column(self) -> None:
        """VedaOrder has exchange_order_id column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "exchange_order_id")

    def test_veda_order_has_run_id_column(self) -> None:
        """VedaOrder has run_id column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "run_id")

    def test_veda_order_has_symbol_column(self) -> None:
        """VedaOrder has symbol column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "symbol")

    def test_veda_order_has_status_column(self) -> None:
        """VedaOrder has status column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "status")

    def test_veda_order_has_qty_column(self) -> None:
        """VedaOrder has qty column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "qty")

    def test_veda_order_has_filled_qty_column(self) -> None:
        """VedaOrder has filled_qty column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "filled_qty")

    def test_veda_order_has_created_at_column(self) -> None:
        """VedaOrder has created_at column."""
        from src.veda.persistence import VedaOrder
        assert hasattr(VedaOrder, "created_at")


# ============================================================================
# Test: OrderRepository Interface
# ============================================================================


class TestOrderRepositoryInterface:
    """Test that OrderRepository has the expected interface."""

    def test_order_repository_exists(self) -> None:
        """OrderRepository class exists."""
        from src.veda.persistence import OrderRepository
        assert OrderRepository is not None

    def test_order_repository_accepts_session_factory(self) -> None:
        """OrderRepository accepts session factory."""
        from src.veda.persistence import OrderRepository
        # Just test the interface exists
        import inspect
        sig = inspect.signature(OrderRepository.__init__)
        params = list(sig.parameters.keys())
        assert "session_factory" in params or len(params) == 2  # self + factory

    def test_order_repository_has_save_method(self) -> None:
        """OrderRepository has save method."""
        from src.veda.persistence import OrderRepository
        assert hasattr(OrderRepository, "save")

    def test_order_repository_has_get_by_id_method(self) -> None:
        """OrderRepository has get_by_id method."""
        from src.veda.persistence import OrderRepository
        assert hasattr(OrderRepository, "get_by_id")

    def test_order_repository_has_get_by_client_order_id_method(self) -> None:
        """OrderRepository has get_by_client_order_id method."""
        from src.veda.persistence import OrderRepository
        assert hasattr(OrderRepository, "get_by_client_order_id")

    def test_order_repository_has_list_by_run_id_method(self) -> None:
        """OrderRepository has list_by_run_id method."""
        from src.veda.persistence import OrderRepository
        assert hasattr(OrderRepository, "list_by_run_id")

    def test_order_repository_has_list_by_status_method(self) -> None:
        """OrderRepository has list_by_status method."""
        from src.veda.persistence import OrderRepository
        assert hasattr(OrderRepository, "list_by_status")


# ============================================================================
# Test: OrderState to/from VedaOrder conversion
# ============================================================================


class TestOrderStateConversion:
    """Test conversion between OrderState and VedaOrder."""

    def test_veda_order_to_order_state(self) -> None:
        """VedaOrder can convert to OrderState."""
        from src.veda.persistence import VedaOrder
        
        now = datetime.now(UTC)
        veda_order = VedaOrder(
            id=str(uuid4()),
            client_order_id=str(uuid4()),
            exchange_order_id="exch-123",
            run_id="run-001",
            symbol="BTC/USD",
            side=OrderSide.BUY.value,
            order_type=OrderType.MARKET.value,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC.value,
            status=OrderStatus.FILLED.value,
            filled_qty=Decimal("1.0"),
            filled_avg_price=Decimal("42000.00"),
            created_at=now,
            submitted_at=now,
            filled_at=now,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        
        order_state = veda_order.to_order_state()
        
        assert order_state.id == veda_order.id
        assert order_state.client_order_id == veda_order.client_order_id
        assert order_state.symbol == "BTC/USD"
        assert order_state.status == OrderStatus.FILLED

    def test_order_state_to_veda_order(self) -> None:
        """VedaOrder.from_order_state creates VedaOrder from OrderState."""
        from src.veda.models import OrderState
        from src.veda.persistence import VedaOrder
        
        now = datetime.now(UTC)
        order_state = OrderState(
            id=str(uuid4()),
            client_order_id=str(uuid4()),
            exchange_order_id="exch-123",
            run_id="run-001",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("1.0"),
            filled_avg_price=Decimal("42000.00"),
            created_at=now,
            submitted_at=now,
            filled_at=now,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        
        veda_order = VedaOrder.from_order_state(order_state)
        
        assert veda_order.id == order_state.id
        assert veda_order.client_order_id == order_state.client_order_id
        assert veda_order.symbol == "BTC/USD"
        assert veda_order.status == OrderStatus.FILLED.value


# ============================================================================
# Integration Tests (require database)
# ============================================================================


@pytest.mark.integration
class TestOrderRepositorySave:
    """Integration tests for OrderRepository.save."""

    async def test_save_order_persists_to_db(
        self, db_session: AsyncSession
    ) -> None:
        """save() persists order to database."""
        from src.veda.models import OrderState
        from src.veda.persistence import OrderRepository, VedaOrder
        
        repo = OrderRepository(session_factory=lambda: db_session)
        
        now = datetime.now(UTC)
        order_state = OrderState(
            id=str(uuid4()),
            client_order_id=str(uuid4()),
            exchange_order_id="exch-123",
            run_id="run-001",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("1.0"),
            filled_avg_price=Decimal("42000.00"),
            created_at=now,
            submitted_at=now,
            filled_at=now,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        
        await repo.save(order_state)
        
        # Verify persisted
        result = await db_session.execute(
            select(VedaOrder).where(VedaOrder.id == order_state.id)
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.symbol == "BTC/USD"


@pytest.mark.integration
class TestOrderRepositoryQuery:
    """Integration tests for OrderRepository queries."""

    async def test_get_by_id_returns_order(
        self, db_session: AsyncSession
    ) -> None:
        """get_by_id returns the saved order."""
        from src.veda.models import OrderState
        from src.veda.persistence import OrderRepository
        
        repo = OrderRepository(session_factory=lambda: db_session)
        
        now = datetime.now(UTC)
        order_id = str(uuid4())
        order_state = OrderState(
            id=order_id,
            client_order_id=str(uuid4()),
            exchange_order_id="exch-123",
            run_id="run-001",
            symbol="ETH/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            qty=Decimal("10.0"),
            limit_price=Decimal("3000.00"),
            stop_price=None,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.ACCEPTED,
            filled_qty=Decimal("0"),
            filled_avg_price=None,
            created_at=now,
            submitted_at=now,
            filled_at=None,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        
        await repo.save(order_state)
        result = await repo.get_by_id(order_id)
        
        assert result is not None
        assert result.symbol == "ETH/USD"
        assert result.status == OrderStatus.ACCEPTED

    async def test_get_by_client_order_id_returns_order(
        self, db_session: AsyncSession
    ) -> None:
        """get_by_client_order_id returns correct order."""
        from src.veda.models import OrderState
        from src.veda.persistence import OrderRepository
        
        repo = OrderRepository(session_factory=lambda: db_session)
        
        now = datetime.now(UTC)
        client_order_id = str(uuid4())
        order_state = OrderState(
            id=str(uuid4()),
            client_order_id=client_order_id,
            exchange_order_id="exch-456",
            run_id="run-002",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("0.5"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("0.5"),
            filled_avg_price=Decimal("41000.00"),
            created_at=now,
            submitted_at=now,
            filled_at=now,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        
        await repo.save(order_state)
        result = await repo.get_by_client_order_id(client_order_id)
        
        assert result is not None
        assert result.client_order_id == client_order_id

    async def test_list_by_run_id_returns_matching_orders(
        self, db_session: AsyncSession
    ) -> None:
        """list_by_run_id returns orders for specific run."""
        from src.veda.models import OrderState
        from src.veda.persistence import OrderRepository
        
        repo = OrderRepository(session_factory=lambda: db_session)
        
        now = datetime.now(UTC)
        run_id = "test-run-xyz"
        
        # Create orders for this run
        for i in range(3):
            order_state = OrderState(
                id=str(uuid4()),
                client_order_id=str(uuid4()),
                exchange_order_id=f"exch-{i}",
                run_id=run_id,
                symbol="BTC/USD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=Decimal("1.0"),
                limit_price=None,
                stop_price=None,
                time_in_force=TimeInForce.GTC,
                status=OrderStatus.FILLED,
                filled_qty=Decimal("1.0"),
                filled_avg_price=Decimal("42000.00"),
                created_at=now,
                submitted_at=now,
                filled_at=now,
                cancelled_at=None,
                reject_reason=None,
                error_code=None,
            )
            await repo.save(order_state)
        
        # Create order for different run
        other_order = OrderState(
            id=str(uuid4()),
            client_order_id=str(uuid4()),
            exchange_order_id="exch-other",
            run_id="other-run",
            symbol="ETH/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("5.0"),
            limit_price=None,
            stop_price=None,
            time_in_force=TimeInForce.GTC,
            status=OrderStatus.FILLED,
            filled_qty=Decimal("5.0"),
            filled_avg_price=Decimal("2500.00"),
            created_at=now,
            submitted_at=now,
            filled_at=now,
            cancelled_at=None,
            reject_reason=None,
            error_code=None,
        )
        await repo.save(other_order)
        
        results = await repo.list_by_run_id(run_id)
        
        assert len(results) == 3
        for order in results:
            assert order.run_id == run_id
