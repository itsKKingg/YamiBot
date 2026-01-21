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
import signal
import aiohttp
import time
from contextlib import asynccontextmanager

from .utils.config import Config
from .utils.logger import setup_logging
from .utils.logger import log_memory_status
from .fallback_manager import FallbackManager
from .rate_limiter import RateLimiter
from .conversation_manager import ConversationManager
from .health_check import start_health_server, stop_health_server

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
        
        # Resource management
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.health_server = None
        self.shutdown_event = asyncio.Event()
        self.cleanup_tasks = []
        
        # Bot status tracking
        self.start_time = None
        self.last_provider_used = None
        self.messages_processed = 0
        
        # Log initial memory status
        self.start_memory = log_memory_status()
        
        logger.info("YamiBot instance created with resource management enabled")
        
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is ready to start
        """
        logger.info("Setting up bot with resource management...")
        
        self.start_time = discord.utils.utcnow()
        
        # Initialize shared HTTP session with connection pooling
        await self._initialize_http_session()
        
        # Setup signal handlers for graceful shutdown
        await self._setup_signal_handlers()
        
        # Initialize fallback manager with shared session
        await self._initialize_fallback_manager()
        
        # Start conversation cleanup task
        cleanup_task = asyncio.create_task(
            self.conversation_manager.start_cleanup_task(self.config.cleanup_interval)
        )
        self.cleanup_tasks.append(cleanup_task)
        
        # Start memory monitoring task
        memory_task = asyncio.create_task(self._monitor_memory())
        self.cleanup_tasks.append(memory_task)
        
        logger.info("Bot setup complete with resource management enabled")
    
    async def _initialize_http_session(self):
        """Initialize shared aiohttp session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=100,           # Total connections
            limit_per_host=10,  # Per-host limit
            ttl_dns_cache=300,   # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "YamiBot/1.0.0"
            }
        )
        
        logger.info("Shared HTTP session initialized with connection pooling")
    
    async def _setup_signal_handlers(self):
        """Setup handlers for SIGTERM and SIGINT"""
        loop = asyncio.get_event_loop()
        
        async def signal_handler(signum):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            await self._graceful_shutdown()
        
        try:
            # Add signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(signal_handler(s)))
            logger.info("Signal handlers registered for graceful shutdown")
        except (OSError, NotImplementedError):
            # Signal handlers not available on Windows or in some environments
            logger.warning("Signal handlers not available on this platform")
    
    async def _initialize_fallback_manager(self):
        """Initialize fallback manager with shared session"""
        # Set shared session for all providers
        self.fallback_manager.set_shared_session(self.http_session)
        await self.fallback_manager.initialize()
        logger.info("Fallback manager initialized with shared session")
    
    async def _monitor_memory(self):
        """Background task to monitor memory usage"""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.memory_check_interval)
                
                # Log current memory status
                memory_info = log_memory_status()
                
                # Check for memory leaks
                if self.start_memory and "rss_mb" in memory_info:
                    memory_growth = memory_info["rss_mb"] - self.start_memory["rss_mb"]
                    if memory_growth > 50:  # 50MB growth threshold
                        logger.warning(f"Memory growth detected: {memory_growth:.2f}MB since startup")
                        
                        # Force cleanup if memory growth is extreme
                        if memory_growth > 100:  # 100MB growth
                            logger.warning("Performing emergency cleanup due to high memory usage")
                            await self.conversation_manager.cleanup_old_conversations()
                
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}", exc_info=True)
    
    async def _graceful_shutdown(self):
        """Perform graceful shutdown of all resources"""
        logger.info("Starting graceful shutdown...")
        
        # Set shutdown event to stop background tasks
        self.shutdown_event.set()
        
        # Cancel cleanup tasks
        for task in self.cleanup_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cleanup tasks to finish
        if self.cleanup_tasks:
            await asyncio.gather(*self.cleanup_tasks, return_exceptions=True)
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
            logger.info("HTTP session closed")
        
        # Stop health check server
        await stop_health_server()
        logger.info("Health check server stopped")
        
        # Close Discord connection
        await self.close()
        
        logger.info("Graceful shutdown complete")
    
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
        
        logger.info("Bot is ready and operational")
        
        # Log memory status on startup
        memory_info = log_memory_status()
        logger.info(f"Bot startup memory usage: {memory_info['rss_mb']}MB")
    
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
        logger.info("Bot close() called, performing cleanup...")
        await self._graceful_shutdown()
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
        # Start health check server
        start_health_server()
        logger.info("Health check server started")
        
        # Start the bot
        await bot.start(bot.config.discord_token)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, initiating graceful shutdown...")
        await bot._graceful_shutdown()
        
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        await bot._graceful_shutdown()
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
