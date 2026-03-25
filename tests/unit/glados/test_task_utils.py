"""Tests for spawn_tracked_task with task_set tracking (M11-1)."""

from __future__ import annotations

import asyncio
import contextlib
import logging

import pytest

from src.glados.task_utils import spawn_tracked_task

logger = logging.getLogger(__name__)


class TestSpawnTrackedTaskSet:
    """Tests for task_set registration and cleanup."""

    async def test_task_added_to_set_on_creation(self) -> None:
        """Task appears in task_set immediately after spawn."""
        task_set: set[asyncio.Task[None]] = set()

        async def noop() -> None:
            await asyncio.sleep(0.1)

        task = spawn_tracked_task(noop(), logger=logger, context="test", task_set=task_set)
        assert task in task_set
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_task_removed_from_set_on_completion(self) -> None:
        """Task is discarded from task_set when it finishes."""
        task_set: set[asyncio.Task[None]] = set()

        async def quick() -> None:
            pass

        task = spawn_tracked_task(quick(), logger=logger, context="test", task_set=task_set)
        await task
        # done callback fires synchronously after await
        assert task not in task_set

    async def test_task_removed_from_set_on_error(self) -> None:
        """Failed task is also removed from task_set."""
        task_set: set[asyncio.Task[None]] = set()

        async def fail() -> None:
            raise ValueError("boom")

        task = spawn_tracked_task(fail(), logger=logger, context="test", task_set=task_set)
        # Wait for task to complete and done callbacks to fire
        with contextlib.suppress(ValueError):
            await task
        assert task not in task_set

    async def test_task_removed_from_set_on_cancel(self) -> None:
        """Cancelled task is removed from task_set."""
        task_set: set[asyncio.Task[None]] = set()

        async def hang() -> None:
            await asyncio.sleep(999)

        task = spawn_tracked_task(hang(), logger=logger, context="test", task_set=task_set)
        assert task in task_set
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task not in task_set

    async def test_none_task_set_is_backward_compatible(self) -> None:
        """task_set=None (default) works without error."""

        async def quick() -> None:
            pass

        task = spawn_tracked_task(quick(), logger=logger, context="test")
        await task  # should not raise
