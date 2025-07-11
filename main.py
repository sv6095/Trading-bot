#!/usr/bin/env python3
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.trading_bot import TradingBot
from src.cli_interface import TradingCLI

def main():
    try:
        bot = TradingBot()
        cli = TradingCLI(bot)
        cli.run()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
