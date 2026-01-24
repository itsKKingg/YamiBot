"""
Music Response Formatter for YamiBot

This module provides formatting functions for music-related responses including
Genius lyrics/annotations, SoundCloud embeddable players, and Juice WRLD content.
"""

import discord
from typing import Dict, List, Optional
from datetime import datetime

from ..utils.logger import setup_logging

logger = setup_logging(__name__)


# ============ GENIUS FORMATTING FUNCTIONS ============

def format_lyrics_card(song: Dict, lyrics: Optional[str] = None, annotations: Optional[List[Dict]] = None) -> str:
    """
    Format song lyrics with annotations into plain text format

    Args:
        song: Song data dictionary from Genius API
        lyrics: Full lyrics text (plain text)
        annotations: Optional list of annotations for the song

    Returns:
        Formatted string with song info, lyrics, and annotations
    """
    if not song:
        return "❌ No song data available"

    lines = []

    # Song header
    lines.append("=" * 50)
    lines.append(f"🎵 {song.get('title', 'Unknown')}")
    lines.append(f"👤 {song.get('artist', 'Unknown')}")
    if song.get('album'):
        lines.append(f"💿 {song.get('album')}")
    
    # Metadata
    if song.get('release_date'):
        lines.append(f"📅 {song.get('release_date')}")
    
    # Producer credits
    if song.get('producers'):
        producers = song.get('producers', [])
        if producers:
            lines.append(f"🎹 Produced by: {', '.join(producers[:3])}")
    
    # Featured artists
    if song.get('features'):
        features = song.get('features', [])
        if features:
            lines.append(f"🎤 Featuring: {', '.join(features[:3])}")
    
    lines.append("=" * 50)
    lines.append("")  # Empty line separator

    # Full lyrics section
    if lyrics:
        lines.append("📜 **LYRICS:**")
        lines.append("")
        lines.append(lyrics)
        lines.append("")
        lines.append("=" * 50)
    else:
        lines.append("⚠️ Lyrics not available")
        lines.append("")
    
    # Annotations section
    if annotations:
        lines.append("")
        lines.append("📝 **ANNOTATIONS & EXPLANATIONS:**")
        lines.append("")
        for i, ann in enumerate(annotations[:5], 1):  # Show top 5
            lyric = ann.get('lyric', '').strip()
            annotation = ann.get('annotation', '').strip()
            author = ann.get('author', 'Unknown')

            if lyric and annotation:
                # Truncate long annotations
                if len(annotation) > 400:
                    annotation = annotation[:397] + "..."

                lines.append(f"{i}. \"{lyric}\"")
                lines.append(f"   💬 {author}:")
                lines.append(f"   {annotation}")
                lines.append("")
    
    # Genius link
    lines.append("")
    if song.get('url'):
        lines.append(f"🔗 View full lyrics and more on Genius: {song.get('url')}")
    lines.append("")
    lines.append("*Powered by Genius*")

    return "\n".join(lines)


def format_artist_bio(artist: Dict) -> str:
    """
    Format artist biography into a Discord-friendly card

    Args:
        artist: Artist data dictionary from Genius API

    Returns:
        Formatted string with artist info
    """
    if not artist:
        return "❌ No artist data available"

    lines = []

    # Artist header
    lines.append(f"🎤 **{artist.get('name', 'Unknown')}**")

    # Verified badge
    if artist.get('is_verified'):
        lines.append("✅ Verified Artist")

    # Stats
    lines.append(f"📊 Songs: {artist.get('songs_count', 0):,}")
    if artist.get('followers'):
        lines.append(f"👥 Followers: {artist.get('followers', 0):,}")

    # Alternate names
    if artist.get('alternate_names'):
        alt_names = artist.get('alternate_names', [])[:3]
        lines.append(f"🏷️ Also known as: {', '.join(alt_names)}")

    lines.append("")  # Empty line separator

    # Bio/description
    bio = artist.get('bio', '').strip()
    if bio:
        # Truncate long bios
        if len(bio) > 1000:
            bio = bio[:997] + "..."
        lines.append(f"📖 **Biography:**")
        lines.append(bio)

    # Genius link
    if artist.get('url'):
        lines.append(f"\n🔗 [View on Genius]({artist.get('url')})")

    return "\n".join(lines)


