"""
Tests for RunManager backtest orchestration (M4)

Unit tests for backtest flow orchestration in RunManager.
"""

import asyncio
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.glados.exceptions import RunNotStartableError
from src.glados.schemas import RunCreate, RunMode, RunStatus
from src.glados.services.run_manager import RunContext, RunManager


class TestRunContext:
    """Tests for RunContext dataclass."""

    def test_creates_with_all_components(self) -> None:
        """RunContext holds all per-run components."""
        mock_greta = MagicMock()
        mock_runner = MagicMock()
        mock_clock = MagicMock()

        ctx = RunContext(
            greta=mock_greta,
            runner=mock_runner,
            clock=mock_clock,
        )

        assert ctx.greta is mock_greta
        assert ctx.runner is mock_runner
        assert ctx.clock is mock_clock

    def test_greta_can_be_none_for_live(self) -> None:
        """RunContext allows None greta for live runs."""
        mock_runner = MagicMock()
        mock_clock = MagicMock()

        ctx = RunContext(
            greta=None,
            runner=mock_runner,
            clock=mock_clock,
        )

        assert ctx.greta is None

    def test_pending_tasks_defaults_to_empty_set(self) -> None:
        """RunContext.pending_tasks defaults to an empty set."""
        ctx = RunContext(
            greta=None,
            runner=MagicMock(),
            clock=MagicMock(),
        )

        assert ctx.pending_tasks == set()
        assert isinstance(ctx.pending_tasks, set)


