"""
Tests for RunRecord model and RunRepository.

D-2: Runs table + repository for restart recovery.
"""

from datetime import datetime, timezone
from typing import Any, cast

import pytest
from sqlalchemy import Table, inspect

from src.walle.models import Base, RunRecord


# ============================================================================
# Test: RunRecord Model Structure
# ============================================================================


class TestRunRecordModel:
    """RunRecord SQLAlchemy model has correct schema."""

    def test_tablename_is_runs(self) -> None:
        """RunRecord maps to 'runs' table."""
        assert RunRecord.__tablename__ == "runs"

    def test_has_required_columns(self) -> None:
        """RunRecord has all required columns."""
        mapper = inspect(RunRecord)
        column_names = {c.key for c in mapper.columns}

        expected = {
            "id",
            "strategy_id",
            "mode",
            "status",
            "symbols",
            "timeframe",
            "config",
            "error",
            "created_at",
            "started_at",
            "stopped_at",
        }
        assert expected.issubset(column_names)

    def test_id_is_primary_key(self) -> None:
        """id column is the primary key."""
        mapper = inspect(RunRecord)
        pk_columns = [c.key for c in mapper.primary_key]
        assert pk_columns == ["id"]

    def test_status_is_indexed(self) -> None:
        """status column is indexed for filtering."""
        table = cast(Table, RunRecord.__table__)
        status_indexed = any(
            "status" in list(idx.columns.keys()) for idx in table.indexes
        )
        assert status_indexed

    def test_repr(self) -> None:
        """__repr__ returns readable string."""
        record = RunRecord(
            id="run-001",
            strategy_id="sma",
            mode="backtest",
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        repr_str = repr(record)
        assert "RunRecord" in repr_str
        assert "run-001" in repr_str

    def test_registered_in_metadata(self) -> None:
        """runs table is registered in Base.metadata."""
        assert "runs" in Base.metadata.tables


# ============================================================================
# Test: RunRepository Class
# ============================================================================


class TestRunRepositoryInterface:
    """RunRepository has the expected CRUD interface."""

    def test_repository_class_exists(self) -> None:
        """RunRepository is importable."""
        from src.walle.repositories.run_repository import RunRepository

        assert RunRepository is not None

    def test_repository_accepts_session_factory(self) -> None:
        """RunRepository constructor takes a session_factory."""
        from unittest.mock import MagicMock

        from src.walle.repositories.run_repository import RunRepository

        mock_factory = MagicMock()
        repo = RunRepository(session_factory=mock_factory)
        assert repo is not None

    def test_repository_has_save_method(self) -> None:
        """RunRepository has an async save() method."""
        from src.walle.repositories.run_repository import RunRepository

        assert hasattr(RunRepository, "save")
        assert callable(getattr(RunRepository, "save"))

    def test_repository_has_get_method(self) -> None:
        """RunRepository has an async get() method."""
        from src.walle.repositories.run_repository import RunRepository

        assert hasattr(RunRepository, "get")
        assert callable(getattr(RunRepository, "get"))

    def test_repository_has_list_method(self) -> None:
        """RunRepository has an async list() method."""
        from src.walle.repositories.run_repository import RunRepository

        assert hasattr(RunRepository, "list")
        assert callable(getattr(RunRepository, "list"))
