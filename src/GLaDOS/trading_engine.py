from ..models import Trade
from .glados_core import GLaDOSCore

class TradingEngine:
    def __init__(self):
        self.glados = GLaDOSCore()

    async def start_trading(self):
        while True:
            trade_data = await self.glados.veda.get_trade_data()
            trade = Trade.from_dict(trade_data)
            self.glados.trade_event_handler.handle_trade(trade)
