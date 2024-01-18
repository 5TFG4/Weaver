from .alpaca_api_handler import AlpacaApiHandler
# 其他API处理器的导入...

class Veda:
    def __init__(self):
        self.handlers = {
            "alpaca": AlpacaApiHandler(),
            # 初始化其他交易所的API处理器...
        }

    async def get_data(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.get_data(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")

    async def place_order(self, source, *args, **kwargs):
        handler = self.handlers.get(source)
        if handler:
            return await handler.place_order(*args, **kwargs)
        else:
            raise ValueError(f"API handler for {source} not found")
