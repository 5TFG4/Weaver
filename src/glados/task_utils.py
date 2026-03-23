"""Async task helpers for callback-driven event handlers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any


def spawn_tracked_task(
    coro: Coroutine[Any, Any, Any],
    *,
    logger: logging.Logger,
    context: str,
    task_set: set[asyncio.Task[Any]] | None = None,
) -> asyncio.Task[Any]:
    """Create an asyncio task and log unhandled exceptions with context.

    Args:
        coro: The coroutine to schedule.
        logger: Logger for exception reporting.
        context: Human-readable label for error messages.
        task_set: If provided, the task is added on creation and
                  removed via done-callback.  Used by RunContext to
                  track in-flight work for drain-before-cleanup.
    """
    task = asyncio.create_task(coro)

    def _on_done(done_task: asyncio.Task[Any]) -> None:
        if task_set is not None:
            task_set.discard(done_task)
        try:
            done_task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Background task failed: %s", context)

    task.add_done_callback(_on_done)
    if task_set is not None:
        task_set.add(task)
    return task
