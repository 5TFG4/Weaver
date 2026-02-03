"""
Tests for RunManager backtest orchestration (M4)

Unit tests for backtest flow orchestration in RunManager.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.glados.schemas import RunCreate, RunMode, RunStatus
from src.glados.services.run_manager import Run, RunContext, RunManager


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

        return RunManager(
            event_log=mock_event_log,
            bar_repository=mock_bar_repo,
            strategy_loader=mock_strategy_loader,
        )

    async def test_start_backtest_creates_run_context(
        self, manager_with_deps: RunManager
    ) -> None:
        """start() creates RunContext for backtest runs."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                symbols=["BTC/USD"],
                timeframe="1m",
                start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
            )
        )

        await manager_with_deps.start(run.id)

        assert run.id in manager_with_deps._run_contexts
        ctx = manager_with_deps._run_contexts[run.id]
        assert ctx.greta is not None
        assert ctx.runner is not None
        assert ctx.clock is not None

    async def test_start_backtest_initializes_greta(
        self, manager_with_deps: RunManager
    ) -> None:
        """start() initializes GretaService with run params."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                symbols=["BTC/USD"],
                timeframe="1m",
                start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
            )
        )

        await manager_with_deps.start(run.id)

        ctx = manager_with_deps._run_contexts[run.id]
        # Greta should be initialized (has run_id set)
        assert ctx.greta.run_id == run.id

    async def test_start_backtest_initializes_runner(
        self, manager_with_deps: RunManager
    ) -> None:
        """start() initializes StrategyRunner with run params."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                symbols=["BTC/USD"],
                timeframe="1m",
                start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
            )
        )

        await manager_with_deps.start(run.id)

        ctx = manager_with_deps._run_contexts[run.id]
        assert ctx.runner.run_id == run.id
        assert ctx.runner.symbols == ["BTC/USD"]

    async def test_start_backtest_loads_strategy(
        self, manager_with_deps: RunManager
    ) -> None:
        """start() loads strategy from loader."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                symbols=["BTC/USD"],
                timeframe="1m",
                start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
            )
        )

        await manager_with_deps.start(run.id)

        manager_with_deps._strategy_loader.load.assert_called_once_with("test-strategy")

    async def test_start_backtest_runs_to_completion(
        self, manager_with_deps: RunManager
    ) -> None:
        """start() for backtest runs clock to completion."""
        run = await manager_with_deps.create(
            RunCreate(
                strategy_id="test-strategy",
                mode=RunMode.BACKTEST,
                symbols=["BTC/USD"],
                timeframe="1m",
                start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
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
                symbols=["BTC/USD"],
                timeframe="1m",
                start_time=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
                end_time=datetime(2024, 1, 1, 9, 35, tzinfo=UTC),
            )
        )

        await manager_with_deps.start(run.id)

        # Check for COMPLETED event
        calls = manager_with_deps._event_log.append.call_args_list
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
                symbols=["BTC/USD"],
                start_time=datetime(2024, 1, 1, tzinfo=UTC),
                end_time=datetime(2024, 1, 2, tzinfo=UTC),
            )
        )
        run.status = RunStatus.RUNNING

        # Manually add context
        mock_ctx = MagicMock()
        mock_ctx.clock = AsyncMock()
        mock_ctx.clock.stop = AsyncMock()
        manager._run_contexts[run.id] = mock_ctx

        return manager, run.id

    async def test_stop_cleans_up_context(
        self, manager_with_running_run: tuple[RunManager, str]
    ) -> None:
        """stop() removes RunContext from manager."""
        manager, run_id = manager_with_running_run

        await manager.stop(run_id)

        assert run_id not in manager._run_contexts

    async def test_stop_stops_clock(
        self, manager_with_running_run: tuple[RunManager, str]
    ) -> None:
        """stop() calls clock.stop() before cleanup."""
        manager, run_id = manager_with_running_run
        ctx = manager._run_contexts[run_id]

        await manager.stop(run_id)

        ctx.clock.stop.assert_called_once()
