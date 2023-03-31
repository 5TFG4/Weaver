import asyncio
from .trading_engine import start_trading
from src.WallE import WallE
from src.Veda import Veda
from src.Marvin import Marvin
from src.Greta import Greta
from src.Haro import Haro

class GLaDOS:
    def __init__(self):
        self.walle = WallE()
        self.veda = Veda()
        self.marvin = Marvin()
        self.greta = Greta()
        self.haro = Haro()
        # other initialization code

    # other methods and event handlers
    async def run(self):
        print("GLaDOS")
        await start_trading()
    
if __name__ == '__main__':
    glados = GLaDOS()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(glados.run())
