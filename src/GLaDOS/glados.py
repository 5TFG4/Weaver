import asyncio
import json

from datetime import datetime

from src.Veda.veda import Veda

from src.constants import ALPACA

from .data_manager import DataManager
from .strategy_loader import StrategyLoader
from .api_handler import ApiHandler
from .event_bus import EventBus
from .error_handler import ErrorHandler


class GLaDOS:
    def __init__(self):
        self.veda = Veda()
        # Init modules
        self.data_manager = DataManager()
        self.strategy_loader = StrategyLoader()
        self.api_handler = ApiHandler(self.veda)
        self.event_bus = EventBus(min_interval=6)
        self.error_handler = ErrorHandler()
        
        self.register_events()
        
        self.running = True

    def register_events(self):
        self.event_bus.register_event("fetch_data", self.fetch_data_handler)
        self.event_bus.register_event("account_details", self.fetch_account_handler)
        self.event_bus.register_event("assets_details", self.fetch_assets_handler)
        self.event_bus.register_event("submit_market_order", self.submit_market_order_handler)

    async def fetch_data_handler(self, symbol, sleepTime):
        start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
        data = await self.api_handler.get_stock_data(ALPACA, [symbol], start_date)
        print(f"Data for {symbol}:")
        print(data.df.head(20))
        #print(symbol)
        await asyncio.sleep(sleepTime)
        self.event_bus.emit_event(f"fetch_data",symbol=symbol, sleepTime=sleepTime)
    
    async def fetch_account_handler(self, sleepTime):
        account_details = await self.api_handler.get_account_details(ALPACA)
        print(account_details)
        await asyncio.sleep(sleepTime)
        self.event_bus.emit_event(f"account_details", sleepTime=sleepTime)
    
    async def fetch_assets_handler(self, sleepTime):
        assets = await self.api_handler.get_assets(ALPACA)

        #for asset in assets:
            #print(asset)
        
        await asyncio.sleep(sleepTime)
        self.event_bus.emit_event(f"assets_details", sleepTime=sleepTime)
    
    async def submit_market_order_handler(self, sleepTime):
        order_response = await self.api_handler.submit_market_order(
                source=ALPACA,
                symbol="BTCUSD",
                qty=0.0002,
                side="BUY"
            )

        #for asset in assets:
            #print(asset)
        
        await asyncio.sleep(sleepTime)
        #self.event_bus.emit_event(f"submit_market_order")

    async def run(self):
        self.event_bus.emit_event("fetch_data", symbol="BTC/USD", sleepTime=12)
        self.event_bus.emit_event("fetch_data", symbol="ETH/USD", sleepTime=2)
        self.event_bus.emit_event("account_details", sleepTime=6)
        self.event_bus.emit_event("assets_details", sleepTime=6)
        self.event_bus.emit_event("submit_market_order", sleepTime=6)

        while self.running:
            await asyncio.sleep(1)

    def stop(self):
        self.running = False

    def process_request(self, request):  
        # Request process logic here
        pass