class TestRunManagerBacktestStart:
    """Tests for RunManager.start() with backtest mode."""

    @pytest_asyncio.fixture
    async def manager_with_deps(self) -> RunManager:
        """Create manager with mocked dependencies for backtest."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])

        mock_strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock()
        mock_strategy.on_tick = AsyncMock(return_value=[])
        mock_strategy_loader.load = MagicMock(return_value=mock_strategy)
        mock_strategy_loader.get_meta = MagicMock(return_value=None)

        return RunManager(
            event_log=mock_event_log,
            bar_repository=mock_bar_repo,
            strategy_loader=mock_strategy_loader,
        )

    async def test_start_backtest_creates_run_context(self, manager_with_deps: RunManager) -> None:
        """start() creates RunContext for backtest runs and cleans up after completion."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        # After backtest completes, context should be cleaned up
        assert run.id not in manager_with_deps._run_contexts
        # Run should be marked completed
        assert run.status == RunStatus.COMPLETED

    async def test_start_backtest_initializes_greta(self, manager_with_deps: RunManager) -> None:
        """start() initializes GretaService with run params."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        # Verify run completed successfully (implies Greta was initialized)
        assert run.status == RunStatus.COMPLETED
        # Verify bar_repository was used (Greta calls it during initialize)
        bar_repo = cast(AsyncMock, manager_with_deps._bar_repository)
        bar_repo.get_bars.assert_called()

    async def test_start_backtest_initializes_runner(self, manager_with_deps: RunManager) -> None:
        """start() initializes StrategyRunner with run params."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        # Verify strategy was loaded and initialized (implies runner was created)
        strategy_loader = cast(MagicMock, manager_with_deps._strategy_loader)
        strategy_loader.load.assert_called_once_with("test-strategy")

        # Verify strategy.initialize was called with correct params
        mock_strategy = strategy_loader.load.return_value
        mock_strategy.initialize.assert_called_once_with(
            {
                "symbols": ["BTC/USD"],
                "timeframe": "1m",
                "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
            }
        )

    async def test_start_backtest_loads_strategy(self, manager_with_deps: RunManager) -> None:
        """start() loads strategy from loader."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        cast(MagicMock, manager_with_deps._strategy_loader).load.assert_called_once_with(
            "test-strategy"
        )

    async def test_start_backtest_runs_to_completion(self, manager_with_deps: RunManager) -> None:
        """start() for backtest runs clock to completion."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        result = await manager_with_deps.start(run.id)

        # Backtest should complete synchronously
        assert result.status == RunStatus.COMPLETED

    async def test_start_backtest_emits_completed_event(
        self, manager_with_deps: RunManager
    ) -> None:
        """start() emits run.Completed event when backtest finishes."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        # Check for COMPLETED event
        event_log = cast(AsyncMock, manager_with_deps._event_log)
        calls = event_log.append.call_args_list
        event_types = [c[0][0].type for c in calls]
        assert "run.Completed" in event_types


class TestRunManagerStopWithContext:
    """Tests for RunManager.stop() cleanup of RunContext."""

    @pytest_asyncio.fixture
    async def manager_with_running_run(self) -> tuple[RunManager, str]:
        """Create manager with a running backtest."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()
        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])
        mock_strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock()
        mock_strategy.on_tick = AsyncMock(return_value=[])
        mock_strategy_loader.load = MagicMock(return_value=mock_strategy)
        mock_strategy_loader.get_meta = MagicMock(return_value=None)

        manager = RunManager(
            event_log=mock_event_log,
            bar_repository=mock_bar_repo,
            strategy_loader=mock_strategy_loader,
        )

        # Create and mock a "running" state (bypassing actual start)
        run = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 2, tzinfo=UTC).isoformat(),
                },
            )
        )
        run.status = RunStatus.RUNNING

        # Manually add context
        mock_ctx = MagicMock()
        mock_ctx.clock = AsyncMock()
        mock_ctx.clock.stop = AsyncMock()
        mock_ctx.runner = AsyncMock()
        mock_ctx.runner.cleanup = AsyncMock()
        mock_ctx.greta = AsyncMock()
        mock_ctx.greta.cleanup = AsyncMock()
        mock_ctx.pending_tasks = set()
        manager._run_contexts[run.id] = mock_ctx

        return manager, run.id

    async def test_stop_cleans_up_context(
        self, manager_with_running_run: tuple[RunManager, str]
    ) -> None:
        """stop() removes RunContext from manager."""
        manager, run_id = manager_with_running_run

        await manager.stop(run_id)

        assert run_id not in manager._run_contexts

    async def test_stop_stops_clock(self, manager_with_running_run: tuple[RunManager, str]) -> None:
        """stop() calls clock.stop() before cleanup."""
        manager, run_id = manager_with_running_run
        ctx = manager._run_contexts[run_id]

        await manager.stop(run_id)

        cast(AsyncMock, ctx.clock.stop).assert_called_once()

    async def test_stop_cleans_runner_subscriptions(
        self, manager_with_running_run: tuple[RunManager, str]
    ) -> None:
        """stop() calls StrategyRunner.cleanup() as explicit contract."""
        manager, run_id = manager_with_running_run
        ctx = manager._run_contexts[run_id]

        await manager.stop(run_id)

        cast(AsyncMock, ctx.runner.cleanup).assert_called_once()

    async def test_stop_cleans_greta_subscriptions(
        self, manager_with_running_run: tuple[RunManager, str]
    ) -> None:
        """stop() calls GretaService.cleanup() for backtest contexts."""
        manager, run_id = manager_with_running_run
        ctx = manager._run_contexts[run_id]

        await manager.stop(run_id)

        cast(AsyncMock, ctx.greta.cleanup).assert_called_once()


