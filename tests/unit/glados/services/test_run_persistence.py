"""
Tests for RunManager persistence wiring.

D-2 (TDD): RunManager persists run state transitions via RunRepository
and recovers active runs on startup.
Tests written BEFORE implementation — expect RED initially.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.glados.schemas import RunCreate, RunMode, RunStatus


# ============================================================================
# Helpers
# ============================================================================


def _make_run_create(**overrides) -> RunCreate:
    """Create a RunCreate request with defaults."""
    defaults = dict(
        strategy_id="sma",
        mode=RunMode.BACKTEST,
        symbols=["AAPL"],
        timeframe="1h",
    )
    defaults.update(overrides)
    return RunCreate(**defaults)


# ============================================================================
# Test: RunManager accepts RunRepository
# ============================================================================


class TestRunManagerRepositoryWiring:
    """RunManager can be created with an optional RunRepository."""

    def test_accepts_run_repository_parameter(self) -> None:
        """RunManager constructor accepts run_repository keyword."""
        from src.glados.services.run_manager import RunManager

        run_repository = MagicMock()
        manager = RunManager(run_repository=run_repository)
        assert manager is not None

    def test_run_repository_defaults_to_none(self) -> None:
        """RunManager works without run_repository (backward compatible)."""
        from src.glados.services.run_manager import RunManager

        manager = RunManager()
        assert manager is not None


# ============================================================================
# Test: RunManager persists on state transitions
# ============================================================================


class TestRunManagerPersistence:
    """RunManager saves run state on create/start/stop/complete/error."""

    @pytest.fixture
    def mock_run_repo(self) -> AsyncMock:
        """Create a mock RunRepository."""
        repo = AsyncMock()
        repo.save = AsyncMock()
        repo.get = AsyncMock(return_value=None)
        repo.list = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def manager(self, mock_run_repo) -> "RunManager":
        """Create RunManager with mock repository."""
        from src.glados.services.run_manager import RunManager

        return RunManager(
            event_log=AsyncMock(),
            run_repository=mock_run_repo,
        )

    @pytest.mark.asyncio
    async def test_create_persists_run(self, manager, mock_run_repo) -> None:
        """create() persists run record to repository."""
        request = _make_run_create()
        run = await manager.create(request)

        mock_run_repo.save.assert_awaited_once()
        saved_record = mock_run_repo.save.call_args[0][0]

        # Verify the saved record has correct fields
        from src.walle.models import RunRecord

        assert isinstance(saved_record, RunRecord)
        assert saved_record.id == run.id
        assert saved_record.strategy_id == "sma"
        assert saved_record.mode == "backtest"
        assert saved_record.status == "pending"

    @pytest.mark.asyncio
    async def test_stop_persists_status_change(self, manager, mock_run_repo) -> None:
        """stop() persists updated status to repository."""
        request = _make_run_create(mode=RunMode.PAPER)
        run = await manager.create(request)

        # Reset mock to only track stop's save call
        mock_run_repo.save.reset_mock()

        await manager.stop(run.id)

        mock_run_repo.save.assert_awaited_once()
        saved_record = mock_run_repo.save.call_args[0][0]
        assert saved_record.status == "stopped"

    @pytest.mark.asyncio
    async def test_create_without_repository_still_works(self) -> None:
        """create() works normally when no run_repository is configured."""
        from src.glados.services.run_manager import RunManager

        manager = RunManager()
        request = _make_run_create()
        run = await manager.create(request)

        assert run.id is not None
        assert run.status == RunStatus.PENDING

    @pytest.mark.asyncio
    async def test_start_persists_running_status(self, manager, mock_run_repo) -> None:
        """start() persists RUNNING transition before execution begins."""
        request = _make_run_create(mode=RunMode.PAPER)
        run = await manager.create(request)

        # Isolate start() persistence calls
        mock_run_repo.save.reset_mock()

        manager._start_live = AsyncMock(return_value=None)  # type: ignore[attr-defined]
        await manager.start(run.id)

        statuses = [
            call_args[0][0].status
            for call_args in mock_run_repo.save.await_args_list
        ]
        assert "running" in statuses

    @pytest.mark.asyncio
    async def test_backtest_completion_persists_completed_status(
        self, manager, mock_run_repo
    ) -> None:
        """start() persists COMPLETED transition after backtest finishes."""
        request = _make_run_create(
            mode=RunMode.BACKTEST,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        run = await manager.create(request)

        # Isolate start() persistence calls
        mock_run_repo.save.reset_mock()

        async def fake_start_backtest(run_obj) -> None:
            run_obj.status = RunStatus.COMPLETED

        manager._start_backtest = fake_start_backtest  # type: ignore[method-assign]
        await manager.start(run.id)

        statuses = [
            call_args[0][0].status
            for call_args in mock_run_repo.save.await_args_list
        ]
        assert "completed" in statuses

    @pytest.mark.asyncio
    async def test_start_failure_persists_error_status(self, manager, mock_run_repo) -> None:
        """start() persists ERROR transition when execution startup fails."""
        request = _make_run_create(mode=RunMode.PAPER)
        run = await manager.create(request)

        # Isolate start() persistence calls
        mock_run_repo.save.reset_mock()

        async def failing_start_live(run_obj) -> None:
            run_obj.status = RunStatus.ERROR
            raise RuntimeError("startup failed")

        manager._start_live = failing_start_live  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="startup failed"):
            await manager.start(run.id)

        statuses = [
            call_args[0][0].status
            for call_args in mock_run_repo.save.await_args_list
        ]
        assert "error" in statuses


# ============================================================================
# Test: RunManager recovery from database
# ============================================================================


class TestRunManagerRecovery:
    """RunManager can recover active runs from database on startup."""

    @pytest.fixture
    def mock_run_repo(self) -> AsyncMock:
        """Create a mock RunRepository."""
        repo = AsyncMock()
        repo.save = AsyncMock()
        repo.get = AsyncMock(return_value=None)
        repo.list = AsyncMock(return_value=[])
        return repo

    @pytest.mark.asyncio
    async def test_recover_loads_running_runs(self, mock_run_repo) -> None:
        """recover() loads runs with RUNNING status from repository."""
        from src.glados.services.run_manager import RunManager
        from src.walle.models import RunRecord

        # Simulate a running run in the database
        running_record = RunRecord(
            id="run-recovered-001",
            strategy_id="sma",
            mode="paper",
            status="running",
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
        )
        mock_run_repo.list.return_value = [running_record]

        manager = RunManager(
            event_log=AsyncMock(),
            run_repository=mock_run_repo,
        )

        count = await manager.recover()

        assert count == 1
        # The recovered run should be accessible
        run = await manager.get("run-recovered-001")
        assert run is not None
        assert run.strategy_id == "sma"

    @pytest.mark.asyncio
    async def test_recover_marks_stale_runs_as_error(self, mock_run_repo) -> None:
        """recover() marks previously-running runs as ERROR (unclean shutdown)."""
        from src.glados.services.run_manager import RunManager
        from src.walle.models import RunRecord

        stale_record = RunRecord(
            id="run-stale-001",
            strategy_id="sma",
            mode="paper",
            status="running",
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
        )
        mock_run_repo.list.return_value = [stale_record]

        manager = RunManager(
            event_log=AsyncMock(),
            run_repository=mock_run_repo,
        )

        await manager.recover()

        # Recovered run should be marked as ERROR (unclean shutdown)
        run = await manager.get("run-stale-001")
        assert run is not None
        assert run.status == RunStatus.ERROR

        # Should persist the error status
        mock_run_repo.save.assert_awaited()

    @pytest.mark.asyncio
    async def test_recover_loads_pending_runs(self, mock_run_repo) -> None:
        """recover() also loads pending runs (can be restarted)."""
        from src.glados.services.run_manager import RunManager
        from src.walle.models import RunRecord

        pending_record = RunRecord(
            id="run-pending-001",
            strategy_id="sma",
            mode="backtest",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        mock_run_repo.list.return_value = [pending_record]

        manager = RunManager(
            event_log=AsyncMock(),
            run_repository=mock_run_repo,
        )

        count = await manager.recover()

        assert count == 1
        run = await manager.get("run-pending-001")
        assert run is not None
        assert run.status == RunStatus.PENDING

    @pytest.mark.asyncio
    async def test_recover_noop_without_repository(self) -> None:
        """recover() returns 0 when no run_repository is configured."""
        from src.glados.services.run_manager import RunManager

        manager = RunManager()
        count = await manager.recover()
        assert count == 0

    @pytest.mark.asyncio
    async def test_recover_does_not_duplicate_existing_runs(
        self, mock_run_repo
    ) -> None:
        """recover() skips runs that are already in memory."""
        from src.glados.services.run_manager import RunManager
        from src.walle.models import RunRecord

        manager = RunManager(
            event_log=AsyncMock(),
            run_repository=mock_run_repo,
        )

        # Create a run first (in memory)
        request = _make_run_create()
        run = await manager.create(request)

        # Now simulate the same run in the database
        existing_record = RunRecord(
            id=run.id,
            strategy_id="sma",
            mode="backtest",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        mock_run_repo.list.return_value = [existing_record]

        count = await manager.recover()

        # Should not add duplicate
        assert count == 0
