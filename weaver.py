"""Weaver Entry Point"""

import asyncio

from src.glados import GLaDOS


async def main() -> None:
    """Start the GLaDOS control plane."""
    glados = GLaDOS()
    await glados.run()


if __name__ == "__main__":
    asyncio.run(main())
