from typing import List

from models import Trade

class Veda:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    
    async def get_trade_data(symbol: str) -> List[Trade]:
        data = {'symbol': 'AAPL', 'price': 150.0, 'size': 10.0, 'timestamp': 1648776145.0}
        trade = Trade.from_dict(data)
        return [trade]
    

    async def async_start(self) -> None:
        print("Veda async_start")
        return