"""
Connector Package - Trading Platform Abstractions

This package provides abstract base classes and implementations for connecting
to various trading platforms and data sources.

Architecture:
- BaseConnector: Abstract base class for all connectors
- BaseTradingConnector: Base class for trading platforms
- BaseDataConnector: Base class for data sources
- Specific implementations: PaperTradingConnector, AlpacaConnector, etc.
"""

from .base_connector import BaseConnector, ConnectorConfig, ConnectorStatus
from .base_trading_connector import (
    BaseTradingConnector, TradingConnectorConfig, 
    Order, OrderStatus, OrderSide, OrderType,
    Position, Account
)
from .base_data_connector import BaseDataConnector, DataConnectorConfig, MarketData, DataType
from .paper_trading_connector import PaperTradingConnector
from .connector_factory import ConnectorFactory, ConnectorType, get_default_connector_configs

__all__ = [
    # Base classes
    "BaseConnector",
    "ConnectorConfig", 
    "ConnectorStatus",
    "BaseTradingConnector",
    "TradingConnectorConfig",
    "BaseDataConnector",
    "DataConnectorConfig",
    
    # Data models
    "Order",
    "OrderStatus",
    "OrderSide", 
    "OrderType",
    "Position",
    "Account",
    "MarketData",
    "DataType",
    
    # Implementations
    "PaperTradingConnector",
    
    # Factory
    "ConnectorFactory",
    "ConnectorType",
    "get_default_connector_configs",
]