def format_annotation(lyric: str, annotation: str, author: str) -> str:
    """
    Format a single lyric annotation

    Args:
        lyric: The lyric line
        annotation: The explanation
        author: Annotation author

    Returns:
        Formatted string
    """
    lines = []

    if lyric:
        lines.append(f"**{lyric}**")

    if annotation:
        # Truncate if too long
        if len(annotation) > 500:
            annotation = annotation[:497] + "..."
        lines.append(f"💬 *{author or 'Unknown'}*:")
        lines.append(annotation)

    return "\n".join(lines) if lines else "No annotation data available"


def create_discord_genius_embed(
    song: Optional[Dict] = None,
    artist: Optional[Dict] = None,
    annotations: Optional[List[Dict]] = None
) -> discord.Embed:
    """
    Create a Discord Embed object for Genius content

    Args:
        song: Optional song data
        artist: Optional artist data
        annotations: Optional annotations list

    Returns:
        Discord Embed object
    """
    if song:
        # Song embed
        embed = discord.Embed(
            title=song.get('title', 'Unknown Song'),
            url=song.get('url'),
            color=0xffff64,  # Genius yellow
            timestamp=datetime.utcnow()
        )

        embed.set_author(
            name=song.get('artist', 'Unknown Artist'),
            icon_url="https://genius.com/favicon.ico"
        )

        # Description with metadata
        description_lines = []

        if song.get('album'):
            description_lines.append(f"**Album:** {song.get('album')}")

        if song.get('release_date'):
            description_lines.append(f"**Released:** {song.get('release_date')}")

        if song.get('producers'):
            producers = song.get('producers', [])[:3]
            description_lines.append(f"**Produced by:** {', '.join(producers)}")

        if song.get('features'):
            features = song.get('features', [])[:3]
            description_lines.append(f"**Featuring:** {', '.join(features)}")

        if description_lines:
            embed.description = "\n".join(description_lines)

        # Thumbnail
        if song.get('image_url'):
            embed.set_thumbnail(url=song.get('image_url'))

        # Annotations as fields
        if annotations:
            for i, ann in enumerate(annotations[:3], 1):  # Max 3 fields
                lyric = ann.get('lyric', '').strip()
                annotation = ann.get('annotation', '').strip()

                if lyric:
                    # Truncate for Discord field limits (1024 chars)
                    field_value = annotation[:900] + "..." if len(annotation) > 900 else annotation

                    embed.add_field(
                        name=f"💬 {lyric[:100]}",
                        value=field_value,
                        inline=False
                    )

        embed.set_footer(text="Powered by Genius")
        return embed

    elif artist:
        # Artist embed
        embed = discord.Embed(
            title=f"{artist.get('name', 'Unknown Artist')}",
            url=artist.get('url'),
            color=0xffff64,
            timestamp=datetime.utcnow()
        )

        # Stats
        stats_lines = []

        if artist.get('songs_count'):
            stats_lines.append(f"🎵 {artist.get('songs_count', 0):,} songs")

        if artist.get('followers'):
            stats_lines.append(f"👥 {artist.get('followers', 0):,} followers")

        if artist.get('is_verified'):
            stats_lines.append("✅ Verified")

        if stats_lines:
            embed.add_field(name="Stats", value="\n".join(stats_lines), inline=True)

        # Bio
        bio = artist.get('bio', '').strip()
        if bio:
            bio = bio[:2000] + "..." if len(bio) > 2000 else bio
            embed.add_field(name="Biography", value=bio, inline=False)

        # Thumbnail
        if artist.get('image_url'):
            embed.set_thumbnail(url=artist.get('image_url'))

        embed.set_footer(text="Powered by Genius")
        return embed

    else:
        # Generic embed
        return discord.Embed(
            title="Genius",
            description="Music lyrics and annotations",
            color=0xffff64
        )


# ============ SOUNDCLOUD FORMATTING FUNCTIONS ============

