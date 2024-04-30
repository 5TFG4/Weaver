import asyncio
from src.GLaDOS.glados import GLaDOS

async def main():
    glados = GLaDOS()
    await glados.run()

if __name__ == "__main__":
    asyncio.run(main())
