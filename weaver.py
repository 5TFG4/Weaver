import asyncio
from src.GLaDOS.controller import Controller

async def main():
    controller = Controller()
    await controller.run()

if __name__ == "__main__":
    asyncio.run(main())
