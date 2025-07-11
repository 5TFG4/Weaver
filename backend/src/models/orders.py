"""
Order and Trading Models
Data structures for order requests, executions, and trading operations.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import time


@dataclass
class OrderRequest:
    """Order request structure"""
    symbol: str
    side: str  # buy/sell
    quantity: int
    order_type: str  # market/limit
    strategy: Optional[str] = None
    price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return asdict(self)


@dataclass
class OrderExecution:
    """Order execution result"""
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    status: str  # filled/partial/rejected
    platform: str
    timestamp: float
    strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return asdict(self)


@dataclass
class OrderRequestEvent:
    """Order request event payload"""
    order: OrderRequest
    module: str
    timestamp: float
    
    def __init__(self, order: OrderRequest, module: str):
        self.order = order
        self.module = module
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "order": self.order.to_dict(),
            "module": self.module,
            "timestamp": self.timestamp
        }


@dataclass
class OrderFilledEvent:
    """Order filled event payload"""
    execution: OrderExecution
    portfolio: Optional[Dict[str, Any]] = None
    
    def __init__(self, execution: OrderExecution, portfolio: Optional[Dict[str, Any]] = None):
        self.execution = execution
        self.portfolio = portfolio
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        result = self.execution.to_dict()
        if self.portfolio:
            result["portfolio"] = self.portfolio
        return result
