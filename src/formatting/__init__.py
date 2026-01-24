"""
Formatting module for YamiBot

This module contains formatters for various response types.
"""

from .music_formatter import (
    format_lyrics_card,
    format_artist_bio,
    format_annotation,
    format_soundcloud_track_details,
    format_soundcloud_embed,
    format_soundcloud_artist,
    format_soundcloud_playlist,
    create_discord_embed,
    create_discord_genius_embed,
    # Juice WRLD formatters
    format_song_card,
    format_song_list,
    format_artist_info,
    create_discord_juice_wrld_embed,
    create_discord_juice_wrld_search_embed,
    create_discord_juice_wrld_song_list_embed,
    create_discord_juice_wrld_lyric_search_embed,
    create_discord_juice_wrld_stats_embed,
    create_discord_juice_wrld_eras_embeds,
    create_discord_juice_wrld_cover_art_embed,
)

__all__ = [
    "format_lyrics_card",
    "format_artist_bio",
    "format_annotation",
    "format_soundcloud_track_details",
    "format_soundcloud_embed",
    "format_soundcloud_artist",
    "format_soundcloud_playlist",
    "create_discord_embed",
    "create_discord_genius_embed",
    # Juice WRLD formatters
    "format_song_card",
    "format_song_list",
    "format_artist_info",
    "create_discord_juice_wrld_embed",
    "create_discord_juice_wrld_search_embed",
    "create_discord_juice_wrld_song_list_embed",
    "create_discord_juice_wrld_lyric_search_embed",
    "create_discord_juice_wrld_stats_embed",
    "create_discord_juice_wrld_eras_embeds",
    "create_discord_juice_wrld_cover_art_embed",
]
