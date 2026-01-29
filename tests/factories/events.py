"""
Event Factories

Provides factory functions and classes for creating test event envelopes.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class EventFactory:
    """
    Factory for creating test event envelopes.
    
    Provides sensible defaults while allowing customization of any field.
    
    Usage:
        # Create with all defaults
        event = EventFactory.create("orders.Placed", {"order_id": "123"})
        
        # Create with custom fields
        event = EventFactory.create(
            "strategy.FetchWindow",
            {"symbol": "AAPL"},
            run_id="my-run-id",
        )
        
        # Use builder pattern
        event = (EventFactory()
            .with_type("orders.Filled")
            .with_run_id("run-123")
            .with_payload({"qty": 100})
            .build())
    """
    
    # Default values
    _id: str | None = None
    _kind: str = "evt"
    _type: str = "test.Event"
    _version: str = "v1"
    _run_id: str | None = None
    _corr_id: str | None = None
    _causation_id: str | None = None
    _trace_id: str | None = None
    _ts: datetime | None = None
    _producer: str = "test"
    _headers: dict[str, Any] | None = None
    _payload: dict[str, Any] | None = None
    
    def with_id(self, id: str) -> "EventFactory":
        """Set event ID."""
        self._id = id
        return self
    
    def with_kind(self, kind: str) -> "EventFactory":
        """Set event kind (evt or cmd)."""
        self._kind = kind
        return self
    
    def with_type(self, type: str) -> "EventFactory":
        """Set event type."""
        self._type = type
        return self
    
    def with_version(self, version: str) -> "EventFactory":
        """Set event version."""
        self._version = version
        return self
    
    def with_run_id(self, run_id: str | None) -> "EventFactory":
        """Set run ID."""
        self._run_id = run_id
        return self
    
    def with_corr_id(self, corr_id: str) -> "EventFactory":
        """Set correlation ID."""
        self._corr_id = corr_id
        return self
    
    def with_causation_id(self, causation_id: str) -> "EventFactory":
        """Set causation ID."""
        self._causation_id = causation_id
        return self
    
    def with_trace_id(self, trace_id: str) -> "EventFactory":
        """Set trace ID."""
        self._trace_id = trace_id
        return self
    
    def with_timestamp(self, ts: datetime) -> "EventFactory":
        """Set timestamp."""
        self._ts = ts
        return self
    
    def with_producer(self, producer: str) -> "EventFactory":
        """Set producer."""
        self._producer = producer
        return self
    
    def with_headers(self, headers: dict[str, Any]) -> "EventFactory":
        """Set headers."""
        self._headers = headers
        return self
    
    def with_payload(self, payload: dict[str, Any]) -> "EventFactory":
        """Set payload."""
        self._payload = payload
        return self
    
    def build(self) -> dict[str, Any]:
        """Build the event envelope as a dictionary."""
        event_id = self._id or str(uuid4())
        return {
            "id": event_id,
            "kind": self._kind,
            "type": self._type,
            "version": self._version,
            "run_id": self._run_id,
            "corr_id": self._corr_id or str(uuid4()),
            "causation_id": self._causation_id or event_id,
            "trace_id": self._trace_id or str(uuid4()),
            "ts": (self._ts or datetime.now(timezone.utc)).isoformat(),
            "producer": self._producer,
            "headers": self._headers or {},
            "payload": self._payload or {},
        }
    
    @classmethod
    def create(
        cls,
        event_type: str,
        payload: dict[str, Any],
        *,
        kind: str = "evt",
        version: str = "v1",
        run_id: str | None = None,
        corr_id: str | None = None,
        producer: str = "test",
    ) -> dict[str, Any]:
        """
        Convenience method to create an event with minimal boilerplate.
        
        Args:
            event_type: The event type (e.g., "orders.Placed")
            payload: The event payload
            kind: Event kind (default: "evt")
            version: Event version (default: "v1")
            run_id: Optional run ID
            corr_id: Optional correlation ID
            producer: Producer name (default: "test")
            
        Returns:
            Event envelope as dictionary
        """
        return (
            cls()
            .with_type(event_type)
            .with_payload(payload)
            .with_kind(kind)
            .with_version(version)
            .with_run_id(run_id)
            .with_corr_id(corr_id or str(uuid4()))
            .with_producer(producer)
            .build()
        )


def create_event(
    event_type: str,
    payload: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Simple function to create a test event.
    
    This is the easiest way to create test events.
    
    Args:
        event_type: The event type
        payload: Optional payload (default: empty dict)
        **kwargs: Additional fields to set
        
    Returns:
        Event envelope as dictionary
    """
    return EventFactory.create(
        event_type,
        payload or {},
        **kwargs,
    )


# =============================================================================
# Pre-built Event Templates
# =============================================================================

def create_fetch_window_event(
    symbol: str,
    timeframe: str = "1m",
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a strategy.FetchWindow event."""
    return create_event(
        "strategy.FetchWindow",
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_back": 100,
        },
        run_id=run_id,
    )


def create_place_request_event(
    symbol: str,
    side: str,
    qty: float,
    order_type: str = "market",
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a strategy.PlaceRequest event."""
    return create_event(
        "strategy.PlaceRequest",
        {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "order_type": order_type,
        },
        run_id=run_id,
    )


def create_order_placed_event(
    order_id: str,
    symbol: str,
    side: str,
    qty: float,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create an orders.Placed event."""
    return create_event(
        "orders.Placed",
        {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "status": "placed",
        },
        run_id=run_id,
    )


def create_order_filled_event(
    order_id: str,
    symbol: str,
    side: str,
    qty: float,
    fill_price: float,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create an orders.Filled event."""
    return create_event(
        "orders.Filled",
        {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "fill_price": fill_price,
            "status": "filled",
        },
        run_id=run_id,
    )


def create_clock_tick_event(
    ts: datetime,
    timeframe: str = "1m",
    bar_index: int = 0,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Create a clock.Tick event."""
    return create_event(
        "clock.Tick",
        {
            "ts": ts.isoformat(),
            "timeframe": timeframe,
            "bar_index": bar_index,
        },
        run_id=run_id,
    )
