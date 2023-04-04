from typing import Dict

class Trade:
    def __init__(self, symbol: str, price: float, size: float, timestamp: float):
        self.symbol = symbol
        self.price = price
        self.size = size
        self.timestamp = timestamp

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Trade':
        return cls(data['symbol'], data['price'], data['size'], data['timestamp'])
