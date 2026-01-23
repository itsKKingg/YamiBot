"""
SoundCloud API Wrapper for YamiBot

This module provides a wrapper for the SoundCloud API to access
track information, artist details, playlists, and embeddable players.

SoundCloud API Documentation: https://developers.soundcloud.com/
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode

from ..utils.logger import setup_logging

logger = setup_logging(__name__)


class SoundCloudAPI:
    """
    Wrapper for the SoundCloud API with OAuth2 authentication and oEmbed support.
    """

    # API endpoint constants
    BASE_URL = "https://api.soundcloud.com"
    OAUTH_TOKEN_URL = "https://api.soundcloud.com/oauth2/token"
    OAUTH_AUTHORIZE_URL = "https://api.soundcloud.com/oauth2/authorize"
    OEMBED_URL = "https://soundcloud.com/oembed"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: Optional[aiohttp.ClientSession] = None
    ):
        """
        Initialize SoundCloud API wrapper

        Args:
            client_id: SoundCloud client ID from https://soundcloud.com/you/apps
            client_secret: SoundCloud client secret
            session: Optional aiohttp ClientSession (will create if not provided)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self._session = session
        self._created_session = session is None

        if self._created_session:
            self._session = aiohttp.ClientSession()

        # Authentication state
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[float] = None

        # Request timeout (seconds)
        self.timeout = 10

        logger.info("SoundCloud API wrapper initialized")

    async def authenticate(self) -> str:
        """
        Authenticate with SoundCloud OAuth2 and get access token

        Returns:
            Access token string

        Raises:
            Exception: If authentication fails
        """
        # Check if token is still valid (hasn't expired)
        if self._access_token and self._token_expiry:
            current_time = asyncio.get_event_loop().time()
            if current_time < self._token_expiry:
                logger.debug("Using cached access token")
                return self._access_token

        logger.info("Authenticating with SoundCloud...")

        # Prepare OAuth2 credentials request
        params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            async with asyncio.timeout(self.timeout):
                async with self._session.post(
                    self.OAUTH_TOKEN_URL,
                    data=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Authentication failed: {response.status} - {error_text}")
                        raise Exception(f"SoundCloud authentication failed: {response.status}")

                    data = await response.json()
                    self._access_token = data.get("access_token")

                    if not self._access_token:
                        raise Exception("No access token received")

                    # Set expiry (subtract buffer time)
                    expires_in = data.get("expires_in", 3600)
                    self._token_expiry = asyncio.get_event_loop().time() + expires_in - 300

                    logger.info("Successfully authenticated with SoundCloud")
                    return self._access_token

        except asyncio.TimeoutError:
            logger.error("Authentication timeout")
            raise Exception("SoundCloud authentication timeout")

        except aiohttp.ClientError as e:
            logger.error(f"Authentication network error: {e}")
            raise Exception(f"SoundCloud authentication error: {e}")

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make authenticated request to SoundCloud API

        Args:
            endpoint: API endpoint path (e.g., "/tracks")
            params: Query parameters
            method: HTTP method (default: GET)
            data: Request body data (for POST, etc.)

        Returns:
            Response data dict or None on error
        """
        # Ensure we have an access token
        if not self._access_token:
            await self.authenticate()

        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }

        try:
            async with asyncio.timeout(self.timeout):
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=data
                ) as response:
                    # Handle rate limiting (429)
                    if response.status == 429:
                        logger.warning("Rate limited by SoundCloud API")
                        return None

                    # Handle auth errors
                    if response.status == 401:
                        logger.warning("Access token expired, re-authenticating...")
                        self._access_token = None
                        await self.authenticate()
                        # Retry once with new token
                        return await self._make_request(endpoint, params, method, data)

                    # Handle other errors
                    if response.status == 404:
                        logger.debug(f"Resource not found: {url}")
                        return None

                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        return None

                    # Parse JSON response
                    return await response.json()

        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {url}")
            return None

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    async def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for tracks on SoundCloud

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of track results with keys:
            - id: Track ID
            - title: Track title
            - artist: Artist name
            - duration: Duration in milliseconds
            - artwork_url: Album artwork URL
            - stream_url: Streaming URL
            - embed_url: URL for embed player
        """
        logger.info(f"Searching SoundCloud tracks for: {query}")

        result = await self._make_request(
            "/tracks",
            params={"q": query, "limit": limit}
        )

        if not result:
            logger.warning(f"No tracks found for: {query}")
            return []

        # If result is a list, use it; if it's a dict with collection, extract that
        tracks = result if isinstance(result, list) else result.get("collection", [])

        # Format track data
        formatted_tracks = []
        for track in tracks[:limit]:
            formatted_track = {
                "id": track.get("id"),
                "title": track.get("title", ""),
                "artist": track.get("user", {}).get("username", ""),
                "artist_id": track.get("user", {}).get("id"),
                "duration": track.get("duration", 0),  # milliseconds
                "artwork_url": track.get("artwork_url", ""),
                "stream_url": track.get("stream_url", ""),
                "permalink_url": track.get("permalink_url", ""),
                "embed_url": track.get("permalink_url", ""),
                "genre": track.get("genre", ""),
                "playback_count": track.get("playback_count", 0),
                "likes_count": track.get("likes_count", 0),
                "description": track.get("description", ""),
                "release_date": track.get("release_date"),
                "is_downloadable": track.get("downloadable", False)
            }
            formatted_tracks.append(formatted_track)

        logger.info(f"Found {len(formatted_tracks)} tracks")
        return formatted_tracks

    async def get_track(self, track_id: str) -> Dict:
        """
        Get detailed track information

        Args:
            track_id: SoundCloud track ID

        Returns:
            Dictionary with full track metadata
        """
        logger.info(f"Getting track details for ID: {track_id}")

        result = await self._make_request(f"/tracks/{track_id}")

        if not result:
            logger.warning(f"Track not found: {track_id}")
            return {}

        track = result

        track_data = {
            "id": track.get("id"),
            "title": track.get("title", ""),
            "artist": track.get("user", {}).get("username", ""),
            "artist_id": track.get("user", {}).get("id"),
            "duration": track.get("duration", 0),
            "artwork_url": track.get("artwork_url", ""),
            "stream_url": track.get("stream_url", ""),
            "permalink_url": track.get("permalink_url", ""),
            "embed_url": track.get("permalink_url", ""),
            "genre": track.get("genre", ""),
            "playback_count": track.get("playback_count", 0),
            "likes_count": track.get("likes_count", 0),
            "comment_count": track.get("comment_count", 0),
            "reposts_count": track.get("reposts_count", 0),
            "description": track.get("description", ""),
            "release_date": track.get("release_date"),
            "created_at": track.get("created_at"),
            "is_downloadable": track.get("downloadable", False),
            "download_url": track.get("download_url", ""),
            "license": track.get("license", ""),
            "tag_list": track.get("tag_list", ""),
            "bpm": track.get("bpm"),
            "key_signature": track.get("key_signature")
        }

        logger.info(f"Retrieved track: {track_data['title']} by {track_data['artist']}")
        return track_data

    async def get_track_embed_code(self, track_id: str) -> str:
        """
        Get oEmbed code for a track (Discord-compatible embed)

        Args:
            track_id: SoundCloud track ID

        Returns:
            oEmbed HTML code string
        """
        logger.info(f"Getting embed code for track ID: {track_id}")

        # First get track details to get permalink URL
        track = await self.get_track(track_id)
        if not track:
            return ""

        permalink_url = track.get("permalink_url")
        if not permalink_url:
            logger.warning(f"Track {track_id} has no permalink URL")
            return ""

        # Use oEmbed endpoint
        try:
            async with asyncio.timeout(self.timeout):
                async with self._session.get(
                    self.OEMBED_URL,
                    params={
                        "format": "json",
                        "url": permalink_url,
                        "maxheight": "400",
                        "maxwidth": "600"
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"oEmbed request failed: {response.status}")
                        return ""

                    data = await response.json()

                    # Return the HTML embed code
                    embed_html = data.get("html", "")
                    logger.info("Retrieved oEmbed code")
                    return embed_html

        except Exception as e:
            logger.error(f"Error getting oEmbed: {e}")
            return ""

    async def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for artists/users on SoundCloud

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of artist profiles
        """
        logger.info(f"Searching SoundCloud artists for: {query}")

        result = await self._make_request(
            "/users",
            params={"q": query, "limit": limit}
        )

        if not result:
            logger.warning(f"No artists found for: {query}")
            return []

        # If result is a list, use it; if it's a dict with collection, extract that
        artists = result if isinstance(result, list) else result.get("collection", [])

        # Format artist data
        formatted_artists = []
        for artist in artists[:limit]:
            formatted_artist = {
                "id": artist.get("id"),
                "name": artist.get("username", ""),
                "full_name": artist.get("full_name", ""),
                "avatar_url": artist.get("avatar_url", ""),
                "permalink_url": artist.get("permalink_url", ""),
                "track_count": artist.get("track_count", 0),
                "followers_count": artist.get("followers_count", 0),
                "following_count": artist.get("following_count", 0),
                "description": artist.get("description", ""),
                "city": artist.get("city", ""),
                "country": artist.get("country", ""),
                "website": artist.get("website", ""),
                "is_verified": artist.get("verified", False)
            }
            formatted_artists.append(formatted_artist)

        logger.info(f"Found {len(formatted_artists)} artists")
        return formatted_artists

    async def get_artist(self, artist_id: str) -> Dict:
        """
        Get detailed artist information

        Args:
            artist_id: SoundCloud user/artist ID

        Returns:
            Dictionary with full artist profile
        """
        logger.info(f"Getting artist details for ID: {artist_id}")

        result = await self._make_request(f"/users/{artist_id}")

        if not result:
            logger.warning(f"Artist not found: {artist_id}")
            return {}

        artist = result

        artist_data = {
            "id": artist.get("id"),
            "name": artist.get("username", ""),
            "full_name": artist.get("full_name", ""),
            "avatar_url": artist.get("avatar_url", ""),
            "permalink_url": artist.get("permalink_url", ""),
            "track_count": artist.get("track_count", 0),
            "followers_count": artist.get("followers_count", 0),
            "following_count": artist.get("following_count", 0),
            "description": artist.get("description", ""),
            "city": artist.get("city", ""),
            "country": artist.get("country_code", ""),
            "website": artist.get("website", ""),
            "is_verified": artist.get("verified", False),
            "created_at": artist.get("created_at"),
            "last_modified": artist.get("last_modified")
        }

        logger.info(f"Retrieved artist: {artist_data['name']}")
        return artist_data

    async def get_artist_tracks(self, artist_id: str, limit: int = 10) -> List[Dict]:
        """
        Get tracks by an artist

        Args:
            artist_id: SoundCloud artist ID
            limit: Maximum number of tracks

        Returns:
            List of artist's tracks
        """
        logger.info(f"Getting tracks for artist ID: {artist_id}")

        result = await self._make_request(
            f"/users/{artist_id}/tracks",
            params={"limit": limit}
        )

        if not result:
            logger.warning(f"No tracks found for artist: {artist_id}")
            return []

        # If result is a list, use it; if it's a dict with collection, extract that
        tracks = result if isinstance(result, list) else result.get("collection", [])

        # Format track data
        formatted_tracks = []
        for track in tracks[:limit]:
            formatted_track = {
                "id": track.get("id"),
                "title": track.get("title", ""),
                "artist": track.get("user", {}).get("username", ""),
                "duration": track.get("duration", 0),
                "artwork_url": track.get("artwork_url", ""),
                "stream_url": track.get("stream_url", ""),
                "permalink_url": track.get("permalink_url", ""),
                "embed_url": track.get("permalink_url", ""),
                "genre": track.get("genre", ""),
                "playback_count": track.get("playback_count", 0),
                "likes_count": track.get("likes_count", 0)
            }
            formatted_tracks.append(formatted_track)

        logger.info(f"Retrieved {len(formatted_tracks)} tracks")
        return formatted_tracks

    async def search_playlists(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for playlists on SoundCloud

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of playlists
        """
        logger.info(f"Searching SoundCloud playlists for: {query}")

        result = await self._make_request(
            "/playlists",
            params={"q": query, "limit": limit}
        )

        if not result:
            logger.warning(f"No playlists found for: {query}")
            return []

        # If result is a list, use it; if it's a dict with collection, extract that
        playlists = result if isinstance(result, list) else result.get("collection", [])

        # Format playlist data
        formatted_playlists = []
        for playlist in playlists[:limit]:
            formatted_playlist = {
                "id": playlist.get("id"),
                "title": playlist.get("title", ""),
                "creator": playlist.get("user", {}).get("username", ""),
                "creator_id": playlist.get("user", {}).get("id"),
                "artwork_url": playlist.get("artwork_url", ""),
                "permalink_url": playlist.get("permalink_url", ""),
                "embed_url": playlist.get("permalink_url", ""),
                "track_count": playlist.get("track_count", 0),
                "duration": playlist.get("duration", 0),
                "likes_count": playlist.get("likes_count", 0),
                "description": playlist.get("description", ""),
                "tracks": []
            }

            # Include track list (first few tracks)
            tracks = playlist.get("tracks", [])[:5]
            for track in tracks:
                formatted_playlist["tracks"].append({
                    "id": track.get("id"),
                    "title": track.get("title", ""),
                    "artist": track.get("user", {}).get("username", ""),
                    "duration": track.get("duration", 0)
                })

            formatted_playlists.append(formatted_playlist)

        logger.info(f"Found {len(formatted_playlists)} playlists")
        return formatted_playlists

    async def get_playlist(self, playlist_id: str) -> Dict:
        """
        Get detailed playlist information with all tracks

        Args:
            playlist_id: SoundCloud playlist ID

        Returns:
            Dictionary with full playlist data
        """
        logger.info(f"Getting playlist details for ID: {playlist_id}")

        result = await self._make_request(f"/playlists/{playlist_id}")

        if not result:
            logger.warning(f"Playlist not found: {playlist_id}")
            return {}

        playlist = result

        playlist_data = {
            "id": playlist.get("id"),
            "title": playlist.get("title", ""),
            "creator": playlist.get("user", {}).get("username", ""),
            "creator_id": playlist.get("user", {}).get("id"),
            "artwork_url": playlist.get("artwork_url", ""),
            "permalink_url": playlist.get("permalink_url", ""),
            "embed_url": playlist.get("permalink_url", ""),
            "track_count": playlist.get("track_count", 0),
            "duration": playlist.get("duration", 0),
            "likes_count": playlist.get("likes_count", 0),
            "reposts_count": playlist.get("reposts_count", 0),
            "description": playlist.get("description", ""),
            "is_album": playlist.get("is_album", False),
            "tracks": []
        }

        # Include all tracks
        tracks = playlist.get("tracks", [])
        for track in tracks:
            track_data = {
                "id": track.get("id"),
                "title": track.get("title", ""),
                "artist": track.get("user", {}).get("username", ""),
                "artist_id": track.get("user", {}).get("id"),
                "duration": track.get("duration", 0),
                "artwork_url": track.get("artwork_url", ""),
                "stream_url": track.get("stream_url", ""),
                "permalink_url": track.get("permalink_url", "")
            }
            playlist_data["tracks"].append(track_data)

        logger.info(f"Retrieved playlist: {playlist_data['title']} with {len(playlist_data['tracks'])} tracks")
        return playlist_data

    async def get_embeddable_player_url(self, track_id: str) -> str:
        """
        Get URL for SoundCloud embed player (Discord-compatible)

        Args:
            track_id: SoundCloud track ID

        Returns:
            URL string for embed player
        """
        track = await self.get_track(track_id)
        if not track:
            return ""

        return track.get("permalink_url", "")

    async def close(self) -> None:
        """
        Clean up session if it was created by this wrapper
        """
        if self._created_session and self._session and not self._session.closed:
            await self._session.close()
            logger.info("SoundCloud API session closed")
