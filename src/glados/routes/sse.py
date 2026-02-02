"""
SSE (Server-Sent Events) Routes

Provides real-time event streaming to clients.
"""

from __future__ import annotations

import threading

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.glados.sse_broadcaster import SSEBroadcaster

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# Shared broadcaster instance (will be injected via DI in production)
_broadcaster: SSEBroadcaster | None = None
_broadcaster_lock = threading.Lock()


def get_broadcaster() -> SSEBroadcaster:
    """Get or create SSEBroadcaster instance (thread-safe)."""
    global _broadcaster
    if _broadcaster is None:
        with _broadcaster_lock:
            # Double-check locking pattern
            if _broadcaster is None:
                _broadcaster = SSEBroadcaster()
    return _broadcaster


def reset_broadcaster() -> None:
    """Reset broadcaster (for testing)."""
    global _broadcaster
    with _broadcaster_lock:
        _broadcaster = None


async def _event_generator():
    """Generate SSE events from broadcaster."""
    broadcaster = get_broadcaster()
    async for event in broadcaster.subscribe():
        yield {
            "id": event.id,
            "event": event.event,
            "data": event.data,
        }


@router.get("/stream")
async def event_stream() -> EventSourceResponse:
    """
    SSE event stream endpoint.
    
    Clients connect here to receive real-time events.
    
    Returns:
        EventSourceResponse with event stream
    """
    return EventSourceResponse(_event_generator())
