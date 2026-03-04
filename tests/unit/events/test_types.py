"""
Unit Tests for Event Types

Tests event type constants and namespaces.
"""

from src.events.types import (
    ALL_EVENT_TYPES,
    ClockEvents,
    LiveEvents,
    Namespace,
    OrderEvents,
    RunEvents,
    StrategyEvents,
    UIEvents,
)


class TestNamespaces:
    """Tests for event namespaces."""

    def test_namespace_constants(self) -> None:
        """All namespaces should be defined."""
        assert Namespace.STRATEGY == "strategy"
        assert Namespace.LIVE == "live"
        assert Namespace.BACKTEST == "backtest"
        assert Namespace.DATA == "data"
        assert Namespace.MARKET == "market"
        assert Namespace.ORDERS == "orders"
        assert Namespace.RUN == "run"
        assert Namespace.CLOCK == "clock"
        assert Namespace.UI == "ui"


class TestEventTypes:
    """Tests for event type constants."""

    def test_strategy_events_follow_naming(self) -> None:
        """Strategy events should follow namespace.EventName pattern."""
        assert StrategyEvents.FETCH_WINDOW == "strategy.FetchWindow"
        assert StrategyEvents.PLACE_REQUEST == "strategy.PlaceRequest"
        assert StrategyEvents.DECISION_MADE == "strategy.DecisionMade"

    def test_live_events_follow_naming(self) -> None:
        """Live events should follow namespace.EventName pattern."""
        assert LiveEvents.FETCH_WINDOW == "live.FetchWindow"
        assert LiveEvents.PLACE_ORDER == "live.PlaceOrder"

    def test_order_events_follow_naming(self) -> None:
        """Order events should follow namespace.EventName pattern."""
        assert OrderEvents.PLACE_REQUEST == "orders.PlaceRequest"
        assert OrderEvents.ACK == "orders.Ack"
        assert OrderEvents.PLACED == "orders.Placed"
        assert OrderEvents.FILLED == "orders.Filled"
        assert OrderEvents.CANCELLED == "orders.Cancelled"
        assert OrderEvents.REJECTED == "orders.Rejected"

    def test_run_events_follow_naming(self) -> None:
        """Run events should follow namespace.EventName pattern."""
        assert RunEvents.STARTED == "run.Started"
        assert RunEvents.STOP_REQUESTED == "run.StopRequested"
        assert RunEvents.STOPPED == "run.Stopped"
        assert RunEvents.HEARTBEAT == "run.Heartbeat"

    def test_clock_events_follow_naming(self) -> None:
        """Clock events should follow namespace.EventName pattern."""
        assert ClockEvents.TICK == "clock.Tick"

    def test_ui_events_follow_naming(self) -> None:
        """UI events should follow namespace.EventName pattern."""
        assert UIEvents.RUN_UPDATED == "ui.RunUpdated"
        assert UIEvents.ORDER_UPDATED == "ui.OrderUpdated"

    def test_all_event_types_is_complete(self) -> None:
        """ALL_EVENT_TYPES should contain all defined events."""
        # Check some key events are present
        assert StrategyEvents.FETCH_WINDOW in ALL_EVENT_TYPES
        assert OrderEvents.PLACED in ALL_EVENT_TYPES
        assert ClockEvents.TICK in ALL_EVENT_TYPES
        assert RunEvents.STARTED in ALL_EVENT_TYPES
        assert UIEvents.ORDER_UPDATED in ALL_EVENT_TYPES

    def test_all_event_types_contains_every_defined_constant(self) -> None:
        """ALL_EVENT_TYPES must contain every event constant from all Event classes.

        M8-P0 / M-01: Prevents drift between defined constants and validation set.
        Collects all string constants from every *Events class and asserts inclusion.
        """
        from src.events.types import (
            BacktestEvents,
            DataEvents,
            MarketEvents,
        )

        event_classes = [
            StrategyEvents,
            LiveEvents,
            BacktestEvents,
            DataEvents,
            MarketEvents,
            OrderEvents,
            RunEvents,
            ClockEvents,
            UIEvents,
        ]

        missing: list[str] = []
        for cls in event_classes:
            for attr in dir(cls):
                if attr.startswith("_"):
                    continue
                value = getattr(cls, attr)
                if isinstance(value, str) and "." in value:
                    if value not in ALL_EVENT_TYPES:
                        missing.append(f"{cls.__name__}.{attr} = {value!r}")

        assert missing == [], f"Missing from ALL_EVENT_TYPES: {missing}"

    def test_event_types_are_unique(self) -> None:
        """All event types should be unique."""
        all_types = list(ALL_EVENT_TYPES)
        assert len(all_types) == len(set(all_types))

    def test_event_types_have_namespace_prefix(self) -> None:
        """All event types should have a namespace prefix."""
        for event_type in ALL_EVENT_TYPES:
            assert "." in event_type, f"{event_type} missing namespace prefix"
            namespace = event_type.split(".")[0]
            valid_namespaces = {
                "strategy",
                "live",
                "backtest",
                "data",
                "market",
                "orders",
                "run",
                "clock",
                "ui",
            }
            assert namespace in valid_namespaces, f"Unknown namespace: {namespace}"
