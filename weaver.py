import asyncio
from src.GLaDOS import create_app

async def main():
  app = create_app()
  await app.start()

if __name__ == '__main__':
  asyncio.run(main())