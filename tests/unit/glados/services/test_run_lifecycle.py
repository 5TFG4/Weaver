"""
Tests for Run Lifecycle — M8-P1 Package A

TDD tests for:
- A.1: RunManager dependency validation (strategy_loader, bar_repository)
- A.2: Per-run cleanup guarantees (stop/complete/error paths)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.events.log import InMemoryEventLog
from src.glados.schemas import RunCreate, RunMode, RunStatus


# =============================================================================
# A.1: RunManager Dependency Validation
# =============================================================================


class TestRunManagerDependencyValidation:
    """A.1: start() must validate required dependencies before execution."""

    async def test_start_backtest_raises_without_strategy_loader(self) -> None:
        """Backtest start should raise RuntimeError if strategy_loader is None."""
        from src.glados.services.run_manager import RunManager

        event_log = InMemoryEventLog()
        run_manager = RunManager(
            event_log=event_log,
            bar_repository=MagicMock(),
            strategy_loader=None,  # Missing!
        )
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        )
        run = await run_manager.create(request)

        with pytest.raises(RuntimeError, match="StrategyLoader"):
            await run_manager.start(run.id)

    async def test_start_backtest_raises_without_bar_repository(self) -> None:
        """Backtest start should raise if bar_repository is None."""
        from src.glados.services.run_manager import RunManager

        event_log = InMemoryEventLog()
        run_manager = RunManager(
            event_log=event_log,
            bar_repository=None,  # Missing!
            strategy_loader=MagicMock(),
        )
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        )
        run = await run_manager.create(request)

        with pytest.raises(RuntimeError, match="BarRepository"):
            await run_manager.start(run.id)

    async def test_start_live_raises_without_strategy_loader(self) -> None:
        """Live start should raise RuntimeError if strategy_loader is None."""
        from src.glados.services.run_manager import RunManager

        event_log = InMemoryEventLog()
        run_manager = RunManager(
            event_log=event_log,
            strategy_loader=None,  # Missing!
        )
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.LIVE,
            symbols=["AAPL"],
        )
        run = await run_manager.create(request)

        with pytest.raises(RuntimeError, match="StrategyLoader"):
            await run_manager.start(run.id)

    async def test_start_backtest_succeeds_with_all_dependencies(self) -> None:
        """Backtest should succeed when all deps provided."""
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        )
        run = await run_manager.create(request)

        result = await run_manager.start(run.id)

        assert result.status == RunStatus.COMPLETED

    async def test_start_live_succeeds_with_all_dependencies(self) -> None:
        """Live start should proceed when strategy_loader provided."""
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.LIVE,
            symbols=["AAPL"],
        )
        run = await run_manager.create(request)

        result = await run_manager.start(run.id)

        assert result.status == RunStatus.RUNNING

        # Cleanup
        await run_manager.stop(run.id)


# =============================================================================
# A.2: Per-Run Cleanup Guarantees
# =============================================================================


class TestPerRunCleanup:
    """A.2: Cleanup must happen on stop, complete, and error paths."""

    async def test_stop_cleans_up_clock_and_context(self) -> None:
        """stop() should stop clock and remove RunContext."""
        from tests.factories.runs import create_run_manager_with_deps

        run_manager = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["AAPL"],
        )
        run = await run_manager.create(request)
        await run_manager.start(run.id)

        # Verify context exists before stop
        assert run.id in run_manager._run_contexts

        await run_manager.stop(run.id)

        # Context should be removed after stop
        assert run.id not in run_manager._run_contexts

    async def test_backtest_completion_cleans_up_context(self) -> None:
        """Completed backtest should automatically clean up RunContext."""
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        )
        run = await run_manager.create(request)

        await run_manager.start(run.id)

        # After backtest completes, context should be cleaned up
        assert run.id not in run_manager._run_contexts
        assert run.status == RunStatus.COMPLETED

    async def test_backtest_error_during_init_cleans_up_context(self) -> None:
        """If GretaService init errors, RunContext should still be cleaned up."""
        from src.glados.services.run_manager import RunManager

        strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        # Strategy initialize raises (simulates bad config / missing data)
        mock_strategy.initialize = AsyncMock(
            side_effect=RuntimeError("GretaService: no bars found for AAPL")
        )
        strategy_loader.load = MagicMock(return_value=mock_strategy)

        bar_repository = MagicMock()
        bar_repository.get_bars = AsyncMock(return_value=[])

        event_log = InMemoryEventLog()
        run_manager = RunManager(
            event_log=event_log,
            bar_repository=bar_repository,
            strategy_loader=strategy_loader,
        )
        request = RunCreate(
            strategy_id="buggy_strategy",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
        )
        run = await run_manager.create(request)

        with pytest.raises(RuntimeError, match="no bars found"):
            await run_manager.start(run.id)

        # Context MUST be cleaned up even on error
        assert run.id not in run_manager._run_contexts
        assert run.status == RunStatus.ERROR
        assert run.stopped_at is not None

    async def test_live_error_cleans_up_context(self) -> None:
        """If live start errors, RunContext should be cleaned up."""
        from src.glados.services.run_manager import RunManager

        strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock(side_effect=RuntimeError("connection failed"))
        strategy_loader.load = MagicMock(return_value=mock_strategy)

        run_manager = RunManager(
            event_log=InMemoryEventLog(),
            strategy_loader=strategy_loader,
        )
        request = RunCreate(
            strategy_id="test",
            mode=RunMode.LIVE,
            symbols=["AAPL"],
        )
        run = await run_manager.create(request)

        with pytest.raises(RuntimeError, match="connection failed"):
            await run_manager.start(run.id)

        assert run.id not in run_manager._run_contexts
        assert run.status == RunStatus.ERROR

    async def test_stop_emits_event_and_sets_timestamp(self) -> None:
        """stop() should emit Stopped event and set stopped_at."""
        from src.events.types import RunEvents
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)
        request = RunCreate(
            strategy_id="test",
            mode=RunMode.PAPER,
            symbols=["AAPL"],
        )
        run = await run_manager.create(request)
        await run_manager.start(run.id)

        await run_manager.stop(run.id)

        assert run.stopped_at is not None
        events = event_log.events
        stopped_events = [e for e in events if e.type == RunEvents.STOPPED]
        assert len(stopped_events) == 1

    async def test_backtest_completion_emits_completed_event(self) -> None:
        """Backtest should emit run.Completed on success."""
        from src.events.types import RunEvents
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        run_manager = create_run_manager_with_deps(event_log=event_log)
        request = RunCreate(
            strategy_id="sma_cross",
            mode=RunMode.BACKTEST,
            symbols=["AAPL"],
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-06-30T00:00:00Z",
        )
        run = await run_manager.create(request)

        await run_manager.start(run.id)

        events = event_log.events
        completed_events = [e for e in events if e.type == RunEvents.COMPLETED]
        assert len(completed_events) == 1
        assert completed_events[0].payload["run_id"] == run.id
        assert completed_events[0].payload["status"] == "completed"
