"""
Tests for Run Manager Service

MVP-2: Run Lifecycle
TDD: Write tests first, then implement.
"""

from __future__ import annotations

import pytest

from src.glados.schemas import RunCreate, RunMode, RunStatus


class TestRunManagerCreate:
    """Tests for RunManager.create()."""

    async def test_creates_run_with_id(self) -> None:
        """create() should return Run with generated UUID."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )

        run = await run_manager.create(request)

        assert run.id is not None
        assert len(run.id) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

    async def test_initial_status_is_pending(self) -> None:
        """New run should have status=PENDING."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )

        run = await run_manager.create(request)

        assert run.status == RunStatus.PENDING

    async def test_preserves_request_fields(self) -> None:
        """Run should contain all fields from request."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="my_strategy",
            mode=RunMode.BACKTEST,
            symbols=["BTC/USD", "ETH/USD"],
            timeframe="5m",
        )

        run = await run_manager.create(request)

        assert run.strategy_id == "my_strategy"
        assert run.mode == RunMode.BACKTEST
        assert run.symbols == ["BTC/USD", "ETH/USD"]
        assert run.timeframe == "5m"

    async def test_sets_created_at_timestamp(self) -> None:
        """Run should have created_at timestamp."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )

        run = await run_manager.create(request)

        assert run.created_at is not None


class TestRunManagerGet:
    """Tests for RunManager.get()."""

    async def test_returns_existing_run(self) -> None:
        """get() should return run by ID."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )
        created = await run_manager.create(request)

        fetched = await run_manager.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.strategy_id == created.strategy_id

    async def test_returns_none_for_unknown_id(self) -> None:
        """get() should return None for non-existent ID."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()

        result = await run_manager.get("non-existent-id")

        assert result is None


class TestRunManagerList:
    """Tests for RunManager.list()."""

    async def test_empty_returns_empty_list(self) -> None:
        """list() should return empty list when no runs exist."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()

        runs, total = await run_manager.list()

        assert runs == []
        assert total == 0

    async def test_returns_all_runs(self) -> None:
        """list() should return all created runs."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        for i in range(3):
            await run_manager.create(
                RunCreate(
                    strategy_id=f"test_{i}",
                    mode=RunMode.PAPER,
                    symbols=["BTC/USD"],
                )
            )

        runs, total = await run_manager.list()

        assert len(runs) == 3
        assert total == 3


class TestRunManagerStop:
    """Tests for RunManager.stop()."""

    async def test_transitions_running_to_stopped(self) -> None:
        """stop() should change status from RUNNING to STOPPED."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )
        run = await run_manager.create(request)
        # Use public API to start the run
        await run_manager.start(run.id)

        stopped = await run_manager.stop(run.id)

        assert stopped.status == RunStatus.STOPPED

    async def test_already_stopped_is_idempotent(self) -> None:
        """stop() on stopped run should not raise."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )
        run = await run_manager.create(request)
        await run_manager.start(run.id)
        await run_manager.stop(run.id)

        # Call stop again - should be idempotent
        stopped = await run_manager.stop(run.id)

        assert stopped.status == RunStatus.STOPPED

    async def test_not_found_raises_error(self) -> None:
        """stop() on non-existent run should raise RunNotFoundError."""
        from src.glados.exceptions import RunNotFoundError
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()

        with pytest.raises(RunNotFoundError) as exc_info:
            await run_manager.stop("non-existent-id")

        assert exc_info.value.run_id == "non-existent-id"

    async def test_sets_stopped_at_timestamp(self) -> None:
        """stop() should set stopped_at timestamp."""
        from src.glados.services.run_manager import RunManager

        run_manager = RunManager()
        request = RunCreate(
            strategy_id="test_strategy",
            mode=RunMode.PAPER,
            symbols=["BTC/USD"],
        )
        run = await run_manager.create(request)
        await run_manager.start(run.id)

        stopped = await run_manager.stop(run.id)

        assert stopped.stopped_at is not None
