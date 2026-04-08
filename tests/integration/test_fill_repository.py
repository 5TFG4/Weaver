"""Integration tests for FillRepository.

These tests validate the run-scoped join path against the real PostgreSQL schema.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from src.walle.models import FillRecord, VedaOrder
from src.walle.repositories.fill_repository import FillRepository


def _make_order(
    order_id: str,
    *,
    run_id: str,
    client_order_id: str,
    created_at: datetime,
) -> VedaOrder:
    """Create a persisted order row for fill join tests."""
    return VedaOrder(
        id=order_id,
        client_order_id=client_order_id,
        exchange_order_id=f"ex-{order_id}",
        run_id=run_id,
        symbol="AAPL",
        side="buy",
        order_type="market",
        qty=Decimal("10"),
        limit_price=None,
        stop_price=None,
        time_in_force="day",
        status="filled",
        filled_qty=Decimal("10"),
        filled_avg_price=Decimal("150.25"),
        created_at=created_at,
        submitted_at=created_at,
        filled_at=created_at + timedelta(minutes=1),
        cancelled_at=None,
        reject_reason=None,
        error_code=None,
    )


def _make_fill(fill_id: str, *, order_id: str, filled_at: datetime) -> FillRecord:
    """Create a persisted fill row for repository tests."""
    return FillRecord(
        id=fill_id,
        order_id=order_id,
        price=Decimal("150.25"),
        quantity=Decimal("2"),
        side="buy",
        filled_at=filled_at,
        exchange_fill_id=f"activity-{fill_id}",
        commission=Decimal("0.50"),
        symbol="AAPL",
    )


@pytest.mark.integration
class TestFillRepository:
    """Integration coverage for FillRepository queries."""

    @pytest_asyncio.fixture
    async def repo(self, database, clean_tables) -> FillRepository:
        """Create repository with clean tables."""
        return FillRepository(database.session_factory)

    async def test_list_by_run_id_filters_and_sorts(self, repo: FillRepository, database) -> None:
        """Returns only fills whose orders belong to the requested run."""
        base_time = datetime(2024, 1, 15, 14, 30, tzinfo=UTC)
        async with database.session() as session:
            session.add_all(
                [
                    _make_order(
                        "order-1",
                        run_id="run-1",
                        client_order_id="client-1",
                        created_at=base_time,
                    ),
                    _make_order(
                        "order-2",
                        run_id="run-1",
                        client_order_id="client-2",
                        created_at=base_time + timedelta(minutes=1),
                    ),
                    _make_order(
                        "order-3",
                        run_id="run-2",
                        client_order_id="client-3",
                        created_at=base_time + timedelta(minutes=2),
                    ),
                    _make_fill(
                        "fill-2",
                        order_id="order-2",
                        filled_at=base_time + timedelta(minutes=3),
                    ),
                    _make_fill(
                        "fill-1",
                        order_id="order-1",
                        filled_at=base_time + timedelta(minutes=2),
                    ),
                    _make_fill(
                        "fill-3",
                        order_id="order-3",
                        filled_at=base_time + timedelta(minutes=4),
                    ),
                ]
            )
            await session.commit()

        result = await repo.list_by_run_id("run-1")

        assert [fill.id for fill in result] == ["fill-1", "fill-2"]
        assert all(fill.order_id in {"order-1", "order-2"} for fill in result)

    async def test_list_by_run_id_returns_empty_when_run_has_no_fills(
        self,
        repo: FillRepository,
    ) -> None:
        """Unknown runs return an empty fill history."""
        result = await repo.list_by_run_id("missing-run")

        assert result == []
