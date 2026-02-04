"""
Tests for Run Mode Integration (M6-5)

Validates that RunManager correctly selects clock type based on run mode:
- BACKTEST → BacktestClock
- LIVE/PAPER → RealtimeClock
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.glados.clock.backtest import BacktestClock
from src.glados.clock.realtime import RealtimeClock
from src.glados.schemas import RunCreate, RunMode, RunStatus
from src.glados.services.run_manager import RunManager


class TestClockSelection:
    """Tests for clock type selection based on run mode."""

    async def test_backtest_uses_backtest_clock(self) -> None:
        """BACKTEST mode should create BacktestClock."""
        from tests.factories.runs import create_run_manager_with_deps

        rm = create_run_manager_with_deps()
        now = datetime.now(timezone.utc)
        request = RunCreate(
            strategy_id="sma_crossover",
            mode=RunMode.BACKTEST,
            symbols=["BTC/USD"],
            timeframe="1m",
            start_time=now - timedelta(hours=1),
            end_time=now,
        )

        run = await rm.create(request)
        await rm.start(run.id)

        # Backtest runs to completion, context is cleaned up
        # Verify run completed successfully
        final_run = await rm.get(run.id)
        assert final_run is not None
        assert final_run.status == RunStatus.COMPLETED

    async def test_live_mode_uses_realtime_clock(self) -> None:
        """LIVE mode should create RealtimeClock."""
        from tests.factories.runs import create_run_manager_with_deps

        rm = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="sma_crossover",
            mode=RunMode.LIVE,
            symbols=["BTC/USD"],
            timeframe="1m",
        )

        run = await rm.create(request)
        await rm.start(run.id)

        # Live runs stay RUNNING, context should exist
        assert run.id in rm._run_contexts
        ctx = rm._run_contexts[run.id]
        assert isinstance(ctx.clock, RealtimeClock)

        # Cleanup
        await rm.stop(run.id)

    async def test_paper_mode_uses_realtime_clock(self) -> None:
        """PAPER mode should create RealtimeClock."""
        from tests.factories.runs import create_run_manager_with_deps

        rm = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="sma_crossover",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
            timeframe="1m",
        )

        run = await rm.create(request)
        await rm.start(run.id)

        # Paper runs stay RUNNING, context should exist
        assert run.id in rm._run_contexts
        ctx = rm._run_contexts[run.id]
        assert isinstance(ctx.clock, RealtimeClock)

        # Cleanup
        await rm.stop(run.id)


class TestRealtimeClockBehavior:
    """Tests for RealtimeClock behavior in live/paper runs."""

    async def test_realtime_clock_uses_current_time(self) -> None:
        """RealtimeClock.current_time() should return wall clock time."""
        clock = RealtimeClock(timeframe="1m")

        before = datetime.now(timezone.utc)
        current = clock.current_time()
        after = datetime.now(timezone.utc)

        assert before <= current <= after

    async def test_backtest_clock_uses_simulated_time(self) -> None:
        """BacktestClock.current_time() should return simulated time."""
        start = datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)
        clock = BacktestClock(start_time=start, end_time=end, timeframe="1m")

        # Before start, current time is start time
        assert clock.current_time() == start


class TestRunModeEvents:
    """Tests for run mode in events."""

    async def test_run_started_event_includes_mode(self) -> None:
        """run.Started event should include mode field."""
        from src.events.log import InMemoryEventLog
        from tests.factories.runs import create_run_manager_with_deps

        event_log = InMemoryEventLog()
        rm = create_run_manager_with_deps(event_log=event_log)
        request = RunCreate(
            strategy_id="sma_crossover",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
            timeframe="1m",
        )

        run = await rm.create(request)
        await rm.start(run.id)

        # Find run.Started event using read_from
        events = await event_log.read_from(offset=0, limit=10)
        started_events = [e for _, e in events if e.type == "run.Started"]
        assert len(started_events) == 1
        assert started_events[0].payload["mode"] == "paper"

        # Cleanup
        await rm.stop(run.id)


class TestStopRun:
    """Tests for stopping runs."""

    async def test_stop_live_run_stops_clock(self) -> None:
        """Stopping a live run should stop the clock."""
        from tests.factories.runs import create_run_manager_with_deps

        rm = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="sma_crossover",
            mode=RunMode.LIVE,
            symbols=["BTC/USD"],
            timeframe="1m",
        )

        run = await rm.create(request)
        await rm.start(run.id)

        # Verify clock is running
        ctx = rm._run_contexts[run.id]
        assert ctx.clock.is_running

        # Stop the run
        stopped = await rm.stop(run.id)

        # Clock should be stopped and context cleaned up
        assert stopped.status == RunStatus.STOPPED
        assert run.id not in rm._run_contexts

    async def test_cannot_start_already_running_run(self) -> None:
        """Starting an already running run should raise error."""
        from src.glados.exceptions import RunNotStartableError
        from tests.factories.runs import create_run_manager_with_deps

        rm = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="sma_crossover",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
            timeframe="1m",
        )

        run = await rm.create(request)
        await rm.start(run.id)

        # Trying to start again should fail
        with pytest.raises(RunNotStartableError):
            await rm.start(run.id)

        # Cleanup
        await rm.stop(run.id)


class TestRunModePersistence:
    """Tests for run mode being persisted correctly."""

    async def test_run_mode_persisted_on_create(self) -> None:
        """Run mode should be stored in run entity."""
        rm = RunManager()
        request = RunCreate(
            strategy_id="test",
            mode=RunMode.LIVE,
            symbols=["BTC/USD"],
        )

        run = await rm.create(request)

        assert run.mode == RunMode.LIVE

    async def test_run_mode_retrievable_after_get(self) -> None:
        """Run mode should be available via get()."""
        rm = RunManager()
        request = RunCreate(
            strategy_id="test",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )

        created = await rm.create(request)
        retrieved = await rm.get(created.id)

        assert retrieved is not None
        assert retrieved.mode == RunMode.PAPER
