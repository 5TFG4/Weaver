"""
Marvin - Strategy Execution Module
Dynamically loads and manages trading strategies using the new strategy architecture.
Generates trade signals based on market data and strategy logic.
"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from core.logger import get_logger
from core.event_bus import EventBus
from strategies import StrategyLoader, BaseStrategy, StrategySignal

logger = get_logger(__name__)

class Marvin:
    """
    Strategy Execution Module - Autonomous module for trading strategy management.
    
    Loads strategies using the new architecture, processes market data, and generates trade signals.
    Operates autonomously based on events.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.running = False
        self.ready = False
        
        # Strategy management - now uses BaseStrategy instances
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Market data tracking
        self.latest_market_data: Dict[str, Dict[str, Any]] = {}
        
        # Trading state
        self.platforms_available = False
        self.market_data_active = False
        
        # Subscribe to system events immediately during initialization
        self.event_bus.subscribe("system_init", self._on_system_init)
        self.event_bus.subscribe("system_ready", self._on_system_ready)
        self.event_bus.subscribe("system_terminate", self._on_system_terminate)
        
        logger.info("Marvin initialized - Strategy Execution Module ready")
    
    async def startup(self) -> None:
        """Start Marvin module and register event handlers"""
        logger.info("Marvin starting up - Initializing strategy management...")
        
        # Subscribe to trading-specific events
        self.event_bus.subscribe("platform_available", self._on_platform_available)
        self.event_bus.subscribe("market_data_update", self._on_market_data_update)
        self.event_bus.subscribe("order_filled", self._on_order_filled)
        
        # Load default strategies
        await self._load_strategies()
        
        self.running = True
        self.ready = True
        
        # Report ready to GLaDOS
        await self.event_bus.publish("module_ready", {
            "module": "marvin",
            "status": "ready",
            "strategies_loaded": len(self.strategies),
            "message": "Strategy management system online"
        })
        
        logger.info("Marvin startup complete - Strategy Execution Module online")
    
    async def _on_system_init(self, data: Any) -> None:
        """Handle system initialization"""
        logger.info("Marvin received system_init - Initializing strategies")
        await self.startup()
    
    async def _on_system_ready(self, data: Any) -> None:
        """Handle system ready - start requesting platforms and market data"""
        logger.info("Marvin received system_ready - Beginning trading operations")
        
        # Request trading platforms
        await self.event_bus.publish("trading_platform_request", {
            "module": "marvin",
            "request_id": f"marvin_platform_req_{asyncio.get_event_loop().time()}",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # Start requesting market data for tracked symbols
        await self._request_market_data()
    
    async def _on_system_terminate(self, data: Any) -> None:
        """Handle system termination"""
        logger.info("Marvin received system_terminate - Stopping strategy execution")
        await self.shutdown()
    
    async def _on_platform_available(self, data: Any) -> None:
        """Handle platform availability response"""
        platforms: Dict[str, Dict[str, Any]] = data.get("platforms", {})
        logger.info(f"Platforms available: {list(platforms.keys())}")
        
        self.platforms_available = True
        
        # Log platform capabilities
        for platform_id, platform_info in platforms.items():
            name: str = platform_info.get("name", "Unknown")
            features: List[str] = platform_info.get("features", [])
            logger.info(f"Platform {platform_id}: {name} - {features}")
    
    async def _on_market_data_update(self, data: Any) -> None:
        """Handle market data updates and generate trading signals"""
        symbol: Optional[str] = data.get("symbol")
        market_data: Dict[str, Any] = data.get("data", {})
        
        if not symbol:
            return
            
        # Store latest market data
        self.latest_market_data[symbol] = data
        self.market_data_active = True
        
        price: float = market_data.get("price", 0.0)
        logger.debug(f"Market data update: {symbol} @ ${price:.2f}")
        
        # Process through all strategies
        for strategy_name, strategy in self.strategies.items():
            if not strategy.is_enabled():
                continue
                
            try:
                signal: Optional[StrategySignal] = strategy.analyze(data)
                if signal:
                    await self._execute_signal(signal)
                    
            except Exception as e:
                logger.error(f"Error in strategy {strategy_name}: {e}")
    
    async def _on_order_filled(self, data: Any) -> None:
        """Handle order execution confirmations"""
        order_id: str = data.get("order_id", "")
        symbol: str = data.get("symbol", "")
        side: str = data.get("side", "")
        quantity: int = data.get("quantity", 0)
        price: float = data.get("price", 0.0)
        strategy: str = data.get("strategy", "unknown")
        
        logger.info(f"Order filled: {order_id} - {side} {quantity} {symbol} @ ${price:.2f}")
        
        # Update strategy performance tracking
        if strategy in self.strategy_performance:
            self.strategy_performance[strategy]["trades"] += 1
            if side == "buy":
                self.strategy_performance[strategy]["total_invested"] += quantity * price
            else:
                self.strategy_performance[strategy]["total_returns"] += quantity * price
    
    async def _load_strategies(self) -> None:
        """Load trading strategies using the new architecture"""
        logger.info("Loading trading strategies...")
        
        # Get default strategy configurations
        strategy_configs = StrategyLoader.get_default_strategy_configs()
        
        # Load strategies using the new architecture
        self.strategies = StrategyLoader.load_strategies_from_config(strategy_configs)
        
        # Initialize performance tracking for each strategy
        for strategy_name, strategy in self.strategies.items():
            self.strategy_performance[strategy_name] = {
                "trades": 0,
                "total_invested": 0.0,
                "total_returns": 0.0,
                "active": True
            }
            
            logger.info(f"Loaded strategy: {strategy_name} (symbols: {strategy.symbols})")
        
        # Publish strategy load completion
        await self.event_bus.publish("strategy_load_complete", {
            "strategies": list(self.strategies.keys()),
            "total_loaded": len(self.strategies),
            "timestamp": asyncio.get_event_loop().time()
        })
        
        logger.info(f"Strategy loading complete - {len(self.strategies)} strategies loaded")
    
    async def _request_market_data(self) -> None:
        """Request market data for all symbols tracked by strategies"""
        all_symbols: set[str] = set()
        
        # Collect all symbols from all strategies
        for strategy in self.strategies.values():
            all_symbols.update(strategy.symbols)
        
        logger.info(f"Requesting market data for symbols: {list(all_symbols)}")
        
        # Request market data for each symbol
        for symbol in all_symbols:
            await self.event_bus.publish("market_data_request", {
                "symbol": symbol,
                "type": "real_time",
                "module": "marvin",
                "request_id": f"marvin_data_req_{symbol}_{asyncio.get_event_loop().time()}",
                "timestamp": asyncio.get_event_loop().time()
            })
    
    async def _execute_signal(self, signal: Union[StrategySignal, Dict[str, Any]]) -> None:
        """Execute a trading signal from a StrategySignal object"""
        # Handle both StrategySignal objects and dict signals for backward compatibility
        if isinstance(signal, StrategySignal):
            # It's a StrategySignal object
            signal_dict = signal.to_dict()
        else:
            # It's already a dict
            signal_dict = signal
            
        action: str = signal_dict.get("action", "")
        symbol: str = signal_dict.get("symbol", "")
        quantity: int = signal_dict.get("quantity", 0)
        reason: str = signal_dict.get("reason", "")
        strategy: str = signal_dict.get("strategy", "")
        
        logger.info(f"Trading signal: {action.upper()} {quantity} {symbol} - {reason} (Strategy: {strategy})")
        
        # Check if we have platforms available
        if not self.platforms_available:
            logger.warning("No trading platforms available - signal ignored")
            return
        
        # Publish trade signal for other modules to see
        await self.event_bus.publish("trade_signal", signal_dict)
        
        # Execute order directly
        order_request: Dict[str, Any] = {
            "order": {
                "symbol": symbol,
                "side": action,
                "quantity": quantity,
                "type": "market",
                "strategy": strategy
            },
            "module": "marvin",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.event_bus.publish("order_request", order_request)
        
        logger.info(f"Order request sent: {action} {quantity} {symbol}")
    
    async def _report_health(self) -> None:
        """Report module health status"""
        active_strategies = len([s for s in self.strategies.values() if s.is_enabled()])
        
        health_status: Dict[str, Any] = {
            "module": "marvin",
            "status": "healthy" if self.running and self.ready else "error",
            "strategies_loaded": len(self.strategies),
            "strategies_active": active_strategies,
            "platforms_available": self.platforms_available,
            "market_data_active": self.market_data_active,
            "symbols_tracked": len(self.latest_market_data),
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.event_bus.publish("module_health", health_status)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown Marvin module"""
        logger.info("Marvin shutting down - Stopping strategy execution...")
        
        self.running = False
        
        # Disable all strategies
        for strategy in self.strategies.values():
            strategy.enabled = False  # type: ignore[attr-defined]
        
        # Log final performance
        logger.info("Final strategy performance:")
        for name, perf in self.strategy_performance.items():
            logger.info(f"  {name}: {perf['trades']} trades, "
                       f"${perf['total_invested']:.2f} invested, "
                       f"${perf['total_returns']:.2f} returns")
        
        self.ready = False
        
        # Report shutdown complete
        await self.event_bus.publish("module_shutdown_complete", {
            "module": "marvin",
            "message": "Strategy execution stopped, performance logged"
        })
        
        logger.info("Marvin shutdown complete - Strategy Execution Module offline")


# Utility functions for external access
async def create_marvin(event_bus: EventBus) -> Marvin:
    """Factory function to create and initialize Marvin module"""
    marvin = Marvin(event_bus)
    return marvin