class TestCleanupRunContextDrain:
    """Tests for pending task drain in _cleanup_run_context (M11-1)."""

    async def test_cleanup_awaits_pending_tasks_before_unsubscribe(self) -> None:
        """_cleanup_run_context waits for pending tasks before calling cleanup."""
        manager = RunManager()

        execution_order: list[str] = []

        async def slow_task() -> None:
            await asyncio.sleep(0.05)
            execution_order.append("task_done")

        mock_runner = AsyncMock()
        mock_runner.cleanup = AsyncMock(
            side_effect=lambda: execution_order.append("runner_cleanup")
        )
        mock_clock = AsyncMock()
        mock_clock.stop = AsyncMock()

        ctx = RunContext(greta=None, runner=mock_runner, clock=mock_clock)

        # Simulate a pending task (with discard callback, matching spawn_tracked_task)
        task = asyncio.create_task(slow_task())
        ctx.pending_tasks.add(task)
        task.add_done_callback(ctx.pending_tasks.discard)

        run_id = "test-drain"
        manager._run_contexts[run_id] = ctx

        await manager._cleanup_run_context(run_id)

        # Task should finish BEFORE runner.cleanup
        assert execution_order == ["task_done", "runner_cleanup"]
        assert run_id not in manager._run_contexts

    async def test_cleanup_handles_failed_pending_tasks(self) -> None:
        """_cleanup_run_context still cleans up even if a pending task fails."""
        manager = RunManager()

        async def failing_task() -> None:
            raise ValueError("task error")

        mock_runner = AsyncMock()
        mock_runner.cleanup = AsyncMock()
        mock_clock = AsyncMock()
        mock_clock.stop = AsyncMock()

        ctx = RunContext(greta=None, runner=mock_runner, clock=mock_clock)
        task = asyncio.create_task(failing_task())
        ctx.pending_tasks.add(task)
        task.add_done_callback(ctx.pending_tasks.discard)

        run_id = "test-fail"
        manager._run_contexts[run_id] = ctx

        # Should not raise — return_exceptions=True
        await manager._cleanup_run_context(run_id)

        # Cleanup still happens
        mock_runner.cleanup.assert_called_once()
        assert run_id not in manager._run_contexts

    async def test_cleanup_with_empty_pending_tasks(self) -> None:
        """_cleanup_run_context works fine with no pending tasks."""
        manager = RunManager()

        mock_runner = AsyncMock()
        mock_runner.cleanup = AsyncMock()
        mock_clock = AsyncMock()
        mock_clock.stop = AsyncMock()

        ctx = RunContext(greta=None, runner=mock_runner, clock=mock_clock)
        run_id = "test-empty"
        manager._run_contexts[run_id] = ctx

        await manager._cleanup_run_context(run_id)

        mock_runner.cleanup.assert_called_once()
        assert run_id not in manager._run_contexts

    async def test_drain_handles_multi_level_task_chains(self) -> None:
        """Drain loops until all child tasks spawned by parent tasks complete.

        Simulates the real E2E chain:
          TASK A (fetch_window) → spawns TASK B (on_data_ready)
          TASK B → spawns TASK C (handle_place_order)
          TASK C → writes result (no further tasks)
        """
        manager = RunManager()

        results: list[str] = []

        mock_runner = AsyncMock()
        mock_runner.cleanup = AsyncMock()
        mock_clock = AsyncMock()
        mock_clock.stop = AsyncMock()

        ctx = RunContext(greta=None, runner=mock_runner, clock=mock_clock)
        run_id = "test-deep-drain"
        manager._run_contexts[run_id] = ctx

        task_set = ctx.pending_tasks

        async def task_c() -> None:
            results.append("C")

        async def task_b() -> None:
            results.append("B")
            # Spawn child task (like handle_place_order)
            t = asyncio.create_task(task_c())
            task_set.add(t)
            t.add_done_callback(task_set.discard)

        async def task_a() -> None:
            results.append("A")
            # Spawn child task (like on_data_ready)
            t = asyncio.create_task(task_b())
            task_set.add(t)
            t.add_done_callback(task_set.discard)

        # Only level-1 task is pending initially
        t_a = asyncio.create_task(task_a())
        task_set.add(t_a)
        t_a.add_done_callback(task_set.discard)

        await manager._cleanup_run_context(run_id)

        # All three levels should have completed
        assert results == ["A", "B", "C"]


# =============================================================================
# M11-2: Strategy Runtime Error Propagation tests
# =============================================================================


