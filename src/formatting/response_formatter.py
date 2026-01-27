"""
Unified Response Formatter for YamiBot

This module provides consistent, answer-only response formatting across all API types
with intelligent file embedding and message chunking for Discord.
"""

import discord
from typing import Dict, List, Optional, Tuple, Any
import re
from datetime import datetime

from ..utils.logger import setup_logging

logger = setup_logging(__name__)


# Constants
DISCORD_MESSAGE_LIMIT = 2000
EMOJI_CONSTANTS = {
    # Music
    "music": "🎵",
    "artist": "👤", 
    "album": "💿",
    "date": "📅",
    "duration": "⏱️",
    "producer": "🎹",
    "features": "🎤",
    "genre": "🎸",
    "stats": "📊",
    "lyrics": "📜",
    "annotation": "💬",
    "link": "🔗",
    "search": "🔍",
    "listening": "🎧",
    "plays": "🎮",
    "likes": "❤️",
    
    # UI Elements
    "part": "1️⃣",
    "search_results": "🔎",
    "verified": "✅",
    "loading": "⚠️",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    
    # Music Platforms
    "spotify": "🎶",
    "soundcloud": "🎧",
    "youtube": "📺",
    "apple_music": "🍎",
    
    # Artists & Biography
    "born": "📅",
    "died": "💀",
    "followers": "👥",
    "bio": "📖"
}


