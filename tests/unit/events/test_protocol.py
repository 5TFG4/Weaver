"""
Unit Tests for Event Protocol

Tests the Envelope and ErrorResponse classes.
"""

from datetime import datetime, timezone

import pytest

from src.events.protocol import Envelope, ErrorResponse


class TestEnvelope:
    """Tests for the Envelope dataclass."""

    def test_envelope_creation(self) -> None:
        """Envelope should have all required fields."""
        envelope = Envelope(
            type="test.Event",
            producer="test",
            payload={"key": "value"},
        )

        assert envelope.type == "test.Event"
        assert envelope.producer == "test"
        assert envelope.payload == {"key": "value"}
        assert envelope.kind == "evt"
        assert envelope.version == "1"
        assert envelope.id is not None
        assert envelope.corr_id is not None
        assert envelope.ts is not None
        assert isinstance(envelope.ts, datetime)

    def test_envelope_immutable(self) -> None:
        """Envelope should be frozen after creation."""
        envelope = Envelope(
            type="test.Event",
            producer="test",
        )

        with pytest.raises(AttributeError):
            envelope.type = "changed.Event"  # type: ignore

    def test_envelope_serialization(self) -> None:
        """Envelope should serialize to/from JSON-compatible dict."""
        original = Envelope(
            type="orders.Placed",
            producer="veda",
            payload={"order_id": "123", "symbol": "AAPL"},
            run_id="run-001",
        )

        # Serialize
        data = original.to_dict()

        assert data["type"] == "orders.Placed"
        assert data["producer"] == "veda"
        assert data["payload"]["order_id"] == "123"
        assert data["run_id"] == "run-001"
        assert "ts" in data
        assert "id" in data
        assert "corr_id" in data

        # Deserialize
        restored = Envelope.from_dict(data)

        assert restored.type == original.type
        assert restored.producer == original.producer
        assert restored.payload == original.payload
        assert restored.run_id == original.run_id

    def test_envelope_with_all_fields(self) -> None:
        """Envelope should accept all optional fields."""
        ts = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)

        envelope = Envelope(
            id="evt-123",
            kind="cmd",
            type="strategy.FetchWindow",
            version="2",
            run_id="run-456",
            corr_id="corr-789",
            causation_id="cause-111",
            trace_id="trace-222",
            ts=ts,
            producer="marvin",
            headers={"priority": "high"},
            payload={"symbol": "BTC/USD", "window": 100},
        )

        assert envelope.id == "evt-123"
        assert envelope.kind == "cmd"
        assert envelope.version == "2"
        assert envelope.causation_id == "cause-111"
        assert envelope.trace_id == "trace-222"
        assert envelope.headers == {"priority": "high"}

    def test_envelope_with_causation(self) -> None:
        """with_causation should create new envelope with causation_id set."""
        original = Envelope(
            type="strategy.FetchWindow",
            producer="marvin",
            corr_id="corr-123",
        )

        derived = original.with_causation(original.id)

        assert derived.causation_id == original.id
        assert derived.corr_id == original.corr_id  # Preserved
        assert derived.id != original.id  # New ID
        assert derived.type == original.type

    def test_envelope_default_timestamps_are_utc(self) -> None:
        """Default timestamps should be UTC."""
        envelope = Envelope(type="test.Event", producer="test")

        assert envelope.ts.tzinfo is not None
        assert envelope.ts.tzinfo == timezone.utc


class TestErrorResponse:
    """Tests for the ErrorResponse dataclass."""

    def test_error_response_creation(self) -> None:
        """ErrorResponse should have all required fields."""
        error = ErrorResponse(
            code="VALIDATION_ERROR",
            message="Invalid payload",
            correlation_id="corr-123",
        )

        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid payload"
        assert error.correlation_id == "corr-123"
        assert error.details == {}

    def test_error_response_with_details(self) -> None:
        """ErrorResponse should accept details dict."""
        error = ErrorResponse(
            code="ORDER_REJECTED",
            message="Insufficient funds",
            correlation_id="corr-456",
            details={"account_balance": 100, "required": 500},
        )

        assert error.details["account_balance"] == 100
        assert error.details["required"] == 500

    def test_error_response_serialization(self) -> None:
        """ErrorResponse should serialize to/from dict."""
        original = ErrorResponse(
            code="RATE_LIMITED",
            message="Too many requests",
            correlation_id="corr-789",
            details={"retry_after": 60},
        )

        data = original.to_dict()
        restored = ErrorResponse.from_dict(data)

        assert restored.code == original.code
        assert restored.message == original.message
        assert restored.correlation_id == original.correlation_id
        assert restored.details == original.details

    def test_error_response_immutable(self) -> None:
        """ErrorResponse should be frozen."""
        error = ErrorResponse(
            code="TEST",
            message="Test error",
            correlation_id="corr-000",
        )

        with pytest.raises(AttributeError):
            error.code = "CHANGED"  # type: ignore
