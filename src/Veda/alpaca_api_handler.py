from .base_api_handler import BaseApiHandler
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest

class AlpacaApiHandler(BaseApiHandler):
    def __init__(self):
        super().__init__()
        self.client = CryptoHistoricalDataClient()

    async def get_data(self, symbols, start_date, timeframe=TimeFrame.Day):
        request_params = CryptoBarsRequest(
                            symbol_or_symbols=symbols,
                            timeframe=timeframe,
                            start=start_date
                        )
        bars = self.client.get_crypto_bars(request_params)
        return bars

    async def place_order(self, symbol, qty, order_type, price=None):
        # 创建订单请求
        if order_type == "market":
            order_request = MarketOrderRequest(symbol=symbol, qty=qty)
        elif order_type == "limit":
            # 确保提供了价格
            if price is None:
                raise ValueError("Price must be provided for limit orders")
            # 创建限价单请求
            # ...（其他订单类型的处理）
        
        # 发送订单请求
        response = self.trading_client.submit_order(order_request)
        return response