class ResponseFormatter:
    """Unified response formatter with chunking and file embedding"""
    
    @staticmethod
    def format_response(intent_type: str, data: Dict[str, Any], api_source: Optional[str] = None) -> str:
        """
        Main formatter dispatcher that routes to appropriate API-specific formatters
        
        Args:
            intent_type: Type of intent (juice_search, music_lyrics, etc.)
            data: Response data from API
            api_source: Source API (genius, juice_wrld, soundcloud, etc.)
            
        Returns:
            Formatted response string (may need chunking)
        """
        try:
            logger.debug(f"🎯 Formatting response for {intent_type} from {api_source}")
            
            # Route to appropriate formatter based on intent and API
            if intent_type in ["juice_search", "juice_song_info"] and api_source == "juice_wrld":
                return ResponseFormatter._format_juice_song(data)
            
            elif intent_type in ["juice_lyric_search"] and api_source == "juice_wrld":
                return ResponseFormatter._format_juice_lyric_search(data)
            
            elif intent_type == "music_lyrics" and api_source == "genius":
                return ResponseFormatter._format_genius_lyrics(data)
            
            elif intent_type == "music_search" and api_source == "soundcloud":
                return ResponseFormatter._format_soundcloud_tracks(data)
            
            elif intent_type == "juice_stats":
                return ResponseFormatter._format_juice_stats(data)
            
            elif intent_type == "juice_artist_info":
                return ResponseFormatter._format_juice_artist(data)
            
            elif intent_type in ["search", "web_search"]:
                return ResponseFormatter._format_search_results(data)
            
            elif intent_type in ["model_list", "model_info"]:
                return ResponseFormatter._format_model_response(data)
            
            elif intent_type in ["chat", "analysis", "code"]:
                return ResponseFormatter._format_chat_response(data)
            
            else:
                # Fallback for unknown intents
                logger.warning(f"Unknown intent type: {intent_type}, falling back to generic formatting")
                return ResponseFormatter._format_generic(data)
                
        except Exception as e:
            logger.error(f"Error formatting response for {intent_type}: {e}")
            return f"❌ Error formatting response: {str(e)}"
    
    @staticmethod
    def _format_juice_song(song_data: Dict[str, Any]) -> str:
        """Format Juice WRLD song information"""
        lines = []
        
        # Song header
        title = song_data.get("title", "Unknown Song")
        artist = song_data.get("artist", "Juice WRLD")
        album = song_data.get("album")
        release_date = song_data.get("release_date")
        duration = song_data.get("duration")
        status = song_data.get("status", "released")
        era = song_data.get("era")
        
        lines.append(f"{EMOJI_CONSTANTS['music']} **{title}**")
        lines.append(f"{EMOJI_CONSTANTS['artist']} {artist}")
        
        if album:
            lines.append(f"{EMOJI_CONSTANTS['album']} {album}")
        
        if release_date:
            lines.append(f"{EMOJI_CONSTANTS['date']} {release_date}")
        
        if duration:
            lines.append(f"{EMOJI_CONSTANTS['duration']} {ResponseFormatter._format_duration(duration)}")
        
        # Metadata
        producers = song_data.get("producers", [])
        if producers:
            lines.append(f"{EMOJI_CONSTANTS['producer']} Produced by: {', '.join(producers[:3])}")
        
        features = song_data.get("features", [])
        if features:
            lines.append(f"{EMOJI_CONSTANTS['features']} Featuring: {', '.join(features[:3])}")
        
        play_count = song_data.get("play_count")
        if play_count:
            lines.append(f"{EMOJI_CONSTANTS['stats']} {play_count:,} plays")
        
        # Era and Status
        if era or status:
            meta_parts = []
            if era:
                meta_parts.append(f"Era: {era}")
            if status:
                meta_parts.append(f"Status: {status.replace('_', ' ').title()}")
            if meta_parts:
                lines.append(f"🎭 {' | '.join(meta_parts)}")
        
        lines.append("")  # Empty line
        
        # Links
        links = []
        if song_data.get("genius_url"):
            links.append(f"[Genius]({song_data['genius_url']})")
        if song_data.get("stream_url"):
            links.append(f"[Stream]({song_data['stream_url']})")
        if song_data.get("juice_wrld_url"):
            links.append(f"[Juice WRLD API]({song_data['juice_wrld_url']})")
        
        if links:
            lines.append(f"{EMOJI_CONSTANTS['link']} **Listen:** {' | '.join(links)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_juice_lyric_search(data: Dict[str, Any]) -> str:
        """Format Juice WRLD lyric search results"""
        lines = []
        
        query = data.get("query", "Unknown phrase")
        songs = data.get("songs", [])
        
        lines.append(f"{EMOJI_CONSTANTS['lyrics']} **Songs containing '{query}':**")
        lines.append("")
        
        if not songs:
            lines.append("❌ No songs found containing that phrase.")
            return "\n".join(lines)
        
        # Show top results
        for i, song in enumerate(songs[:10], 1):
            title = song.get("title", "Unknown Song")
            snippet = song.get("matched_lyrics", "")
            song_id = song.get("id")
            
            lines.append(f"**{i}. {title}**")
            if song_id is not None:
                lines.append(f"   `ID: {song_id}`")
            
            if snippet:
                # Highlight the search term
                highlighted = ResponseFormatter._highlight_text(snippet, query)
                lines.append(f"   > {highlighted}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_genius_lyrics(data: Dict[str, Any]) -> str:
        """Format Genius lyrics with annotations"""
        lines = []
        
        song = data.get("song", {})
        lyrics = data.get("lyrics", "")
        annotations = data.get("annotations", [])
        
        # Header
        title = song.get("title", "Unknown Song")
        artist = song.get("artist", "Unknown Artist")
        album = song.get("album")
        release_date = song.get("release_date")
        
        lines.append(f"{EMOJI_CONSTANTS['lyrics']} **LYRICS: {title}**")
        lines.append(f"{EMOJI_CONSTANTS['artist']} {artist}")
        
        if album:
            lines.append(f"{EMOJI_CONSTANTS['album']} {album}")
        
        if release_date:
            lines.append(f"{EMOJI_CONSTANTS['date']} {release_date}")
        
        lines.append("")
        lines.append("=" * 50)
        lines.append("")
        
        # Full lyrics
        if lyrics:
            lines.append("**📜 LYRICS:**")
            lines.append("")
            lines.append(lyrics)
            lines.append("")
            lines.append("=" * 50)
        else:
            lines.append("⚠️ Lyrics not available")
            lines.append("")
        
        # Annotations
        if annotations:
            lines.append("")
            lines.append("**💬 ANNOTATIONS:**")
            lines.append("")
            
            for i, ann in enumerate(annotations[:5], 1):
                lyric = ann.get("lyric", "").strip()
                annotation = ann.get("annotation", "").strip()
                author = ann.get("author", "Unknown")
                
                if lyric and annotation:
                    # Truncate long annotations
                    if len(annotation) > 400:
                        annotation = annotation[:397] + "..."
                    
                    lines.append(f"**{i}. \"{lyric}\"**")
                    lines.append(f"   💬 {author}:")
                    lines.append(f"   {annotation}")
                    lines.append("")
        
        # Link
        if song.get("url"):
            lines.append(f"{EMOJI_CONSTANTS['link']} [View on Genius]({song['url']})")
        
        lines.append("")
        lines.append("*Powered by Genius*")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_soundcloud_tracks(data: Dict[str, Any]) -> str:
        """Format SoundCloud track results"""
        lines = []
        
        tracks = data.get("tracks", [])
        query = data.get("query", "")
        
        lines.append(f"{EMOJI_CONSTANTS['search_results']} **Found {len(tracks)} tracks** matching '{query}':")
        lines.append("")
        
        for i, track in enumerate(tracks[:10], 1):
            title = track.get("title", "Unknown Track")
            artist = track.get("artist", "Unknown Artist")
            duration_ms = track.get("duration", 0)
            play_count = track.get("playback_count", 0)
            likes_count = track.get("likes_count", 0)
            genre = track.get("genre")
            permalink = track.get("permalink_url")
            
            lines.append(f"**{i}. {title}**")
            lines.append(f"   {EMOJI_CONSTANTS['artist']} {artist}")
            
            # Duration
            if duration_ms:
                duration_sec = duration_ms // 1000
                minutes, seconds = divmod(duration_sec, 60)
                lines.append(f"   {EMOJI_CONSTANTS['duration']} {minutes}:{seconds:02d}")
            
            # Stats
            stats = []
            if play_count:
                stats.append(f"{play_count:,} plays")
            if likes_count:
                stats.append(f"{likes_count:,} likes")
            if stats:
                lines.append(f"   📊 {' | '.join(stats)}")
            
            # Genre
            if genre:
                lines.append(f"   {EMOJI_CONSTANTS['genre']} {genre}")
            
            # Link
            if permalink:
                lines.append(f"   {EMOJI_CONSTANTS['link']} [Listen on SoundCloud]({permalink})")
            
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_juice_stats(data: Dict[str, Any]) -> str:
        """Format Juice WRLD database statistics"""
        lines = []
        
        # Header
        lines.append(f"📊 **Juice WRLD Database Statistics**")
        lines.append("")
        
        # Extract stats
        total_released = data.get("released") or data.get("total_released", 0)
        total_unreleased = data.get("unreleased") or data.get("total_unreleased", 0)
        total_unsurfaced = data.get("unsurfaced") or data.get("total_unsurfaced", 0)
        total_sessions = data.get("studio_session") or data.get("studio_sessions", 0)
        total_all = data.get("total") or data.get("total_songs", 0)
        
        # Stats display
        if total_released:
            lines.append(f"✅ **Released:** {total_released:,}")
        if total_unreleased:
            lines.append(f"🟣 **Unreleased:** {total_unreleased:,}")
        if total_unsurfaced:
            lines.append(f"🕳️ **Unsurfaced:** {total_unsurfaced:,}")
        if total_sessions:
            lines.append(f"🎛️ **Studio Sessions:** {total_sessions:,}")
        if total_all:
            lines.append(f"📦 **Total:** {total_all:,}")
        
        # Add raw stats if none were mapped
        if len(lines) <= 2:  # Only header and empty line
            lines.append("**Raw Database Info:**")
            for key, value in list(data.items())[:10]:
                if value:
                    lines.append(f"• **{key.replace('_', ' ').title()}:** {value}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_juice_artist(data: Dict[str, Any]) -> str:
        """Format Juice WRLD artist information"""
        lines = []
        
        artist = data.get("artist", {})
        
        # Header
        name = artist.get("name", "Unknown Artist")
        lines.append(f"{EMOJI_CONSTANTS['artist']} **{name}**")
        
        # Verified status
        if artist.get("is_verified"):
            lines.append(f"{EMOJI_CONSTANTS['verified']} Verified Artist")
        
        # Stats
        songs_count = artist.get("songs_count", 0)
        followers = artist.get("followers", 0)
        
        if songs_count:
            lines.append(f"{EMOJI_CONSTANTS['music']} {songs_count:,} songs")
        if followers:
            lines.append(f"{EMOJI_CONSTANTS['followers']} {followers:,} followers")
        
        # Alternate names
        alt_names = artist.get("alternate_names", [])
        if alt_names:
            lines.append(f"🏷️ Also known as: {', '.join(alt_names[:3])}")
        
        lines.append("")
        
        # Biography
        bio = artist.get("bio", "").strip()
        if bio:
            if len(bio) > 1000:
                bio = bio[:997] + "..."
            lines.append(f"{EMOJI_CONSTANTS['bio']} **Biography:**")
            lines.append(bio)
            lines.append("")
        
        # Genres
        genres = artist.get("genres", [])
        if genres:
            lines.append(f"{EMOJI_CONSTANTS['genre']} **Genres:** {', '.join(genres[:5])}")
        
        # Links
        links = []
        if artist.get("genius_url"):
            links.append(f"[Genius]({artist['genius_url']})")
        if artist.get("juice_wrld_url"):
            links.append(f"[Juice WRLD API]({artist['juice_wrld_url']})")
        
        if links:
            lines.append(f"{EMOJI_CONSTANTS['link']} {' | '.join(links)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_search_results(data: Dict[str, Any]) -> str:
        """Format web search results"""
        lines = []
        
        query = data.get("query", "")
        results = data.get("results", [])
        
        lines.append(f"{EMOJI_CONSTANTS['search']} **Search results for '{query}':**")
        lines.append("")
        
        if not results:
            lines.append("❌ No results found.")
            return "\n".join(lines)
        
        for i, result in enumerate(results[:5], 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            
            lines.append(f"**{i}. {title}**")
            if url:
                lines.append(f"   {EMOJI_CONSTANTS['link']} {url}")
            if snippet:
                lines.append(f"   {snippet[:200]}{'...' if len(snippet) > 200 else ''}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_model_response(data: Dict[str, Any]) -> str:
        """Format AI model information"""
        lines = []
        
        models = data.get("models", [])
        provider = data.get("provider")
        
        if provider:
            lines.append(f"🤖 **{provider.title()} Models:**")
        else:
            lines.append("🤖 **Available AI Models:**")
        
        lines.append("")
        
        for model in models[:10]:
            name = model.get("name", "Unknown")
            best_for = model.get("best_for", [])
            context_length = model.get("context_length")
            
            lines.append(f"**{name}**")
            if best_for:
                lines.append(f"   Best for: {', '.join(best_for)}")
            if context_length:
                lines.append(f"   Context: {context_length:,} tokens")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_chat_response(data: Dict[str, Any]) -> str:
        """Format chat/conversational responses"""
        lines = []
        
        response = data.get("response", "")
        
        if response:
            lines.append(response)
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_generic(data: Dict[str, Any]) -> str:
        """Fallback formatter for unknown response types"""
        lines = []
        
        # Try to extract meaningful content
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and value.strip():
                    lines.append(f"**{key.replace('_', ' ').title()}:** {value}")
                elif isinstance(value, (int, float)) and value:
                    lines.append(f"**{key.replace('_', ' ').title()}:** {value}")
        elif isinstance(data, str):
            lines.append(data)
        else:
            lines.append("Response data received but could not be formatted.")
        
        return "\n".join(lines)
    
    @staticmethod
    def chunk_message(message: str, max_length: int = DISCORD_MESSAGE_LIMIT) -> List[str]:
        """
        Split a long message into multiple chunks while preserving formatting
        
        Args:
            message: Message to chunk
            max_length: Maximum length per chunk (default: 2000 for Discord)
            
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        lines = message.split('\n')
        current_chunk = ""
        
        for line in lines:
            # Check if adding this line would exceed the limit
            potential_chunk = current_chunk + '\n' + line if current_chunk else line
            
            if len(potential_chunk) <= max_length:
                current_chunk = potential_chunk
            else:
                # If current chunk has content, save it
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # If single line is too long, split it
                if len(line) > max_length:
                    # Split long line at word boundaries
                    words = line.split(' ')
                    temp_line = ""
                    for word in words:
                        potential_line = temp_line + ' ' + word if temp_line else word
                        if len(potential_line) <= max_length:
                            temp_line = potential_line
                        else:
                            if temp_line:
                                chunks.append(temp_line)
                            temp_line = word
                    
                    if temp_line:
                        current_chunk = temp_line
                else:
                    current_chunk = line
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    @staticmethod
    def add_pagination(chunks: List[str]) -> List[str]:
        """
        Add pagination numbers to message chunks
        
        Args:
            chunks: List of message chunks
            
        Returns:
            List with pagination headers added
        """
        if len(chunks) <= 1:
            return chunks
        
        total_chunks = len(chunks)
        paginated_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            if i == 1:
                # First chunk - just add total count
                header = f"📄 **Part {i} of {total_chunks}**\n\n"
                paginated_chunks.append(header + chunk)
            else:
                # Subsequent chunks - add continuation header
                header = f"📄 **Part {i} of {total_chunks}** (continued)\n\n"
                paginated_chunks.append(header + chunk)
        
        return paginated_chunks
    
    @staticmethod
    async def embed_files_in_response(message: str, files_data: List[Dict[str, str]]) -> Tuple[str, List[discord.File]]:
        """
        Embed files in response when possible, fall back to links otherwise
        
        Args:
            message: Message content
            files_data: List of file data with 'url', 'type', 'context' keys
            
        Returns:
            Tuple of (updated_message, list_of_discord_files)
        """
        from ..file_handler import file_handler
        
        discord_files = []
        updated_message = message
        
        try:
            for file_data in files_data:
                url = file_data.get("url")
                file_type = file_data.get("type", "")
                context = file_data.get("context", "")
                
                if not url:
                    continue
                
                # Check if file can be embedded based on type and size
                if file_type.lower() in ["image", "audio"] and context:
                    try:
                        result = await file_handler.prepare_file_for_discord(url, context)
                        
                        if result['should_embed'] and result['file_path']:
                            # Add file to Discord files list
                            discord_files.append(discord.File(str(result['file_path'])))
                            
                            # Update message to indicate file is attached
                            updated_message += f"\n\n📎 **{context}** attached as file."
                        else:
                            # Fall back to link
                            updated_message += f"\n\n📎 **{context}:** {url}"
                    
                    except Exception as e:
                        logger.error(f"Error preparing file for embedding: {e}")
                        updated_message += f"\n\n📎 **{context}:** {url}"
        
        except Exception as e:
            logger.error(f"Error in embed_files_in_response: {e}")
        
        return updated_message, discord_files
    
    @staticmethod
    def _format_duration(duration) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if not duration:
            return "Unknown"
        
        # Already formatted
        if isinstance(duration, str):
            return duration
        
        # Convert to seconds
        if isinstance(duration, (int, float)):
            total_seconds = int(duration)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        
        return "Unknown"
    
    @staticmethod
    def _highlight_text(text: str, search_term: str) -> str:
        """Highlight search term in text using bold formatting"""
        if not text or not search_term:
            return text
        
        # Simple case-insensitive replacement
        pattern = re.escape(search_term)
        return re.sub(pattern, f"**{search_term}**", text, flags=re.IGNORECASE)


# Main formatting function for external use
def format_response(intent_type: str, data: Dict[str, Any], api_source: Optional[str] = None) -> str:
    """
    Main entry point for response formatting
    
    Args:
        intent_type: Type of intent
        data: Response data from API
        api_source: Source API
        
    Returns:
        Formatted response string
    """
    return ResponseFormatter.format_response(intent_type, data, api_source)


def chunk_and_format_response(intent_type: str, data: Dict[str, Any], api_source: Optional[str] = None, 
                            include_pagination: bool = True) -> List[str]:
    """
    Format response and chunk if necessary
    
    Args:
        intent_type: Type of intent
        data: Response data from API  
        api_source: Source API
        include_pagination: Whether to add pagination numbers
        
    Returns:
        List of message chunks ready to send
    """
    # Format the response
    response = format_response(intent_type, data, api_source)
    
    # Chunk the response
    chunks = ResponseFormatter.chunk_message(response)
    
    # Add pagination if needed
    if include_pagination and len(chunks) > 1:
        chunks = ResponseFormatter.add_pagination(chunks)
    
    return chunks