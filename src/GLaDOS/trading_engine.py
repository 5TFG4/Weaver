from .event_handlers import TradeEventHandler
from .models import Trade
from src.GLaDOS import Veda

class TradingEngine:
    def __init__(self):
        self.veda = Veda()
        self.trade_event_handler = TradeEventHandler()

    async def start_trading(self):
        while True:
            # 从 Veda 获取新的交易数据
            trade_data = await self.veda.get_trade_data()

            # 创建 Trade 对象
            trade = Trade.from_dict(trade_data)

            # 处理交易数据
            self.trade_event_handler.handle_trade(trade)
