"""
Event Protocol Definitions

Defines the core event envelope structure and error response format.
All events in the system use this envelope for consistency and traceability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def _generate_id() -> str:
    """Generate a unique event ID."""
    return str(uuid4())


def _utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Envelope:
    """
    Immutable event envelope following the stable contract.

    Attributes:
        id: Unique event identifier
        kind: 'evt' for events, 'cmd' for commands
        type: Event type (e.g., 'strategy.FetchWindow', 'orders.Placed')
        version: Schema version (default '1')
        run_id: Associated run identifier (optional)
        corr_id: Correlation ID for request tracing
        causation_id: ID of the event that caused this one (optional)
        trace_id: Distributed tracing ID (optional)
        ts: Timestamp (UTC)
        producer: Name of the producing module
        headers: Additional metadata (optional)
        payload: Event-specific data
    """

    type: str
    producer: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=_generate_id)
    kind: Literal["evt", "cmd"] = "evt"
    version: str = "1"
    run_id: str | None = None
    corr_id: str = field(default_factory=_generate_id)
    causation_id: str | None = None
    trace_id: str | None = None
    ts: datetime = field(default_factory=_utc_now)
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize envelope to dictionary."""
        return {
            "id": self.id,
            "kind": self.kind,
            "type": self.type,
            "version": self.version,
            "run_id": self.run_id,
            "corr_id": self.corr_id,
            "causation_id": self.causation_id,
            "trace_id": self.trace_id,
            "ts": self.ts.isoformat(),
            "producer": self.producer,
            "headers": self.headers,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Envelope:
        """Deserialize envelope from dictionary."""
        ts = data.get("ts")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = _utc_now()

        return cls(
            id=data.get("id", _generate_id()),
            kind=data.get("kind", "evt"),
            type=data["type"],
            version=data.get("version", "1"),
            run_id=data.get("run_id"),
            corr_id=data.get("corr_id", _generate_id()),
            causation_id=data.get("causation_id"),
            trace_id=data.get("trace_id"),
            ts=ts,
            producer=data.get("producer", "unknown"),
            headers=data.get("headers", {}),
            payload=data.get("payload", {}),
        )

    def with_causation(self, causation_id: str) -> Envelope:
        """Create a new envelope with the given causation_id."""
        return Envelope(
            id=_generate_id(),
            kind=self.kind,
            type=self.type,
            version=self.version,
            run_id=self.run_id,
            corr_id=self.corr_id,
            causation_id=causation_id,
            trace_id=self.trace_id,
            ts=_utc_now(),
            producer=self.producer,
            headers=self.headers,
            payload=self.payload,
        )


@dataclass(frozen=True)
class ErrorResponse:
    """
    Standardized error response format.

    Attributes:
        code: Machine-readable error code (e.g., 'VALIDATION_ERROR')
        message: Human-readable error message
        details: Additional error details (optional)
        correlation_id: Request correlation ID for tracing
    """

    code: str
    message: str
    correlation_id: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize error response to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ErrorResponse:
        """Deserialize error response from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            details=data.get("details", {}),
            correlation_id=data.get("correlation_id", ""),
        )
