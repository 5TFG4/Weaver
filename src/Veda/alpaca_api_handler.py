from .base_api_handler import BaseApiHandler
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide
from alpaca.trading.enums import AssetClass
from alpaca.trading.requests import GetAssetsRequest

class AlpacaApiHandler(BaseApiHandler):
    def __init__(self, api_key, api_secret):
        super().__init__()
        self.data_client = CryptoHistoricalDataClient(api_key=api_key)
        self.trading_client = TradingClient(api_key=api_key, secret_key=api_secret, paper=True)

    async def get_data(self, symbols, start_date, end_date=None, timeframe=TimeFrame.Day):
        request_params = CryptoBarsRequest(
                            symbol_or_symbols=symbols,
                            timeframe=timeframe,
                            start=start_date,
                            end=end_date
                        )
        bars = self.data_client.get_crypto_bars(request_params)
        return bars

    async def place_order(self, symbol, qty, order_type, side=OrderSide.BUY, price=None):
        if order_type == "market":
            order_request = MarketOrderRequest(symbol=symbol, qty=qty, side=side)
        elif order_type == "limit":
            if price is None:
                raise ValueError("Price must be provided for limit orders")
            order_request = LimitOrderRequest(symbol=symbol, qty=qty, side=side, limit_price=price)
        else:
            raise ValueError("Unsupported order type")

        response = self.trading_client.submit_order(order_request)
        return response

    async def get_account_details(self):
        account = self.trading_client.get_account()
        return account
    
    async def get_assets(self, asset_class=AssetClass.CRYPTO):
        search_params = GetAssetsRequest(asset_class=asset_class)
        assets = self.trading_client.get_all_assets(search_params)
        return assets