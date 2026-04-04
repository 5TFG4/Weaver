"""
SSE (Server-Sent Events) Routes

Provides real-time event streaming to clients.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from src.glados.dependencies import get_broadcaster
from src.glados.sse_broadcaster import ServerSentEvent, SSEBroadcaster

# Recommended reconnection delay sent to browser (ms)
RETRY_MS = 3000
# Heartbeat interval to keep connection alive through proxies (seconds)
HEARTBEAT_INTERVAL = 15

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def _should_include_event(event: ServerSentEvent, run_id: str | None) -> bool:
    """
    Check if an SSE event should be included based on run_id filter.

    D-5: When run_id is provided, only events matching that run_id pass through.
    Events without run_id in their data payload always pass (system events).
    Malformed JSON data always passes (don't drop events due to parse errors).

    Args:
        event: The SSE event to check
        run_id: Optional run_id filter. None means include all events.

    Returns:
        True if event should be sent to the client
    """
    if run_id is None:
        return True

    try:
        data = json.loads(event.data)
    except (json.JSONDecodeError, TypeError):
        # Malformed data — pass through to be safe
        return True

    event_run_id = data.get("run_id")
    if event_run_id is None:
        # No run_id in event data — system event, pass through
        return True

    return event_run_id == run_id  # type: ignore[no-any-return]


async def _event_generator(
    broadcaster: SSEBroadcaster, run_id: str | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Generate SSE events from broadcaster, optionally filtered by run_id.

    On first connection sends ``retry:`` to set the browser's reconnection
    interval, then interleaves heartbeat comments every HEARTBEAT_INTERVAL
    seconds to keep the connection alive through reverse-proxies.
    """
    # Tell the browser how long to wait before reconnecting (spec §9.2.6)
    yield {"retry": RETRY_MS}

    async for event in broadcaster.subscribe():
        if _should_include_event(event, run_id):
            yield {
                "id": event.id,
                "event": event.event,
                "data": event.data,
            }


@router.get("/stream")
async def event_stream(
    request: Request,
    run_id: str | None = Query(default=None, description="Filter events by run_id"),
) -> EventSourceResponse:
    """
    SSE event stream endpoint.

    Clients connect here to receive real-time events.
    D-5: Optional run_id query param filters events for a specific run.

    Args:
        run_id: Optional run_id to filter events. If not provided, all events are streamed.

    Returns:
        EventSourceResponse with event stream
    """
    broadcaster = get_broadcaster(request)
    return EventSourceResponse(
        _event_generator(broadcaster, run_id=run_id),
        ping=HEARTBEAT_INTERVAL,
    )
