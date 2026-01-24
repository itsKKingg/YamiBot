"""
Genius API Wrapper for YamiBot

This module provides a comprehensive wrapper for the Genius API to access
lyrics, song information, artist details, and annotations.

Genius API Documentation: https://docs.genius.com/
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional
from datetime import datetime

from ..utils.logger import setup_logging

logger = setup_logging(__name__)


class GeniusAPI:
    """
    Wrapper for the Genius API providing async methods for music data retrieval.
    """

    # API endpoint constants
    BASE_URL = "https://api.genius.com"
    SEARCH_ENDPOINT = "/search"
    SONG_ENDPOINT = "/songs"
    ARTIST_ENDPOINT = "/artists"
    WEB_BASE_URL = "https://genius.com"

    def __init__(self, access_token: str, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize Genius API wrapper

        Args:
            access_token: Genius API access token from https://genius.com/api-clients
            session: Optional aiohttp ClientSession (will create if not provided)
        """
        self.access_token = access_token
        self._session = session
        self._created_session = session is None

        if self._created_session:
            self._session = aiohttp.ClientSession()

        # Request timeout (seconds)
        self.timeout = 10

        # Retry configuration
        self.max_retries = 2
        self.retry_delay = 1  # seconds

        logger.info("Genius API wrapper initialized")

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        method: str = "GET"
    ) -> Optional[Dict]:
        """
        Make authenticated request to Genius API with retry logic

        Args:
            endpoint: API endpoint path (e.g., "/search")
            params: Query parameters
            method: HTTP method (default: GET)

        Returns:
            Response data dict or None on error
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with asyncio.timeout(self.timeout):
                    async with self._session.request(
                        method,
                        url,
                        headers=headers,
                        params=params
                    ) as response:
                        # Handle rate limiting (429)
                        if response.status == 429:
                            if attempt < self.max_retries:
                                wait_time = self.retry_delay * (attempt + 1)
                                logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.error("Rate limit exceeded after retries")
                                return None

                        # Handle other errors
                        if response.status == 404:
                            logger.debug(f"Resource not found: {url}")
                            return None

                        if response.status >= 400:
                            logger.error(f"API error {response.status}: {await response.text()}")
                            return None

                        # Parse JSON response
                        data = await response.json()
                        return data.get("response", {})

            except asyncio.TimeoutError:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

            except aiohttp.ClientError as e:
                logger.error(f"Network error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None

        logger.error(f"Request failed after {self.max_retries + 1} attempts")
        return None

    async def search(
        self,
        query: str,
        search_type: str = "song",
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for songs, artists, or albums

        Args:
            query: Search query
            search_type: Type to search for ("song", "artist", "album")
            limit: Maximum number of results to return

        Returns:
            List of matching results
        """
        logger.info(f"Searching Genius for: {query} (type: {search_type}, limit: {limit})")

        result = await self._make_request(
            self.SEARCH_ENDPOINT,
            params={"q": query, "per_page": limit}
        )

        if not result or "hits" not in result:
            logger.warning(f"No results found for query: {query}")
            return []

        # Filter results by type
        hits = result.get("hits", [])
        filtered_results = []

        for hit in hits:
            result_type = hit.get("type", "").lower()
            if search_type.lower() in result_type or result_type == search_type:
                filtered_results.append(hit.get("result"))

        logger.info(f"Found {len(filtered_results)} {search_type} results")
        return filtered_results[:limit]

    async def search_songs(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search specifically for songs

        Args:
            query: Song search query
            limit: Maximum number of results

        Returns:
            List of song results
        """
        return await self.search(query, search_type="song", limit=limit)

    async def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search specifically for artists

        Args:
            query: Artist search query
            limit: Maximum number of results

        Returns:
            List of artist results
        """
        return await self.search(query, search_type="artist", limit=limit)

    async def get_song(self, song_id: int) -> Dict:
        """
        Get detailed song information

        Args:
            song_id: Genius song ID

        Returns:
            Dictionary with song details:
            - id: Song ID
            - title: Song title
            - artist: Artist name
            - album: Album name
            - url: Genius URL
            - lyrics_url: URL to lyrics page
            - release_date: Release date
            - producers: List of producers
            - features: List of featured artists
        """
        logger.info(f"Getting song details for ID: {song_id}")

        result = await self._make_request(f"{self.SONG_ENDPOINT}/{song_id}")

        if not result or "song" not in result:
            logger.warning(f"Song not found: {song_id}")
            return {}

        song = result["song"]

        # Extract relevant information
        song_data = {
            "id": song.get("id"),
            "title": song.get("title", ""),
            "artist": song.get("primary_artist", {}).get("name", ""),
            "album": song.get("album", {}).get("name", "") if song.get("album") else "",
            "url": song.get("url", ""),
            "lyrics_url": song.get("url", ""),  # Same as URL, links to lyrics page
            "release_date": song.get("release_date"),
            "producers": [p.get("name", "") for p in song.get("producer_artists", [])],
            "features": [f.get("name", "") for f in song.get("featured_artists", [])],
            "description": song.get("description", {}).get("plain", ""),
            "image_url": song.get("header_image_url", "")
        }

        logger.info(f"Retrieved song: {song_data['title']} by {song_data['artist']}")
        return song_data

    async def get_song_by_name(self, title: str, artist: Optional[str] = None) -> Dict:
        """
        Search for a song by name (and optionally artist) and return first match

        Args:
            title: Song title
            artist: Optional artist name for better matching

        Returns:
            Dictionary with song details
        """
        query = title
        if artist:
            query = f"{title} {artist}"

        results = await self.search_songs(query, limit=5)

        if not results:
            logger.warning(f"No songs found for: {query}")
            return {}

        # Find best match
        for result in results:
            song_title = result.get("title", "").lower()
            result_artist = result.get("primary_artist", {}).get("name", "").lower()

            title_match = title.lower() in song_title or song_title in title.lower()

            if artist:
                artist_match = artist.lower() in result_artist or result_artist in artist.lower()
                if title_match and artist_match:
                    song_id = result.get("id")
                    if song_id:
                        return await self.get_song(song_id)
            elif title_match:
                song_id = result.get("id")
                if song_id:
                    return await self.get_song(song_id)

        # Fallback to first result
        first_song_id = results[0].get("id")
        if first_song_id:
            return await self.get_song(first_song_id)

        return {}

    async def get_artist(self, artist_id: int) -> Dict:
        """
        Get detailed artist information

        Args:
            artist_id: Genius artist ID

        Returns:
            Dictionary with artist details:
            - id: Artist ID
            - name: Artist name
            - bio: Artist biography
            - url: Genius URL
            - image_url: Artist image URL
            - songs_count: Number of songs
            - followers: Follower count (if available)
        """
        logger.info(f"Getting artist details for ID: {artist_id}")

        result = await self._make_request(f"{self.ARTIST_ENDPOINT}/{artist_id}")

        if not result or "artist" not in result:
            logger.warning(f"Artist not found: {artist_id}")
            return {}

        artist = result["artist"]

        artist_data = {
            "id": artist.get("id"),
            "name": artist.get("name", ""),
            "bio": artist.get("description", {}).get("plain", ""),
            "url": artist.get("url", ""),
            "image_url": artist.get("image_url", ""),
            "songs_count": artist.get("songs_count", 0),
            "followers": artist.get("follower_count", 0),
            "alternate_names": artist.get("alternate_names", []),
            "is_verified": artist.get("is_verified", False)
        }

        logger.info(f"Retrieved artist: {artist_data['name']}")
        return artist_data

    async def get_song_annotations(
        self,
        song_id: int,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get annotations for a song

        Note: Genius API doesn't provide a direct endpoint for annotations.
        This method attempts to extract annotations by referencing the song page.

        Args:
            song_id: Genius song ID
            limit: Maximum number of annotations to return

        Returns:
            List of annotation dictionaries:
            - lyric: The lyric line
            - annotation: The explanation/annotation
            - author: Annotation author (if available)
        """
        logger.info(f"Getting annotations for song ID: {song_id}")

        # First get the song to get its URL
        song = await self.get_song(song_id)
        if not song:
            logger.warning(f"Cannot get annotations - song not found: {song_id}")
            return []

        song_url = song.get("url")
        if not song_url:
            logger.warning(f"Cannot get annotations - no song URL: {song_id}")
            return []

        # Try to get annotations from the song page
        # Note: This is a simplified implementation. A full implementation would
        # scrape the song page HTML to extract annotations.
        # For now, we'll return a placeholder indicating annotations exist.

        try:
            # Use referents endpoint to get annotations
            result = await self._make_request(
                f"/referents",
                params={"song_id": song_id, "per_page": limit}
            )

            if not result or "referents" not in result:
                logger.info("No annotations found via API")
                return []

            annotations = []
            for referent in result.get("referents", []):
                annotation_data = referent.get("annotations", [])
                if annotation_data:
                    annotation = annotation_data[0]  # First annotation
                    annotations.append({
                        "lyric": referent.get("fragment", "").strip(),
                        "annotation": annotation.get("body", {}).get("plain", ""),
                        "author": annotation.get("author", {}).get("name", "Unknown"),
                        "votes": annotation.get("votes_total", 0),
                        "url": annotation.get("url", "")
                    })

            logger.info(f"Retrieved {len(annotations)} annotations")
            return annotations[:limit]

        except Exception as e:
            logger.error(f"Error getting annotations: {e}")
            return []

    async def get_lyrics(self, song_id: int) -> str:
        """
        Scrape lyrics from Genius song page
        
        Note: Genius API doesn't provide lyrics directly, so we scrape the page
        
        Args:
            song_id: Genius song ID
            
        Returns:
            Lyrics text or empty string if not found
        """
        logger.info(f"Fetching lyrics for song ID: {song_id}")
        
        # First get the song to get its URL
        song = await self.get_song(song_id)
        if not song or not song.get("url"):
            logger.warning(f"Cannot get lyrics - song not found: {song_id}")
            return ""
            
        song_url = song.get("url")
        
        try:
            # Scrape the lyrics from the song page
            async with asyncio.timeout(self.timeout):
                async with self._session.get(song_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch lyrics page: {response.status}")
                        return ""
                    
                    html = await response.text()
                    
                    # Extract lyrics from HTML
                    # Genius uses various div containers for lyrics
                    # Try to find lyrics in common patterns
                    import re
                    
                    # Pattern 1: Look for lyrics in data-lyrics-container divs
                    lyrics_pattern = r'<div[^>]*data-lyrics-container="true"[^>]*>(.*?)</div>'
                    lyrics_matches = re.findall(lyrics_pattern, html, re.DOTALL)
                    
                    if lyrics_matches:
                        # Combine all lyrics sections
                        lyrics_html = " ".join(lyrics_matches)
                        
                        # Clean HTML tags
                        lyrics_text = re.sub(r'<br\s*/?>', '\n', lyrics_html)  # Convert <br> to newlines
                        lyrics_text = re.sub(r'<[^>]+>', '', lyrics_text)  # Remove all HTML tags
                        lyrics_text = lyrics_text.replace('&amp;', '&')
                        lyrics_text = lyrics_text.replace('&lt;', '<')
                        lyrics_text = lyrics_text.replace('&gt;', '>')
                        lyrics_text = lyrics_text.replace('&quot;', '"')
                        lyrics_text = lyrics_text.replace('&#39;', "'")
                        lyrics_text = lyrics_text.strip()
                        
                        logger.info(f"Successfully extracted lyrics ({len(lyrics_text)} characters)")
                        return lyrics_text
                    
                    # Pattern 2: Fallback - look for Lyrics__ class divs
                    lyrics_pattern_2 = r'<div[^>]*class="[^"]*Lyrics__Container[^"]*"[^>]*>(.*?)</div>'
                    lyrics_matches_2 = re.findall(lyrics_pattern_2, html, re.DOTALL)
                    
                    if lyrics_matches_2:
                        lyrics_html = " ".join(lyrics_matches_2)
                        lyrics_text = re.sub(r'<br\s*/?>', '\n', lyrics_html)
                        lyrics_text = re.sub(r'<[^>]+>', '', lyrics_text)
                        lyrics_text = lyrics_text.replace('&amp;', '&')
                        lyrics_text = lyrics_text.replace('&lt;', '<')
                        lyrics_text = lyrics_text.replace('&gt;', '>')
                        lyrics_text = lyrics_text.replace('&quot;', '"')
                        lyrics_text = lyrics_text.replace('&#39;', "'")
                        lyrics_text = lyrics_text.strip()
                        
                        logger.info(f"Successfully extracted lyrics using fallback method ({len(lyrics_text)} characters)")
                        return lyrics_text
                    
                    logger.warning("Could not extract lyrics from page")
                    return ""
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching lyrics from {song_url}")
            return ""
        except Exception as e:
            logger.error(f"Error fetching lyrics: {e}")
            return ""
    
    async def close(self) -> None:
        """
        Clean up session if it was created by this wrapper
        """
        if self._created_session and self._session and not self._session.closed:
            await self._session.close()
            logger.info("Genius API session closed")
