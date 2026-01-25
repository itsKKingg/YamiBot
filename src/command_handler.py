"""
Command Handler for YamiBot

This module handles both natural language commands and slash commands.
Routes intents detected by IntentDetector to appropriate actions.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, Tuple
import asyncio

from .utils.logger import setup_logging
from .intent_detector import IntentDetector
from .message_validator import MessageValidator
from .formatting.music_formatter import (
    format_lyrics_card,
    format_song_card,
    create_discord_genius_embed,
    create_discord_juice_wrld_embed,
    create_discord_juice_wrld_search_embed,
    create_discord_juice_wrld_song_list_embed,
    create_discord_juice_wrld_lyric_search_embed,
    create_discord_juice_wrld_stats_embed,
    create_discord_juice_wrld_eras_embeds,
    create_discord_juice_wrld_cover_art_embed,
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
        self.processed_messages = set()  # Track processed message IDs to prevent duplicates
        self.max_processed_messages = 1000  # Limit size of tracking set

        logger.info("Command handler initialized")

    async def handle_message(self, message: discord.Message) -> bool:
        """
        Check if message contains a command and handle it

        Args:
            message: Discord message object

        Returns:
            True if message was a command and was handled, False otherwise
        """
        # Check if we've already processed this message (prevent duplicates)
        if message.id in self.processed_messages:
            logger.warning(f"⚠️ Message {message.id} already processed, skipping to prevent duplicate response")
            return True  # Return True to indicate it was handled (even though we're skipping)
        
        # Extract clean message content
        content = MessageValidator.extract_message_content(message, self.bot)

        # Classify intent
        intent_result = self.intent_detector.classify_intent(content)

        # If no special intent (just chat), return False
        if intent_result["intent"] == "chat":
            logger.debug(f"No command intent detected for message: {content[:50]}")
            return False

        # Mark message as processed BEFORE handling to prevent race conditions
        self.processed_messages.add(message.id)
        
        # Limit the size of the processed messages set
        if len(self.processed_messages) > self.max_processed_messages:
            # Remove oldest entries (though set doesn't maintain order, this limits memory)
            excess = len(self.processed_messages) - self.max_processed_messages
            for _ in range(excess):
                self.processed_messages.pop()

        # Handle the intent
        intent = intent_result["intent"]
        api_source = intent_result.get("api_source")
        params = intent_result.get("params", {})
        
        logger.info(
            f"🎯 Handling intent: {intent} "
            f"(api_source: {api_source}, params: {params}) "
            f"for user {message.author.id} (msg_id: {message.id})"
        )
        
        try:
            await self._handle_intent(message, intent_result)
            logger.info(f"✅ Intent {intent} handled successfully for user {message.author.id}")
        except Exception as e:
            logger.error(f"❌ Error handling intent {intent}: {e}", exc_info=True)
            # Remove from processed set if handling failed, so it can be retried
            self.processed_messages.discard(message.id)
            raise
        
        return True

    async def _handle_juice_download(self, message: discord.Message, query: str) -> None:
        """Handle Juice WRLD download requests"""
        if not query:
            await message.reply("Which song do you want to download?")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            song = await self._resolve_juice_song(song_query=query, song_id=None)
            if not song:
                await message.reply("❌ Couldn't find that song.")
                return

            download_url = song.get("download_url")
            if download_url:
                await message.reply(
                    content=f"💾 **Download:** {download_url}",
                    embed=create_discord_juice_wrld_embed(song=song)
                )
            else:
                await message.reply("❌ No download link available for this track.")

    async def _handle_juice_browse(self, message: discord.Message) -> None:
        """Handle Juice WRLD browse requests"""
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            # Try to browse different types of content
            try:
                # Browse artists, albums, and tracks
                artists = await self.bot.juice_wrld_api.browse_artists()
                albums = await self.bot.juice_wrld_api.browse_albums()
                tracks = await self.bot.juice_wrld_api.browse_tracks()

                # Get stats for overview
                stats = await self.bot.juice_wrld_api.get_stats()

                content = f"📚 **Juice WRLD Library Overview**\n\n"
                content += f"📊 **Statistics:**\n"
                content += f"• Total Songs: {stats.get('total_songs', 'N/A')}\n"
                content += f"• Total Eras: {stats.get('total_eras', 'N/A')}\n"
                content += f"• Total Categories: {stats.get('total_categories', 'N/A')}\n\n"

                if artists:
                    content += f"🎤 **Artists ({len(artists)}):**\n"
                    for artist in artists[:5]:
                        content += f"• {artist.get('name', 'Unknown')}\n"
                    if len(artists) > 5:
                        content += f"... and {len(artists) - 5} more\n"
                    content += "\n"

                if albums:
                    content += f"💿 **Albums ({len(albums)}):**\n"
                    for album in albums[:5]:
                        content += f"• {album.get('title', 'Unknown')}\n"
                    if len(albums) > 5:
                        content += f"... and {len(albums) - 5} more\n"
                    content += "\n"

                if tracks:
                    content += f"🎵 **Sample Tracks ({len(tracks)}):**\n"
                    for track in tracks[:5]:
                        content += f"• {track.get('title', 'Unknown')}\n"
                    if len(tracks) > 5:
                        content += f"... and {len(tracks) - 5} more\n"

                await message.reply(content)

            except Exception as e:
                logger.error(f"Error browsing Juice WRLD content: {e}")
                await message.reply("❌ Couldn't browse the library right now.")

    async def _resolve_juice_song(self, song_query: str, song_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Resolve song from natural language query using fuzzy matching
        Uses fuzzy matching for versioned songs like "Rental (v1)"
        """
        if not song_query and not song_id:
            return None

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            return None

        try:
            if song_id:
                # Direct ID lookup
                return await self.bot.juice_wrld_api.get_song(song_id)

            if song_query:
                # Try exact search first
                results = await self.bot.juice_wrld_api.search_songs(song_query, limit=10)

                if results:
                    # Check if top result is strong match
                    if self.bot.juice_wrld_api._is_strong_title_match(song_query, results[0].get("title", "")):
                        # Get full details
                        song_id = results[0].get("id")
                        if song_id:
                            return await self.bot.juice_wrld_api.get_song(song_id)

                # Fuzzy matching fallback
                all_songs = await self.bot.juice_wrld_api.search_all_songs(limit=1000)

                import difflib
                song_titles = [s.get("title", "") for s in all_songs]
                matches = difflib.get_close_matches(song_query, song_titles, n=3, cutoff=0.6)

                if matches:
                    matched_song = next((s for s in all_songs if s.get("title") in matches), None)
                    if matched_song:
                        song_id = matched_song.get("id")
                        if song_id:
                            return await self.bot.juice_wrld_api.get_song(song_id)

                # Return best search result if no strong matches
                return results[0] if results else None

        except Exception as e:
            logger.error(f"Error resolving Juice WRLD song: {e}")

        return None

    async def _looks_like_year(self, text: str) -> bool:
        """Check if text looks like a year"""
        try:
            year = int(text.strip())
            return 1900 <= year <= 2030
        except (ValueError, TypeError):
            return False

    async def _resolve_era(self, era_query: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Resolve era from query"""
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            return None, None

        try:
            eras = await self.bot.juice_wrld_api.list_eras()
            
            # Try exact name match first
            for era in eras:
                if era_query.lower() in era.get("name", "").lower():
                    return era.get("id"), era
            
            # Try ID match
            for era in eras:
                if era_query.lower() == era.get("id", "").lower():
                    return era.get("id"), era
            
            # Fuzzy matching
            import difflib
            era_names = [e.get("name", "") for e in eras]
            matches = difflib.get_close_matches(era_query, era_names, n=1, cutoff=0.6)
            
            if matches:
                matched_name = matches[0]
                matched_era = next((e for e in eras if e.get("name") == matched_name), None)
                if matched_era:
                    return matched_era.get("id"), matched_era

        except Exception as e:
            logger.error(f"Error resolving era: {e}")

        return None, None

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

            # ============ JUICE WRLD API INTENTS (PRIMARY MUSIC SOURCE) ============
            elif intent == "juice_search":
                logger.info(f"🎵 Routing to juice_search handler")
                await self._handle_juice_search(message, params.get("query", ""))

            elif intent == "juice_lyric_search":
                logger.info(f"🎵 Routing to juice_lyric_search handler")
                await self._handle_juice_lyric_search(message, params.get("phrase", ""))

            elif intent == "juice_song_info":
                await self._handle_juice_song_info(
                    message,
                    song_query=params.get("query"),
                    song_id=params.get("song_id"),
                    info_type=params.get("info_type", "details"),
                )

            elif intent == "juice_eras_list":
                await self._handle_juice_eras_list(message)

            elif intent == "juice_era_filter":
                await self._handle_juice_era_filter(message, params.get("era", ""))

            elif intent == "juice_category_filter":
                await self._handle_juice_category_filter(message, params.get("category", ""))

            elif intent == "juice_random":
                await self._handle_juice_random(message)

            elif intent == "juice_stats":
                await self._handle_juice_stats(message)

            elif intent == "juice_cover_art":
                await self._handle_juice_cover_art(message, params.get("query", ""))

            elif intent == "juice_stream":
                await self._handle_juice_stream(message, params.get("query", ""))

            elif intent == "juice_download":
                await self._handle_juice_download(message, params.get("query", ""))

            elif intent == "juice_browse":
                await self._handle_juice_browse(message)

            elif intent == "juice_collection":
                await self._handle_juice_collection(message, params.get("query", ""))

            elif intent == "juice_producer_filter":
                await self._handle_juice_producer_filter(message, params.get("producer", ""))

            # ============ LEGACY MUSIC INTENTS (ROUTED TO JUICE BY DEFAULT) ============
            elif intent == "music_lyrics":
                api_source = intent_result.get("api_source")
                logger.info(f"🎵 Routing to music_lyrics handler (api_source: {api_source})")
                await self._handle_music_lyrics(message, params.get("query", params.get("rest", "")), api_source)

            elif intent == "music_search":
                api_source = intent_result.get("api_source")
                logger.info(f"🎵 Routing to music_search handler (api_source: {api_source})")
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

    def _looks_like_year(self, value: str) -> bool:
        value = (value or "").strip()
        return len(value) == 4 and value.isdigit() and 1900 <= int(value) <= 2100

    @staticmethod
    def _normalize_match_text(text: str) -> str:
        import re

        t = (text or "").lower().strip()
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        t = re.sub(r"\s+", " ", t)
        return t

    @classmethod
    def _is_strong_title_match(cls, query: str, title: str) -> bool:
        q = cls._normalize_match_text(query)
        t = cls._normalize_match_text(title)
        return q == t or q in t or t in q

    async def _resolve_juice_song(
        self,
        *,
        song_query: Optional[str] = None,
        song_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            return {}

        if song_id is not None:
            return await self.bot.juice_wrld_api.get_song(song_id)

        if not song_query:
            return {}

        q = song_query.strip()
        if q.isdigit():
            return await self.bot.juice_wrld_api.get_song(int(q))

        songs = await self.bot.juice_wrld_api.search_songs(q, limit=5)
        if not songs:
            return {}

        best = songs[0]
        # Prefer exact-ish title matches
        for s in songs:
            if self._is_strong_title_match(q, s.get("title", "")):
                best = s
                break

        best_id = best.get("id")
        if best_id is not None:
            details = await self.bot.juice_wrld_api.get_song(best_id)
            return details or best

        return best

    async def _resolve_era(self, era_query: str) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            return None, None

        eras = await self.bot.juice_wrld_api.list_eras()
        if not eras:
            return None, None

        q = (era_query or "").strip()
        if not q:
            return None, None

        if q.isdigit():
            for era in eras:
                if str(era.get("id")) == q:
                    return era.get("id"), era
            return q, None

        qn = q.lower()
        best = None
        for era in eras:
            name = (era.get("name") or "").lower()
            if not name:
                continue
            if qn == name or qn in name or name in qn:
                best = era
                break

        if best:
            return best.get("id"), best

        return None, None

    def _is_probably_juice_query(self, query: str) -> bool:
        q = (query or "").lower()
        if "juice" in q or "wrld" in q or "juice wrld" in q:
            return True
        # If it doesn't mention another artist, assume Juice for this bot's music mode
        if " by " in q and not any(x in q for x in ["juice", "wrld"]):
            return False
        return True

    # ============ JUICE WRLD PRIMARY INTENT HANDLERS ============

    async def _handle_juice_search(self, message: discord.Message, query: str) -> None:
        """
        Handle Juice WRLD song search requests

        Args:
            message: Discord message object
            query: Search query (song title, ID, etc.)
        """
        logger.info(f"🔍 Juice WRLD search requested: '{query}' by user {message.author.id}")
        
        if not query:
            await message.reply("What song would you like to search for?")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            logger.error("Juice WRLD API is not initialized!")
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            # If a numeric ID is provided, jump directly to details
            if query.strip().isdigit():
                logger.info(f"📝 Fetching Juice WRLD song by ID: {query}")
                song = await self.bot.juice_wrld_api.get_song(int(query.strip()))
                if not song:
                    logger.warning(f"No song found for ID: {query}")
                    await message.reply(f"❌ No song found for ID: {query}")
                    return
                logger.info(f"✅ Found song by ID: {song.get('title')}")
                await message.reply(embed=create_discord_juice_wrld_embed(song=song))
                return

            logger.info(f"📝 Searching Juice WRLD API for: '{query}'")
            songs = await self.bot.juice_wrld_api.search_songs(query, limit=10)
            
            if not songs:
                logger.warning(f"No Juice WRLD songs found for: {query}")
                await message.reply(f"❌ No Juice WRLD songs found for: **{query}**")
                return

            logger.info(f"✅ Found {len(songs)} songs matching '{query}'")

            # If the top result matches strongly, show full details (test checklist expectation)
            if songs and self._is_strong_title_match(query, songs[0].get("title", "")):
                song_id = songs[0].get("id")
                if song_id is not None:
                    logger.info(f"📝 Fetching full details for strong match: {songs[0].get('title')}")
                    details = await self.bot.juice_wrld_api.get_song(song_id)
                    if details:
                        logger.info(f"✅ Sending Juice WRLD song details for: {details.get('title')}")
                        await message.reply(embed=create_discord_juice_wrld_embed(song=details))
                        return

            # Otherwise show a results embed
            logger.info(f"✅ Sending Juice WRLD search results embed with {len(songs)} songs")
            await message.reply(embed=create_discord_juice_wrld_search_embed(query=query, songs=songs))

    async def _handle_juice_lyric_search(self, message: discord.Message, phrase: str) -> None:
        if not phrase:
            await message.reply("What lyric phrase should I search for?")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            songs = await self.bot.juice_wrld_api.lyric_search(phrase, limit=10)
            embed = create_discord_juice_wrld_lyric_search_embed(phrase=phrase, songs=songs)
            await message.reply(embed=embed)

    async def _handle_juice_song_info(
        self,
        message: discord.Message,
        *,
        song_query: Optional[str],
        song_id: Optional[int],
        info_type: str,
    ) -> None:
        if not song_query and song_id is None:
            await message.reply("Which song are you asking about?")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            song = await self._resolve_juice_song(song_query=song_query, song_id=song_id)
            if not song:
                await message.reply("❌ I couldn't find that song in the Juice WRLD database.")
                return

            info_type = (info_type or "details").lower()

            if info_type == "producer":
                producers = song.get("producers") or []
                if not producers:
                    await message.reply("❌ Producer credits not available for this track.")
                    return
                embed = create_discord_juice_wrld_embed(song=song)
                await message.reply(content=f"🏭 **Producer(s):** {', '.join(producers)}", embed=embed)
                return

            if info_type in {"studio", "recording_date"}:
                studio = song.get("studio_location") or "Unknown studio/location"
                rec_date = song.get("recording_date") or "Unknown date"
                await message.reply(f"📍 **Recorded at** {studio} **on** {rec_date}.")
                # Also provide the full card
                await message.channel.send(embed=create_discord_juice_wrld_embed(song=song))
                return

            # Default: full details
            await message.reply(embed=create_discord_juice_wrld_embed(song=song))

    async def _handle_juice_eras_list(self, message: discord.Message) -> None:
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            eras = await self.bot.juice_wrld_api.list_eras()
            embeds = create_discord_juice_wrld_eras_embeds(eras)
            if not embeds:
                await message.reply("❌ No era data available.")
                return

            await message.reply(embed=embeds[0])
            for e in embeds[1:]:
                await message.channel.send(embed=e)

    async def _handle_juice_era_filter(self, message: discord.Message, era_query: str) -> None:
        if not era_query:
            await message.reply("Which era (name or ID) should I filter by?")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            # Year routing: map year → matching eras by timeframe
            if self._looks_like_year(era_query):
                year = int(era_query.strip())
                eras = await self.bot.juice_wrld_api.list_eras()
                matched = []
                for era in eras:
                    s = str(era.get("start_date") or "")
                    e = str(era.get("end_date") or "")
                    if str(year) in s or str(year) in e:
                        matched.append(era)

                if not matched:
                    await message.reply(f"❌ No eras found matching year {year}.")
                    return

                # Fetch songs for the first matching era (and mention others)
                era = matched[0]
                era_id = era.get("id")
                songs = await self.bot.juice_wrld_api.filter_songs(era=era_id, limit=25)
                subtitle = f"Filtered by year **{year}** → era **{era.get('name')}**"
                await message.reply(embed=create_discord_juice_wrld_song_list_embed("🎭 Songs by Year", songs, subtitle=subtitle))
                return

            era_id, era_obj = await self._resolve_era(era_query)
            if era_id is None:
                await message.reply(f"❌ I couldn't find an era matching: **{era_query}**")
                return

            songs = await self.bot.juice_wrld_api.filter_songs(era=era_id, limit=25)
            subtitle = None
            if era_obj:
                subtitle = f"_{era_obj.get('start_date')} → {era_obj.get('end_date')}_"
            await message.reply(
                embed=create_discord_juice_wrld_song_list_embed(
                    title=f"🎭 Songs from {era_obj.get('name') if era_obj else era_query}",
                    songs=songs,
                    subtitle=subtitle,
                )
            )

    async def _handle_juice_category_filter(self, message: discord.Message, category: str) -> None:
        if not category:
            await message.reply("Which category? (released / unreleased / unsurfaced / studio_session)")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        cat = category.strip().lower().replace(" ", "_")
        if cat == "studio_sessions":
            cat = "studio_session"

        async with message.channel.typing():
            # Unreleased database mode: include unsurfaced too (feature #14)
            if cat == "unreleased":
                unreleased = await self.bot.juice_wrld_api.filter_songs(category="unreleased", limit=25)
                unsurfaced = await self.bot.juice_wrld_api.filter_songs(category="unsurfaced", limit=25)
                # Merge by ID when possible
                seen = set()
                merged = []
                for s in unreleased + unsurfaced:
                    sid = s.get("id")
                    if sid is not None and sid in seen:
                        continue
                    if sid is not None:
                        seen.add(sid)
                    merged.append(s)
                await message.reply(
                    embed=create_discord_juice_wrld_song_list_embed(
                        title="🟣 Unreleased + Unsurfaced Database",
                        songs=merged,
                        subtitle=f"Showing {min(len(merged), 25)} results (combined)",
                    )
                )
                return

            songs = await self.bot.juice_wrld_api.filter_songs(category=cat, limit=25)
            await message.reply(
                embed=create_discord_juice_wrld_song_list_embed(
                    title=f"📁 Category: {cat.replace('_', ' ').title()}",
                    songs=songs,
                )
            )

    async def _handle_juice_random(self, message: discord.Message) -> None:
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            song = await self.bot.juice_wrld_api.random_song()
            if not song:
                await message.reply("❌ Couldn't fetch a random track right now.")
                return
            await message.reply(embed=create_discord_juice_wrld_embed(song=song))

    async def _handle_juice_stats(self, message: discord.Message) -> None:
        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            stats = await self.bot.juice_wrld_api.get_stats()
            await message.reply(embed=create_discord_juice_wrld_stats_embed(stats))

    async def _handle_juice_cover_art(self, message: discord.Message, query: str) -> None:
        if not query:
            await message.reply("Which song do you want cover art for?")
            return

        async with message.channel.typing():
            song = await self._resolve_juice_song(song_query=query, song_id=None)
            if not song:
                await message.reply("❌ Couldn't find that song.")
                return
            await message.reply(embed=create_discord_juice_wrld_cover_art_embed(song))

    async def _handle_juice_stream(self, message: discord.Message, query: str) -> None:
        if not query:
            await message.reply("Which song do you want a streaming link for?")
            return

        async with message.channel.typing():
            song = await self._resolve_juice_song(song_query=query, song_id=None)
            if not song:
                await message.reply("❌ Couldn't find that song.")
                return

            stream_url = song.get("stream_url")
            if stream_url:
                await message.reply(content=f"🔗 Listen here: {stream_url}", embed=create_discord_juice_wrld_embed(song=song))
            else:
                await message.reply("❌ No streaming link available for this track.")

    async def _handle_juice_collection(self, message: discord.Message, query: str) -> None:
        if not query:
            await message.reply("What should I include in the .zip? (comma-separated song titles, or an era name/ID)")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            q = query.strip()

            # If multiple songs are provided
            if "," in q:
                parts = [p.strip() for p in q.split(",") if p.strip()]
                song_ids = []
                for part in parts[:10]:
                    song = await self._resolve_juice_song(song_query=part, song_id=None)
                    sid = song.get("id") if song else None
                    if sid is not None:
                        song_ids.append(sid)

                if not song_ids:
                    await message.reply("❌ I couldn't resolve any song IDs for that collection.")
                    return

                url = await self.bot.juice_wrld_api.generate_archive(song_ids=song_ids)
                if not url:
                    await message.reply("❌ Couldn't generate the archive right now.")
                    return

                await message.reply(f"📦 Your collection is ready: {url}")
                return

            # Otherwise treat it as an era
            era_id, era_obj = await self._resolve_era(q.replace(" era", ""))
            if era_id is None:
                await message.reply("❌ I couldn't find that era. Try an era name, era ID, or a comma-separated song list.")
                return

            url = await self.bot.juice_wrld_api.generate_archive(era=era_id)
            if not url:
                await message.reply("❌ Couldn't generate the era archive right now.")
                return

            era_name = era_obj.get("name") if era_obj else str(q)
            await message.reply(f"📦 **{era_name}** archive ready: {url}")

    async def _handle_juice_producer_filter(self, message: discord.Message, producer: str) -> None:
        if not producer:
            await message.reply("Which producer should I filter by?")
            return

        if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
            await message.reply("❌ Juice WRLD API is not available right now.")
            return

        async with message.channel.typing():
            songs = await self.bot.juice_wrld_api.filter_songs(producer=producer, limit=25)
            await message.reply(
                embed=create_discord_juice_wrld_song_list_embed(
                    title=f"🏭 Produced by {producer}",
                    songs=songs,
                )
            )

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
        logger.info(f"🎵 Music lyrics requested: '{query}' (api_source: {api_source}) by user {message.author.id}")
        
        if not query:
            await message.reply("What song's lyrics would you like me to find?")
            return

        try:
            async with message.channel.typing():
                # Determine which API to use
                # api_source is one of: "juice_wrld", "genius", "soundcloud", or None
                
                # Track if we should try Genius as fallback
                should_try_genius = False

                if api_source == "juice_wrld":
                    logger.info(f"📝 Routing lyrics request to Juice WRLD API for: '{query}'")
                    # Use Juice WRLD API first (primary). Genius is backup for Juice WRLD songs only.
                    if not hasattr(self.bot, "juice_wrld_api") or self.bot.juice_wrld_api is None:
                        await message.reply("⚠️ Juice WRLD API is unavailable, trying Genius backup...")
                        should_try_genius = True
                    else:
                        try:
                            # 1. Search and resolve the song from Juice WRLD API (Requirement #1)
                            logger.info(f"Searching Juice WRLD API for: {query}")
                            song = await self._resolve_juice_song(song_query=query, song_id=None)

                            if not song or not song.get("id"):
                                # Auto-fallback to Genius with notification (Requirement #4)
                                await message.reply("⚠️ Song not found in Juice WRLD database, checking Genius...")
                                should_try_genius = True
                            else:
                                # 2. Call the dedicated lyrics endpoint (Requirement #1)
                                logger.info(f"Fetching lyrics from Juice WRLD API for song ID: {song.get('id')}")
                                lyrics = await self.bot.juice_wrld_api.get_lyrics(song["id"])
                                lyrics = (lyrics or "").strip()

                                if lyrics:
                                    # Update song dict with retrieved lyrics
                                    song["lyrics"] = lyrics

                                    # 3. Format response as Discord embed with metadata (Requirement #1)
                                    await message.reply(embed=create_discord_juice_wrld_embed(song=song))

                                    # 4. Send lyrics as plain text (chunked), preserving section labels like [Verse] (Requirement #2)
                                    header = f"📜 **LYRICS — {song.get('title', 'Unknown')}**\n\n"

                                    content = header + lyrics
                                    if len(content) > 1900:
                                        chunks = []
                                        current_chunk = ""
                                        for line in content.split("\n"):
                                            if len(current_chunk) + len(line) + 1 > 1900:
                                                chunks.append(current_chunk)
                                                current_chunk = line + "\n"
                                            else:
                                                current_chunk += line + "\n"
                                        if current_chunk:
                                            chunks.append(current_chunk)

                                        for chunk in chunks:
                                            await message.channel.send(chunk)
                                    else:
                                        await message.channel.send(content)

                                    logger.info(
                                        f"Juice WRLD lyrics retrieved from Juice WRLD API for: {query} by user {message.author.id}"
                                    )
                                    return

                                # No lyrics in Juice WRLD payload - fall back to Genius (backup)
                                await message.reply("⚠️ Lyrics not found in Juice WRLD database, checking Genius...")
                                should_try_genius = True

                        except Exception as e:
                            logger.error(f"Error retrieving from Juice WRLD API: {e}", exc_info=True)
                            await message.reply("⚠️ Error accessing Juice WRLD database, checking Genius fallback...")
                            should_try_genius = True

                if api_source == "genius" or should_try_genius:
                    # Genius fallback (backup only): only for Juice WRLD songs when Juice WRLD API fails.
                    if not self._is_probably_juice_query(query):
                        await message.reply("❌ Genius fallback is only enabled for Juice WRLD songs.")
                        return

                    if should_try_genius and api_source != "genius":
                        # Notification already sent in Juice WRLD block
                        pass

                    # Use Genius API (Plain text output only)
                    if not hasattr(self.bot, 'genius_api') or self.bot.genius_api is None:
                        await message.reply("❌ Genius API is not configured. Please set GENIUS_ACCESS_TOKEN in .env")
                        return

                    # Search for the song
                    songs = await self.bot.genius_api.search_songs(query, limit=3)

                    if not songs:
                        if should_try_genius:
                            await message.reply(f"❌ Song not found in either database (Juice WRLD or Genius) for: {query}")
                        else:
                            await message.reply(f"❌ No lyrics found for: {query}\n\nTry a different search term?")
                        return

                    # Get the first matching song with details
                    song_id = songs[0].get('id')
                    if song_id:
                        song = await self.bot.genius_api.get_song(song_id)
                        
                        # Get full lyrics text
                        lyrics = await self.bot.genius_api.get_lyrics(song_id)

                        # Get annotations
                        annotations = await self.bot.genius_api.get_song_annotations(song_id, limit=5)

                        # Format response as PLAIN TEXT (no Discord embed)
                        response = format_lyrics_card(song=song, lyrics=lyrics, annotations=annotations)
                        
                        # Split response if too long for Discord (2000 char limit)
                        if len(response) > 1900:
                            # Send in chunks
                            chunks = []
                            current_chunk = ""
                            for line in response.split('\n'):
                                if len(current_chunk) + len(line) + 1 > 1900:
                                    chunks.append(current_chunk)
                                    current_chunk = line + '\n'
                                else:
                                    current_chunk += line + '\n'
                            if current_chunk:
                                chunks.append(current_chunk)
                            
                            # Send first chunk as reply, rest as follow-ups
                            await message.reply(chunks[0])
                            for chunk in chunks[1:]:
                                await message.channel.send(chunk)
                        else:
                            await message.reply(response)

                        logger.info(f"Genius lyrics retrieved (plain text) for: {query} by user {message.author.id}")
                    else:
                        await message.reply("❌ Could not retrieve song details")

                elif api_source == "soundcloud":
                    # SoundCloud doesn't provide lyrics
                    await message.reply("❌ SoundCloud doesn't provide lyrics. Use Genius for lyrics instead.")

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
        logger.info(f"🎵 Music search requested: '{query}' (api_source: {api_source}) by user {message.author.id}")
        
        if not query:
            await message.reply("What would you like me to search for?")
            return

        try:
            async with message.channel.typing():
                # Determine API based on request type
                # SoundCloud: Only for explicit SoundCloud track discovery
                if api_source == "soundcloud":
                    logger.info(f"📝 Routing search request to SoundCloud API for: '{query}'")
                    # Use SoundCloud for track discovery ONLY on SoundCloud platform
                    if not hasattr(self.bot, 'soundcloud_api') or self.bot.soundcloud_api is None:
                        await message.reply(
                            "❌ SoundCloud API is not configured. "
                            "Please set SOUNDCLOUD_CLIENT_ID and SOUNDCLOUD_CLIENT_SECRET in .env"
                        )
                        return

                    # Search for tracks on SoundCloud
                    logger.info(f"Searching SoundCloud for: {query} by user {message.author.id}")
                    tracks = await self.bot.soundcloud_api.search_tracks(query, limit=5)

                    if not tracks:
                        await message.reply(f"❌ No tracks found on SoundCloud for: {query}")
                        return

                    # Format response with SoundCloud track info
                    response = f"🎧 **Found {len(tracks)} tracks on SoundCloud** matching '{query}':\n\n"
                    
                    for i, track in enumerate(tracks[:5], 1):
                        title = track.get('title', 'Unknown Track')
                        artist = track.get('artist', 'Unknown Artist')
                        duration_ms = track.get('duration', 0)
                        play_count = track.get('playback_count', 0)
                        permalink = track.get('permalink_url', '')
                        
                        # Format duration
                        if duration_ms:
                            duration_sec = duration_ms // 1000
                            minutes, seconds = divmod(duration_sec, 60)
                            duration_str = f"{minutes}:{seconds:02d}"
                        else:
                            duration_str = "Unknown"
                        
                        response += f"{i}. **{title}** by {artist}\n"
                        response += f"   ⏱️ Duration: {duration_str}"
                        if play_count:
                            response += f" | 🎮 {play_count:,} plays"
                        response += "\n"
                        if permalink:
                            response += f"   🔗 [Listen on SoundCloud]({permalink})\n"
                        response += "\n"
                    
                    response += "*Tracks found on SoundCloud platform*"
                    
                    await message.reply(response)
                    logger.info(f"SoundCloud track discovery completed for: {query} by user {message.author.id}")
                    return

                elif api_source == "juice_wrld":
                    # Juice WRLD API is the primary music source
                    logger.info(f"📝 Delegating to Juice WRLD handler for: '{query}'")
                    await self._handle_juice_search(message, query)
                    logger.info(f"✅ Juice WRLD handler completed for: '{query}'")
                    return

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
                # Juice WRLD API is a Juice WRLD song database. For "artist" requests,
                # we provide database stats (and still allow Genius as an optional fallback).
                if api_source == "juice_wrld":
                    await message.reply(
                        "🎤 The Juice WRLD API focuses on **Juice WRLD songs** rather than general artist profiles.\n"
                        "Here are the current database stats:"
                    )
                    await self._handle_juice_stats(message)
                    return

                else:
                    # Fall back to Genius API for artist info
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
                    response = format_lyrics_card(song=song, lyrics=None, annotations=annotations)

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
