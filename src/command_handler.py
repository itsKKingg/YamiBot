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
from .formatting.music_formatter import (
    format_lyrics_card,
    format_song_card,
    format_song_list,
    format_artist_info,
    create_discord_embed,
    create_discord_genius_embed,
    create_discord_juice_wrld_embed,
)

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

            elif intent == "music_lyrics":
                api_source = intent_result.get("api_source")
                await self._handle_music_lyrics(message, params.get("query", params.get("rest", "")), api_source)

            elif intent == "music_search":
                api_source = intent_result.get("api_source")
                await self._handle_music_search(message, params.get("query", params.get("rest", "")), api_source)

            elif intent == "music_artist":
                api_source = intent_result.get("api_source")
                await self._handle_music_artist(message, params.get("query", params.get("rest", "")), api_source)

            elif intent == "music_annotation":
                api_source = intent_result.get("api_source")
                await self._handle_music_annotation(message, params.get("query", params.get("rest", "")), api_source)

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

    # ============ MUSIC COMMAND HANDLERS ============

    async def _handle_music_lyrics(
        self,
        message: discord.Message,
        query: str,
        api_source: Optional[str] = None
    ) -> None:
        """
        Handle music lyrics requests

        Args:
            message: Discord message object
            query: Search query (song title, artist, etc.)
            api_source: API source recommendation from intent detector
        """
        if not query:
            await message.reply("What song's lyrics would you like me to find?")
            return

        try:
            async with message.channel.typing():
                # Determine which API to use
                # api_source is one of: "juice_wrld", "genius", "soundcloud", or None

                if api_source == "juice_wrld":
                    # Use Juice WRLD API
                    if not hasattr(self.bot, 'juice_wrld_api') or self.bot.juice_wrld_api is None:
                        await message.reply("⚠️ Juice WRLD API is not configured. Falling back to Genius.")
                        # Fall through to Genius
                    else:
                        try:
                            # Search for songs
                            logger.info(f"Searching Juice WRLD API for: {query} by user {message.author.id}")
                            songs = await self.bot.juice_wrld_api.search_songs(query, limit=3)

                            if not songs:
                                await message.reply(f"❌ No Juice WRLD songs found for: {query}\n\nTrying Genius instead...")
                                # Fall through to Genius
                            elif len(songs) > 0:
                                # Get the first matching song with full details
                                song_id = songs[0].get('id')
                                if song_id:
                                    song = await self.bot.juice_wrld_api.get_song(song_id)

                                    # Format response using Discord embed
                                    embed = create_discord_juice_wrld_embed(song=song)
                                    await message.reply(embed=embed)

                                    logger.info(f"Juice WRLD lyrics retrieved for: {query} by user {message.author.id}")
                                    return  # Successfully handled, don't fall through
                                else:
                                    await message.reply("❌ Could not retrieve Juice WRLD song details. Trying Genius...")
                                    # Fall through to Genius
                            else:
                                # Should not reach here but fall through to be safe
                                await message.reply("❌ Could not retrieve Juice WRLD song details.")
                                # Fall through to Genius

                        except Exception as e:
                            logger.error(f"Error retrieving from Juice WRLD API: {e}", exc_info=True)
                            await message.reply(f"⚠️ Juice WRLD API error. Falling back to Genius...")
                            # Fall through to Genius

                if api_source == "genius" or api_source is None:
                    # Use Genius API
                    if not hasattr(self.bot, 'genius_api') or self.bot.genius_api is None:
                        await message.reply("❌ Genius API is not configured. Please set GENIUS_ACCESS_TOKEN in .env")
                        return

                    # Search for the song
                    songs = await self.bot.genius_api.search_songs(query, limit=3)

                    if not songs:
                        await message.reply(f"❌ No lyrics found for: {query}\n\nTry a different search term?")
                        return

                    # Get the first matching song with details
                    song_id = songs[0].get('id')
                    if song_id:
                        song = await self.bot.genius_api.get_song(song_id)

                        # Get annotations
                        annotations = await self.bot.genius_api.get_song_annotations(song_id, limit=3)

                        # Format response using Discord embed
                        embed = create_discord_genius_embed(song=song, annotations=annotations)
                        await message.reply(embed=embed)

                        logger.info(f"Genius lyrics retrieved for: {query} by user {message.author.id}")
                    else:
                        await message.reply("❌ Could not retrieve song details")

                else:
                    await message.reply("❌ Cannot get lyrics from SoundCloud. Try searching on Genius instead.")

        except Exception as e:
            logger.error(f"Error handling music lyrics request: {e}", exc_info=True)
            await message.reply("❌ Sorry, I couldn't get the lyrics right now. Please try again later.")

    async def _handle_music_search(
        self,
        message: discord.Message,
        query: str,
        api_source: Optional[str] = None
    ) -> None:
        """
        Handle music search and embedding requests

        Args:
            message: Discord message object
            query: Search query
            api_source: API source recommendation from intent detector
        """
        if not query:
            await message.reply("What would you like me to search for?")
            return

        try:
            async with message.channel.typing():
                # Determine API based on request type
                if api_source == "soundcloud" or "embed" in query.lower() or "play" in query.lower():
                    # Use SoundCloud for audio embedding
                    if not hasattr(self.bot, 'soundcloud_api') or self.bot.soundcloud_api is None:
                        await message.reply(
                            "❌ SoundCloud API is not configured. "
                            "Please set SOUNDCLOUD_CLIENT_ID and SOUNDCLOUD_CLIENT_SECRET in .env"
                        )
                        return

                    # Search for tracks
                    tracks = await self.bot.soundcloud_api.search_tracks(query, limit=3)

                    if not tracks:
                        await message.reply(f"❌ No tracks found on SoundCloud for: {query}")
                        return

                    # Get first track with full details
                    track_id = tracks[0].get('id')
                    if track_id:
                        track = await self.bot.soundcloud_api.get_track(str(track_id))

                        # Format as Discord embed
                        embed = create_discord_embed(track)
                        await message.reply(embed=embed)

                        logger.info(f"SoundCloud track retrieved: {track.get('title')} for user {message.author.id}")
                    else:
                        await message.reply("❌ Could not retrieve track details")

                elif api_source == "juice_wrld":
                    # Use Juice WRLD API for general music search
                    if not hasattr(self.bot, 'juice_wrld_api') or self.bot.juice_wrld_api is None:
                        await message.reply("❌ Juice WRLD API is not configured")
                        return

                    # Search for songs
                    logger.info(f"Searching Juice WRLD API for: {query} by user {message.author.id}")
                    songs = await self.bot.juice_wrld_api.search_songs(query, limit=5)

                    if not songs:
                        await message.reply(f"❌ No Juice WRLD songs found for: {query}")
                        return

                    # Format response using the song list formatter
                    response = format_song_list(songs)
                    await message.reply(response)
                    logger.info(f"Juice WRLD search performed for: {query} by user {message.author.id}")

                elif api_source == "genius" or api_source is None:
                    # Use Genius for general music search
                    if not hasattr(self.bot, 'genius_api') or self.bot.genius_api is None:
                        await message.reply("❌ Genius API is not configured")
                        return

                    # Search for songs
                    songs = await self.bot.genius_api.search_songs(query, limit=5)

                    if not songs:
                        await message.reply(f"❌ No songs found for: {query}")
                        return

                    # Format response
                    response = f"🎵 **Found {len(songs)} songs** matching '{query}':\n\n"
                    for i, song in enumerate(songs[:5], 1):
                        title = song.get('title', 'Unknown')
                        artist = song.get('primary_artist', {}).get('name', 'Unknown')
                        url = song.get('url', '')

                        response += f"{i}. **{title}** by {artist}\n"
                        if url:
                            response += f"   🔗 [View on Genius]({url})\n"

                    await message.reply(response)
                    logger.info(f"Genius search performed for: {query} by user {message.author.id}")

                else:
                    await message.reply("❌ I'm not sure which music service to use for that request.")

        except Exception as e:
            logger.error(f"Error handling music search: {e}", exc_info=True)
            await message.reply("❌ Sorry, I couldn't complete the search. Please try again later.")

    async def _handle_music_artist(
        self,
        message: discord.Message,
        query: str,
        api_source: Optional[str] = None
    ) -> None:
        """
        Handle artist information requests

        Args:
            message: Discord message object
            query: Artist name
            api_source: API source recommendation from intent detector
        """
        if not query:
            await message.reply("Which artist would you like to know about?")
            return

        try:
            async with message.channel.typing():
                # Use Juice WRLD API for artist info if requested
                if api_source == "juice_wrld":
                    if not hasattr(self.bot, 'juice_wrld_api') or self.bot.juice_wrld_api is None:
                        await message.reply("❌ Juice WRLD API is not configured")
                        return

                    # Search for artist (assuming the API has search_artists method)
                    logger.info(f"Searching Juice WRLD API for artist: {query} by user {message.author.id}")
                    artists = await self.bot.juice_wrld_api.search_artists(query, limit=1)

                    if not artists:
                        await message.reply(f"❌ No Juice WRLD artist found for: {query}")
                        return

                    # Get artist details
                    artist_id = artists[0].get('id')
                    if artist_id:
                        artist = await self.bot.juice_wrld_api.get_artist(artist_id)

                        # Format response using Discord embed
                        embed = create_discord_juice_wrld_embed(artist=artist)
                        await message.reply(embed=embed)

                        logger.info(f"Juice WRLD artist info retrieved for: {query} by user {message.author.id}")
                    else:
                        await message.reply("❌ Could not retrieve Juice WRLD artist details")

                else:
                    # Fall back to Genius API for artist info (default choice)
                    if not hasattr(self.bot, 'genius_api') or self.bot.genius_api is None:
                        await message.reply("❌ Genius API is not configured")
                        return

                    # Search for artist
                    artists = await self.bot.genius_api.search_artists(query, limit=1)

                    if not artists:
                        await message.reply(f"❌ No artist found for: {query}")
                        return

                    # Get artist details
                    artist_id = artists[0].get('id')
                    if artist_id:
                        artist = await self.bot.genius_api.get_artist(artist_id)

                        # Format as Discord embed
                        embed = create_discord_genius_embed(artist=artist)
                        await message.reply(embed=embed)

                        logger.info(f"Genius artist info retrieved for: {query} by user {message.author.id}")
                    else:
                        await message.reply("❌ Could not retrieve artist details")

        except Exception as e:
            logger.error(f"Error handling artist request: {e}", exc_info=True)
            await message.reply("❌ Sorry, I couldn't get the artist information. Please try again later.")

    async def _handle_music_annotation(
        self,
        message: discord.Message,
        query: str,
        api_source: Optional[str] = None
    ) -> None:
        """
        Handle annotation/meaning requests

        Args:
            message: Discord message object
            query: Lyric line or song reference
            api_source: API source recommendation from intent detector
        """
        if not query:
            await message.reply("What would you like me to explain?")
            return

        try:
            async with message.channel.typing():
                # Check if Juice WRLD API should be used
                if api_source == "juice_wrld":
                    if hasattr(self.bot, 'juice_wrld_api') and self.bot.juice_wrld_api is not None:
                        try:
                            # Try Juice WRLD API first
                            logger.info(f"Searching Juice WRLD API for annotations: {query} by user {message.author.id}")
                            songs = await self.bot.juice_wrld_api.search_songs(query, limit=3)

                            if songs and len(songs) > 0:
                                song_id = songs[0].get('id')
                                if song_id:
                                    # Get song details using Juice WRLD formatter
                                    song = await self.bot.juice_wrld_api.get_song(song_id)

                                    # For Juice WRLD, we'll provide the song details as annotations
                                    # since detailed annotations may not be available like Genius
                                    response = format_song_card(song)
                                    await message.reply(response)
                                    logger.info(f"Juice WRLD song info retrieved for: {query} by user {message.author.id}")
                                    return  # Successfully handled
                                    
                            # If Juice WRLD fails, fall through to Genius
                        except Exception as e:
                            logger.error(f"Juice WRLD API error for annotations: {e}", exc_info=True)
                            # Fall through to Genius

                # Use Genius API for annotations (primary/default)
                if not hasattr(self.bot, 'genius_api') or self.bot.genius_api is None:
                    await message.reply("❌ Genius API is not configured")
                    return

                # Search for song first
                songs = await self.bot.genius_api.search_songs(query, limit=3)

                if not songs:
                    await message.reply(f"❌ No songs found matching: {query}")
                    return

                # Get annotations from first matching song
                song_id = songs[0].get('id')
                if song_id:
                    annotations = await self.bot.genius_api.get_song_annotations(song_id, limit=5)

                    if not annotations:
                        await message.reply(
                            f"❌ No annotations found for this song.\n\n"
                            f"🎵 Searched: {query}\n"
                            f"🎤 Song: {songs[0].get('title')} by {songs[0].get('primary_artist', {}).get('name')}"
                        )
                        return

                    # Format annotations
                    song = await self.bot.genius_api.get_song(song_id)
                    response = format_lyrics_card(song, annotations)

                    await message.reply(response)
                    logger.info(f"Genius annotations retrieved for: {query} by user {message.author.id}")
                else:
                    await message.reply("❌ Could not retrieve annotations")

        except Exception as e:
            logger.error(f"Error handling annotation request: {e}", exc_info=True)
            await message.reply("❌ Sorry, I couldn't get the annotations. Please try again later.")


