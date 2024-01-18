import asyncio

from datetime import datetime

from src.Veda.veda import Veda

from .data_manager import DataManager
from .strategy_loader import StrategyLoader
from .api_handler import ApiHandler
from .event_bus import EventBus
from .error_handler import ErrorHandler


class Controller:
    def __init__(self):
        self.veda = Veda()
        # 初始化每个模块
        self.data_manager = DataManager()
        self.strategy_loader = StrategyLoader()
        self.api_handler = ApiHandler(self.veda)
        self.event_bus = EventBus(min_interval=6)
        self.error_handler = ErrorHandler()
        
        self.register_events()
        
        self.running = True

    def register_events(self):
        self.event_bus.register_event("fetch_data_btc/usd", self.fetch_data_handler("BTC/USD", 12))
        self.event_bus.register_event("fetch_data_eth/usd", self.fetch_data_handler("ETH/USD", 2))

    def fetch_data_handler(self, symbol, sleepTime):
        async def handler():
            start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
            data = await self.api_handler.get_stock_data("alpaca", [symbol], start_date)
            #print(f"Data for {symbol}:")
            #print(data.df.head(20))
            print(symbol)
            await asyncio.sleep(sleepTime)
            self.event_bus.emit_event(f"fetch_data_{symbol.lower()}")
        return handler

    async def run(self):
        self.event_bus.emit_event("fetch_data_btc/usd")
        self.event_bus.emit_event("fetch_data_eth/usd")

        while self.running:
            await asyncio.sleep(1)

    def stop(self):
        self.running = False

    def process_request(self, request):  
        # 这里是处理请求的逻辑  
        pass