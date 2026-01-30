"""
Event Type Constants

Defines all event type namespaces and specific event types used in the system.
Event types follow the pattern: namespace.EventName[.version]
"""

from typing import Final


# =============================================================================
# Namespaces
# =============================================================================

class Namespace:
    """Event namespace constants."""

    STRATEGY: Final[str] = "strategy"
    LIVE: Final[str] = "live"
    BACKTEST: Final[str] = "backtest"
    DATA: Final[str] = "data"
    MARKET: Final[str] = "market"
    ORDERS: Final[str] = "orders"
    RUN: Final[str] = "run"
    CLOCK: Final[str] = "clock"
    UI: Final[str] = "ui"


# =============================================================================
# Strategy Events (emitted by Marvin)
# =============================================================================

class StrategyEvents:
    """Events emitted by strategy execution."""

    FETCH_WINDOW: Final[str] = "strategy.FetchWindow"
    PLACE_REQUEST: Final[str] = "strategy.PlaceRequest"
    DECISION_MADE: Final[str] = "strategy.DecisionMade"


# =============================================================================
# Live Events (handled by Veda)
# =============================================================================

class LiveEvents:
    """Events for live trading domain."""

    FETCH_WINDOW: Final[str] = "live.FetchWindow"
    PLACE_ORDER: Final[str] = "live.PlaceOrder"


# =============================================================================
# Backtest Events (handled by Greta)
# =============================================================================

class BacktestEvents:
    """Events for backtesting domain."""

    FETCH_WINDOW: Final[str] = "backtest.FetchWindow"
    PLACE_ORDER: Final[str] = "backtest.PlaceOrder"


# =============================================================================
# Data Events
# =============================================================================

class DataEvents:
    """Events related to market data."""

    WINDOW_READY: Final[str] = "data.WindowReady"
    WINDOW_CHUNK: Final[str] = "data.WindowChunk"
    WINDOW_COMPLETE: Final[str] = "data.WindowComplete"


# =============================================================================
# Market Events
# =============================================================================

class MarketEvents:
    """Real-time market events."""

    QUOTE: Final[str] = "market.Quote"
    TRADE: Final[str] = "market.Trade"
    BAR: Final[str] = "market.Bar"


# =============================================================================
# Order Events
# =============================================================================

class OrderEvents:
    """Order lifecycle events."""

    PLACE_REQUEST: Final[str] = "orders.PlaceRequest"
    ACK: Final[str] = "orders.Ack"
    PLACED: Final[str] = "orders.Placed"
    FILLED: Final[str] = "orders.Filled"
    PARTIALLY_FILLED: Final[str] = "orders.PartiallyFilled"
    CANCELLED: Final[str] = "orders.Cancelled"
    REJECTED: Final[str] = "orders.Rejected"


# =============================================================================
# Run Events
# =============================================================================

class RunEvents:
    """Run lifecycle events."""

    STARTED: Final[str] = "run.Started"
    STOP_REQUESTED: Final[str] = "run.StopRequested"
    STOPPED: Final[str] = "run.Stopped"
    HEARTBEAT: Final[str] = "run.Heartbeat"
    ERROR: Final[str] = "run.Error"


# =============================================================================
# Clock Events
# =============================================================================

class ClockEvents:
    """Clock/timing events."""

    TICK: Final[str] = "clock.Tick"


# =============================================================================
# UI Events (thin events for frontend)
# =============================================================================

class UIEvents:
    """Thin events for UI updates."""

    RUN_UPDATED: Final[str] = "ui.RunUpdated"
    ORDER_UPDATED: Final[str] = "ui.OrderUpdated"
    POSITION_UPDATED: Final[str] = "ui.PositionUpdated"
    ACCOUNT_UPDATED: Final[str] = "ui.AccountUpdated"


# =============================================================================
# All Event Types (for validation)
# =============================================================================

ALL_EVENT_TYPES: Final[set[str]] = {
    # Strategy
    StrategyEvents.FETCH_WINDOW,
    StrategyEvents.PLACE_REQUEST,
    StrategyEvents.DECISION_MADE,
    # Live
    LiveEvents.FETCH_WINDOW,
    LiveEvents.PLACE_ORDER,
    # Backtest
    BacktestEvents.FETCH_WINDOW,
    BacktestEvents.PLACE_ORDER,
    # Data
    DataEvents.WINDOW_READY,
    DataEvents.WINDOW_CHUNK,
    DataEvents.WINDOW_COMPLETE,
    # Market
    MarketEvents.QUOTE,
    MarketEvents.TRADE,
    MarketEvents.BAR,
    # Orders
    OrderEvents.PLACE_REQUEST,
    OrderEvents.ACK,
    OrderEvents.PLACED,
    OrderEvents.FILLED,
    OrderEvents.PARTIALLY_FILLED,
    OrderEvents.CANCELLED,
    OrderEvents.REJECTED,
    # Run
    RunEvents.STARTED,
    RunEvents.STOP_REQUESTED,
    RunEvents.STOPPED,
    RunEvents.HEARTBEAT,
    RunEvents.ERROR,
    # Clock
    ClockEvents.TICK,
    # UI
    UIEvents.RUN_UPDATED,
    UIEvents.ORDER_UPDATED,
    UIEvents.POSITION_UPDATED,
    UIEvents.ACCOUNT_UPDATED,
}
