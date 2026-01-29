"""
In-Memory Event Log for Unit Tests

Provides a lightweight event log implementation that doesn't require a database.
Use this for unit tests that need to test event flow without integration overhead.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4


@dataclass(frozen=True)
class TestEnvelope:
    """
    Simplified event envelope for testing.
    
    This mirrors the production Envelope structure but is optimized for testing.
    """
    
    id: str
    kind: str  # "evt" | "cmd"
    type: str  # e.g., "strategy.FetchWindow", "orders.Placed"
    version: str
    run_id: str | None
    corr_id: str
    causation_id: str
    trace_id: str
    ts: datetime
    producer: str
    headers: dict[str, Any]
    payload: dict[str, Any]
    
    @classmethod
    def create(
        cls,
        type: str,
        payload: dict[str, Any],
        *,
        kind: str = "evt",
        version: str = "v1",
        run_id: str | None = None,
        corr_id: str | None = None,
        causation_id: str | None = None,
        trace_id: str | None = None,
        producer: str = "test",
        headers: dict[str, Any] | None = None,
    ) -> "TestEnvelope":
        """
        Create a new envelope with auto-generated IDs.
        
        This is the preferred way to create test envelopes.
        """
        event_id = str(uuid4())
        return cls(
            id=event_id,
            kind=kind,
            type=type,
            version=version,
            run_id=run_id,
            corr_id=corr_id or str(uuid4()),
            causation_id=causation_id or event_id,
            trace_id=trace_id or str(uuid4()),
            ts=datetime.now(timezone.utc),
            producer=producer,
            headers=headers or {},
            payload=payload,
        )


# Type alias for event handlers
EventHandler = Callable[[TestEnvelope], None]


@dataclass
class InMemoryEventLog:
    """
    In-memory event log for unit testing.
    
    Provides the same interface as the production EventLog but stores
    everything in memory without database dependencies.
    
    Features:
    - Append events
    - Subscribe to event types (pattern matching)
    - Consumer offset tracking
    - Event replay
    
    Usage:
        log = InMemoryEventLog()
        
        # Subscribe to events
        received = []
        log.subscribe("orders.*", lambda e: received.append(e))
        
        # Append an event
        envelope = TestEnvelope.create("orders.Placed", {"order_id": "123"})
        log.append(envelope)
        
        # Check received
        assert len(received) == 1
        assert received[0].type == "orders.Placed"
    """
    
    # All events in order
    _events: list[TestEnvelope] = field(default_factory=list)
    
    # Subscribers by pattern
    _subscribers: dict[str, list[EventHandler]] = field(
        default_factory=lambda: defaultdict(list)
    )
    
    # Consumer offsets (consumer_id -> last processed index)
    _offsets: dict[str, int] = field(default_factory=dict)
    
    @property
    def events(self) -> list[TestEnvelope]:
        """Get all events in the log."""
        return self._events.copy()
    
    @property
    def event_count(self) -> int:
        """Get the total number of events."""
        return len(self._events)
    
    def append(self, envelope: TestEnvelope) -> None:
        """
        Append an event to the log and notify subscribers.
        
        Args:
            envelope: The event envelope to append
        """
        self._events.append(envelope)
        self._notify_subscribers(envelope)
    
    def subscribe(self, pattern: str, handler: EventHandler) -> None:
        """
        Subscribe to events matching a pattern.
        
        Patterns support wildcards:
        - "orders.*" matches "orders.Placed", "orders.Filled", etc.
        - "*.Placed" matches "orders.Placed", "trades.Placed", etc.
        - "*" matches everything
        
        Args:
            pattern: Event type pattern (supports * wildcard)
            handler: Callback function to receive matching events
        """
        self._subscribers[pattern].append(handler)
    
    def unsubscribe(self, pattern: str, handler: EventHandler) -> None:
        """Remove a subscription."""
        if pattern in self._subscribers:
            self._subscribers[pattern] = [
                h for h in self._subscribers[pattern] if h != handler
            ]
    
    def get_events_by_type(self, event_type: str) -> list[TestEnvelope]:
        """Get all events of a specific type."""
        return [e for e in self._events if e.type == event_type]
    
    def get_events_by_run(self, run_id: str) -> list[TestEnvelope]:
        """Get all events for a specific run."""
        return [e for e in self._events if e.run_id == run_id]
    
    def get_events_by_corr_id(self, corr_id: str) -> list[TestEnvelope]:
        """Get all events with a specific correlation ID."""
        return [e for e in self._events if e.corr_id == corr_id]
    
    def get_offset(self, consumer_id: str) -> int:
        """Get the last processed offset for a consumer."""
        return self._offsets.get(consumer_id, -1)
    
    def set_offset(self, consumer_id: str, offset: int) -> None:
        """Set the offset for a consumer."""
        self._offsets[consumer_id] = offset
    
    def get_unprocessed(self, consumer_id: str) -> list[TestEnvelope]:
        """Get events not yet processed by a consumer."""
        offset = self.get_offset(consumer_id)
        return self._events[offset + 1:]
    
    def replay(
        self,
        handler: EventHandler,
        *,
        from_offset: int = 0,
        event_type: str | None = None,
    ) -> int:
        """
        Replay events to a handler.
        
        Args:
            handler: Callback to receive events
            from_offset: Starting offset (default: 0, replay all)
            event_type: Optional filter by event type
            
        Returns:
            Number of events replayed
        """
        count = 0
        for i, event in enumerate(self._events[from_offset:], start=from_offset):
            if event_type is None or event.type == event_type:
                handler(event)
                count += 1
        return count
    
    def clear(self) -> None:
        """Clear all events and reset offsets."""
        self._events.clear()
        self._offsets.clear()
    
    def _notify_subscribers(self, envelope: TestEnvelope) -> None:
        """Notify all matching subscribers of a new event."""
        for pattern, handlers in self._subscribers.items():
            if self._matches_pattern(envelope.type, pattern):
                for handler in handlers:
                    handler(envelope)
    
    @staticmethod
    def _matches_pattern(event_type: str, pattern: str) -> bool:
        """
        Check if an event type matches a pattern.
        
        Supports:
        - Exact match: "orders.Placed"
        - Prefix wildcard: "orders.*"
        - Suffix wildcard: "*.Placed"
        - Match all: "*"
        """
        if pattern == "*":
            return True
        
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")
        
        if pattern.startswith("*."):
            suffix = pattern[2:]
            return event_type.endswith("." + suffix)
        
        return event_type == pattern