def setup_slash_commands(bot: commands.Bot) -> None:
    """
    Setup slash commands for the bot

    Args:
        bot: Discord bot instance
    """
    @bot.tree.command(name="status", description="Show bot status and statistics")
    async def status_slash(interaction: discord.Interaction):
        """Slash command for status"""
        await interaction.response.defer(ephemeral=True)

        command_handler = CommandHandler(bot)

        # Create a mock message object for the handler
        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author
                async def reply(self, content):
                    await interaction.followup.send(content, ephemeral=True)

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_status(mock_message)

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
        await interaction.response.defer(ephemeral=True)

        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author
                async def reply(self, content):
                    await interaction.followup.send(content, ephemeral=True)

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_model_switch(mock_message, model_name)

    @bot.tree.command(name="models", description="List all available AI models")
    async def models_slash(interaction: discord.Interaction):
        """Slash command to list models"""
        await interaction.response.defer(ephemeral=True)

        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author
                async def reply(self, content):
                    await interaction.followup.send(content, ephemeral=True)

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_model_list(mock_message)

    @bot.tree.command(name="stats", description="Show conversation statistics")
    async def stats_slash(interaction: discord.Interaction):
        """Slash command for stats"""
        await interaction.response.defer(ephemeral=True)

        command_handler = CommandHandler(bot)

        class MockMessage:
            def __init__(self, channel, author):
                self.channel = channel
                self.author = author
                async def reply(self, content):
                    await interaction.followup.send(content, ephemeral=True)

        mock_message = MockMessage(interaction.channel, interaction.user)
        await command_handler._handle_status(mock_message)

    logger.info("Slash commands registered")
