"""
Main Discord bot entry point for YamiBot

This module initializes the Discord bot, loads all commands, and handles
bot lifecycle events including startup, shutdown, and error handling.
"""

import os
import discord
from discord.ext import commands
import logging
from typing import Optional

from .utils.config import Config
from .utils.logger import setup_logging
from .fallback_manager import FallbackManager
from .rate_limiter import RateLimiter

# Setup logging
logger = setup_logging(__name__)

class YamiBot(commands.Bot):
    """
    Custom Discord bot class that extends commands.Bot
    with additional functionality for YamiBot
    """
    
    def __init__(self, config: Config):
        """
        Initialize the bot with configuration and setup
        
        Args:
            config: Configuration object containing bot settings
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.bot_prefix),
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.fallback_manager = FallbackManager(config)
        self.rate_limiter = RateLimiter()
        
        # Bot status tracking
        self.start_time = None
        self.last_provider_used = None
        
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is ready to start
        Loads all commands and syncs application commands
        """
        logger.info("Setting up bot commands...")
        
        # Load all command modules
        await self.load_commands()
        
        # Sync application commands
        if self.config.sync_commands:
            await self.tree.sync()
            logger.info("Synced application commands")
        
        self.start_time = discord.utils.utcnow()
        logger.info("Bot setup complete")
    
    async def load_commands(self) -> None:
        """
        Load all command modules from the commands directory
        """
        try:
            # Import and register command modules
            from .commands.ask import AskCommand
            from .commands.status import StatusCommand
            from .commands.providers import ProvidersCommand
            
            # Add command cog instances
            await self.add_cog(AskCommand(self))
            await self.add_cog(StatusCommand(self))
            await self.add_cog(ProvidersCommand(self))
            
            logger.info("Successfully loaded all commands")
            
        except Exception as e:
            logger.error(f"Failed to load commands: {e}", exc_info=True)
            raise
    
    async def on_ready(self) -> None:
        """
        Event handler called when the bot connects to Discord
        """
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"/ask | {self.config.bot_prefix}help"
            )
        )
        
        # Initialize fallback manager
        await self.fallback_manager.initialize()
        
        logger.info("Bot is ready and operational")
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Global error handler for command errors
        """
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
            return
            
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)
        await ctx.send("❌ An error occurred while processing your command. Please try again later.")
    
    async def close(self) -> None:
        """
        Cleanup when bot is shutting down
        """
        logger.info("Shutting down bot...")
        await super().close()
        logger.info("Bot shutdown complete")

def create_bot() -> YamiBot:
    """
    Factory function to create and return a configured bot instance
    
    Returns:
        Configured YamiBot instance ready to run
    """
    try:
        # Load configuration
        config = Config()
        
        # Create and return bot instance
        bot = YamiBot(config)
        return bot
        
    except Exception as e:
        logger.error(f"Failed to create bot: {e}", exc_info=True)
        raise

async def main():
    """
    Main entry point for the bot
    """
    bot = create_bot()
    
    try:
        # Start the bot
        await bot.start(bot.config.discord_token)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.close()
        
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        await bot.close()
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())