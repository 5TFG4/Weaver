"""
Veda - Exchange API Manager
Handles all interactions with trading platforms and exchanges.
Provides market data, executes orders, and manages exchange connections.
"""

import asyncio
import random
from typing import Dict, List, Any, Optional
from core.logger import get_logger
from core.event_bus import EventBus

logger = get_logger(__name__)


class PlatformInfo:
    """Type-safe platform information structure"""
    
    def __init__(
        self, 
        name: str, 
        status: str, 
        features: List[str], 
        limits: Dict[str, int]
    ) -> None:
        self.name = name
        self.status = status
        self.features = features
        self.limits = limits
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "name": self.name,
            "status": self.status,
            "features": self.features,
            "limits": self.limits
        }


class Portfolio:
    """Type-safe portfolio management"""
    
    def __init__(self, initial_cash: float = 10000.0) -> None:
        self.cash: float = initial_cash
        self.positions: Dict[str, int] = {}
        self.total_value: float = initial_cash
    
    def update_position(self, symbol: str, side: str, quantity: int, price: float) -> None:
        """Update portfolio positions after trade execution"""
        if side == "buy":
            self.cash -= quantity * price
            self.positions[symbol] = self.positions.get(symbol, 0) + quantity
        elif side == "sell":
            self.cash += quantity * price
            self.positions[symbol] = self.positions.get(symbol, 0) - quantity
        
        # Update total value calculation
        self._recalculate_total_value()
    
    def _recalculate_total_value(self) -> None:
        """Recalculate total portfolio value"""
        # For simplicity, just use cash + position count * avg price
        position_value = sum(abs(qty) * 100 for qty in self.positions.values())  # Dummy calculation
        self.total_value = self.cash + position_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "cash": self.cash,
            "positions": self.positions.copy(),
            "total_value": self.total_value
        }


class MarketData:
    """Type-safe market data structure"""
    
    def __init__(
        self,
        symbol: str,
        price: float,
        open_price: float,
        high: float,
        low: float,
        volume: int,
        change: float,
        change_percent: float,
        bid: float,
        ask: float,
        timestamp: float
    ) -> None:
        self.symbol = symbol
        self.price = price
        self.open = open_price
        self.high = high
        self.low = low
        self.volume = volume
        self.change = change
        self.change_percent = change_percent
        self.bid = bid
        self.ask = ask
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "change": self.change,
            "change_percent": self.change_percent,
            "bid": self.bid,
            "ask": self.ask,
            "timestamp": self.timestamp
        }


class OrderRequest:
    """Type-safe order request structure"""
    
    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        strategy: Optional[str] = None
    ) -> None:
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.order_type = order_type
        self.strategy = strategy


