"""
Veda - Live Data & Trading

Handles live trading domain operations:
- Exchange API integration (Alpaca, etc.)
- Real-time market data fetching
- Order submission and tracking
- Rate limiting and caching

Responds to live.* events and emits data.*/market.*/orders.* events.
"""

from .adapters import AlpacaAdapter, MockExchangeAdapter
from .exceptions import (
    ExchangeConnectionError,
    InsufficientFundsError,
    InvalidOrderError,
    OrderNotCancellableError,
    OrderNotFoundError,
    RateLimitError,
    SymbolNotFoundError,
    VedaError,
)
from .interfaces import ExchangeAdapter, ExchangeOrder, OrderSubmitResult
from .models import (
    AccountInfo,
    Bar,
    Fill,
    OrderIntent,
    OrderSide,
    OrderState,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Quote,
    TimeInForce,
    Trade,
)
from .order_manager import OrderManager
from .persistence import OrderRepository, VedaOrder
from .position_tracker import PositionTracker
from .veda import Veda

__all__ = [
    # Main class
    "Veda",
    # Adapters
    "ExchangeAdapter",
    "AlpacaAdapter",
    "MockExchangeAdapter",
    # Managers
    "OrderManager",
    "PositionTracker",
    # Persistence
    "OrderRepository",
    "VedaOrder",
    # Models
    "OrderIntent",
    "OrderState",
    "OrderSide",
    "Fill",
    "AccountInfo",
    "Position",
    "PositionSide",
    "Bar",
    "Quote",
    "Trade",
    # Interfaces
    "ExchangeAdapter",
    "ExchangeOrder",
    "OrderSubmitResult",
    # Exceptions
    "VedaError",
    "ExchangeConnectionError",
    "RateLimitError",
    "OrderNotFoundError",
    "OrderNotCancellableError",
    "InsufficientFundsError",
    "InvalidOrderError",
    "SymbolNotFoundError",
]

