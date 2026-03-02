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
) -> asyncio.Task[Any]:
    """Create an asyncio task and log unhandled exceptions with context."""
    task = asyncio.create_task(coro)

    def _on_done(done_task: asyncio.Task[Any]) -> None:
        try:
            done_task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Background task failed: %s", context)

    task.add_done_callback(_on_done)
    return task