class TestBacktestErrorPropagation:
    """Tests for M11-2: strategy errors → RunStatus.ERROR + run.Error event."""

    @pytest_asyncio.fixture
    async def manager_with_deps(self) -> RunManager:
        """Create manager with mocked dependencies for error testing."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()

        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])

        mock_strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock()
        mock_strategy.on_tick = AsyncMock(return_value=[])
        mock_strategy_loader.load = MagicMock(return_value=mock_strategy)
        mock_strategy_loader.get_meta = MagicMock(return_value=None)

        return RunManager(
            event_log=mock_event_log,
            bar_repository=mock_bar_repo,
            strategy_loader=mock_strategy_loader,
        )

    async def test_strategy_on_tick_error_stops_run(self, manager_with_deps: RunManager) -> None:
        """Exception in on_tick callback → run.status = ERROR."""
        strategy_loader = cast(MagicMock, manager_with_deps._strategy_loader)
        mock_strategy = strategy_loader.load.return_value
        mock_strategy.on_tick = AsyncMock(side_effect=RuntimeError("strategy exploded"))

        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="bad-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 32, tzinfo=UTC).isoformat(),
                },
            )
        )

        result = await manager_with_deps.start(run.id)
        assert result.status == RunStatus.ERROR

    async def test_strategy_on_data_error_detected_in_drain(self) -> None:
        """Failing spawned task detected during drain → ERROR status."""
        mock_event_log = AsyncMock()
        mock_event_log.append = AsyncMock()
        mock_bar_repo = AsyncMock()
        mock_bar_repo.get_bars = AsyncMock(return_value=[])
        mock_strategy_loader = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.initialize = AsyncMock()
        mock_strategy.on_tick = AsyncMock(return_value=[])
        mock_strategy_loader.load = MagicMock(return_value=mock_strategy)
        mock_strategy_loader.get_meta = MagicMock(return_value=None)

        manager = RunManager(
            event_log=mock_event_log,
            bar_repository=mock_bar_repo,
            strategy_loader=mock_strategy_loader,
        )

        run = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
            )
        )

        run_obj = manager._runs[run.id]
        run_obj.status = RunStatus.RUNNING

        async def failing_task() -> None:
            raise ValueError("async data error")

        from src.glados.clock.backtest import BacktestClock

        clock = BacktestClock(
            start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            end_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
        )
        mock_runner = AsyncMock()
        mock_runner.cleanup = AsyncMock()
        mock_greta = AsyncMock()
        mock_greta.cleanup = AsyncMock()

        ctx = RunContext(greta=mock_greta, runner=mock_runner, clock=clock)
        failing = asyncio.create_task(failing_task())
        ctx.pending_tasks.add(failing)
        manager._run_contexts[run.id] = ctx

        # Run clock to completion
        await clock.start(run.id)
        await clock.wait()

        # Drain pending tasks (same logic as _start_backtest)
        drain_errors: list[BaseException] = []
        if ctx.pending_tasks:
            results = await asyncio.gather(*ctx.pending_tasks, return_exceptions=True)
            drain_errors = [r for r in results if isinstance(r, BaseException)]

        clock_error = clock.error
        if clock_error is not None or drain_errors:
            run_obj.status = RunStatus.ERROR

        assert run_obj.status == RunStatus.ERROR
        assert len(drain_errors) == 1
        assert "async data error" in str(drain_errors[0])

        await manager._cleanup_run_context(run.id)

    async def test_error_run_emits_run_error_event(self, manager_with_deps: RunManager) -> None:
        """Error run emits run.Error event."""
        strategy_loader = cast(MagicMock, manager_with_deps._strategy_loader)
        mock_strategy = strategy_loader.load.return_value
        mock_strategy.on_tick = AsyncMock(side_effect=RuntimeError("tick boom"))

        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="bad-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 32, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        event_log = cast(AsyncMock, manager_with_deps._event_log)
        calls = event_log.append.call_args_list
        event_types = [c[0][0].type for c in calls]
        assert "run.Error" in event_types

    async def test_error_run_cleanup_completes(self, manager_with_deps: RunManager) -> None:
        """Error path still runs full cleanup (clock stop + unsubscribe)."""
        strategy_loader = cast(MagicMock, manager_with_deps._strategy_loader)
        mock_strategy = strategy_loader.load.return_value
        mock_strategy.on_tick = AsyncMock(side_effect=RuntimeError("cleanup test"))

        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="bad-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 32, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager_with_deps.start(run.id)

        assert run.id not in manager_with_deps._run_contexts
        assert run.status == RunStatus.ERROR
        assert run.stopped_at is not None

    async def test_clock_error_partial_ticks_still_error(
        self, manager_with_deps: RunManager
    ) -> None:
        """Clock._error from a later tick → still RunStatus.ERROR."""
        strategy_loader = cast(MagicMock, manager_with_deps._strategy_loader)
        mock_strategy = strategy_loader.load.return_value
        call_count = 0

        async def on_tick_fail_second(tick):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise RuntimeError("second tick fail")
            return []

        mock_strategy.on_tick = on_tick_fail_second

        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="bad-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 35, tzinfo=UTC).isoformat(),
                },
            )
        )

        result = await manager_with_deps.start(run.id)
        assert result.status == RunStatus.ERROR

    async def test_successful_run_has_no_error_event(self, manager_with_deps: RunManager) -> None:
        """Successful backtest does not emit run.Error event."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="good-strategy",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 32, tzinfo=UTC).isoformat(),
                },
            )
        )

        result = await manager_with_deps.start(run.id)
        assert result.status == RunStatus.COMPLETED

        event_log = cast(AsyncMock, manager_with_deps._event_log)
        calls = event_log.append.call_args_list
        event_types = [c[0][0].type for c in calls]
        assert "run.Error" not in event_types
        assert "run.Completed" in event_types


