"""
Main Discord bot entry point for YamiBot

This module initializes the Discord bot with natural conversation via @mentions.
The bot responds to messages that mention it and maintains conversation context within threads.
"""

import os
import discord
from discord.ext import commands
import logging
from typing import Optional
import asyncio

from .utils.config import Config
from .utils.logger import setup_logging
from .fallback_manager import FallbackManager
from .rate_limiter import RateLimiter
from .conversation_manager import ConversationManager

# Setup logging
logger = setup_logging(__name__)

class YamiBot(commands.Bot):
    """
    Custom Discord bot class that extends commands.Bot
    with AI conversation capabilities via @mentions
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
        intents.members = True
        
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.fallback_manager = FallbackManager(config)
        self.rate_limiter = RateLimiter()
        self.conversation_manager = ConversationManager(
            max_history=config.max_conversation_history,
            context_timeout=config.conversation_timeout
        )
        
        # Bot status tracking
        self.start_time = None
        self.last_provider_used = None
        self.messages_processed = 0
        
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is ready to start
        """
        logger.info("Setting up bot...")
        
        self.start_time = discord.utils.utcnow()
        
        # Start conversation cleanup task
        asyncio.create_task(self.conversation_manager.start_cleanup_task())
        
        logger.info("Bot setup complete")
    
    async def on_ready(self) -> None:
        """
        Event handler called when the bot connects to Discord
        """
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="@mentions | AI conversation bot"
            )
        )
        
        # Initialize fallback manager
        await self.fallback_manager.initialize()
        
        logger.info("Bot is ready and operational")
    
    async def on_message(self, message: discord.Message) -> None:
        """
        Event handler for all messages
        Handles @mentions and natural conversation
        """
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        # Ignore messages from other bots (optional)
        if message.author.bot:
            return
        
        # Check if bot is mentioned
        if self.user not in message.mentions:
            return
        
        # Get thread ID if message is in a thread
        thread_id = None
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id
        
        try:
            # Show typing indicator
            async with message.channel.typing():
                # Extract the actual message content (remove bot mention)
                content = message.content
                for mention in message.mentions:
                    content = content.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
                content = content.strip()
                
                if not content:
                    await message.reply("Hey! You mentioned me but didn't say anything. How can I help you?")
                    return
                
                logger.info(f"Processing message from {message.author} in {message.channel}: {content[:100]}")
                
                # Add user message to conversation history
                self.conversation_manager.add_message(
                    channel_id=message.channel.id,
                    role="user",
                    content=content,
                    thread_id=thread_id
                )
                
                # Get conversation history for context
                conversation_history = self.conversation_manager.get_conversation_history(
                    channel_id=message.channel.id,
                    thread_id=thread_id
                )
                
                # Query AI with conversation context
                response_text, metadata = await self.fallback_manager.query(
                    prompt=content,
                    messages=conversation_history
                )
                
                if response_text:
                    # Add assistant response to conversation history
                    self.conversation_manager.add_message(
                        channel_id=message.channel.id,
                        role="assistant",
                        content=response_text,
                        thread_id=thread_id
                    )
                    
                    # Track which provider was used
                    self.last_provider_used = metadata.get("provider", "unknown")
                    self.messages_processed += 1
                    
                    # Split long responses if needed (Discord has 2000 char limit)
                    if len(response_text) > 2000:
                        # Split into chunks
                        chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await message.reply(chunk)
                            else:
                                await message.channel.send(chunk)
                    else:
                        # Reply in thread
                        await message.reply(response_text)
                    
                    # Log metadata
                    logger.info(
                        f"Response sent via {metadata.get('provider')} "
                        f"({metadata.get('total_tokens', 0)} tokens, "
                        f"{metadata.get('response_time', 0):.2f}s)"
                    )
                else:
                    # All providers failed
                    error_msg = "😔 Sorry, I'm having trouble connecting to my AI services right now. Please try again in a moment."
                    await message.reply(error_msg)
                    logger.error(f"All providers failed: {metadata.get('error')}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await message.reply("❌ An error occurred while processing your message. Please try again.")
    
    async def on_error(self, event: str, *args, **kwargs) -> None:
        """
        Global error handler for bot events
        """
        logger.error(f"Error in event {event}", exc_info=True)
    
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
