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
from .adapters.factory import (
    create_adapter_for_mode,
    create_alpaca_adapter,
    create_mock_adapter,
)
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
from .veda_service import VedaService, create_veda_service

__all__ = [
    # Main classes
    "Veda",
    "VedaService",
    # Factory functions
    "create_veda_service",
    "create_alpaca_adapter",
    "create_mock_adapter",
    "create_adapter_for_mode",
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
    "OrderStatus",
    "OrderType",
    "OrderSide",
    "TimeInForce",
    "Fill",
    "AccountInfo",
    "Position",
    "PositionSide",
    "Bar",
    "Quote",
    "Trade",
    # Interfaces
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
