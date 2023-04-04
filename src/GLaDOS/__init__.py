#from .glados_core import GLaDOSCore
from ..models import Trade
#from .trading_engine import TradingEngine
from .event_handlers import EventHandler

class GLaDOS:
    _instance = None
    
    def __new__(cls, veda):
        if not cls._instance:
            cls._instance = super().__new__(cls, veda)
            #cls.walle = WallE()
            cls.veda = veda
            # cls.marvin = Marvin()
            # cls.greta = Greta()
            # cls.haro = Haro()
            cls.event_handler = EventHandler()
        return cls._instance
    
    async def start_trading(self):
        while True:
            trade_data = await self.veda.get_trade_data()
            #trade = Trade.from_dict(trade_data[0])
            self.event_handler.handle_trade(trade_data[0])
