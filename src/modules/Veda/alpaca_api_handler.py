import asyncio
import json
from datetime import datetime
from .base_api_handler import BaseApiHandler
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetAssetsRequest
from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass
from alpaca.data.timeframe import TimeFrame

class AlpacaApiHandler(BaseApiHandler):
    def __init__(self, api_key, api_secret):
        """Initializes the handler with trading and data clients using provided API credentials."""
        super().__init__()
        self.data_client = CryptoHistoricalDataClient(api_key=api_key)
        self.trading_client = TradingClient(api_key=api_key, secret_key=api_secret, paper=True)

    async def get_data(self, symbols, start_date=datetime(2022, 9, 1), end_date=None, timeframe=TimeFrame.Day):
        """Fetches historical data for given symbols within a specified date range."""
        request_params = CryptoBarsRequest(
                            symbol_or_symbols=symbols,
                            timeframe=timeframe,
                            start=start_date,
                            end=end_date
                        )
        barset = await asyncio.to_thread(self.data_client.get_crypto_bars, request_params)

        if barset and barset.data:
            barset_dict = {symbol: [bar.__dict__ for bar in bars] for symbol, bars in barset.data.items()}
            return json.dumps(barset_dict, default=str)  
        else:
            return json.dumps({'message': 'No data returned.'})

    async def place_order(self, symbol, qty, order_type, side=OrderSide.BUY, price=None, **kwargs):
        """Places an order with specified parameters. Supports market and limit orders."""
        if order_type == "market":
            order_kwargs = {"symbol": symbol, "qty": qty, "side": side}
            if "time_in_force" in kwargs:
                order_kwargs["time_in_force"] = kwargs["time_in_force"]
            order_request = MarketOrderRequest(**order_kwargs)
        elif order_type == "limit":
            if price is None:
                raise ValueError("Price must be provided for limit orders")
            order_request = LimitOrderRequest(symbol=symbol, qty=qty, side=side, limit_price=price)
        else:
            raise ValueError("Unsupported order type")
        response = await asyncio.to_thread(self.trading_client.submit_order, order_request)
        return response

    async def get_account_details(self):
        """Retrieves details of the current account."""
        return await asyncio.to_thread(self.trading_client.get_account)
    
    async def get_assets(self, asset_class=AssetClass.CRYPTO):
        """Fetches available assets for trading, filtered by asset class."""
        search_params = GetAssetsRequest(asset_class=asset_class)
        return await asyncio.to_thread(self.trading_client.get_all_assets, search_params)
    
    async def submit_market_order(self, symbol, qty, side, time_in_force=TimeInForce.GTC):
        """Submits a market order for a given symbol and quantity, specifying the side and time in force."""
        return await self.place_order(
            symbol=symbol,
            qty=qty,
            order_type="market",
            side=OrderSide[side.upper()],
            time_in_force=time_in_force
        )
