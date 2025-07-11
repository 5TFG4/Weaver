"""
Base Trading Connector

Provides abstract base class for trading platform connectors.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from decimal import Decimal
from enum import Enum

from .base_connector import BaseConnector, ConnectorConfig

if TYPE_CHECKING:
    from core.event_bus import EventBus

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

@dataclass
class TradingConnectorConfig(ConnectorConfig):
    """Configuration for trading connectors"""
    paper_trading: bool = True
    default_order_type: OrderType = OrderType.MARKET
    max_order_size: Optional[Decimal] = None
    min_order_size: Optional[Decimal] = None
    supported_symbols: List[str] = field(default_factory=lambda: [])
    commission_rate: Decimal = Decimal("0.001")  # 0.1%
    
@dataclass
class Order:
    """Order representation"""
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "day"
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    filled_price: Optional[Decimal] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
@dataclass
class Position:
    """Position representation"""
    symbol: str
    quantity: Decimal
    side: str  # "long" or "short"
    market_value: Decimal
    unrealized_pnl: Decimal
    average_entry_price: Decimal
    
@dataclass
class Account:
    """Account information"""
    account_id: str
    buying_power: Decimal
    portfolio_value: Decimal
    cash: Decimal
    day_trade_buying_power: Decimal
    positions: List[Position] = field(default_factory=lambda: [])

class BaseTradingConnector(BaseConnector):
    """
    Abstract base class for trading platform connectors.
    
    Provides common functionality for order management,
    position tracking, and account information.
    """
    
    def __init__(self, config: TradingConnectorConfig, event_bus: Optional["EventBus"] = None) -> None:
        super().__init__(config, event_bus)
        self.trading_config = config
        self._orders: Dict[str, Order] = {}
        self._positions: Dict[str, Position] = {}
        self._account: Optional[Account] = None
        
    @property
    def is_paper_trading(self) -> bool:
        """Check if connector is in paper trading mode"""
        return self.trading_config.paper_trading
        
    @property
    def account(self) -> Optional[Account]:
        """Get current account information"""
        return self._account
        
    @property
    def positions(self) -> Dict[str, Position]:
        """Get current positions"""
        return self._positions.copy()
        
    @property
    def orders(self) -> Dict[str, Order]:
        """Get current orders"""
        return self._orders.copy()
        
    @abstractmethod
    async def submit_order(self, order: Order) -> str:
        """
        Submit an order to the trading platform.
        
        Args:
            order: Order to submit
            
        Returns:
            str: Order ID
        """
        pass
        
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            bool: True if successfully cancelled
        """
        pass
        
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Get order status.
        
        Args:
            order_id: ID of order to check
            
        Returns:
            Order: Order object with current status
        """
        pass
        
    @abstractmethod
    async def get_account_info(self) -> Account:
        """
        Get account information.
        
        Returns:
            Account: Current account information
        """
        pass
        
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List[Position]: Current positions
        """
        pass
        
    @abstractmethod
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                 start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get historical market data.
        
        Args:
            symbol: Trading symbol
            timeframe: Data timeframe (1m, 5m, 1h, 1d, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List[Dict]: Historical data points
        """
        pass
        
    async def validate_order(self, order: Order) -> bool:
        """
        Validate an order before submission.
        
        Args:
            order: Order to validate
            
        Returns:
            bool: True if order is valid
        """
        # Check if symbol is supported
        if (self.trading_config.supported_symbols and 
            order.symbol not in self.trading_config.supported_symbols):
            return False
            
        # Check order size limits
        if self.trading_config.max_order_size and order.quantity > self.trading_config.max_order_size:
            return False
            
        if self.trading_config.min_order_size and order.quantity < self.trading_config.min_order_size:
            return False
            
        # Check if we have sufficient buying power (for live trading)
        if not self.is_paper_trading and self._account:
            if order.side == OrderSide.BUY:
                required_buying_power = order.quantity * (order.price or Decimal("0"))
                if required_buying_power > self._account.buying_power:
                    return False
                    
        return True
        
    async def _publish_order_update(self, order: Order) -> None:
        """Publish order update to event bus"""
        if self.event_bus:
            await self.event_bus.publish("order_update", {
                "connector_name": self.name,
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": float(order.quantity),
                "status": order.status.value,
                "filled_quantity": float(order.filled_quantity),
                "filled_price": float(order.filled_price) if order.filled_price else None
            })
            
    async def _publish_position_update(self, position: Position) -> None:
        """Publish position update to event bus"""
        if self.event_bus:
            await self.event_bus.publish("position_update", {
                "connector_name": self.name,
                "symbol": position.symbol,
                "quantity": float(position.quantity),
                "side": position.side,
                "market_value": float(position.market_value),
                "unrealized_pnl": float(position.unrealized_pnl),
                "average_entry_price": float(position.average_entry_price)
            })
            
    async def _publish_account_update(self, account: Account) -> None:
        """Publish account update to event bus"""
        if self.event_bus:
            await self.event_bus.publish("account_update", {
                "connector_name": self.name,
                "account_id": account.account_id,
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "cash": float(account.cash),
                "day_trade_buying_power": float(account.day_trade_buying_power)
            })
