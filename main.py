"""
Main entry point for YamiBot

This module serves as the primary entry point for running the Discord bot.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.bot import main

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())