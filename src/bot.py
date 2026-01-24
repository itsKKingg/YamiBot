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
from .utils.error_handler import format_error_for_user, UserFriendlyError
from .utils.input_validator import InputValidator
from .utils.permissions import PermissionManager
from .fallback_manager import FallbackManager
from .rate_limiter import RateLimiter
from .conversation_manager import ConversationManager
from .message_validator import MessageValidator
from .health_check import start_health_server, stop_health_server
from .health_checker import HealthChecker
from .command_handler import setup_slash_commands, CommandHandler
from .model_registry import ModelRegistry
from .model_router import ModelRouter
from .model_analytics import ModelAnalytics
from .intent_detector import IntentDetector
from .integrations.genius_api import GeniusAPI
from .integrations.soundcloud_api import SoundCloudAPI
from .integrations.juice_wrld_api import JuiceWrldAPI

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
        intents.reactions = True  # For reaction confirmation system
        intents.integrations = True  # For slash commands
        
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None
        )
        
        self.config = config
        
        # Model management
        self.model_registry = ModelRegistry()
        self.model_router = None  # Will be initialized after fallback_manager
        self.model_analytics = ModelAnalytics()
        self.intent_detector = IntentDetector()
        
        self.fallback_manager = FallbackManager(config)
        self.rate_limiter = RateLimiter(config)
        self.conversation_manager = ConversationManager(
            max_history=config.max_conversation_history,
            context_timeout=config.conversation_timeout
        )
        self.permission_manager = PermissionManager(config)
        self.input_validator = InputValidator()
        
        # Resource management
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.health_server = None
        self.shutdown_event = asyncio.Event()
        self.cleanup_tasks = []
        
        # Bot status tracking
        self.start_time = None
        self.last_provider_used = None
        self.last_model_used = None
        self.messages_processed = 0
        self._is_closing = False

        # Command handler
        self.command_handler = None
        
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

        # Initialize command handler
        self.command_handler = CommandHandler(self)

        # Setup slash commands
        setup_slash_commands(self)

        # Initialize model router with fallback manager
        self.model_router = ModelRouter(self.model_registry, self.fallback_manager)
        self.fallback_manager.model_router = self.model_router

        # Set bot reference in fallback manager for health checker access
        self.fallback_manager.bot = self
        
        # Start analytics logging task
        analytics_task = asyncio.create_task(
            self.model_analytics.start_periodic_logging(interval_seconds=600)
        )
        self.cleanup_tasks.append(analytics_task)

        # Initialize music APIs if keys are available
        self._initialize_music_apis()

        logger.info("Bot setup complete with resource management and model routing enabled")
    
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

    def _initialize_music_apis(self):
        """Initialize music APIs.

        Juice WRLD API is the primary data source and does not require API keys.
        Genius is configured as a *backup only* for Juice WRLD songs when Juice WRLD API fails.
        """
        # Juice WRLD API (primary)
        try:
            self.juice_wrld_api = JuiceWrldAPI(session=self.http_session)
            logger.info("Juice WRLD API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Juice WRLD API: {e}")
            self.juice_wrld_api = None

        # Genius API (backup)
        if self.config.genius_access_token:
            try:
                self.genius_api = GeniusAPI(
                    access_token=self.config.genius_access_token,
                    session=self.http_session
                )
                logger.info("Genius API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Genius API: {e}")
                self.genius_api = None
        else:
            logger.info("Genius API key not configured, lyrics fallback unavailable")
            self.genius_api = None

        # SoundCloud API (optional; explicit SoundCloud requests only)
        if self.config.soundcloud_client_id and self.config.soundcloud_client_secret:
            try:
                self.soundcloud_api = SoundCloudAPI(
                    client_id=self.config.soundcloud_client_id,
                    client_secret=self.config.soundcloud_client_secret,
                    session=self.http_session
                )
                logger.info("SoundCloud API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SoundCloud API: {e}")
                self.soundcloud_api = None
        else:
            logger.info("SoundCloud API keys not configured, SoundCloud features unavailable")
            self.soundcloud_api = None

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
        if self._is_closing:
            return
        self._is_closing = True
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
        await super().close()
        
        logger.info("Graceful shutdown complete")
    
    async def on_ready(self) -> None:
        """
        Event handler called when the bot connects to Discord
        """
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Sync slash commands with Discord
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"❌ Failed to sync slash commands: {e}")

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
        Event handler for all messages with comprehensive validation
        Handles @mentions and natural conversation with security measures
        """
        # ========== Step 1: Basic Message Validation ==========
        should_process, reason = MessageValidator.should_process_message(message, self)
        if not should_process:
            logger.debug(f"Ignoring message: {reason}")
            return
        
        # ========== Step 2: Permission Check ==========
        can_proceed, denial_reason = await MessageValidator.check_permissions(
            message, self.permission_manager
        )
        if not can_proceed:
            await message.reply(MessageValidator.format_validation_error(denial_reason))
            logger.warning(f"Permission denied for {message.author} ({message.author.id}): {denial_reason}")
            return
        
        # ========== Step 3: Rate Limiting Check ==========
        is_trusted = self.permission_manager.is_trusted(message.author.id)
        can_request, rate_limit_reason = self.rate_limiter.can_user_request(
            message.author.id, is_trusted=is_trusted
        )
        if not can_request:
            await message.reply(MessageValidator.format_rate_limit_error(rate_limit_reason))
            logger.info(f"Rate limit hit for {message.author} ({message.author.id}): {rate_limit_reason}")
            return
        
        # ========== Step 4: Extract and Validate Content ==========
        content = MessageValidator.extract_message_content(message, self)
        
        # Validate content
        is_valid, validation_error = self.input_validator.validate_message(content)
        if not is_valid:
            await message.reply(MessageValidator.format_validation_error(validation_error))
            logger.info(f"Invalid input from {message.author} ({message.author.id}): {validation_error}")
            return
        
        # Additional check for repeated characters (spam detection)
        is_valid_repeat, repeat_error = self.input_validator.check_repeated_characters(content)
        if not is_valid_repeat:
            await message.reply(MessageValidator.format_validation_error(repeat_error))
            logger.warning(f"Spam detected from {message.author} ({message.author.id}): {repeat_error}")
            return
        
        # Sanitize content
        content = self.input_validator.sanitize_message(content)

        # Get thread ID if message is in a thread
        thread_id = None
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id

        # ========== Step 5: Check for Commands ==========
        # Check if message contains a command (natural language)
        if self.command_handler:
            try:
                is_command = await self.command_handler.handle_message(message)
                if is_command:
                    # Message was a command, don't process as regular chat
                    logger.debug(f"Message was handled as command, skipping AI chat processing")
                    return
            except Exception as e:
                logger.error(f"Error in command handler: {e}", exc_info=True)
                # Continue with normal processing if command handler fails

        # ========== Step 6: Process Request (AI Chat) ==========
        logger.debug(f"Processing message as AI chat request (not a command)")
        try:
            async with message.channel.typing():
                logger.info(
                    f"Processing message from {message.author} ({message.author.id}) "
                    f"[trusted={is_trusted}] in {message.channel}: {content[:100]}"
                )
                
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
                
                # Detect intent for intelligent model selection
                intent_result = self.intent_detector.classify_intent(content)
                intent = intent_result.get("intent", "chat")
                
                # Extract model override if present
                model_override = None
                if self.model_router:
                    model_override = self.model_router.extract_model_override(content)

                # Query AI with conversation context and intent-based routing
                response_text, metadata = await self.fallback_manager.get_response_with_routing(
                    prompt=content,
                    intent=intent,
                    messages=conversation_history,
                    model_override=model_override
                )
                
                if response_text:
                    # Validate and sanitize response
                    response_text = self.input_validator.validate_response(response_text)
                    
                    # Add assistant response to conversation history
                    self.conversation_manager.add_message(
                        channel_id=message.channel.id,
                        role="assistant",
                        content=response_text,
                        thread_id=thread_id
                    )
                    
                    # Record successful request for rate limiting
                    self.rate_limiter.record_user_request(message.author.id)
                    
                    # Track which provider was used
                    self.last_provider_used = metadata.get("provider", "unknown")
                    self.messages_processed += 1
                    
                    # Send response (already truncated by validate_response if needed)
                    await message.reply(response_text)
                    
                    # Log metadata
                    logger.info(
                        f"Response sent to {message.author} ({message.author.id}) "
                        f"via {metadata.get('provider')} "
                        f"({metadata.get('total_tokens', 0)} tokens, "
                        f"{metadata.get('response_time', 0):.2f}s, "
                        f"{len(response_text)} chars)"
                    )
                else:
                    # All providers failed
                    error_msg = "😔 Sorry, I'm having trouble connecting to my AI services right now. Please try again in a moment."
                    await message.reply(error_msg)
                    logger.error(f"All providers failed for {message.author.id}: {metadata.get('error')}")
        
        except Exception as e:
            logger.error(f"Error processing message from {message.author.id}: {e}", exc_info=True)
            error_msg = format_error_for_user(e)
            await message.reply(f"❌ {error_msg}")
    
    async def on_error(self, event: str, *args, **kwargs) -> None:
        """
        Global error handler for bot events
        """
        logger.error(f"Error in event {event}", exc_info=True)

    async def on_message_delete(self, message: discord.Message) -> None:
        """
        Event handler for message deletion
        Removes deleted messages from conversation context
        """
        # Ignore bot's own messages
        if message.author == self.user:
            return

        # Ignore messages from other bots
        if message.author.bot:
            return

        # Get thread ID if applicable
        thread_id = None
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id

        # Get conversation ID
        conversation_id = self.conversation_manager._get_conversation_id(message.channel.id, thread_id)

        # Check if conversation exists
        if conversation_id not in self.conversation_manager.conversations:
            return

        # Try to find and remove the message
        messages = self.conversation_manager.conversations[conversation_id]["messages"]
        initial_count = len(messages)

        # Remove messages matching the deleted message's content and timestamp
        # We compare content since we don't store Discord message IDs in conversation history
        self.conversation_manager.conversations[conversation_id]["messages"] = [
            msg for msg in messages
            if not (
                msg["content"] == message.content and
                abs((msg["timestamp"] - message.created_at).total_seconds()) < 60
            )
        ]

        # Log if a message was removed
        if len(self.conversation_manager.conversations[conversation_id]["messages"]) < initial_count:
            removed_count = initial_count - len(self.conversation_manager.conversations[conversation_id]["messages"])
            logger.info(f"Removed {removed_count} message(s) from conversation {conversation_id} due to deletion")
        else:
            logger.debug(f"Message not found in conversation context (may have already expired)")

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """
        Event handler for message edits
        Updates message in conversation context
        """
        # Ignore bot's own messages
        if after.author == self.user:
            return

        # Ignore messages from other bots
        if after.author.bot:
            return

        # Only process if content actually changed
        if before.content == after.content:
            return

        # Get thread ID if applicable
        thread_id = None
        if isinstance(after.channel, discord.Thread):
            thread_id = after.channel.id

        # Get conversation ID
        conversation_id = self.conversation_manager._get_conversation_id(after.channel.id, thread_id)

        # Check if conversation exists
        if conversation_id not in self.conversation_manager.conversations:
            return

        # Try to find and update the message
        messages = self.conversation_manager.conversations[conversation_id]["messages"]

        for msg in messages:
            # Find message matching old content and timestamp
            if msg["content"] == before.content and abs((msg["timestamp"] - after.created_at).total_seconds()) < 60:
                # Update the message with new content and timestamp
                msg["content"] = after.content
                msg["timestamp"] = after.edited_at if after.edited_at else discord.utils.utcnow()
                logger.info(f"Updated message in conversation {conversation_id} due to edit")
                return

        # If we get here, message wasn't found in context
        logger.debug(f"Edited message not found in conversation context (may have already expired)")

    async def close(self) -> None:
        """
        Cleanup when bot is shutting down
        """
        if self._is_closing:
            return
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
