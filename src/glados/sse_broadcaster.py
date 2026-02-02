"""
SSE Broadcaster

Manages Server-Sent Events connections and broadcasts events to all clients.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass
class ServerSentEvent:
    """Represents a Server-Sent Event."""

    id: str
    event: str
    data: str


class SSEBroadcaster:
    """
    Manages SSE connections and broadcasts events to all clients.
    
    Features:
    - Multi-client support
    - Event ID tracking for reconnection support
    - Automatic client cleanup on disconnect
    - Bounded queues to prevent memory exhaustion from slow clients
    
    MVP-3 Implementation:
    - Basic pub/sub pattern
    - No persistence (events not stored)
    - No heartbeat (clients may timeout)
    
    Future (M3+):
    - EventLog integration for persistence
    - Heartbeat for connection keep-alive
    - Last-Event-ID support for replay
    """

    # Maximum events queued per client before dropping
    MAX_QUEUE_SIZE = 100

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[ServerSentEvent]] = set()
        self._event_id: int = 0

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)

    async def subscribe(self) -> AsyncIterator[ServerSentEvent]:
        """
        Subscribe to event stream.
        
        Yields:
            ServerSentEvent objects as they are published
        """
        queue: asyncio.Queue[ServerSentEvent] = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._clients.add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._clients.discard(queue)

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Publish event to all connected clients.
        
        Args:
            event_type: Event type name (e.g., "run.started")
            data: Event payload (will be JSON serialized)
            
        Note:
            Uses put_nowait to avoid blocking on slow clients.
            If a client's queue is full, the event is dropped for that client.
        """
        self._event_id += 1
        event = ServerSentEvent(
            id=str(self._event_id),
            event=event_type,
            data=json.dumps(data),
        )
        # Use put_nowait to avoid blocking on slow clients
        for queue in self._clients.copy():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop event for slow client to avoid memory buildup
                pass
