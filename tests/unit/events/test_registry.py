"""
Unit Tests for Event Registry

Tests event registration and payload validation.
"""

import pytest

from src.events.protocol import Envelope
from src.events.registry import (
    EventRegistry,
    EventSchema,
    ValidationError,
    get_registry,
    register_event,
    validate_event,
)


class TestEventSchema:
    """Tests for EventSchema validation."""

    def test_schema_validates_required_fields(self) -> None:
        """Schema should catch missing required fields."""
        schema = EventSchema(
            event_type="orders.Placed",
            required_fields={"order_id", "symbol", "side"},
        )

        # Valid payload
        errors = schema.validate({"order_id": "123", "symbol": "AAPL", "side": "buy"})
        assert errors == []

        # Missing field
        errors = schema.validate({"order_id": "123", "symbol": "AAPL"})
        assert len(errors) == 1
        assert "Missing required fields" in errors[0]
        assert "side" in errors[0]

    def test_schema_validates_unknown_fields(self) -> None:
        """Schema should catch unknown fields when fields are defined."""
        schema = EventSchema(
            event_type="test.Event",
            required_fields={"id"},
            optional_fields={"name"},
        )

        # Valid with optional
        errors = schema.validate({"id": "123", "name": "test"})
        assert errors == []

        # Unknown field
        errors = schema.validate({"id": "123", "unknown": "value"})
        assert len(errors) == 1
        assert "Unknown fields" in errors[0]

    def test_schema_custom_validator(self) -> None:
        """Schema should run custom validator function."""

        def validate_positive_qty(payload: dict) -> list[str]:
            errors = []
            if payload.get("qty", 0) <= 0:
                errors.append("qty must be positive")
            return errors

        schema = EventSchema(
            event_type="orders.PlaceRequest",
            required_fields={"symbol", "qty"},
            validator=validate_positive_qty,
        )

        # Valid
        errors = schema.validate({"symbol": "AAPL", "qty": 10})
        assert errors == []

        # Invalid qty
        errors = schema.validate({"symbol": "AAPL", "qty": -5})
        assert "qty must be positive" in errors


class TestEventRegistry:
    """Tests for EventRegistry."""

    def test_register_event_type(self) -> None:
        """Should register event type with schema."""
        registry = EventRegistry()

        registry.register(
            "orders.Placed",
            required_fields={"order_id", "symbol"},
        )

        assert registry.is_registered("orders.Placed")
        assert not registry.is_registered("orders.Unknown")

    def test_validate_payload_success(self) -> None:
        """Should pass validation for correct payload."""
        registry = EventRegistry()
        registry.register(
            "data.WindowReady",
            required_fields={"symbol", "timeframe"},
            optional_fields={"bar_count"},
        )

        # Should not raise
        registry.validate(
            "data.WindowReady",
            {"symbol": "AAPL", "timeframe": "1m", "bar_count": 100},
        )

    def test_validate_payload_failure(self) -> None:
        """Should raise ValidationError for incorrect payload."""
        registry = EventRegistry()
        registry.register(
            "orders.Placed",
            required_fields={"order_id", "symbol", "side"},
        )

        with pytest.raises(ValidationError) as exc_info:
            registry.validate("orders.Placed", {"order_id": "123"})

        assert exc_info.value.event_type == "orders.Placed"
        assert "Missing required fields" in exc_info.value.errors[0]

    def test_validate_unregistered_passes(self) -> None:
        """Unregistered event types should pass validation."""
        registry = EventRegistry()

        # Should not raise - allows extensibility
        registry.validate("unknown.Event", {"any": "payload"})

    def test_get_event_schema(self) -> None:
        """Should retrieve registered schema."""
        registry = EventRegistry()
        registry.register(
            "run.Started",
            required_fields={"run_id", "strategy"},
        )

        schema = registry.get_schema("run.Started")

        assert schema is not None
        assert schema.event_type == "run.Started"
        assert "run_id" in schema.required_fields

    def test_unregister_event(self) -> None:
        """Should remove event type from registry."""
        registry = EventRegistry()
        registry.register("test.Event", required_fields={"id"})

        assert registry.is_registered("test.Event")

        registry.unregister("test.Event")

        assert not registry.is_registered("test.Event")

    def test_list_types(self) -> None:
        """Should list all registered event types."""
        registry = EventRegistry()
        registry.register("type.A")
        registry.register("type.B")
        registry.register("type.C")

        types = registry.list_types()

        assert types == ["type.A", "type.B", "type.C"]

    def test_validate_envelope(self) -> None:
        """Should validate envelope's payload against its type schema."""
        registry = EventRegistry()
        registry.register(
            "strategy.FetchWindow",
            required_fields={"symbol", "window_size"},
        )

        valid_envelope = Envelope(
            type="strategy.FetchWindow",
            producer="marvin",
            payload={"symbol": "AAPL", "window_size": 100},
        )
        registry.validate_envelope(valid_envelope)  # Should not raise

        invalid_envelope = Envelope(
            type="strategy.FetchWindow",
            producer="marvin",
            payload={"symbol": "AAPL"},  # Missing window_size
        )
        with pytest.raises(ValidationError):
            registry.validate_envelope(invalid_envelope)


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_global_registry_singleton(self) -> None:
        """get_registry should return the same instance."""
        r1 = get_registry()
        r2 = get_registry()

        assert r1 is r2

    def test_register_and_validate_global(self) -> None:
        """Global functions should work with the singleton."""
        # Register
        register_event(
            "test.GlobalEvent",
            required_fields={"test_field"},
        )

        # Validate
        validate_event("test.GlobalEvent", {"test_field": "value"})

        with pytest.raises(ValidationError):
            validate_event("test.GlobalEvent", {})

        # Cleanup
        get_registry().unregister("test.GlobalEvent")
