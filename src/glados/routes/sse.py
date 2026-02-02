"""
SSE (Server-Sent Events) Routes

Provides real-time event streaming to clients.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from src.glados.dependencies import get_broadcaster
from src.glados.sse_broadcaster import SSEBroadcaster

router = APIRouter(prefix="/api/v1/events", tags=["events"])


async def _event_generator(broadcaster: SSEBroadcaster):
    """Generate SSE events from broadcaster."""
    async for event in broadcaster.subscribe():
        yield {
            "id": event.id,
            "event": event.event,
            "data": event.data,
        }


@router.get("/stream")
async def event_stream(request: Request) -> EventSourceResponse:
    """
    SSE event stream endpoint.
    
    Clients connect here to receive real-time events.
    
    Returns:
        EventSourceResponse with event stream
    """
    broadcaster = get_broadcaster(request)
    return EventSourceResponse(_event_generator(broadcaster))