def format_soundcloud_track_details(track: Dict) -> str:
    """
    Format SoundCloud track with detailed information (plain text)
    
    Args:
        track: Track data dictionary from SoundCloud API
        
    Returns:
        Formatted string with detailed track info
    """
    if not track:
        return "❌ No track data available"
    
    lines = []
    
    # Track header
    lines.append("=" * 50)
    lines.append(f"🎧 {track.get('title', 'Unknown Track')}")
    lines.append(f"👤 {track.get('artist', 'Unknown Artist')}")
    lines.append("=" * 50)
    lines.append("")
    
    # Duration
    duration_ms = track.get('duration', 0)
    if duration_ms:
        duration_sec = duration_ms // 1000
        minutes, seconds = divmod(duration_sec, 60)
        lines.append(f"⏱️ Duration: {minutes}:{seconds:02d}")
    
    # Stats
    play_count = track.get('playback_count', 0)
    if play_count:
        lines.append(f"🎮 Play Count: {play_count:,}")
    
    likes_count = track.get('likes_count', 0)
    if likes_count:
        lines.append(f"❤️ Likes: {likes_count:,}")
    
    # Genre
    genre = track.get('genre', '')
    if genre:
        lines.append(f"🎸 Genre: {genre}")
    
    lines.append("")
    
    # Description
    description = track.get('description', '').strip()
    if description:
        lines.append("📝 **Description:**")
        lines.append(description[:500] + "..." if len(description) > 500 else description)
        lines.append("")
    
    # Artist profile link
    permalink = track.get('permalink_url', '')
    if permalink:
        lines.append(f"🔗 Listen on SoundCloud: {permalink}")
    
    lines.append("")
    lines.append("*Track found on SoundCloud platform*")
    
    return "\n".join(lines)

def format_soundcloud_embed(track: Dict) -> str:
    """
    Format SoundCloud track with embeddable player

    Args:
        track: Track data dictionary from SoundCloud API

    Returns:
        Formatted string with embed code
    """
    if not track:
        return "❌ No track data available"

    lines = []

    # Track header
    lines.append(f"🎧 **{track.get('title', 'Unknown Track')}**")
    lines.append(f"👤 Artist: {track.get('artist', 'Unknown')}")

    # Duration
    duration_ms = track.get('duration', 0)
    if duration_ms:
        duration_sec = duration_ms // 1000
        minutes, seconds = divmod(duration_sec, 60)
        lines.append(f"⏱️ Duration: {minutes}:{seconds:02d}")

    # Stats
    play_count = track.get('playback_count', 0)
    if play_count:
        lines.append(f"🎮 Plays: {play_count:,}")

    likes_count = track.get('likes_count', 0)
    if likes_count:
        lines.append(f"❤️ Likes: {likes_count:,}")

    # Genre
    genre = track.get('genre', '')
    if genre:
        lines.append(f"🎸 Genre: {genre}")

    # Embed player link
    embed_url = track.get('embed_url', track.get('permalink_url', ''))
    if embed_url:
        lines.append(f"\n🔗 [Listen on SoundCloud]({embed_url})")
        lines.append(f"📱 [Open Player]({embed_url})")

    # Description
    description = track.get('description', '').strip()
    if description:
        description = description[:300] + "..." if len(description) > 300 else description
        lines.append(f"\n📝 {description}")

    return "\n".join(lines)


def format_soundcloud_artist(artist: Dict) -> str:
    """
    Format SoundCloud artist profile

    Args:
        artist: Artist data dictionary from SoundCloud API

    Returns:
        Formatted string with artist info
    """
    if not artist:
        return "❌ No artist data available"

    lines = []

    # Artist header
    lines.append(f"🎤 **{artist.get('name', artist.get('full_name', 'Unknown Artist'))}**")

    # Verified badge
    if artist.get('is_verified'):
        lines.append("✅ Verified Artist")

    # Stats
    lines.append(f"📊 Tracks: {artist.get('track_count', 0):,}")
    lines.append(f"👥 Followers: {artist.get('followers_count', 0):,}")
    lines.append(f"➕ Following: {artist.get('following_count', 0):,}")

    # Location
    city = artist.get('city', '')
    country = artist.get('country', '')
    if city or country:
        location_parts = [city, country]
        lines.append(f"📍 {', '.join(filter(None, location_parts))}")

    # SoundCloud link
    if artist.get('permalink_url'):
        lines.append(f"\n🔗 [View on SoundCloud]({artist.get('permalink_url')})")

    # Bio/description
    description = artist.get('description', '').strip()
    if description:
        description = description[:500] + "..." if len(description) > 500 else description
        lines.append(f"\n📖 {description}")

    # Website
    website = artist.get('website', '')
    if website:
        lines.append(f"\n🌐 [Website]({website})")

    return "\n".join(lines)