# =============================================================================
# M11-3: Concurrent Run Operation Safety tests
# =============================================================================


def _make_manager_with_deps() -> RunManager:
    """Helper: create RunManager with full mocked deps."""
    mock_event_log = AsyncMock()
    mock_event_log.append = AsyncMock()
    mock_bar_repo = AsyncMock()
    mock_bar_repo.get_bars = AsyncMock(return_value=[])
    mock_strategy_loader = MagicMock()
    mock_strategy = MagicMock()
    mock_strategy.initialize = AsyncMock()
    mock_strategy.on_tick = AsyncMock(return_value=[])
    mock_strategy_loader.load = MagicMock(return_value=mock_strategy)
    mock_strategy_loader.get_meta = MagicMock(return_value=None)
    return RunManager(
        event_log=mock_event_log,
        bar_repository=mock_bar_repo,
        strategy_loader=mock_strategy_loader,
    )


class TestConcurrentRunSafety:
    """Tests for M11-3: per-run asyncio.Lock prevents race conditions."""

    async def test_get_run_lock_returns_same_lock_for_same_id(self) -> None:
        """_get_run_lock returns the same Lock for the same run_id."""
        manager = RunManager()
        lock_a = manager._get_run_lock("run-1")
        lock_b = manager._get_run_lock("run-1")
        assert lock_a is lock_b

    async def test_get_run_lock_returns_different_locks_for_different_ids(self) -> None:
        """_get_run_lock returns distinct Locks for different run_ids."""
        manager = RunManager()
        lock_1 = manager._get_run_lock("run-1")
        lock_2 = manager._get_run_lock("run-2")
        assert lock_1 is not lock_2

    async def test_concurrent_start_same_run_only_one_succeeds(self) -> None:
        """Two concurrent start() calls for the same run → only one succeeds."""
        manager = _make_manager_with_deps()
        run = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
            )
        )

        results = await asyncio.gather(
            manager.start(run.id),
            manager.start(run.id),
            return_exceptions=True,
        )

        # One should succeed (COMPLETED), the other should raise RunNotStartableError
        statuses = [r.status for r in results if not isinstance(r, BaseException)]
        errors = [r for r in results if isinstance(r, BaseException)]

        assert len(statuses) == 1
        assert statuses[0] in (RunStatus.COMPLETED, RunStatus.ERROR)
        assert len(errors) == 1
        assert isinstance(errors[0], RunNotStartableError)

    async def test_concurrent_start_different_runs_both_succeed(self) -> None:
        """Two concurrent start() calls for different runs → both succeed."""
        manager = _make_manager_with_deps()
        run_a = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
            )
        )
        run_b = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["ETH/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
            )
        )

        results = await asyncio.gather(
            manager.start(run_a.id),
            manager.start(run_b.id),
        )

        assert results[0].status == RunStatus.COMPLETED
        assert results[1].status == RunStatus.COMPLETED

    async def test_stop_during_start_waits_for_lock(self) -> None:
        """stop() blocks until start() releases the lock, then runs cleanly."""
        manager = _make_manager_with_deps()

        # Make strategy slow so start holds the lock for a while
        strategy_loader = cast(MagicMock, manager._strategy_loader)
        mock_strategy = strategy_loader.load.return_value

        start_entered = asyncio.Event()

        async def slow_tick(tick):  # type: ignore[no-untyped-def]
            start_entered.set()
            await asyncio.sleep(0.1)
            return []

        mock_strategy.on_tick = slow_tick

        run = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 31, tzinfo=UTC).isoformat(),
                },
            )
        )

        stop_order: list[str] = []

        async def do_start() -> None:
            await manager.start(run.id)
            stop_order.append("start_done")

        async def do_stop() -> None:
            await start_entered.wait()
            await manager.stop(run.id)
            stop_order.append("stop_done")

        await asyncio.gather(do_start(), do_stop())

        # start completes before stop can acquire the lock
        assert stop_order[0] == "start_done"

    async def test_double_stop_is_idempotent(self) -> None:
        """Two stop() calls for same run → no error, second is no-op."""
        manager = _make_manager_with_deps()
        run = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
            )
        )
        await manager.start(run.id)

        # Double stop — should not raise
        await manager.stop(run.id)
        await manager.stop(run.id)

        assert run.status == RunStatus.STOPPED

    async def test_run_lock_cleaned_up_after_run(self) -> None:
        """Lock dict doesn't leak entries after run completes."""
        manager = _make_manager_with_deps()
        run = await manager.create(
            RunCreate(
                strategy_id="test",
                mode=RunMode.BACKTEST,
                config={
                    "symbols": ["BTC/USD"],
                    "timeframe": "1m",
                    "backtest_start": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                    "backtest_end": datetime(2024, 1, 1, 9, 30, tzinfo=UTC).isoformat(),
                },
            )
        )

        await manager.start(run.id)

        # After backtest completes, lock should be cleaned up
        assert run.id not in manager._run_locks

    async def test_run_lock_exists_during_init(self) -> None:
        """_run_locks dict is initialized as empty."""
        manager = RunManager()
        assert hasattr(manager, "_run_locks")
        assert manager._run_locks == {}


class TestBacktestConfigSource:
    """S9: Backtest reads config keys backtest_start/backtest_end from run.config."""

    async def test_backtest_reads_config_keys(self) -> None:
        """_start_backtest uses backtest_start/backtest_end/timeframe from config."""
        from tests.factories.runs import create_run_manager_with_deps

        manager = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="sample",
            mode=RunMode.BACKTEST,
            config={
                "symbols": ["BTC/USD"],
                "timeframe": "5m",
                "backtest_start": "2024-01-01T09:30:00+00:00",
                "backtest_end": "2024-01-01T10:30:00+00:00",
            },
        )
        run = await manager.create(request)
        result = await manager.start(run.id)
        assert result.status == RunStatus.COMPLETED

    async def test_backtest_rejects_missing_backtest_start(self) -> None:
        """_start_backtest raises when config lacks backtest_start."""
        from tests.factories.runs import create_run_manager_with_deps

        manager = create_run_manager_with_deps()
        request = RunCreate(
            strategy_id="sample",
            mode=RunMode.BACKTEST,
            config={"symbols": ["BTC/USD"], "timeframe": "1m"},
        )
        run = await manager.create(request)
        with pytest.raises(RuntimeError, match="backtest_start"):
            await manager.start(run.id)
