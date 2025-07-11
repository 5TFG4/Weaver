"""
Market Data Models
Data structures for market data, trading platforms, and pricing information.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any
import time


@dataclass
class MarketData:
    """Market data for a specific symbol"""
    symbol: str
    price: float
    open_price: float
    high: float
    low: float
    volume: int
    change: float
    change_percent: float
    bid: float
    ask: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return asdict(self)


@dataclass
class PlatformInfo:
    """Trading platform information"""
    name: str
    status: str
    features: List[str]
    limits: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return asdict(self)


@dataclass
class Portfolio:
    """Portfolio positions and balances"""
    cash: float
    positions: Dict[str, int]
    total_value: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return asdict(self)


@dataclass
class MarketDataUpdate:
    """Market data update event payload"""
    symbol: str
    data: MarketData
    request_id: str
    source: str
    timestamp: float
    
    def __init__(self, symbol: str, data: MarketData, request_id: str = "", source: str = "real_time_feed"):
        self.symbol = symbol
        self.data = data
        self.request_id = request_id
        self.source = source
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "symbol": self.symbol,
            "data": self.data.to_dict(),
            "request_id": self.request_id,
            "source": self.source,
            "timestamp": self.timestamp
        }


@dataclass
class PlatformAvailable:
    """Platform availability response"""
    platforms: Dict[str, PlatformInfo]
    request_id: str
    timestamp: float
    
    def __init__(self, platforms: Dict[str, PlatformInfo], request_id: str = ""):
        self.platforms = platforms
        self.request_id = request_id
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "platforms": {pid: platform.to_dict() for pid, platform in self.platforms.items()},
            "request_id": self.request_id,
            "timestamp": self.timestamp
        }
