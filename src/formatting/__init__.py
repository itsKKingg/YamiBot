"""
Formatting module for YamiBot

This module contains formatters for various response types.
"""

from .music_formatter import (
    format_song_card,
    format_song_list,
    format_artist_card,
    format_album_card,
    format_discography,
    truncate_for_discord,
    format_artist_search_results,
    format_album_search_results,
    format_featured_songs,
    # Keep existing exports for backwards compatibility
    format_lyrics_card,
    format_artist_bio,
    format_annotation,
    format_soundcloud_embed,
    format_soundcloud_artist,
    format_soundcloud_playlist,
    create_discord_embed,
    create_discord_genius_embed
)

__all__ = [
    "format_song_card",
    "format_song_list",
    "format_artist_card",
    "format_album_card",
    "format_discography",
    "truncate_for_discord",
    "format_artist_search_results",
    "format_album_search_results",
    "format_featured_songs",
    # Existing exports
    "format_lyrics_card",
    "format_artist_bio",
    "format_annotation",
    "format_soundcloud_embed",
    "format_soundcloud_artist",
    "format_soundcloud_playlist",
    "create_discord_embed",
    "create_discord_genius_embed"
]