def format_soundcloud_playlist(playlist: Dict, max_tracks: int = 5) -> str:
    """
    Format SoundCloud playlist with track list

    Args:
        playlist: Playlist data dictionary from SoundCloud API
        max_tracks: Maximum number of tracks to show

    Returns:
        Formatted string with playlist info
    """
    if not playlist:
        return "❌ No playlist data available"

    lines = []

    # Playlist header
    lines.append(f"📋 **{playlist.get('title', 'Unknown Playlist')}**")
    lines.append(f"👤 Creator: {playlist.get('creator', 'Unknown')}")

    # Stats
    track_count = playlist.get('track_count', 0)
    lines.append(f"🎵 Tracks: {track_count:,}")

    duration_ms = playlist.get('duration', 0)
    if duration_ms:
        duration_sec = duration_ms // 1000
        hours, remainder = divmod(duration_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            lines.append(f"⏱️ Duration: {hours}h {minutes}m")
        else:
            lines.append(f"⏱️ Duration: {minutes}m")

    # Likes
    likes_count = playlist.get('likes_count', 0)
    if likes_count:
        lines.append(f"❤️ Likes: {likes_count:,}")

    # Embed player link
    embed_url = playlist.get('embed_url', playlist.get('permalink_url', ''))
    if embed_url:
        lines.append(f"\n🔗 [Listen on SoundCloud]({embed_url})")

    lines.append("")  # Empty line separator

    # Track list
    tracks = playlist.get('tracks', [])[:max_tracks]
    if tracks:
        lines.append(f"📝 **Top {len(tracks)} Tracks:**")
        for i, track in enumerate(tracks, 1):
            title = track.get('title', 'Unknown Track')
            artist = track.get('artist', 'Unknown Artist')

            # Duration
            duration_ms = track.get('duration', 0)
            if duration_ms:
                duration_sec = duration_ms // 1000
                minutes, seconds = divmod(duration_sec, 60)
                duration_str = f" ({minutes}:{seconds:02d})"
            else:
                duration_str = ""

            lines.append(f"{i}. **{title}** - {artist}{duration_str}")

        if track_count > len(tracks):
            lines.append(f"\n... and {track_count - len(tracks)} more tracks")
    else:
        lines.append("📝 No tracks available")

    # Description
    description = playlist.get('description', '').strip()
    if description:
        description = description[:300] + "..." if len(description) > 300 else description
        lines.append(f"\n📖 {description}")

    return "\n".join(lines)


def create_discord_embed(track: Dict) -> discord.Embed:
    """
    Create a Discord Embed object for SoundCloud track

    Args:
        track: Track data dictionary from SoundCloud API

    Returns:
        Discord Embed object with SoundCloud branding
    """
    if not track:
        return discord.Embed(
            title="SoundCloud",
            description="No track data available",
            color=0xff5500  # SoundCloud orange
        )

    embed = discord.Embed(
        title=track.get('title', 'Unknown Track'),
        url=track.get('permalink_url'),
        color=0xff5500,  # SoundCloud orange
        timestamp=datetime.utcnow()
    )

    # Author
    embed.set_author(
        name=track.get('artist', 'Unknown Artist'),
        icon_url="https://a-v2.sndcdn.com/assets/images/sc-icons/favicon-2cadd14a.ico"
    )

    # Description with metadata
    description_lines = []

    # Duration
    duration_ms = track.get('duration', 0)
    if duration_ms:
        duration_sec = duration_ms // 1000
        minutes, seconds = divmod(duration_sec, 60)
        description_lines.append(f"⏱️ Duration: {minutes}:{seconds:02d}")

    # Genre
    genre = track.get('genre', '')
    if genre:
        description_lines.append(f"🎸 Genre: {genre}")

    # Stats
    play_count = track.get('playback_count', 0)
    likes_count = track.get('likes_count', 0)

    if play_count or likes_count:
        stats_parts = []
        if play_count:
            stats_parts.append(f"🎮 {play_count:,} plays")
        if likes_count:
            stats_parts.append(f"❤️ {likes_count:,} likes")
        description_lines.append(" | ".join(stats_parts))

    # Release date
    release_date = track.get('release_date')
    if release_date:
        description_lines.append(f"📅 Released: {release_date}")

    if description_lines:
        embed.description = "\n".join(description_lines)

    # Thumbnail (artwork)
    artwork_url = track.get('artwork_url')
    if artwork_url:
        embed.set_thumbnail(url=artwork_url)

    # Fields
    # Description as a field if present
    description_text = track.get('description', '').strip()
    if description_text:
        # Truncate for Discord field limits
        if len(description_text) > 1000:
            description_text = description_text[:997] + "..."
        embed.add_field(name="Description", value=description_text, inline=False)

    embed.set_footer(text="Powered by SoundCloud")
    return embed


# ============ JUICE WRLD FORMATTING FUNCTIONS ============

def format_song_card(song: Dict) -> str:
    """
    Format a single Juice WRLD song with metadata

    Args:
        song: Song data dictionary from Juice WRLD API

    Returns:
        Formatted Discord-friendly string with song info
    """
    if not song:
        return "❌ No song data available"

    lines = []

    # Song header
    lines.append(f"🎵 **{song.get('title', 'Unknown')}**")
    lines.append(f"👤 Artist: {song.get('artist', 'Juice WRLD')}")

    # Album
    if song.get('album'):
        lines.append(f"💿 Album: {song.get('album')}")

    # Metadata
    if song.get('release_date'):
        lines.append(f"📅 Released: {song.get('release_date')}")

    # Producer credits
    if song.get('producers'):
        producers = song.get('producers', [])
        if producers:
            lines.append(f"🎹 Produced by: {', '.join(producers[:3])}")

    # Featured artists
    if song.get('features'):
        features = song.get('features', [])
        if features:
            lines.append(f"🎤 Featuring: {', '.join(features[:3])}")

    # Stats
    play_count = song.get('play_count', 0)
    if play_count:
        lines.append(f"🎮 Plays: {play_count:,}")

    # Links
    if song.get('genius_url'):
        lines.append(f"🔗 [View on Genius]({song.get('genius_url')})")

    if song.get('juice_wrld_url'):
        lines.append(f"🔗 [View on Juice WRLD API]({song.get('juice_wrld_url')})")

    # Description
    description = song.get('description', '').strip()
    if description:
        # Truncate long descriptions
        if len(description) > 500:
            description = description[:497] + "..."
        lines.append(f"\n📝 {description}")

    return "\n".join(lines)


def format_song_list(songs: List[Dict], max_songs: int = 5) -> str:
    """
    Format multiple Juice WRLD songs as a searchable list

    Args:
        songs: List of song data dictionaries from Juice WRLD API
        max_songs: Maximum number of songs to display

    Returns:
        Formatted string with song list
    """
    if not songs:
        return "❌ No songs available"

    lines = []

    # Header with total count
    total_count = len(songs)
    display_count = min(total_count, max_songs)
    lines.append(f"🎵 **Found {total_count} songs**")
    lines.append(f"Showing first {display_count} results\n")

    # Song list
    for i, song in enumerate(songs[:max_songs], 1):
        title = song.get('title', 'Unknown Song')
        album = song.get('album', 'Unknown Album')
        release_date = song.get('release_date', '')

        # Format release year
        year = ''
        if release_date:
            try:
                year = f" ({release_date[:4]})"
            except (IndexError, TypeError):
                pass

        # Play count if available
        play_count = song.get('play_count', 0)
        plays_str = f" | {play_count:,} plays" if play_count else ""

        lines.append(f"{i}. **{title}**{year}")
        lines.append(f"   💿 {album}{plays_str}")

    # Truncation notice
    if total_count > max_songs:
        lines.append(f"\n... and {total_count - max_songs} more songs")

    return "\n".join(lines)


def format_artist_info(artist: Dict) -> str:
    """
    Format Juice WRLD artist profile information

    Args:
        artist: Artist data dictionary from Juice WRLD API

    Returns:
        Formatted string with artist info
    """
    if not artist:
        return "❌ No artist data available"

    lines = []

    # Artist header
    lines.append(f"🎤 **{artist.get('name', 'Unknown')}**")

    # Verified badge
    if artist.get('is_verified'):
        lines.append("✅ Verified Artist")

    # Stats
    lines.append(f"📊 Songs: {artist.get('songs_count', 0):,}")

    followers = artist.get('followers', 0)
    if followers:
        lines.append(f"👥 Followers: {followers:,}")

    # Alternate names
    if artist.get('alternate_names'):
        alt_names = artist.get('alternate_names', [])[:3]
        lines.append(f"🏷️ Also known as: {', '.join(alt_names)}")

    lines.append("")  # Empty line separator

    # Bio/description
    bio = artist.get('bio', '').strip()
    if bio:
        # Truncate long bios
        if len(bio) > 1000:
            bio = bio[:997] + "..."
        lines.append(f"📖 **Biography:**")
        lines.append(bio)

    # Genres
    genres = artist.get('genres', [])
    if genres:
        lines.append(f"\n🎸 Genres: {', '.join(genres[:5])}")

    # Links
    if artist.get('genius_url'):
        lines.append(f"\n🔗 [View on Genius]({artist.get('genius_url')})")

    if artist.get('juice_wrld_url'):
        lines.append(f"🔗 [View on Juice WRLD API]({artist.get('juice_wrld_url')})")

    return "\n".join(lines)


def _format_duration(duration_value) -> str:
    if not duration_value:
        return "Unknown"

    # Already formatted
    if isinstance(duration_value, str):
        d = duration_value.strip()
        if ":" in d:
            return d
        # maybe seconds as string
        if d.isdigit():
            duration_value = int(d)
        else:
            return d

    # seconds
    if isinstance(duration_value, (int, float)):
        total_seconds = int(duration_value)
        minutes, seconds = divmod(total_seconds, 60)
        if minutes >= 60:
            hours, minutes = divmod(minutes, 60)
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    return "Unknown"


def create_discord_juice_wrld_embed(
    song: Optional[Dict] = None,
    artist: Optional[Dict] = None
) -> discord.Embed:
    """Create a Discord Embed object for Juice WRLD content.

    For songs, this follows the required metadata fields:
    👤 Artist, 🎵 Album, 📅 Release Date, 🏭 Producer(s), 🎭 Era,
    📍 Studio Location, ⏱️ Duration, 📊 Status.
    """
    if song:
        stream_url = song.get("stream_url") or song.get("download_url")
        embed_url = stream_url or song.get("juice_wrld_url") or song.get("genius_url")

        embed = discord.Embed(
            title=song.get("title", "Unknown Song"),
            url=embed_url,
            color=0x6B21A8,
            timestamp=datetime.utcnow(),
        )

        embed.set_author(
            name=song.get("artist", "Juice WRLD"),
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Juice_WRLD_in_2019.jpg/440px-Juice_WRLD_in_2019.jpg",
        )

        # Thumbnail
        thumb = (
            song.get("cover_art_url")
            or song.get("image_url")
            or song.get("artwork_url")
            or song.get("artwork")
        )
        if thumb:
            embed.set_thumbnail(url=thumb)

        # Description
        desc = (song.get("description") or "").strip()
        if desc:
            embed.description = desc[:500] + "..." if len(desc) > 500 else desc
        else:
            status = (song.get("status") or "Unknown").replace("_", " ")
            era = song.get("era") or "Unknown era"
            embed.description = f"🎭 **{era}** • 📊 **{status}**"

        # Required fields
        embed.add_field(name="👤 Artist", value=song.get("artist") or "Juice WRLD", inline=True)
        embed.add_field(name="🎵 Album", value=song.get("album") or "Unknown", inline=True)
        embed.add_field(name="📅 Release Date", value=song.get("release_date") or "Unknown", inline=True)

        producers = song.get("producers") or []
        producers_value = ", ".join(producers) if producers else "Unknown"
        embed.add_field(name="🏭 Producer(s)", value=producers_value[:1024], inline=False)

        embed.add_field(name="🎭 Era", value=song.get("era") or "Unknown", inline=True)

        studio_loc = song.get("studio_location") or "Unknown"
        rec_date = song.get("recording_date")
        if rec_date:
            studio_loc = f"{studio_loc}\n🗓️ {rec_date}"
        embed.add_field(name="📍 Studio Location", value=studio_loc[:1024], inline=True)

        embed.add_field(name="⏱️ Duration", value=_format_duration(song.get("duration")), inline=True)

        status_val = (song.get("status") or "Unknown").replace("_", " ")
        embed.add_field(name="📊 Status", value=status_val.title() if status_val else "Unknown", inline=True)

        # Streaming link
        if stream_url:
            embed.add_field(name="🔗 Streaming", value=f"[Listen here]({stream_url})", inline=False)

        # Helpful IDs
        if song.get("id") is not None:
            embed.set_footer(text=f"Powered by Juice WRLD API • Song ID: {song.get('id')}")
        else:
            embed.set_footer(text="Powered by Juice WRLD API")

        return embed

    if artist:
        embed = discord.Embed(
            title=f"{artist.get('name', 'Juice WRLD')}",
            url=artist.get("juice_wrld_url") or artist.get("genius_url"),
            color=0x6B21A8,
            timestamp=datetime.utcnow(),
        )

        stats_lines = []
        if artist.get("songs_count"):
            stats_lines.append(f"🎵 {artist.get('songs_count', 0):,} songs")
        if artist.get("followers"):
            stats_lines.append(f"👥 {artist.get('followers', 0):,} followers")
        if artist.get("is_verified"):
            stats_lines.append("✅ Verified")
        if stats_lines:
            embed.add_field(name="Stats", value="\n".join(stats_lines), inline=True)

        genres = artist.get("genres", [])
        if genres:
            embed.add_field(name="Genres", value=", ".join(genres[:5]), inline=True)

        bio = (artist.get("bio") or "").strip()
        if bio:
            embed.add_field(
                name="Biography",
                value=bio[:2000] + "..." if len(bio) > 2000 else bio,
                inline=False,
            )

        thumb = artist.get("image_url") or artist.get("avatar_url")
        if thumb:
            embed.set_thumbnail(url=thumb)

        embed.set_footer(text="Powered by Juice WRLD API")
        return embed

    return discord.Embed(
        title="Juice WRLD",
        description="Music and artist information",
        color=0x6B21A8,
    )


def create_discord_juice_wrld_search_embed(query: str, songs: List[Dict], max_results: int = 10) -> discord.Embed:
    embed = discord.Embed(
        title="🔎 Juice WRLD Search Results",
        description=f"Results for **{query}**",
        color=0x6B21A8,
        timestamp=datetime.utcnow(),
    )

    embed.set_author(
        name="Juice WRLD",
        icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Juice_WRLD_in_2019.jpg/440px-Juice_WRLD_in_2019.jpg",
    )

    if not songs:
        embed.description = f"❌ No songs found for **{query}**"
        embed.set_footer(text="Powered by Juice WRLD API")
        return embed

    thumb = songs[0].get("cover_art_url") or songs[0].get("image_url") or songs[0].get("artwork_url")
    if thumb:
        embed.set_thumbnail(url=thumb)

    lines = []
    for i, s in enumerate(songs[:max_results], 1):
        title = s.get("title") or "Unknown"
        status = (s.get("status") or "").replace("_", " ").title()
        era = s.get("era") or ""
        song_id = s.get("id")
        bits = [f"**{i}. {title}**"]
        meta = " • ".join([b for b in [era, status] if b])
        if meta:
            bits.append(f"_{meta}_")
        if song_id is not None:
            bits.append(f"`ID: {song_id}`")
        lines.append(" ".join(bits))

    embed.add_field(name=f"Songs ({min(len(songs), max_results)}/{len(songs)})", value="\n".join(lines)[:1024], inline=False)
    embed.set_footer(text="Powered by Juice WRLD API")
    return embed


def create_discord_juice_wrld_song_list_embed(
    title: str,
    songs: List[Dict],
    *,
    subtitle: Optional[str] = None,
    max_results: int = 15,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=subtitle or "",
        color=0x6B21A8,
        timestamp=datetime.utcnow(),
    )

    if not songs:
        embed.description = (subtitle + "\n\n" if subtitle else "") + "❌ No songs found."
        embed.set_footer(text="Powered by Juice WRLD API")
        return embed

    thumb = songs[0].get("cover_art_url") or songs[0].get("image_url") or songs[0].get("artwork_url")
    if thumb:
        embed.set_thumbnail(url=thumb)

    lines = []
    for i, s in enumerate(songs[:max_results], 1):
        title_txt = s.get("title") or "Unknown"
        status = (s.get("status") or "").replace("_", " ").title()
        date = s.get("release_date") or s.get("recording_date") or ""
        era = s.get("era") or ""
        song_id = s.get("id")

        meta_bits = [b for b in [date, era, status] if b]
        meta = " • ".join(meta_bits)
        line = f"**{i}. {title_txt}**"
        if meta:
            line += f"\n_{meta}_"
        if song_id is not None:
            line += f"\n`ID: {song_id}`"
        lines.append(line)

    embed.add_field(
        name=f"Songs ({min(len(songs), max_results)}/{len(songs)})",
        value="\n\n".join(lines)[:1024],
        inline=False,
    )
    embed.set_footer(text="Powered by Juice WRLD API")
    return embed


def create_discord_juice_wrld_lyric_search_embed(phrase: str, songs: List[Dict], max_results: int = 10) -> discord.Embed:
    embed = discord.Embed(
        title="🔎 Lyric Search (Juice WRLD)",
        description=f"Songs containing **{phrase}**",
        color=0x6B21A8,
        timestamp=datetime.utcnow(),
    )

    if not songs:
        embed.description = f"❌ No songs found containing **{phrase}**"
        embed.set_footer(text="Powered by Juice WRLD API")
        return embed

    lines = []
    for i, s in enumerate(songs[:max_results], 1):
        title_txt = s.get("title") or "Unknown"
        song_id = s.get("id")
        snippet = ""
        matched = s.get("matched_lyrics")
        if isinstance(matched, str) and matched.strip():
            snippet = matched.strip()
        elif isinstance(matched, list) and matched:
            snippet = str(matched[0]).strip()

        if snippet:
            # highlight phrase when possible
            snippet_low = snippet.lower()
            p_low = phrase.lower()
            if p_low in snippet_low:
                idx = snippet_low.find(p_low)
                snippet = snippet[:idx] + "**" + snippet[idx:idx+len(phrase)] + "**" + snippet[idx+len(phrase):]
            snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet

        line = f"**{i}. {title_txt}**"
        if song_id is not None:
            line += f" `ID: {song_id}`"
        if snippet:
            line += f"\n> {snippet}"
        lines.append(line)

    embed.add_field(name=f"Matches ({min(len(songs), max_results)}/{len(songs)})", value="\n\n".join(lines)[:1024], inline=False)
    embed.set_footer(text="Powered by Juice WRLD API")
    return embed


def create_discord_juice_wrld_stats_embed(stats: Dict) -> discord.Embed:
    embed = discord.Embed(
        title="📊 Juice WRLD Database Stats",
        color=0x6B21A8,
        timestamp=datetime.utcnow(),
    )

    if not stats:
        embed.description = "❌ Stats unavailable."
        embed.set_footer(text="Powered by Juice WRLD API")
        return embed

    # tolerate a few likely shapes
    total_released = stats.get("released") or stats.get("total_released")
    total_unreleased = stats.get("unreleased") or stats.get("total_unreleased")
    total_unsurfaced = stats.get("unsurfaced") or stats.get("total_unsurfaced")
    total_sessions = stats.get("studio_session") or stats.get("studio_sessions") or stats.get("total_studio_sessions")
    total_all = stats.get("total") or stats.get("total_songs") or stats.get("overall")

    fields = [
        ("✅ Released", total_released),
        ("🟣 Unreleased", total_unreleased),
        ("🕳️ Unsurfaced", total_unsurfaced),
        ("🎛️ Studio Sessions", total_sessions),
        ("📦 Total", total_all),
    ]

    for name, value in fields:
        if value is not None and value != "":
            embed.add_field(name=name, value=str(value), inline=True)

    # show raw keys summary if nothing mapped
    if not embed.fields:
        embed.description = "\n".join([f"**{k}**: {v}" for k, v in list(stats.items())[:12]])

    embed.set_footer(text="Powered by Juice WRLD API")
    return embed


def create_discord_juice_wrld_eras_embeds(eras: List[Dict], page_size: int = 15) -> List[discord.Embed]:
    if not eras:
        embed = discord.Embed(
            title="🎭 Juice WRLD Eras",
            description="❌ No era data available.",
            color=0x6B21A8,
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text="Powered by Juice WRLD API")
        return [embed]

    pages: List[discord.Embed] = []
    for start in range(0, len(eras), page_size):
        chunk = eras[start:start + page_size]
        page_num = (start // page_size) + 1
        total_pages = (len(eras) + page_size - 1) // page_size

        embed = discord.Embed(
            title=f"🎭 Juice WRLD Eras (Page {page_num}/{total_pages})",
            description="34-era timeline (sorted by API order)",
            color=0x6B21A8,
            timestamp=datetime.utcnow(),
        )

        lines = []
        for era in chunk:
            name = era.get("name") or "Unknown"
            era_id = era.get("id")
            start_date = era.get("start_date") or "?"
            end_date = era.get("end_date") or "?"
            count = era.get("song_count")
            count_str = f" • {count} songs" if count is not None else ""
            id_str = f" (ID: {era_id})" if era_id is not None else ""
            lines.append(f"**{name}**{id_str}\n_{start_date} → {end_date}{count_str}_")

        embed.add_field(name="Eras", value="\n\n".join(lines)[:1024], inline=False)
        embed.set_footer(text="Powered by Juice WRLD API")
        pages.append(embed)

    return pages


def create_discord_juice_wrld_cover_art_embed(song: Dict) -> discord.Embed:
    title = song.get("title") or "Cover Art"
    embed = discord.Embed(
        title=f"🖼️ Cover Art — {title}",
        url=song.get("cover_art_url") or song.get("juice_wrld_url"),
        color=0x6B21A8,
        timestamp=datetime.utcnow(),
    )

    art_url = song.get("cover_art_url")
    if art_url:
        embed.set_thumbnail(url=art_url)
        embed.add_field(name="Download", value=f"[Open image]({art_url})", inline=False)
    else:
        embed.description = "❌ No cover art available for this song."

    embed.set_footer(text="Powered by Juice WRLD API")
    return embed
