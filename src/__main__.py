"""Start Weaver."""
import sys
#import asyncio
# from src.GLaDOS import GLaDOS
# from src.WallE import WallE
from src.Veda import Veda
# from src.Marvin import Marvin
# from src.Greta import Greta
# from src.Haro import Haro

def main() -> int:
    """Start Weaver."""
    #cls.walle = WallE()
    veda = Veda()
    # cls.marvin = Marvin()
    # cls.greta = Greta()
    # cls.haro = Haro()
    #glados = GLaDOS()
    
    from GLaDOS import runner

    exit_code = runner.run(veda)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
