"""
Paper Trading Connector

A simulated trading connector for backtesting and paper trading.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from decimal import Decimal
import random

from .base_trading_connector import (
    BaseTradingConnector, TradingConnectorConfig, 
    Order, OrderStatus, OrderSide, OrderType,
    Position, Account
)

if TYPE_CHECKING:
    from core.event_bus import EventBus

class PaperTradingConnector(BaseTradingConnector):
    """
    Paper trading connector for simulated trading.
    
    Simulates order fills, position tracking, and account management
    without real money at risk.
    """
    
    def __init__(self, config: TradingConnectorConfig, event_bus: Optional["EventBus"] = None) -> None:
        super().__init__(config, event_bus)
        
        # Initialize paper trading account
        self._account = self._create_default_account()
        
        # Market data simulation
        self._market_prices: Dict[str, Decimal] = {}
        self._price_task: Optional[asyncio.Task[None]] = None
        
    def _create_default_account(self) -> Account:
        """Create a default paper trading account"""
        return Account(
            account_id="paper_account",
            buying_power=Decimal("100000"),  # $100k starting capital
            portfolio_value=Decimal("100000"),
            cash=Decimal("100000"),
            day_trade_buying_power=Decimal("400000")  # 4x leverage
        )
        
    async def connect(self) -> bool:
        """Connect to paper trading system"""
        try:
            # Start price simulation
            self._price_task = asyncio.create_task(self._simulate_prices())
            
            # Initialize default symbols with random prices
            default_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMZN"]
            for symbol in default_symbols:
                self._market_prices[symbol] = Decimal(str(random.uniform(100, 500)))
                
            await self._publish_status_update()
            return True
            
        except Exception as e:
            await self._publish_error(e)
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from paper trading system"""
        if self._price_task and not self._price_task.done():
            self._price_task.cancel()
            try:
                await self._price_task
            except asyncio.CancelledError:
                pass
                
    async def health_check(self) -> bool:
        """Check if paper trading system is healthy"""
        return self._price_task is not None and not self._price_task.done()
        
    async def submit_order(self, order: Order) -> str:
        """Submit a simulated order"""
        # Validate order
        if not await self.validate_order(order):
            raise ValueError("Order validation failed")
            
        # Generate order ID
        order_id = str(uuid.uuid4())
        order.order_id = order_id
        order.created_at = datetime.now().isoformat()
        
        # Store order
        self._orders[order_id] = order
        
        # Simulate order processing
        asyncio.create_task(self._process_order(order))
        
        await self._publish_order_update(order)
        return order_id
        
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a simulated order"""
        if order_id not in self._orders:
            return False
            
        order = self._orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False
            
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now().isoformat()
        
        await self._publish_order_update(order)
        return True
        
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status"""
        return self._orders.get(order_id)
        
    async def get_account_info(self) -> Account:
        """Get simulated account information"""
        # Ensure account is initialized
        if self._account is None:
            self._account = self._create_default_account()
        
        # Update portfolio value based on positions
        portfolio_value = self._account.cash
        
        for position in self._positions.values():
            if position.symbol in self._market_prices:
                current_price = self._market_prices[position.symbol]
                position.market_value = position.quantity * current_price
                position.unrealized_pnl = position.market_value - (position.quantity * position.average_entry_price)
                portfolio_value += position.market_value
                
        self._account.portfolio_value = portfolio_value
        self._account.positions = list(self._positions.values())
        
        return self._account
        
    async def get_positions(self) -> List[Position]:
        """Get current simulated positions"""
        return list(self._positions.values())
        
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                 start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get simulated historical data"""
        # For paper trading, generate simple random walk data
        # In production, this would connect to real data sources
        
        data_points: List[Dict[str, Any]] = []
        current_price = self._market_prices.get(symbol, Decimal("100"))
        
        # Generate 100 data points for simulation
        for _ in range(100):
            # Random walk
            change = Decimal(str(random.uniform(-0.05, 0.05)))  # ±5% change
            current_price = current_price * (1 + change)
            
            data_points.append({
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "open": float(current_price),
                "high": float(current_price * Decimal("1.02")),
                "low": float(current_price * Decimal("0.98")),
                "close": float(current_price),
                "volume": random.randint(1000, 10000)
            })
            
        return data_points
        
    async def _process_order(self, order: Order) -> None:
        """Process a simulated order"""
        # Simulate order processing delay
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Get current market price
        if order.symbol not in self._market_prices:
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.now().isoformat()
            await self._publish_order_update(order)
            return
            
        current_price = self._market_prices[order.symbol]
        
        # Simulate order fill
        if order.order_type == OrderType.MARKET:
            # Market orders fill immediately at current price
            fill_price = current_price
            await self._fill_order(order, fill_price, order.quantity)
            
        elif order.order_type == OrderType.LIMIT:
            # Limit orders fill if price is favorable
            if order.price is None:
                order.status = OrderStatus.REJECTED
                order.updated_at = datetime.now().isoformat()
                await self._publish_order_update(order)
                return
                
            if ((order.side == OrderSide.BUY and current_price <= order.price) or
                (order.side == OrderSide.SELL and current_price >= order.price)):
                await self._fill_order(order, order.price, order.quantity)
            # Otherwise, order remains pending
            
    async def _fill_order(self, order: Order, fill_price: Decimal, fill_quantity: Decimal) -> None:
        """Fill a simulated order"""
        # Ensure account is initialized
        if self._account is None:
            self._account = self._create_default_account()
            
        order.status = OrderStatus.FILLED
        order.filled_quantity = fill_quantity
        order.filled_price = fill_price
        order.updated_at = datetime.now().isoformat()
        
        # Update account and positions
        if order.side == OrderSide.BUY:
            # Buying - reduce cash, increase position
            cost = fill_quantity * fill_price
            commission = cost * self.trading_config.commission_rate
            total_cost = cost + commission
            
            self._account.cash -= total_cost
            self._account.buying_power -= total_cost
            
            # Update position
            if order.symbol in self._positions:
                position = self._positions[order.symbol]
                new_quantity = position.quantity + fill_quantity
                new_average_price = ((position.quantity * position.average_entry_price) + 
                                   (fill_quantity * fill_price)) / new_quantity
                position.quantity = new_quantity
                position.average_entry_price = new_average_price
            else:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=fill_quantity,
                    side="long",
                    market_value=fill_quantity * fill_price,
                    unrealized_pnl=Decimal("0"),
                    average_entry_price=fill_price
                )
                
        else:  # SELL
            # Selling - increase cash, reduce position
            proceeds = fill_quantity * fill_price
            commission = proceeds * self.trading_config.commission_rate
            net_proceeds = proceeds - commission
            
            self._account.cash += net_proceeds
            self._account.buying_power += net_proceeds
            
            # Update position
            if order.symbol in self._positions:
                position = self._positions[order.symbol]
                position.quantity -= fill_quantity
                
                if position.quantity <= 0:
                    del self._positions[order.symbol]
                    
        await self._publish_order_update(order)
        
        # Publish position and account updates
        if order.symbol in self._positions:
            await self._publish_position_update(self._positions[order.symbol])
            
        await self._publish_account_update(self._account)
        
    async def _simulate_prices(self) -> None:
        """Simulate market price movements"""
        while True:
            try:
                # Update prices for all symbols
                for symbol in self._market_prices:
                    # Random walk with slight upward bias
                    change = Decimal(str(random.uniform(-0.03, 0.035)))  # -3% to +3.5%
                    self._market_prices[symbol] = self._market_prices[symbol] * (1 + change)
                    
                    # Ensure prices don't go below $1
                    if self._market_prices[symbol] < Decimal("1"):
                        self._market_prices[symbol] = Decimal("1")
                        
                    # Publish market data update
                    if self.event_bus:
                        await self.event_bus.publish("market_data_update", {
                            "symbol": symbol,
                            "price": float(self._market_prices[symbol]),
                            "timestamp": datetime.now().isoformat(),
                            "connector_name": self.name
                        })
                        
                # Wait before next update
                await asyncio.sleep(5.0)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._publish_error(e)
                await asyncio.sleep(5.0)
