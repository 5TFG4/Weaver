"""
Event Registry

Maintains a registry of event types to their payload schemas.
Provides validation for event payloads before publishing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .protocol import Envelope


class ValidationError(Exception):
    """Raised when event payload validation fails."""

    def __init__(self, event_type: str, message: str, errors: list[str] | None = None):
        self.event_type = event_type
        self.message = message
        self.errors = errors or []
        super().__init__(f"{event_type}: {message}")


@dataclass
class EventSchema:
    """
    Schema definition for an event type.

    Attributes:
        event_type: The event type string (e.g., 'orders.Placed')
        required_fields: Fields that must be present in payload
        optional_fields: Fields that may be present in payload
        validator: Optional custom validation function
    """

    event_type: str
    required_fields: set[str] = field(default_factory=set)
    optional_fields: set[str] = field(default_factory=set)
    validator: Callable[[dict[str, Any]], list[str]] | None = None

    def validate(self, payload: dict[str, Any]) -> list[str]:
        """
        Validate a payload against this schema.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Check required fields
        missing = self.required_fields - set(payload.keys())
        if missing:
            errors.append(f"Missing required fields: {', '.join(sorted(missing))}")

        # Check for unknown fields
        known_fields = self.required_fields | self.optional_fields
        if known_fields:  # Only check if we have defined fields
            unknown = set(payload.keys()) - known_fields
            if unknown:
                errors.append(f"Unknown fields: {', '.join(sorted(unknown))}")

        # Run custom validator if provided
        if self.validator:
            custom_errors = self.validator(payload)
            errors.extend(custom_errors)

        return errors


class EventRegistry:
    """
    Registry for event types and their schemas.

    Provides registration and validation of event payloads.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, EventSchema] = {}

    def register(
        self,
        event_type: str,
        required_fields: set[str] | None = None,
        optional_fields: set[str] | None = None,
        validator: Callable[[dict[str, Any]], list[str]] | None = None,
    ) -> None:
        """
        Register an event type with its schema.

        Args:
            event_type: The event type string
            required_fields: Fields that must be present
            optional_fields: Fields that may be present
            validator: Optional custom validation function
        """
        self._schemas[event_type] = EventSchema(
            event_type=event_type,
            required_fields=required_fields or set(),
            optional_fields=optional_fields or set(),
            validator=validator,
        )

    def unregister(self, event_type: str) -> None:
        """Remove an event type from the registry."""
        self._schemas.pop(event_type, None)

    def is_registered(self, event_type: str) -> bool:
        """Check if an event type is registered."""
        return event_type in self._schemas

    def get_schema(self, event_type: str) -> EventSchema | None:
        """Get the schema for an event type."""
        return self._schemas.get(event_type)

    def validate(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Validate a payload against its registered schema.

        Args:
            event_type: The event type to validate against
            payload: The payload to validate

        Raises:
            ValidationError: If validation fails
        """
        schema = self._schemas.get(event_type)
        if schema is None:
            # Allow unregistered events to pass through
            return

        errors = schema.validate(payload)
        if errors:
            raise ValidationError(
                event_type=event_type,
                message="Payload validation failed",
                errors=errors,
            )

    def validate_envelope(self, envelope: Envelope) -> None:
        """
        Validate an envelope's payload against its type's schema.

        Args:
            envelope: The envelope to validate

        Raises:
            ValidationError: If validation fails
        """
        self.validate(envelope.type, envelope.payload)

    def list_types(self) -> list[str]:
        """List all registered event types."""
        return sorted(self._schemas.keys())


# =============================================================================
# Global Registry Instance
# =============================================================================

_global_registry = EventRegistry()


def get_registry() -> EventRegistry:
    """Get the global event registry instance."""
    return _global_registry


def register_event(
    event_type: str,
    required_fields: set[str] | None = None,
    optional_fields: set[str] | None = None,
    validator: Callable[[dict[str, Any]], list[str]] | None = None,
) -> None:
    """Register an event type in the global registry."""
    _global_registry.register(event_type, required_fields, optional_fields, validator)


def validate_event(event_type: str, payload: dict[str, Any]) -> None:
    """Validate a payload against the global registry."""
    _global_registry.validate(event_type, payload)
