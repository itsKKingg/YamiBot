"""
Juice WRLD API Wrapper for YamiBot.

This module provides a comprehensive wrapper for the Juice WRLD REST API,
handling all endpoints for songs, artists, albums, and features.
"""

from typing import Dict, List, Optional
import aiohttp
import asyncio
import logging
from urllib.parse import urljoin


class JuiceWRLDAPI:
    """
    Juice WRLD API wrapper for music-related queries.

    Handles all endpoints including songs, artists, albums, and features.
    Implements retry logic with backoff and proper error handling.
    """

    def __init__(
        self,
        base_url: str = "https://api.juicewrldapi.com",
        session: Optional[aiohttp.ClientSession] = None,
        timeout: int = 10,
        max_retries: int = 2
    ):
        """
        Initialize the Juice WRLD API wrapper.

        Args:
            base_url: Base URL for the API (default: https://api.juicewrldapi.com)
            session: Optional aiohttp session to use (creates new if None)
            timeout: Request timeout in seconds (default: 10)
            max_retries: Maximum retry attempts on network errors (default: 2)
        """
        self.base_url = base_url
        self.session = session
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response or None on error
        """
        session = await self._get_session()

        try:
            url = urljoin(self.base_url, endpoint)
            self.logger.debug(f"Making request to {url} with params: {params}")

            async with session.get(url, params=params) as response:
                # Handle rate limiting
                if response.status == 429:
                    self.logger.warning("Rate limited by Juice WRLD API")
                    if retry_count < self.max_retries:
                        retry_after = int(response.headers.get("Retry-After", 2))
                        await asyncio.sleep(retry_after)
                        return await self._make_request(endpoint, params, retry_count + 1)
                    return None

                # Handle not found
                if response.status == 404:
                    self.logger.debug(f"Resource not found: {endpoint}")
                    return None

                # Handle server errors
                if response.status >= 500:
                    self.logger.error(f"Server error {response.status}: {endpoint}")
                    if retry_count < self.max_retries:
                        await asyncio.sleep(2  ** retry_count)
                        return await self._make_request(endpoint, params, retry_count + 1)
                    return None

                # Handle client errors
                if response.status >= 400:
                    self.logger.error(f"Client error {response.status}: {endpoint}")
                    return None

                # Success
                try:
                    data = await response.json()
                    self.logger.debug(f"Successfully fetched data from {endpoint}")
                    return data
                except Exception as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    return None

        except asyncio.TimeoutError:
            self.logger.warning(f"Request timeout for {endpoint}")
            if retry_count < self.max_retries:
                await asyncio.sleep(2  ** retry_count)
                return await self._make_request(endpoint, params, retry_count + 1)
            return None

        except aiohttp.ClientError as e:
            self.logger.error(f"Client error for {endpoint}: {e}")
            if retry_count < self.max_retries:
                await asyncio.sleep(2  ** retry_count)
                return await self._make_request(endpoint, params, retry_count + 1)
            return None

        except Exception as e:
            self.logger.error(f"Unexpected error for {endpoint}: {e}", exc_info=True)
            return None

    # Song Endpoints

    async def search_songs(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search songs by query string.

        Args:
            query: Search query
            limit: Maximum number of results (default: 10)

        Returns:
            List of song dictionaries or empty list on error
        """
        params = {"q": query, "limit": limit}
        result = await self._make_request("/songs/search", params)

        if isinstance(result, dict) and "songs" in result:
            return result["songs"][:limit]
        elif isinstance(result, list):
            return result[:limit]
        return []

    async def get_song(self, song_id: str) -> Optional[Dict]:
        """
        Get specific song details by ID.

        Args:
            song_id: Song ID as string

        Returns:
            Song dictionary or None if not found
        """
        if not song_id:
            self.logger.warning("Empty song ID provided")
            return None

        result = await self._make_request(f"/songs/{song_id}")
        return result if isinstance(result, dict) else None

    async def list_songs(self, page: int = 1, limit: int = 20) -> Dict:
        """
        List all songs with pagination.

        Args:
            page: Page number (default: 1)
            limit: Items per page (default: 20)

        Returns:
            Dictionary with songs and pagination info or empty dict on error
        """
        params = {"page": page, "limit": limit}
        result = await self._make_request("/songs", params)
        return result if isinstance(result, dict) else {"songs": [], "total": 0, "page": page, "limit": limit}

    # Artist Endpoints

    async def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search artists by name.

        Args:
            query: Artist name query
            limit: Maximum number of results (default: 10)

        Returns:
            List of artist dictionaries or empty list on error
        """
        params = {"q": query, "limit": limit}
        result = await self._make_request("/artists/search", params)

        if isinstance(result, dict) and "artists" in result:
            return result["artists"][:limit]
        elif isinstance(result, list):
            return result[:limit]
        return []

    async def get_artist(self, artist_id: str) -> Optional[Dict]:
        """
        Get artist details by ID.

        Args:
            artist_id: Artist ID as string

        Returns:
            Artist dictionary or None if not found
        """
        if not artist_id:
            self.logger.warning("Empty artist ID provided")
            return None

        result = await self._make_request(f"/artists/{artist_id}")
        return result if isinstance(result, dict) else None

    async def list_artists(self, page: int = 1, limit: int = 20) -> Dict:
        """
        List all artists with pagination.

        Args:
            page: Page number (default: 1)
            limit: Items per page (default: 20)

        Returns:
            Dictionary with artists and pagination info or empty dict on error
        """
        params = {"page": page, "limit": limit}
        result = await self._make_request("/artists", params)
        return result if isinstance(result, dict) else {"artists": [], "total": 0, "page": page, "limit": limit}

    # Album/Discography Endpoints

    async def search_albums(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search albums by title.

        Args:
            query: Album title query
            limit: Maximum number of results (default: 10)

        Returns:
            List of album dictionaries or empty list on error
        """
        params = {"q": query, "limit": limit}
        result = await self._make_request("/albums/search", params)

        if isinstance(result, dict) and "albums" in result:
            return result["albums"][:limit]
        elif isinstance(result, list):
            return result[:limit]
        return []

    async def get_album(self, album_id: str) -> Optional[Dict]:
        """
        Get album details by ID.

        Args:
            album_id: Album ID as string

        Returns:
            Album dictionary or None if not found
        """
        if not album_id:
            self.logger.warning("Empty album ID provided")
            return None

        result = await self._make_request(f"/albums/{album_id}")
        return result if isinstance(result, dict) else None

    async def get_artist_albums(self, artist_id: str) -> List[Dict]:
        """
        Get all albums by artist ID.

        Args:
            artist_id: Artist ID as string

        Returns:
            List of album dictionaries or empty list on error
        """
        if not artist_id:
            self.logger.warning("Empty artist ID provided")
            return []

        result = await self._make_request(f"/artists/{artist_id}/albums")

        if isinstance(result, dict) and "albums" in result:
            return result["albums"]
        elif isinstance(result, list):
            return result
        return []

    async def get_artist_discography(self, artist_name: str) -> List[Dict]:
        """
        Get artist's discography by name.

        Args:
            artist_name: Artist name to search for

        Returns:
            List of discography entries or empty list on error
        """
        if not artist_name:
            self.logger.warning("Empty artist name provided")
            return []

        # First find the artist
        artists = await self.search_artists(artist_name, limit=1)
        if not artists:
            return []

        # Then get their albums
        artist_id = artists[0].get("id", "")
        if not artist_id:
            return []

        return await self.get_artist_albums(artist_id)

    # Feature Collaborations

    async def get_songs_by_feature(self, artist_name: str, limit: int = 20) -> List[Dict]:
        """
        Find songs featuring a specific artist.

        Args:
            artist_name: Artist name to search features for
            limit: Maximum number of results (default: 20)

        Returns:
            List of song dictionaries or empty list on error
        """
        if not artist_name:
            self.logger.warning("Empty artist name provided")
            return []

        params = {"artist": artist_name, "limit": limit}
        result = await self._make_request("/songs/features", params)

        if isinstance(result, dict) and "songs" in result:
            return result["songs"][:limit]
        elif isinstance(result, list):
            return result[:limit]
        return []

    # Utility

    async def close(self) -> None:
        """Clean up aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("Juice WRLD API session closed")