class OrderExecution:
    """Type-safe order execution result"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        status: str,
        platform: str,
        timestamp: float,
        strategy: Optional[str] = None
    ) -> None:
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.status = status
        self.platform = platform
        self.timestamp = timestamp
        self.strategy = strategy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for event publishing"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status,
            "platform": self.platform,
            "timestamp": self.timestamp,
            "strategy": self.strategy
        }


class Veda:
    """
    Exchange API Manager - Autonomous module for trading platform integration.
    
    Handles platform discovery, market data provision, and order execution.
    Operates autonomously based on event requests.
    """
    
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus: EventBus = event_bus
        self.running: bool = False
        self.ready: bool = False
        
        # Platform management with type safety
        self.available_platforms: Dict[str, PlatformInfo] = self._initialize_platforms()
        
        # Portfolio management
        self.portfolio: Portfolio = Portfolio(initial_cash=10000.0)
        
        # Market data management
        self.market_data_cache: Dict[str, MarketData] = {}
        self.base_prices: Dict[str, float] = {
            "AAPL": 175.0,
            "GOOGL": 140.0,
            "MSFT": 380.0,
            "TSLA": 250.0,
            "NVDA": 450.0
        }
        
        # Order tracking
        self.order_counter: int = 10000
        
        # Subscribe to system events immediately during initialization
        self.event_bus.subscribe("system_init", self._on_system_init)
        self.event_bus.subscribe("system_terminate", self._on_system_terminate)
        
        logger.info("Veda initialized - Exchange API Manager ready")
    
    def _initialize_platforms(self) -> Dict[str, PlatformInfo]:
        """Initialize available trading platforms with type safety"""
        platforms: Dict[str, PlatformInfo] = {}
        
        platforms["alpaca"] = PlatformInfo(
            name="Alpaca Markets",
            status="connected",
            features=["stocks", "crypto", "real_time_data"],
            limits={"daily_trades": 200, "api_calls": 1000}
        )
        
        platforms["paper_trading"] = PlatformInfo(
            name="Paper Trading Simulator",
            status="connected", 
            features=["stocks", "crypto", "options", "simulation"],
            limits={"daily_trades": 999999, "api_calls": 999999}
        )
        
        return platforms
    
    async def startup(self) -> None:
        """Start Veda module and register event handlers"""
        logger.info("Veda starting up - Initializing exchange connections...")
        
        # Subscribe to trading-specific events
        self.event_bus.subscribe("trading_platform_request", self._on_platform_request)
        self.event_bus.subscribe("market_data_request", self._on_market_data_request)
        self.event_bus.subscribe("order_request", self._on_order_request)
        
        # Simulate connection setup with realistic delay
        await asyncio.sleep(0.5)
        
        self.running = True
        self.ready = True
        
        # Report ready to GLaDOS with typed data
        ready_data: Dict[str, Any] = {
            "module": "veda",
            "status": "ready",
            "platforms": len(self.available_platforms),
            "message": "Exchange connections established"
        }
        await self.event_bus.publish("module_ready", ready_data)
        
        # Start market data simulation task
        asyncio.create_task(self._market_data_simulator())
        
        logger.info("Veda startup complete - Exchange API Manager online")
    
    async def _on_system_init(self, data: Any) -> None:
        """Handle system initialization event"""
        logger.info("Veda received system_init - Starting exchange connections")
        await self.startup()
    
    async def _on_system_terminate(self, data: Any) -> None:
        """Handle system termination event"""
        logger.info("Veda received system_terminate - Closing exchange connections")
        await self.shutdown()
    
    def _safe_get(self, data: Any, key: str, default: Any = None) -> Any:
        """Safely get value from data dictionary with proper typing"""
        if hasattr(data, 'get'):
            return data.get(key, default)
        return default
    
    async def _on_platform_request(self, data: Any) -> None:
        """Handle trading platform availability requests"""
        # Type-safe data extraction
        request_id: Optional[str] = self._safe_get(data, "request_id")
        
        logger.info(f"Platform request received, request_id: {request_id}")
        
        # Convert platforms to serializable format
        platforms_dict: Dict[str, Dict[str, Any]] = {
            platform_id: platform.to_dict() 
            for platform_id, platform in self.available_platforms.items()
        }
        
        # Respond with available platforms
        response_data: Dict[str, Any] = {
            "platforms": platforms_dict,
            "request_id": request_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.event_bus.publish("platform_available", response_data)
        
        logger.info(f"Platform availability sent: {len(self.available_platforms)} platforms")
    
    async def _on_market_data_request(self, data: Any) -> None:
        """Handle market data requests with type safety"""
        # Type-safe data extraction
        symbol: str = self._safe_get(data, "symbol", "AAPL")
        data_type: str = self._safe_get(data, "type", "real_time")
        request_id: Optional[str] = self._safe_get(data, "request_id")
        
        logger.info(f"Market data request: {symbol} ({data_type})")
        
        # Generate typed market data
        market_data: MarketData = self._generate_market_data(symbol)
        
        # Publish market data update
        update_data: Dict[str, Any] = {
            "symbol": symbol,
            "data": market_data.to_dict(),
            "request_id": request_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.event_bus.publish("market_data_update", update_data)
        
        logger.info(f"Market data sent for {symbol}")
    
    async def _on_order_request(self, data: Any) -> None:
        """Handle order execution requests with full type safety"""
        # Type-safe data extraction
        order_data: Dict[str, Any] = self._safe_get(data, "order", {})
        
        # Parse order request with type safety
        order_request = OrderRequest(
            symbol=self._safe_get(order_data, "symbol", "AAPL"),
            side=self._safe_get(order_data, "side", "buy"),
            quantity=int(self._safe_get(order_data, "quantity", 1)),
            order_type=self._safe_get(order_data, "type", "market"),
            strategy=self._safe_get(order_data, "strategy")
        )
        
        logger.info(f"Order request: {order_request.side} {order_request.quantity} "
                   f"{order_request.symbol} ({order_request.order_type})")
        
        # Simulate order execution with realistic delay
        await asyncio.sleep(0.1)
        
        # Execute order and get result
        execution: OrderExecution = await self._execute_order(order_request)
        
        # Update portfolio
        self.portfolio.update_position(
            execution.symbol,
            execution.side, 
            execution.quantity,
            execution.price
        )
        
        # Publish order filled event with portfolio update
        filled_data: Dict[str, Any] = execution.to_dict()
        filled_data["portfolio"] = self.portfolio.to_dict()
        
        await self.event_bus.publish("order_filled", filled_data)
        
        logger.info(f"Order executed: {execution.order_id} - {execution.side} "
                   f"{execution.quantity} {execution.symbol} @ ${execution.price:.2f}")
    
    async def _execute_order(self, order_request: OrderRequest) -> OrderExecution:
        """Execute an order and return typed result"""
        # Generate unique order ID
        self.order_counter += 1
        order_id: str = f"order_{self.order_counter}"
        
        # Get current market price
        execution_price: float = self._get_current_price(order_request.symbol)
        
        # Create order execution result
        execution = OrderExecution(
            order_id=order_id,
            symbol=order_request.symbol,
            side=order_request.side,
            quantity=order_request.quantity,
            price=execution_price,
            status="filled",
            platform="paper_trading",
            timestamp=asyncio.get_event_loop().time(),
            strategy=order_request.strategy
        )
        
        return execution
    
    async def _market_data_simulator(self) -> None:
        """Simulate real-time market data updates with type safety"""
        symbols: List[str] = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        
        while self.running:
            for symbol in symbols:
                if not self.running:
                    break
                
                # Generate typed market data
                market_data: MarketData = self._generate_market_data(symbol)
                
                # Publish market data update
                update_data: Dict[str, Any] = {
                    "symbol": symbol,
                    "data": market_data.to_dict(),
                    "source": "real_time_feed",
                    "timestamp": asyncio.get_event_loop().time()
                }
                await self.event_bus.publish("market_data_update", update_data)
            
            # Wait before next update cycle
            await asyncio.sleep(5)
    
    def _generate_market_data(self, symbol: str) -> MarketData:
        """Generate dummy market data with full type safety"""
        base_price: float = self.base_prices.get(symbol, 100.0)
        
        # Add random variation
        variation: float = random.uniform(-5.0, 5.0)
        current_price: float = base_price + variation
        
        # Generate OHLCV data with proper types
        high: float = current_price + random.uniform(0, 2.0)
        low: float = current_price - random.uniform(0, 2.0) 
        open_price: float = low + random.uniform(0, high - low)
        volume: int = random.randint(1000000, 10000000)
        change: float = current_price - base_price
        change_percent: float = (change / base_price) * 100
        
        # Create typed market data object
        market_data = MarketData(
            symbol=symbol,
            price=round(current_price, 2),
            open_price=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            volume=volume,
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            bid=round(current_price - 0.01, 2),
            ask=round(current_price + 0.01, 2),
            timestamp=asyncio.get_event_loop().time()
        )
        
        # Cache the data
        self.market_data_cache[symbol] = market_data
        
        return market_data
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol with type safety"""
        if symbol in self.market_data_cache:
            return self.market_data_cache[symbol].price
        else:
            # Generate fresh market data if not cached
            market_data: MarketData = self._generate_market_data(symbol)
            return market_data.price
    
    async def _report_health(self) -> None:
        """Report module health status with typed data"""
        connected_platforms: int = len([
            p for p in self.available_platforms.values() 
            if p.status == "connected"
        ])
        
        health_status: Dict[str, Any] = {
            "module": "veda",
            "status": "healthy" if self.running and self.ready else "error",
            "platforms_connected": connected_platforms,
            "total_platforms": len(self.available_platforms),
            "portfolio_value": self.portfolio.total_value,
            "cached_symbols": len(self.market_data_cache),
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.event_bus.publish("module_health", health_status)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown Veda module with proper cleanup"""
        logger.info("Veda shutting down - Closing exchange connections...")
        
        # Stop operations
        self.running = False
        
        # Cancel any pending orders (simulation)
        logger.info("Cancelling pending orders...")
        await asyncio.sleep(0.2)
        
        # Close exchange connections (simulation) 
        logger.info("Closing exchange API connections...")
        for platform in self.available_platforms.values():
            platform.status = "disconnected"
        await asyncio.sleep(0.3)
        
        # Clear caches
        self.market_data_cache.clear()
        
        self.ready = False
        
        # Report shutdown complete with typed data
        shutdown_data: Dict[str, Any] = {
            "module": "veda",
            "message": "Exchange connections closed, pending orders cancelled"
        }
        await self.event_bus.publish("module_shutdown_complete", shutdown_data)
        
        logger.info("Veda shutdown complete - Exchange API Manager offline")


# Factory function with proper typing
async def create_veda(event_bus: EventBus) -> Veda:
    """Factory function to create and initialize Veda module"""
    veda: Veda = Veda(event_bus)
    return veda
