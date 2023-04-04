import asyncio
from src.GLaDOS import GLaDOS
from src.WallE import WallE
from src.Veda import Veda
from src.Marvin import Marvin
from src.Greta import Greta
from src.Haro import Haro

async def main():
    #cls.walle = WallE()
    veda = Veda()
    # cls.marvin = Marvin()
    # cls.greta = Greta()
    # cls.haro = Haro()
    glados = GLaDOS(veda)
    await glados.start_trading()

if __name__ == 'src.__main__':
    asyncio.run(main())
