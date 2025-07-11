"""
Base Data Connector

Provides abstract base class for market data connectors.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from decimal import Decimal
from enum import Enum

from .base_connector import BaseConnector, ConnectorConfig

if TYPE_CHECKING:
    from core.event_bus import EventBus

class DataType(Enum):
    """Data type enumeration"""
    TICK = "tick"
    QUOTE = "quote"
    TRADE = "trade"
    BAR = "bar"
    NEWS = "news"

@dataclass
class DataConnectorConfig(ConnectorConfig):
    """Configuration for data connectors"""
    supported_symbols: List[str] = field(default_factory=lambda: [])
    data_types: List[DataType] = field(default_factory=lambda: [DataType.TICK, DataType.QUOTE, DataType.TRADE])
    update_frequency: float = 1.0  # seconds
    buffer_size: int = 1000
    
@dataclass
class MarketData:
    """Market data representation"""
    symbol: str
    timestamp: str
    data_type: DataType
    price: Optional[Decimal] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    bid_size: Optional[Decimal] = None
    ask_size: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    close: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=lambda: {})

class BaseDataConnector(BaseConnector):
    """
    Abstract base class for market data connectors.
    
    Provides common functionality for market data streaming,
    historical data retrieval, and data normalization.
    """
    
    def __init__(self, config: DataConnectorConfig, event_bus: Optional["EventBus"] = None) -> None:
        super().__init__(config, event_bus)  # type: ignore
        self.data_config = config
        self._subscriptions: Dict[str, List[DataType]] = {}
        self._data_buffer: Dict[str, List[MarketData]] = {}
        
    @property
    def subscriptions(self) -> Dict[str, List[DataType]]:
        """Get current subscriptions"""
        return self._subscriptions.copy()
        
    @abstractmethod
    async def subscribe_market_data(self, symbol: str, data_types: List[DataType]) -> bool:
        """
        Subscribe to market data for a symbol.
        
        Args:
            symbol: Trading symbol
            data_types: List of data types to subscribe to
            
        Returns:
            bool: True if subscription successful
        """
        pass
        
    @abstractmethod
    async def unsubscribe_market_data(self, symbol: str, data_types: Optional[List[DataType]] = None) -> bool:
        """
        Unsubscribe from market data.
        
        Args:
            symbol: Trading symbol
            data_types: List of data types to unsubscribe from (None = all)
            
        Returns:
            bool: True if unsubscription successful
        """
        pass
        
    @abstractmethod
    async def get_latest_data(self, symbol: str, data_type: DataType) -> Optional[MarketData]:
        """
        Get latest market data for a symbol.
        
        Args:
            symbol: Trading symbol
            data_type: Type of data to retrieve
            
        Returns:
            MarketData: Latest market data or None
        """
        pass
        
    @abstractmethod
    async def get_historical_data(self, symbol: str, data_type: DataType, 
                                 start_date: str, end_date: str, 
                                 timeframe: str = "1m") -> List[MarketData]:
        """
        Get historical market data.
        
        Args:
            symbol: Trading symbol
            data_type: Type of data to retrieve
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Data timeframe (1m, 5m, 1h, 1d, etc.)
            
        Returns:
            List[MarketData]: Historical data points
        """
        pass
        
    async def add_subscription(self, symbol: str, data_types: List[DataType]) -> bool:
        """
        Add a subscription for market data.
        
        Args:
            symbol: Trading symbol
            data_types: List of data types to subscribe to
            
        Returns:
            bool: True if subscription successful
        """
        # Check if symbol is supported
        if (self.data_config.supported_symbols and 
            symbol not in self.data_config.supported_symbols):
            return False
            
        # Check if data types are supported
        unsupported_types = [dt for dt in data_types if dt not in self.data_config.data_types]
        if unsupported_types:
            return False
            
        # Add to internal subscriptions
        if symbol not in self._subscriptions:
            self._subscriptions[symbol] = []
            
        for data_type in data_types:
            if data_type not in self._subscriptions[symbol]:
                self._subscriptions[symbol].append(data_type)
                
        # Initialize data buffer
        if symbol not in self._data_buffer:
            self._data_buffer[symbol] = []
            
        # Subscribe to external data source
        success = await self.subscribe_market_data(symbol, data_types)
        
        if success:
            await self._publish_subscription_update(symbol, data_types, "subscribed")
            
        return success
        
    async def remove_subscription(self, symbol: str, data_types: Optional[List[DataType]] = None) -> bool:
        """
        Remove a subscription for market data.
        
        Args:
            symbol: Trading symbol
            data_types: List of data types to unsubscribe from (None = all)
            
        Returns:
            bool: True if unsubscription successful
        """
        if symbol not in self._subscriptions:
            return False
            
        if data_types is None:
            # Remove all subscriptions for symbol
            data_types = self._subscriptions[symbol].copy()
            
        # Remove from internal subscriptions
        for data_type in data_types:
            if data_type in self._subscriptions[symbol]:
                self._subscriptions[symbol].remove(data_type)
                
        # Clean up empty subscriptions
        if not self._subscriptions[symbol]:
            del self._subscriptions[symbol]
            if symbol in self._data_buffer:
                del self._data_buffer[symbol]
                
        # Unsubscribe from external data source
        success = await self.unsubscribe_market_data(symbol, data_types)
        
        if success:
            await self._publish_subscription_update(symbol, data_types, "unsubscribed")
            
        return success
        
    async def process_market_data(self, data: MarketData) -> None:
        """
        Process incoming market data.
        
        Args:
            data: Market data to process
        """
        # Add to buffer
        if data.symbol in self._data_buffer:
            self._data_buffer[data.symbol].append(data)
            
            # Maintain buffer size
            if len(self._data_buffer[data.symbol]) > self.data_config.buffer_size:
                self._data_buffer[data.symbol] = self._data_buffer[data.symbol][-self.data_config.buffer_size:]
                
        # Publish to event bus
        await self._publish_market_data_update(data)
        
    async def _publish_market_data_update(self, data: MarketData) -> None:
        """Publish market data update to event bus"""
        if self.event_bus:
            await self.event_bus.publish("market_data_update", {
                "connector_name": self.name,
                "symbol": data.symbol,
                "timestamp": data.timestamp,
                "data_type": data.data_type.value,
                "price": float(data.price) if data.price else None,
                "bid": float(data.bid) if data.bid else None,
                "ask": float(data.ask) if data.ask else None,
                "volume": float(data.volume) if data.volume else None,
                "bid_size": float(data.bid_size) if data.bid_size else None,
                "ask_size": float(data.ask_size) if data.ask_size else None,
                "high": float(data.high) if data.high else None,
                "low": float(data.low) if data.low else None,
                "open": float(data.open) if data.open else None,
                "close": float(data.close) if data.close else None,
                "metadata": data.metadata
            })
            
    async def _publish_subscription_update(self, symbol: str, data_types: List[DataType], action: str) -> None:
        """Publish subscription update to event bus"""
        if self.event_bus:
            await self.event_bus.publish("subscription_update", {
                "connector_name": self.name,
                "symbol": symbol,
                "data_types": [dt.value for dt in data_types],
                "action": action
            })
