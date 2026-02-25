"""Weaver Package Entry Point"""

import sys


def main() -> int:
    """
    Start Weaver.

    This is the main entry point when running as a module:
        python -m src
    """
    # Startup deferred to weaver.py / GLaDOS app lifespan
    print("Weaver - Automated Trading System")
    print("Use 'python weaver.py' to start GLaDOS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
