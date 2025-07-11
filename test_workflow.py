#!/usr/bin/env python3
"""
Test script to demonstrate the autonomous event-driven trading system workflow.
This script starts GLaDOS and shows the module coordination in action.
"""

import asyncio
import sys
import os

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from modules.glados import GLaDOS

async def main():
    """Main test function"""
    print("🤖 Starting Weaver Trading Bot - Event-Driven Architecture Demo")
    print("=" * 60)
    
    # Create GLaDOS instance
    glados = GLaDOS()
    
    try:
        # Run the trading system
        await glados.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
        await glados.shutdown()
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        await glados.shutdown()
        raise

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete")
    except Exception as e:
        print(f"💥 Application error: {e}")
        sys.exit(1)
