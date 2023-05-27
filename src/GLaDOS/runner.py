import asyncio
import logging

from Veda.veda import Veda

from .glados import GLaDOS

TASK_CANCELATION_TIMEOUT = 5

_LOGGER = logging.getLogger(__name__)

async def setup_and_run_weaver(veda: Veda) -> int:
    """Set up Weaver and run."""
    glados = GLaDOS()

    glados.veda = veda

    if glados is None:
        return 1

    # threading._shutdown can deadlock forever
    # pylint: disable-next=protected-access
    # threading._shutdown = deadlock_safe_shutdown  # type: ignore[attr-defined]

    return await glados.async_run()


def run(veda: Veda) -> int:
    """Run Home Assistant."""
    
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(setup_and_run_weaver(veda))
    finally:
        try:
            _cancel_all_tasks_with_timeout(loop, TASK_CANCELATION_TIMEOUT)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def _cancel_all_tasks_with_timeout(
    loop: asyncio.AbstractEventLoop, timeout: int
) -> None:
    """Adapted _cancel_all_tasks from python 3.9 with a timeout."""
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.wait(to_cancel, timeout=timeout))

    for task in to_cancel:
        if task.cancelled():
            continue
        if not task.done():
            _LOGGER.warning(
                "Task could not be canceled and was still running after shutdown: %s",
                task,
            )
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )