"""
Veda - Live Data & Trading

Handles live trading domain operations:
- Exchange API integration (Alpaca, etc.)
- Real-time market data fetching
- Order submission and tracking
- Rate limiting and caching

Responds to live.* events and emits data.*/market.*/orders.* events.
"""

from .veda import Veda

__all__ = ["Veda"]
