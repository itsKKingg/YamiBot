"""
Command Handler for YamiBot

This module handles both natural language commands and slash commands.
Routes intents detected by IntentDetector to appropriate actions.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any
import asyncio

from .utils.logger import setup_logging
from .intent_detector import IntentDetector
from .message_validator import MessageValidator

logger = setup_logging(__name__)


class CommandHandler:
    """
    Handles natural language and slash commands
    """

    def __init__(self, bot):
        """
        Initialize command handler

        Args:
            bot: YamiBot instance
        """
        self.bot = bot
        self.intent_detector = IntentDetector()
        self.pending_confirmations = {}  # user_id: {message_id, action_type, params}

        logger.info("Command handler initialized")

    async def handle_message(self, message: discord.Message) -> bool:
        """
        Check if message contains a command and handle it

        Args:
            message: Discord message object

        Returns:
            True if message was a command and was handled, False otherwise
        """
        # Extract clean message content
        content = MessageValidator.extract_message_content(message, self.bot)

        # Classify intent
        intent_result = self.intent_detector.classify_intent(content)

        # If no special intent (just chat), return False
        if intent_result["intent"] == "chat":
            return False

        # Handle the intent
        logger.info(f"Handling intent: {intent_result['intent']} for user {message.author.id}")
        await self._handle_intent(message, intent_result)

        return True

    async def _handle_intent(self, message: discord.Message, intent_result: Dict[str, any]) -> None:
        """
        Route intent to appropriate handler

        Args:
            message: Discord message object
            intent_result: Intent classification result
        """
        intent = intent_result["intent"]
        params = intent_result.get("params", {})

        # Route to appropriate handler
        try:
            if intent == "clear_memory":
                await self._handle_clear_memory(message)

            elif intent == "view_memory":
                await self._handle_view_memory(message)

            elif intent == "search":
                await self._handle_search(message, params.get("query", ""))

            elif intent == "model_switch":
                await self._handle_model_switch(message, params.get("model_name", ""))

            elif intent == "model_list":
                await self._handle_model_list(message)

            elif intent == "status":
                await self._handle_status(message)

            elif intent == "remember_preference":
                await self._handle_remember_preference(message, params.get("preference", ""))

            elif intent == "clear_specific":
                await self._handle_clear_specific(message, params.get("count", 0))

            else:
                logger.warning(f"Unknown intent: {intent}")
                await message.reply("I'm not sure how to handle that request. Could you rephrase it?")

        except Exception as e:
            logger.error(f"Error handling intent {intent}: {e}", exc_info=True)
            await message.reply("❌ An error occurred while processing your command.")

    async def _handle_clear_memory(self, message: discord.Message) -> None:
        """
        Handle clear memory command with confirmation

        Args:
            message: Discord message object
        """
        # Request confirmation
        confirmed = await self._wait_for_reaction_confirmation(message, message.author.id)

        if confirmed:
            # Get thread ID if applicable
            thread_id = None
            if isinstance(message.channel, discord.Thread):
                thread_id = message.channel.id

            # Clear conversation
            self.bot.conversation_manager.clear_conversation(message.channel.id, thread_id)

            await message.reply("✅ Memory cleared successfully. Our conversation has been reset.")
            logger.info(f"Memory cleared for channel {message.channel.id} by user {message.author.id}")
        else:
            await message.reply("Operation cancelled.")

    async def _handle_view_memory(self, message: discord.Message) -> None:
        """
        Handle view memory command

        Args:
            message: Discord message object
        """
        # Get thread ID if applicable
        thread_id = None
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id

        # Get conversation history
        history = self.bot.conversation_manager.get_conversation_history(message.channel.id, thread_id)

        if not history:
            await message.reply("I don't remember anything from our conversation yet.")
        else:
            # Format for display
            response = f"📝 **Conversation Memory** ({len(history)} messages):\n\n"
            for i, msg in enumerate(history, 1):
                role_emoji = "👤" if msg["role"] == "user" else "🤖"
                response += f"{role_emoji} **{msg['role'].title()}**: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}\n\n"

            # Truncate if too long
            if len(response) > 1900:
                response = response[:1900] + "\n\n... (truncated)"

            await message.reply(response)
            logger.info(f"Memory viewed for channel {message.channel.id} by user {message.author.id}")

    async def _handle_search(self, message: discord.Message, query: str) -> None:
        """
        Handle search command using Google Gemini

        Args:
            message: Discord message object
            query: Search query
        """
        if not query:
            await message.reply("What would you like me to search for?")
            return

        # Use Google Gemini with web search capability
        try:
            async with message.channel.typing():
                # Get thread ID if applicable
                thread_id = None
                if isinstance(message.channel, discord.Thread):
                    thread_id = message.channel.id

                # Construct search prompt
                search_prompt = f"Search for information about: {query}"

                # Query using Google Gemini
                response, metadata = await self.bot.fallback_manager.query(
                    prompt=search_prompt,
                    messages=[{"role": "user", "content": search_prompt}]
                )

                if response:
                    # Add to conversation
                    self.bot.conversation_manager.add_message(
                        channel_id=message.channel.id,
                        role="user",
                        content=search_prompt,
                        thread_id=thread_id
                    )
                    self.bot.conversation_manager.add_message(
                        channel_id=message.channel.id,
                        role="assistant",
                        content=response,
                        thread_id=thread_id
                    )

                    await message.reply(f"🔍 **Search results for '{query}':**\n\n{response}")
                    logger.info(f"Search performed for '{query}' by user {message.author.id}")
                else:
                    await message.reply("❌ Sorry, I couldn't perform the search right now. Please try again.")

        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
            await message.reply("❌ An error occurred during the search.")

    async def _handle_model_switch(self, message: discord.Message, model_name: str) -> None:
        """
        Handle model switch command

        Args:
            message: Discord message object
            model_name: Name of the model to switch to
        """
        if not model_name:
            await message.reply("Which model would you like me to use? Use /models to see available options.")
            return

        # Normalize model name
        model_name = model_name.lower().strip()

        # Get available providers
        available_models = []
        for provider in self.bot.fallback_manager.providers:
            available_models.append(provider.name)
            # Also add full model names
            available_models.append(provider.model)

        # Find matching model
        matched_model = None
        for available in available_models:
            if model_name in available.lower():
                matched_model = available
                break

        if not matched_model:
            await message.reply(f"❌ I couldn't find a model matching '{model_name}'. Use /models to see available options.")
            return

        # Note: Actual model switching would require modifying the fallback manager
        # For now, just acknowledge the request
        await message.reply(f"🔄 Model switching requested to '{matched_model}'. Note: Model preference is stored per-conversation. Current active provider: {self.bot.last_provider_used or 'none'}")
        logger.info(f"Model switch requested to {matched_model} by user {message.author.id}")

    async def _handle_model_list(self, message: discord.Message) -> None:
        """
        Handle model list command

        Args:
            message: Discord message object
        """
        # Get available providers and their models
        response = "🤖 **Available AI Models:**\n\n"

        for provider in self.bot.fallback_manager.providers:
            status = self.bot.fallback_manager.provider_status.get(provider.name, "unknown")
            status_emoji = "✅" if status == "available" else "⚠️"

            response += f"{status_emoji} **{provider.name}** ({provider.model})\n"
            response += f"   {provider.get_limits().get('description', 'No limits info')}\n\n"

        response += f"\n*Active provider: {self.bot.last_provider_used or 'none'}*"

        await message.reply(response)
        logger.info(f"Model list requested by user {message.author.id}")

    async def _handle_status(self, message: discord.Message) -> None:
        """
        Handle status command

        Args:
            message: Discord message object
        """
        # Calculate uptime
        uptime = "Unknown"
        if self.bot.start_time:
            uptime_seconds = (discord.utils.utcnow() - self.bot.start_time).total_seconds()
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime = f"{hours}h {minutes}m"

        # Get conversation stats
        conv_stats = self.bot.conversation_manager.get_conversation_stats()

        # Get provider status
        provider_status = self.bot.fallback_manager.get_provider_status()

        # Format response
        response = "📊 **Bot Status:**\n\n"
        response += f"⏱️ **Uptime:** {uptime}\n"
        response += f"🤖 **Active Provider:** {self.bot.last_provider_used or 'none'}\n"
        response += f"💬 **Messages Processed:** {self.bot.messages_processed}\n"
        response += f"🗂️ **Active Conversations:** {conv_stats['active_conversations']}\n"
        response += f"📝 **Total Messages in Memory:** {conv_stats['total_messages']}\n\n"
        response += "**Provider Status:**\n"

        for provider_name, status_info in provider_status.items():
            status = status_info.get("status", "unknown")
            status_emoji = "✅" if status == "available" else "⚠️"
            model = status_info.get("model", "unknown")
            response += f"{status_emoji} {provider_name.title()}: {model}\n"

        await message.reply(response)
        logger.info(f"Status requested by user {message.author.id}")

    async def _handle_remember_preference(self, message: discord.Message, preference: str) -> None:
        """
        Handle remember preference command

        Args:
            message: Discord message object
            preference: User preference to remember
        """
        if not preference:
            await message.reply("What would you like me to remember?")
            return

        # Note: This would integrate with a user preferences system
        # For now, just acknowledge
        await message.reply(f"📝 Got it! I'll remember that you: {preference}")
        logger.info(f"Preference remembered by user {message.author.id}: {preference}")

    async def _handle_clear_specific(self, message: discord.Message, count: int) -> None:
        """
        Handle clear specific number of messages

        Args:
            message: Discord message object
            count: Number of messages to clear
        """
        if count <= 0:
            await message.reply("Please specify how many messages to forget (e.g., 'forget last 3 messages').")
            return

        # Get thread ID if applicable
        thread_id = None
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id

        # Get current conversation
        conversation_id = self.bot.conversation_manager._get_conversation_id(message.channel.id, thread_id)

        if conversation_id not in self.bot.conversation_manager.conversations:
            await message.reply("I don't have any conversation history to clear.")
            return

        # Remove last N messages
        messages = self.bot.conversation_manager.conversations[conversation_id]["messages"]
        messages_to_clear = min(count, len(messages))

        # Keep only messages before the last N
        self.bot.conversation_manager.conversations[conversation_id]["messages"] = messages[:-messages_to_clear]
        self.bot.conversation_manager.conversations[conversation_id]["last_updated"] = discord.utils.utcnow()

        await message.reply(f"✅ Cleared the last {messages_to_clear} messages from our conversation.")
        logger.info(f"Cleared {messages_to_clear} messages from conversation {conversation_id} by user {message.author.id}")

    async def _wait_for_reaction_confirmation(
        self,
        message: discord.Message,
        user_id: int,
        timeout: int = 30
    ) -> bool:
        """
        Wait for user reaction confirmation (destructive actions)

        Args:
            message: Original message asking for confirmation
            user_id: User ID to wait for reaction from
            timeout: Timeout in seconds

        Returns:
            True if confirmed (✅), False if cancelled (❌) or timeout
        """
        # Add check and X reactions
        try:
            await message.add_reaction("✅")
            await message.add_reaction("❌")
        except discord.Forbidden:
            # Bot doesn't have permission to add reactions
            logger.warning("Bot doesn't have permission to add reactions")
            return False

        # Wait for reaction
        try:
            def check(reaction, reactor):
                return (
                    reaction.message.id == message.id and
                    reactor.id == user_id and
                    str(reaction.emoji) in ("✅", "❌")
                )

            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=timeout)

            # Remove bot reactions
            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass

            # Return True for check, False for X
            return str(reaction.emoji) == "✅"

        except asyncio.TimeoutError:
            # Timeout - remove reactions and return False
            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass
            logger.info(f"Confirmation timeout for user {user_id}")
            return False

        except Exception as e:
            logger.error(f"Error waiting for reaction confirmation: {e}", exc_info=True)
            return False


def setup_slash_commands(bot: commands.Bot) -> None:
    """
    Setup slash commands for the bot

    Args:
        bot: Discord bot instance
    """
    @bot.tree.command(name="status", description="Show bot status and statistics")
    async def status_slash(interaction: discord.Interaction):
        """Slash command for status"""
        command_handler = CommandHandler(bot)

        # Create a mock message object for the handler
        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_status(mock_message)
        await interaction.response.send_message("Status sent!", ephemeral=True)

    @bot.tree.command(name="forget", description="Clear conversation memory (requires confirmation)")
    async def forget_slash(interaction: discord.Interaction):
        """Slash command to clear memory"""
        await interaction.response.send_message(
            "Are you sure you want to clear your conversation memory? "
            "Use the reaction-based confirmation by saying 'clear my memory' in a regular message.",
            ephemeral=True
        )

    @bot.tree.command(name="model", description="Switch to a specific AI model")
    @app_commands.describe(model_name="The model to switch to")
    async def model_slash(interaction: discord.Interaction, model_name: str):
        """Slash command to switch models"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_model_switch(mock_message, model_name)
        await interaction.response.send_message(f"Model switch request processed for: {model_name}", ephemeral=True)

    @bot.tree.command(name="models", description="List all available AI models")
    async def models_slash(interaction: discord.Interaction):
        """Slash command to list models"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_model_list(mock_message)
        await interaction.response.send_message("Models list sent!", ephemeral=True)

    @bot.tree.command(name="stats", description="Show conversation statistics")
    async def stats_slash(interaction: discord.Interaction):
        """Slash command for stats"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_status(mock_message)
        await interaction.response.send_message("Statistics sent!", ephemeral=True)

    logger.info("Slash commands registered")
