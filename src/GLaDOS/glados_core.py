from src.WallE import WallE
from src.Veda import Veda
from src.Marvin import Marvin
from src.Greta import Greta
from src.Haro import Haro
from .event_handlers import TradeEventHandler

class GLaDOSCore:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            #cls.walle = WallE()
            cls.veda = Veda()
            # cls.marvin = Marvin()
            # cls.greta = Greta()
            # cls.haro = Haro()
            cls.trade_event_handler = TradeEventHandler()
        return cls._instance
