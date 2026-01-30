"""
Test Data Factories Package

This package provides factory classes for generating test data.
Uses custom dataclass-based builders for consistent, composable test data generation.

Modules:
- events.py: Event envelope factories
- orders.py: Order and fill factories
- runs.py: Run and strategy config factories
"""

from tests.factories.events import EventFactory, create_event
from tests.factories.orders import OrderFactory, create_order
from tests.factories.runs import RunFactory, create_run

__all__ = [
    "EventFactory",
    "OrderFactory",
    "RunFactory",
    "create_event",
    "create_order",
    "create_run",
]
