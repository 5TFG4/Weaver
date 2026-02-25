"""
Tests for FillRecord model and FillRepository.

D-3: Fills table + persistence for audit trail.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy import Table, inspect

from src.walle.models import Base, FillRecord


# ============================================================================
# Test: FillRecord Model Structure
# ============================================================================


class TestFillRecordModel:
    """FillRecord SQLAlchemy model has correct schema."""

    def test_tablename_is_fills(self) -> None:
        """FillRecord maps to 'fills' table."""
        assert FillRecord.__tablename__ == "fills"

    def test_has_required_columns(self) -> None:
        """FillRecord has all required columns."""
        mapper = inspect(FillRecord)
        column_names = {c.key for c in mapper.columns}

        expected = {
            "id",
            "order_id",
            "price",
            "quantity",
            "side",
            "filled_at",
        }
        assert expected.issubset(column_names)

    def test_id_is_primary_key(self) -> None:
        """id column is the primary key."""
        mapper = inspect(FillRecord)
        pk_columns = [c.key for c in mapper.primary_key]
        assert pk_columns == ["id"]

    def test_order_id_is_indexed(self) -> None:
        """order_id column is indexed for lookup."""
        table = cast(Table, FillRecord.__table__)
        order_id_indexed = any(
            "order_id" in list(idx.columns.keys()) for idx in table.indexes
        )
        assert order_id_indexed

    def test_repr(self) -> None:
        """__repr__ returns readable string."""
        record = FillRecord(
            id="fill-001",
            order_id="order-001",
            price=Decimal("150.25"),
            quantity=Decimal("10"),
            side="buy",
            filled_at=datetime.now(timezone.utc),
        )
        repr_str = repr(record)
        assert "FillRecord" in repr_str
        assert "fill-001" in repr_str

    def test_registered_in_metadata(self) -> None:
        """fills table is registered in Base.metadata."""
        assert "fills" in Base.metadata.tables


# ============================================================================
# Test: FillRepository Class
# ============================================================================


class TestFillRepositoryInterface:
    """FillRepository has the expected interface."""

    def test_repository_class_exists(self) -> None:
        """FillRepository is importable."""
        from src.walle.repositories.fill_repository import FillRepository

        assert FillRepository is not None

    def test_repository_accepts_session_factory(self) -> None:
        """FillRepository constructor takes a session_factory."""
        from unittest.mock import MagicMock

        from src.walle.repositories.fill_repository import FillRepository

        mock_factory = MagicMock()
        repo = FillRepository(session_factory=mock_factory)
        assert repo is not None

    def test_repository_has_save_method(self) -> None:
        """FillRepository has an async save() method."""
        from src.walle.repositories.fill_repository import FillRepository

        assert hasattr(FillRepository, "save")

    def test_repository_has_list_by_order_method(self) -> None:
        """FillRepository has an async list_by_order() method."""
        from src.walle.repositories.fill_repository import FillRepository

        assert hasattr(FillRepository, "list_by_order")
