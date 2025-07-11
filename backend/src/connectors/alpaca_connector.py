"""
Alpaca Trading Connector

Real exchange connector for Alpaca Markets.
Supports both live trading and paper trading modes.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from decimal import Decimal
from dataclasses import dataclass

try:
    import aiohttp
    aiohttp_available = True
except ImportError:
    aiohttp_available = False
    if TYPE_CHECKING:
        import aiohttp

from core.logger import get_logger
from .base_trading_connector import (
    BaseTradingConnector, TradingConnectorConfig, 
    Order, OrderStatus, OrderType,
    Position, Account
)

if TYPE_CHECKING:
    from core.event_bus import EventBus

@dataclass
class AlpacaConnectorConfig(TradingConnectorConfig):
    """Alpaca-specific configuration"""
    api_key: str = ""
    secret_key: str = ""
    paper_trading: bool = True  # Default to paper trading for safety
    
class AlpacaConnector(BaseTradingConnector):
    """
    Alpaca Markets trading connector.
    
    Supports both paper trading and live trading through configuration.
    Uses Alpaca's REST API for order management and account data.
    """
    
    def __init__(self, config: AlpacaConnectorConfig, event_bus: Optional["EventBus"] = None) -> None:
        super().__init__(config, event_bus)
        
        if not aiohttp_available:
            raise ImportError("aiohttp is required for Alpaca connector. Install with: pip install aiohttp")
            
        self.alpaca_config = config
        self.logger = get_logger(__name__)
        
        # Check if this is a data-only connector
        self.is_data_only = config.parameters.get("data_only", False)
        self.enable_trading = config.parameters.get("enable_trading", True)
        
        # Validate configuration before proceeding
        self._validate_config()
        
        # Set base URLs based on paper trading mode
        if config.paper_trading:
            self.base_url = "https://paper-api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
            
        # HTTP session for API calls
        self._session: Optional[Any] = None
        
        # Market data streaming
        self._market_data_task: Optional[asyncio.Task[None]] = None
        
    @property
    def headers(self) -> Dict[str, str]:
        """Get authentication headers for Alpaca API"""
        return {
            "APCA-API-KEY-ID": self.alpaca_config.api_key,
            "APCA-API-SECRET-KEY": self.alpaca_config.secret_key,
            "Content-Type": "application/json"
        }
        
    async def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            # Log connection attempt
            mode = "Data-Only" if self.is_data_only else ("Paper Trading" if self.alpaca_config.paper_trading else "Live Trading")
            self.logger.info(f"Connecting to Alpaca API - Mode: {mode}")
            self.logger.info(f"Base URL: {self.base_url}")
            self.logger.info(f"Data URL: {self.data_url}")
            self.logger.info(f"API Key: {self.alpaca_config.api_key[:8]}..." if self.alpaca_config.api_key else "No API Key")
            
            # Create HTTP session
            self._session = aiohttp.ClientSession(  # type: ignore
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)  # type: ignore
            )
            
            # Test connection
            if self.is_data_only:
                # For data-only connectors, just test data API access
                self.logger.info("Testing data API access...")
                test_success = await self._test_data_api()
                if test_success:
                    self.logger.info("✓ Data API connection successful")
                else:
                    self.logger.error("❌ Data API connection failed")
                    return False
            else:
                # For trading connectors, test account access
                self.logger.info("Testing connection with account info request...")
                account_info = await self._get_account_info()
                if account_info:
                    self._account = account_info
                    self.logger.info(f"✓ Connected to Alpaca - Account: {account_info.account_id}")
                else:
                    self.logger.error("❌ Failed to get account info from Alpaca")
                    return False
                
            # Start market data streaming for configured symbols
            # Only start if market data is enabled and we're not in trading-only mode
            if (self.alpaca_config.supported_symbols and 
                self.alpaca_config.parameters.get("enable_market_data", True)):
                
                # If this is a paper trading connector, check if we have a separate data connector
                if self.alpaca_config.paper_trading and not self.is_data_only:
                    # Skip market data for paper trading if we have live data available
                    live_api_key = os.getenv("ALPACA_API_KEY", "")
                    if live_api_key:
                        self.logger.info("⏭️  Skipping market data streaming (live data connector available)")
                    else:
                        self.logger.info(f"Starting market data streaming for {len(self.alpaca_config.supported_symbols)} symbols")
                        self._market_data_task = asyncio.create_task(
                            self._stream_market_data()
                        )
                else:
                    # For live trading or data-only connectors, always start market data
                    self.logger.info(f"Starting market data streaming for {len(self.alpaca_config.supported_symbols)} symbols")
                    self._market_data_task = asyncio.create_task(
                        self._stream_market_data()
                    )
                
            await self._publish_status_update()
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Connection error: {e}")
            await self._publish_error(e)
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from Alpaca API"""
        self.logger.info("Disconnecting from Alpaca API...")
        
        # Stop market data streaming
        if self._market_data_task and not self._market_data_task.done():
            self.logger.info("Stopping market data streaming...")
            self._market_data_task.cancel()
            try:
                await self._market_data_task
            except asyncio.CancelledError:
                pass
                
        # Close HTTP session
        if self._session and not self._session.closed:
            self.logger.info("Closing HTTP session...")
            try:
                await self._session.close()
            except Exception as e:
                self.logger.error(f"Error closing session: {e}")
                
        self.logger.info("✓ Alpaca connector disconnected")
            
    async def health_check(self) -> bool:
        """Check if Alpaca API connection is healthy"""
        if not self._session or self._session.closed:
            return False
            
        try:
            async with self._session.get(
                f"{self.base_url}/v2/account",
                headers=self.headers
            ) as response:
                return response.status == 200
        except Exception:
            return False
            
    async def submit_order(self, order: Order) -> str:
        """Submit order to Alpaca"""
        if self.is_data_only or not self.enable_trading:
            raise ValueError("Trading is disabled for this connector")
            
        if not self._session:
            raise ConnectionError("Not connected to Alpaca API")
            
        # Validate order
        if not await self.validate_order(order):
            raise ValueError("Order validation failed")
            
        # Prepare order data for Alpaca API
        order_data = {
            "symbol": order.symbol,
            "qty": str(order.quantity),
            "side": order.side.value,
            "type": self._convert_order_type(order.order_type),
            "time_in_force": "day"  # Default to day orders
        }
        
        # Add price for limit orders
        if order.order_type == OrderType.LIMIT and order.price:
            order_data["limit_price"] = str(order.price)
            
        try:
            async with self._session.post(
                f"{self.base_url}/v2/orders",
                headers=self.headers,
                json=order_data
            ) as response:
                
                if response.status == 201:
                    result = await response.json()
                    order_id = result["id"]
                    
                    # Update order with Alpaca response
                    order.order_id = order_id
                    order.created_at = result["created_at"]
                    order.status = self._convert_order_status(result["status"])
                    
                    # Store order
                    self._orders[order_id] = order
                    
                    await self._publish_order_update(order)
                    return order_id
                else:
                    error_text = await response.text()
                    raise Exception(f"Alpaca order submission failed: {response.status} - {error_text}")
                    
        except Exception as e:
            await self._publish_error(e)
            raise
            
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order on Alpaca"""
        if not self._session:
            return False
            
        try:
            async with self._session.delete(
                f"{self.base_url}/v2/orders/{order_id}",
                headers=self.headers
            ) as response:
                
                if response.status == 204:
                    # Update local order status
                    if order_id in self._orders:
                        order = self._orders[order_id]
                        order.status = OrderStatus.CANCELLED
                        order.updated_at = datetime.now().isoformat()
                        await self._publish_order_update(order)
                    return True
                    
                return False
                
        except Exception as e:
            await self._publish_error(e)
            return False
            
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status from Alpaca"""
        if not self._session:
            return None
            
        try:
            async with self._session.get(
                f"{self.base_url}/v2/orders/{order_id}",
                headers=self.headers
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Update local order if it exists
                    if order_id in self._orders:
                        order = self._orders[order_id]
                        order.status = self._convert_order_status(result["status"])
                        order.filled_quantity = Decimal(result["filled_qty"] or "0")
                        if result["filled_avg_price"]:
                            order.filled_price = Decimal(result["filled_avg_price"])
                        order.updated_at = result["updated_at"]
                        
                        await self._publish_order_update(order)
                        return order
                        
        except Exception as e:
            await self._publish_error(e)
            
        return None
        
    async def get_account_info(self) -> Account:
        """Get account information from Alpaca"""
        account_info = await self._get_account_info()
        if account_info:
            self._account = account_info
            return account_info
        elif self._account:
            return self._account
        else:
            # Return default account if none available
            return Account(
                account_id="alpaca_account",
                buying_power=Decimal("0"),
                portfolio_value=Decimal("0"),
                cash=Decimal("0"),
                day_trade_buying_power=Decimal("0")
            )
            
    async def get_positions(self) -> List[Position]:
        """Get positions from Alpaca"""
        if not self._session:
            return []
            
        try:
            async with self._session.get(
                f"{self.base_url}/v2/positions",
                headers=self.headers
            ) as response:
                
                if response.status == 200:
                    positions_data = await response.json()
                    positions: List[Position] = []
                    
                    for pos_data in positions_data:
                        position = Position(
                            symbol=pos_data["symbol"],
                            quantity=Decimal(pos_data["qty"]),
                            side="long" if Decimal(pos_data["qty"]) > 0 else "short",
                            market_value=Decimal(pos_data["market_value"]),
                            unrealized_pnl=Decimal(pos_data["unrealized_pl"]),
                            average_entry_price=Decimal(pos_data["avg_entry_price"])
                        )
                        positions.append(position)
                        
                    # Update local positions cache
                    self._positions = {pos.symbol: pos for pos in positions}
                    return positions
                    
        except Exception as e:
            await self._publish_error(e)
            
        return []
        
    async def get_historical_data(self, symbol: str, timeframe: str, 
                                 start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get historical data from Alpaca"""
        if not self._session:
            return []
            
        try:
            # Convert timeframe to Alpaca format
            alpaca_timeframe = self._convert_timeframe(timeframe)
            
            params: Dict[str, Any] = {
                "symbols": symbol,
                "timeframe": alpaca_timeframe,
                "start": start_date,
                "end": end_date,
                "limit": 1000
            }
            
            async with self._session.get(
                f"{self.data_url}/v2/stocks/bars",
                headers=self.headers,
                params=params
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    bars = result.get("bars", {}).get(symbol, [])
                    
                    historical_data: List[Dict[str, Any]] = []
                    for bar in bars:
                        historical_data.append({
                            "timestamp": bar["t"],
                            "symbol": symbol,
                            "open": float(bar["o"]),
                            "high": float(bar["h"]),
                            "low": float(bar["l"]),
                            "close": float(bar["c"]),
                            "volume": int(bar["v"])
                        })
                        
                    return historical_data
                    
        except Exception as e:
            await self._publish_error(e)
            
        return []
        
    async def _get_account_info(self) -> Optional[Account]:
        """Internal method to fetch account info from Alpaca"""
        if not self._session:
            return None
            
        try:
            async with self._session.get(
                f"{self.base_url}/v2/account",
                headers=self.headers
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    return Account(
                        account_id=result["id"],
                        buying_power=Decimal(result["buying_power"]),
                        portfolio_value=Decimal(result["portfolio_value"]),
                        cash=Decimal(result["cash"]),
                        day_trade_buying_power=Decimal(result["daytrading_buying_power"])
                    )
                else:
                    error_text = await response.text()
                    self.logger.error(f"❌ Alpaca API error - Status: {response.status}, Response: {error_text}")
                    
        except Exception as e:
            self.logger.error(f"❌ Account info request failed: {e}")
            await self._publish_error(e)
            
        return None
        
    async def _test_data_api(self) -> bool:
        """Test data API access for data-only connectors"""
        if not self._session:
            return False
            
        try:
            # Test with a simple request for latest bars
            params = {"symbols": "AAPL"}
            async with self._session.get(
                f"{self.data_url}/v2/stocks/bars/latest",
                headers=self.headers,
                params=params
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return "bars" in result and len(result["bars"]) > 0
                else:
                    error_text = await response.text()
                    self.logger.error(f"❌ Data API error - Status: {response.status}, Response: {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Data API test failed: {e}")
            return False
        
    async def _stream_market_data(self) -> None:
        """Stream real-time market data from Alpaca"""
        while True:
            try:
                # Check if session is available
                if not self._session or self._session.closed:
                    await asyncio.sleep(10.0)
                    continue
                    
                # Try multiple data sources for better market data
                
                for symbol in self.alpaca_config.supported_symbols:
                    try:
                        # First try to get latest trades (more reliable than quotes)
                        params = {"symbols": symbol}
                        async with self._session.get(
                            f"{self.data_url}/v2/stocks/trades/latest",
                            headers=self.headers,
                            params=params
                        ) as response:
                            
                            if response.status == 200:
                                result = await response.json()
                                trades = result.get("trades", {})
                                
                                if symbol in trades:
                                    trade = trades[symbol]
                                    price = Decimal(trade["p"])
                                    
                                    # Debug logging
                                    self.logger.info(f"📊 {symbol} Trade: ${price} (from {trade['p']})")
                                    
                                    # Publish market data update
                                    if self.event_bus:
                                        await self.event_bus.publish("market_data_update", {
                                            "symbol": symbol,
                                            "data": {
                                                "price": float(price),
                                                "bid": float(price),  # Use trade price for bid/ask
                                                "ask": float(price),
                                                "timestamp": trade["t"],
                                                "connector_name": self.name,
                                                "volume": trade["s"]
                                            }
                                        })
                                    continue  # Move to next symbol
                        
                        # If trades don't work, try quotes
                        async with self._session.get(
                            f"{self.data_url}/v2/stocks/quotes/latest",
                            headers=self.headers,
                            params=params
                        ) as response:
                            
                            if response.status == 200:
                                result = await response.json()
                                quotes = result.get("quotes", {})
                                
                                if symbol in quotes:
                                    quote = quotes[symbol]
                                    bid = Decimal(quote["bp"])
                                    ask = Decimal(quote["ap"])
                                    
                                    # Debug logging
                                    self.logger.info(f"💰 {symbol} Quote: Bid ${bid}, Ask ${ask}")
                                    
                                    # Skip if bid/ask are zero
                                    if bid > 0 and ask > 0:
                                        price = (bid + ask) / 2  # Mid price
                                        
                                        # Publish market data update
                                        if self.event_bus:
                                            await self.event_bus.publish("market_data_update", {
                                                "symbol": symbol,
                                                "data": {
                                                    "price": float(price),
                                                    "bid": float(bid),
                                                    "ask": float(ask),
                                                    "timestamp": quote["t"],
                                                    "connector_name": self.name
                                                }
                                            })
                                        continue  # Move to next symbol
                        
                        # If both fail, try getting the last bar (daily)
                        async with self._session.get(
                            f"{self.data_url}/v2/stocks/bars/latest",
                            headers=self.headers,
                            params=params
                        ) as response:
                            
                            if response.status == 200:
                                result = await response.json()
                                bars = result.get("bars", {})
                                
                                if symbol in bars:
                                    bar = bars[symbol]
                                    price = Decimal(bar["c"])  # Close price
                                    
                                    # Debug logging
                                    self.logger.info(f"📈 {symbol} Bar: Close ${price}, Volume {bar['v']}")
                                    
                                    # Publish market data update
                                    if self.event_bus:
                                        await self.event_bus.publish("market_data_update", {
                                            "symbol": symbol,
                                            "data": {
                                                "price": float(price),
                                                "bid": float(price),
                                                "ask": float(price),
                                                "timestamp": bar["t"],
                                                "connector_name": self.name,
                                                "volume": bar["v"],
                                                "source": "bar"
                                            }
                                        })
                                        
                    except Exception as e:
                        # Log individual symbol errors but continue
                        self.logger.error(f"❌ Error fetching data for {symbol}: {e}")
                        await self._publish_error(Exception(f"Error fetching data for {symbol}: {e}"))
                        
                # Wait before next update
                await asyncio.sleep(10.0)  # Update every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._publish_error(e)
                await asyncio.sleep(10.0)
                
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert internal order type to Alpaca format"""
        mapping = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit"
        }
        return mapping.get(order_type, "market")
        
    def _convert_order_status(self, alpaca_status: str) -> OrderStatus:
        """Convert Alpaca order status to internal format"""
        mapping = {
            "new": OrderStatus.PENDING,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "done_for_day": OrderStatus.CANCELLED,
            "canceled": OrderStatus.CANCELLED,
            "expired": OrderStatus.CANCELLED,
            "replaced": OrderStatus.PENDING,
            "pending_cancel": OrderStatus.PENDING,
            "pending_replace": OrderStatus.PENDING,
            "accepted": OrderStatus.PENDING,
            "pending_new": OrderStatus.PENDING,
            "accepted_for_bidding": OrderStatus.PENDING,
            "stopped": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "suspended": OrderStatus.CANCELLED,
            "calculated": OrderStatus.PENDING
        }
        return mapping.get(alpaca_status.lower(), OrderStatus.PENDING)
        
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert timeframe to Alpaca format"""
        mapping = {
            "1m": "1Min",
            "5m": "5Min", 
            "15m": "15Min",
            "30m": "30Min",
            "1h": "1Hour",
            "1d": "1Day"
        }
        return mapping.get(timeframe, "1Min")
    
    def _validate_config(self) -> None:
        """Validate Alpaca connector configuration"""
        if not self.alpaca_config.api_key:
            raise ValueError("Alpaca API key is required")
        if not self.alpaca_config.secret_key:
            raise ValueError("Alpaca secret key is required")
        if not self.alpaca_config.supported_symbols:
            raise ValueError("At least one supported symbol is required")
