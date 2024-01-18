import asyncio

from .data_manager import DataManager
from .strategy_loader import StrategyLoader
from .api_handler import ApiHandler
from .event_bus import EventBus
from .error_handler import ErrorHandler

class Controller:
    def __init__(self):
        # 初始化每个模块
        self.data_manager = DataManager()
        self.strategy_loader = StrategyLoader()
        self.api_handler = ApiHandler()
        self.event_bus = EventBus()
        self.error_handler = ErrorHandler()
        self.running = True

    async def run(self):
        while self.running:
            print ("test")
            await asyncio.sleep(1)  # 示例: 休眠1秒

    def stop(self):
        self.running = False

    def process_request(self, request):  
        # 这里是处理请求的逻辑  
        pass