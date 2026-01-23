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

    def _get_juice_api(self):
        """Get JuiceWRLDAPI instance with bot's session."""
        from .integrations.juicewrld_api import JuiceWRLDAPI
        
        session = getattr(self.bot.fallback_manager, 'session', None) if self.bot.fallback_manager else None
        return JuiceWRLDAPI(session=session)

    async def _send_response(self, ctx, content: str, **kwargs):
        """Send response for both message and interaction contexts."""
        if isinstance(ctx, discord.Message):
            # Message context
            await ctx.reply(content, **kwargs)
        else:
            # Interaction context
            await ctx.followup.send(content, **kwargs)

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
        Handle model switch command using model router

        Args:
            message: Discord message object
            model_name: Name of the model to switch to
        """
        if not model_name:
            await message.reply("Which model would you like me to use? Use /models to see available options.")
            return

        # Normalize model name
        model_name = model_name.lower().strip()

        # Use model router to validate and find model
        if not self.bot.model_router:
            await message.reply("❌ Model routing is not available.")
            return

        provider, model, reason = self.bot.model_router.override_model(model_name)

        if not provider or not model:
            await message.reply(f"❌ I couldn't find a model matching '{model_name}'. Use /models to see available options.")
            return

        # Check if model is available
        if not self.bot.model_router.is_model_available(provider, model):
            await message.reply(f"⚠️ The model {provider}/{model} is currently unavailable. Please try another model.")
            return

        # Set user preference
        from .utils.user_preferences import UserPreferences
        if not hasattr(self.bot, 'user_preferences'):
            self.bot.user_preferences = UserPreferences()

        self.bot.user_preferences.set_user_preference(message.author.id, "model", f"{provider}/{model}")

        model_info = self.bot.model_registry.get_model_info(provider, model)
        model_display_name = model_info.get("name", f"{provider}/{model}") if model_info else f"{provider}/{model}"

        await message.reply(
            f"✅ Model preference set to **{model_display_name}**\n"
            f"Provider: {provider.title()}\n"
            f"Best for: {', '.join(model_info.get('best_for', ['general'])) if model_info else 'general'}\n\n"
            f"This preference will be used for your future requests. Use 'default' to reset."
        )
        logger.info(f"Model preference set to {provider}/{model} by user {message.author.id}")

    async def _handle_model_list(self, message: discord.Message) -> None:
        """
        Handle model list command using model registry

        Args:
            message: Discord message object
        """
        # Get all models from registry, grouped by provider
        response = "🤖 **Available AI Models:**\n\n"

        if not self.bot.model_registry:
            await message.reply("❌ Model registry is not available.")
            return

        all_models = self.bot.model_registry.get_all_models()

        for provider_name, models in all_models.items():
            response += f"**{provider_name.title()}**\n"

            for model_name, model_info in models.items():
                # Check availability
                is_available = self.bot.model_router.is_model_available(provider_name, model_name) if self.bot.model_router else True
                status_emoji = "✅" if is_available else "⚠️"

                model_display = model_info.get("name", model_name)
                best_for = ", ".join(model_info.get("best_for", ["general"])[:3])
                speed = model_info.get("speed", "medium")
                cost = model_info.get("cost", "medium")

                response += f"{status_emoji} `{model_name}`\n"
                response += f"   └─ {model_display}\n"
                response += f"      Best for: {best_for}\n"
                response += f"      Speed: {speed} | Cost: {cost}\n\n"

        response += f"*Last used model: {self.bot.last_model_used or 'none'}*"
        response += f"\n\n💡 Tip: Use `/model <name>` to set a preference or mention me with `use <model>` in your message!"

        # Split if too long
        if len(response) > 1900:
            response = response[:1900] + "\n\n... (truncated, use `/models` for full list)"

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
        response += f"🧠 **Model:** {self.bot.last_model_used or 'none'}\n"
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

    async def _handle_music_search(self, ctx, api, query: str) -> None:
        """Handle music search queries."""
        from .formatting.music_formatter import (
            format_song_list, format_artist_search_results
        )

        if not query:
            await self._send_response(ctx, "What song or artist would you like me to search for?")
            return

        try:
            # Try to search for songs
            songs = await api.search_songs(query, limit=5)
            
            if songs:
                response = f"🔍 **Search results for '{query}':**\n\n"
                response += format_song_list(songs)
                await self._send_response(ctx, response)
            else:
                # Try searching for artists
                artists = await api.search_artists(query, limit=5)
                if artists:
                    response = f"🎤 **Artists matching '{query}':**\n\n"
                    response += format_artist_search_results(artists)
                    await self._send_response(ctx, response)
                else:
                    await self._send_response(ctx, f"❌ No music found matching '{query}'.")
        
        except Exception as e:
            logger.error(f"Error searching for music: {e}", exc_info=True)
            await self._send_response(ctx, "❌ Error searching for music. Please try again.")

    async def _handle_music_lyrics(self, ctx, api, query: str) -> None:
        """Handle lyrics lookup."""
        from .formatting.music_formatter import format_song_card

        if not query:
            await self._send_response(ctx, "Which song lyrics would you like me to show?")
            return

        try:
            # Search for songs matching query
            songs = await api.search_songs(query, limit=1)
            
            if songs:
                song_id = songs[0].get('id', '')
                if song_id:
                    song_details = await api.get_song(song_id)
                    if song_details:
                        response = format_song_card(song_details)
                        await self._send_response(ctx, response)
                    else:
                        await self._send_response(ctx, f"❌ Could not fetch details for song '{query}'.")
                else:
                    await self._send_response(ctx, f"❌ No lyrics found for '{query}'.")
            else:
                await self._send_response(ctx, f"❌ No song found with title '{query}'.")
        
        except Exception as e:
            logger.error(f"Error fetching lyrics: {e}", exc_info=True)
            await self._send_response(ctx, "❌ Error fetching lyrics. Please try again.")

    async def _handle_music_artist(self, ctx, api, query: str) -> None:
        """Handle artist information lookup."""
        from .formatting.music_formatter import format_artist_card

        if not query:
            await self._send_response(ctx, "Which artist would you like me to tell you about?")
            return

        try:
            # Search for artists
            artists = await api.search_artists(query, limit=1)
            
            if artists:
                artist_id = artists[0].get('id', '')
                if artist_id:
                    artist_details = await api.get_artist(artist_id)
                    if artist_details:
                        response = format_artist_card(artist_details)
                        await self._send_response(ctx, response)
                    else:
                        await self._send_response(ctx, f"❌ Could not fetch details for artist '{query}'.")
                else:
                    await self._send_response(ctx, f"❌ No information found for artist '{query}'.")
            else:
                await self._send_response(ctx, f"❌ No artist found with name '{query}'.")
        
        except Exception as e:
            logger.error(f"Error fetching artist info: {e}", exc_info=True)
            await self._send_response(ctx, "❌ Error fetching artist information. Please try again.")

    async def _handle_music_discography(self, ctx, api, query: str) -> None:
        """Handle discography lookup."""
        from .formatting.music_formatter import format_discography

        if not query:
            await self._send_response(ctx, "Which artist's discography would you like me to show?")
            return

        try:
            # Get artist discography
            albums = await api.get_artist_discography(query)
            
            if albums:
                response = format_discography(query, albums)
                await self._send_response(ctx, response)
            else:
                await self._send_response(ctx, f"❌ No discography found for '{query}'.")
        
        except Exception as e:
            logger.error(f"Error fetching discography: {e}", exc_info=True)
            await self._send_response(ctx, "❌ Error fetching discography. Please try again.")

    async def _handle_music_features(self, ctx, api, query: str) -> None:
        """Handle featured songs lookup."""
        from .formatting.music_formatter import format_featured_songs

        if not query:
            await self._send_response(ctx, "Which artist's featured songs would you like to see?")
            return

        try:
            # Get songs featuring the artist
            songs = await api.get_songs_by_feature(query, limit=10)
            
            if songs:
                response = format_featured_songs(query, songs)
                await self._send_response(ctx, response)
            else:
                await self._send_response(ctx, f"❌ No songs found featuring '{query}'.")
        
        except Exception as e:
            logger.error(f"Error fetching featured songs: {e}", exc_info=True)
            await self._send_response(ctx, "❌ Error fetching featured songs. Please try again.")

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

    # Music Commands
    @bot.tree.command(name="song", description="Search and display song details")
    @app_commands.describe(query="Song title or search query")
    async def song_slash(interaction: discord.Interaction, query: str):
        """Slash command to search for songs"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_music_search(mock_message, command_handler._get_juice_api(), query)
        await interaction.response.send_message(f"Song search results for: {query}", ephemeral=True)

    @bot.tree.command(name="lyrics", description="Find and show song lyrics")
    @app_commands.describe(song_title="Song title to find lyrics for")
    async def lyrics_slash(interaction: discord.Interaction, song_title: str):
        """Slash command to find lyrics"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_music_lyrics(mock_message, command_handler._get_juice_api(), song_title)
        await interaction.response.send_message(f"Lyrics lookup for: {song_title}", ephemeral=True)

    @bot.tree.command(name="artist", description="Get artist information")
    @app_commands.describe(artist_name="Artist name to get info about")
    async def artist_slash(interaction: discord.Interaction, artist_name: str):
        """Slash command to get artist info"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_music_artist(mock_message, command_handler._get_juice_api(), artist_name)
        await interaction.response.send_message(f"Artist info for: {artist_name}", ephemeral=True)

    @bot.tree.command(name="discography", description="Show artist's albums and songs")
    @app_commands.describe(artist_name="Artist name to show discography for")
    async def discography_slash(interaction: discord.Interaction, artist_name: str):
        """Slash command to get discography"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_music_discography(mock_message, command_handler._get_juice_api(), artist_name)
        await interaction.response.send_message(f"Discography for: {artist_name}", ephemeral=True)

    @bot.tree.command(name="features", description="Find songs featuring an artist")
    @app_commands.describe(artist_name="Artist name to find features for")
    async def features_slash(interaction: discord.Interaction, artist_name: str):
        """Slash command to find featured songs"""
        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_music_features(mock_message, command_handler._get_juice_api(), artist_name)
        await interaction.response.send_message(f"Features lookup for: {artist_name}", ephemeral=True)

    # Music Commands - Create handler instance once
    command_handler = CommandHandler(bot)
    
    @bot.tree.command(name="song", description="Search and display song details")
    @app_commands.describe(query="Song title or search query")
    async def song_slash(interaction: discord.Interaction, query: str):
        """Slash command to search for songs"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            api = command_handler._get_juice_api()
            
            # Handle the search
            if query:
                await command_handler._handle_music_search(interaction, api, query)
            else:
                await interaction.followup.send("Please provide a song query.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in song slash command: {e}", exc_info=True)
            await interaction.followup.send("❌ Error processing song search.", ephemeral=True)

    @bot.tree.command(name="lyrics", description="Find and show song lyrics")
    @app_commands.describe(song_title="Song title to find lyrics for")
    async def lyrics_slash(interaction: discord.Interaction, song_title: str):
        """Slash command to find lyrics"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            api = command_handler._get_juice_api()
            
            if song_title:
                await command_handler._handle_music_lyrics(interaction, api, song_title)
            else:
                await interaction.followup.send("Please provide a song title.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in lyrics slash command: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching lyrics.", ephemeral=True)

    @bot.tree.command(name="artist", description="Get artist information")
    @app_commands.describe(artist_name="Artist name to get info about")
    async def artist_slash(interaction: discord.Interaction, artist_name: str):
        """Slash command to get artist info"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            api = command_handler._get_juice_api()
            
            if artist_name:
                await command_handler._handle_music_artist(interaction, api, artist_name)
            else:
                await interaction.followup.send("Please provide an artist name.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in artist slash command: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching artist information.", ephemeral=True)

    @bot.tree.command(name="discography", description="Show artist's albums and songs")
    @app_commands.describe(artist_name="Artist name to show discography for")
    async def discography_slash(interaction: discord.Interaction, artist_name: str):
        """Slash command to get discography"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            api = command_handler._get_juice_api()
            
            if artist_name:
                await command_handler._handle_music_discography(interaction, api, artist_name)
            else:
                await interaction.followup.send("Please provide an artist name.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in discography slash command: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching discography.", ephemeral=True)

    @bot.tree.command(name="features", description="Find songs featuring an artist")
    @app_commands.describe(artist_name="Artist name to find features for")
    async def features_slash(interaction: discord.Interaction, artist_name: str):
        """Slash command to find featured songs"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            api = command_handler._get_juice_api()
            
            if artist_name:
                await command_handler._handle_music_features(interaction, api, artist_name)
            else:
                await interaction.followup.send("Please provide an artist name.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in features slash command: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching featured songs.", ephemeral=True)

    logger.info("Slash commands registered")
