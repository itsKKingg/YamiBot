"""
Juice WRLD API Wrapper for YamiBot

Primary music data source using https://juicewrldapi.com/juicewrld

Implements:
- Song search, lyric search, filters (era/category/producer)
- Song details, eras listing, random radio, global stats
- Cover art / streaming / archive URL helpers
- All 15+ endpoints with intelligent routing and caching
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
from urllib.parse import quote

import aiohttp

from ..utils.logger import setup_logging

logger = setup_logging(__name__)

JsonValue = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


@dataclass(frozen=True)
class JuiceWrldApiUrls:
    cover_art: str
    download: str
    archive: str


class CacheEntry:
    """Cache entry with TTL support"""
    
    def __init__(self, data: Any, ttl_seconds: int = 3600):
        self.data = data
        self.created_at = datetime.now()
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        return datetime.now() - self.created_at > self.ttl


class JuiceWRLDAPI:
    """Async wrapper for the Juice WRLD API with caching and fuzzy matching."""

    BASE_URL = "https://juicewrldapi.com/juicewrld"

    # Core endpoints
    SONGS_ENDPOINT = "/songs/"
    ERAS_ENDPOINT = "/eras/"
    STATS_ENDPOINT = "/stats/"
    RANDOM_ENDPOINT = "/radio/random/"
    
    # Extended endpoints
    ALBUMS_ENDPOINT = "/albums/"
    FEATURED_ENDPOINT = "/featured/"
    PRODUCERS_ENDPOINT = "/producers/"
    CATEGORIES_ENDPOINT = "/categories/"
    STREAMING_ENDPOINT = "/streaming/"
    ARTISTS_ENDPOINT = "/artists/"
    CHARTS_ENDPOINT = "/charts/"
    PLAYLISTS_ENDPOINT = "/playlists/"
    BIOGRAPHY_ENDPOINT = "/biography/"
    RELATED_ENDPOINT = "/related/"

    # File endpoints
    COVER_ART_ENDPOINT = "/files/cover-art/"
    DOWNLOAD_ENDPOINT = "/files/download/"
    FILES_ENDPOINT = "/files/"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._created_session = session is None
        if self._created_session:
            self._session = aiohttp.ClientSession()

        self.timeout_seconds = 15
        self.max_retries = 2
        self.retry_delay = 1

        # Cache configuration
        self._cache: Dict[str, CacheEntry] = {}
        self._max_cache_size = 1000
        self._fuzzy_match_cache: Dict[str, Dict[str, Any]] = {}
        
        # Cache TTLs
        self.CACHE_TTL_SEARCH = 3600  # 1 hour for search results
        self.CACHE_TTL_METADATA = 86400  # 24 hours for metadata
        self.CACHE_TTL_STATS = 7200  # 2 hours for stats

        self.urls = JuiceWrldApiUrls(
            cover_art=f"{self.BASE_URL}{self.COVER_ART_ENDPOINT}",
            download=f"{self.BASE_URL}{self.DOWNLOAD_ENDPOINT}",
            archive=f"{self.BASE_URL}{self.FILES_ENDPOINT}",
        )

        logger.info("Juice WRLD API wrapper initialized with caching and fuzzy matching")

    def _get_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from endpoint and params"""
        key_data = {"endpoint": endpoint, "params": params or {}}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                logger.debug(f"Cache HIT for key: {key[:16]}...")
                return entry.data
            else:
                logger.debug(f"Cache EXPIRED for key: {key[:16]}...")
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl_seconds: Optional[int] = None):
        """Set data in cache with TTL"""
        # Enforce cache size limit
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        ttl = ttl_seconds or self.CACHE_TTL_SEARCH
        self._cache[key] = CacheEntry(data, ttl)
        logger.debug(f"Cache SET for key: {key[:16]}... (TTL: {ttl}s)")

    def cache_decorator(ttl_seconds: Optional[int] = None):
        """Decorator for caching API methods"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(self: 'JuiceWRLDAPI', *args, **kwargs):
                # Generate cache key from function name and arguments
                endpoint = func.__name__
                params = {"args": args, "kwargs": kwargs}
                cache_key = self._get_cache_key(endpoint, params)
                
                # Try cache first
                cached_data = self._get_from_cache(cache_key)
                if cached_data is not None:
                    return cached_data
                
                # Call function and cache result
                result = await func(self, *args, **kwargs)
                if result is not None:
                    self._set_cache(cache_key, result, ttl_seconds)
                
                return result
            return wrapper
        return decorator

    async def _make_request(
        self,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Optional[JsonValue]:
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(self.max_retries + 1):
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    async with self._session.request(
                        method,
                        url,
                        params=params,
                        json=json_body,
                        allow_redirects=True,
                    ) as resp:
                        if resp.status == 429:
                            if attempt < self.max_retries:
                                wait_time = self.retry_delay * (attempt + 1) ** 2  # Exponential backoff
                                logger.warning(
                                    "Juice WRLD API rate limited. Waiting %ss before retry %s/%s",
                                    wait_time,
                                    attempt + 1,
                                    self.max_retries,
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            logger.error("Juice WRLD API rate limit exceeded")
                            return None

                        if resp.status == 404:
                            logger.debug(f"Juice WRLD API 404: {url}")
                            return None

                        if resp.status >= 400:
                            logger.error("Juice WRLD API error %s: %s", resp.status, await resp.text())
                            return None

                        content_type = resp.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            return await resp.json()

                        # Some endpoints may redirect or return plain text URLs
                        text = await resp.text()
                        return text

            except asyncio.TimeoutError:
                logger.warning(
                    "Juice WRLD API request timeout (attempt %s/%s): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    url,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

            except aiohttp.ClientError as e:
                logger.error(
                    "Juice WRLD API network error (attempt %s/%s): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

            except Exception as e:
                logger.error("Juice WRLD API unexpected error: %s", e, exc_info=True)
                return None

        return None

    @staticmethod
    def _extract_list(data: JsonValue) -> List[Dict[str, Any]]:
        if not data:
            return []
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("results", "songs", "data", "items", "collection", "songs_list"):
                val = data.get(key)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
        return []

    @staticmethod
    def _extract_object(data: JsonValue) -> Dict[str, Any]:
        if not data:
            return {}
        if isinstance(data, dict):
            # Sometimes the API nests a single object under a key
            for key in ("song", "data", "result", "metadata", "info"):
                val = data.get(key)
                if isinstance(val, dict):
                    return val
            return data
        return {}

    @staticmethod
    def _as_list_of_names(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        if isinstance(value, list):
            names: List[str] = []
            for item in value:
                if isinstance(item, str):
                    if item.strip():
                        names.append(item.strip())
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("title") or item.get("artist")
                    if isinstance(name, str) and name.strip():
                        names.append(name.strip())
            return names
        return []

    def cover_art_url(self, path_or_url: Optional[str]) -> Optional[str]:
        if not path_or_url:
            return None
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return f"{self.urls.cover_art}?path={quote(path_or_url)}"

    def download_url(self, path_or_url: Optional[str]) -> Optional[str]:
        if not path_or_url:
            return None
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return f"{self.urls.download}?path={quote(path_or_url)}"

    def _normalize_song(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        song_id = raw.get("id") or raw.get("song_id") or raw.get("_id")

        title = raw.get("title") or raw.get("name") or raw.get("song") or ""
        artist = raw.get("artist") or raw.get("primary_artist") or raw.get("artist_name") or "Juice WRLD"
        if isinstance(artist, dict):
            artist = artist.get("name") or "Juice WRLD"

        album = raw.get("album")
        if isinstance(album, dict):
            album = album.get("name") or album.get("title")

        era = raw.get("era") or raw.get("era_name")
        era_id = raw.get("era_id")
        if isinstance(era, dict):
            era_id = era_id or era.get("id")
            era = era.get("name") or era.get("title")

        producers = self._as_list_of_names(raw.get("producers") or raw.get("producer") or raw.get("producer_names"))
        features = self._as_list_of_names(raw.get("features") or raw.get("featured_artists") or raw.get("featuring"))

        status = raw.get("status") or raw.get("category") or raw.get("type") or raw.get("mood")
        release_date = raw.get("release_date") or raw.get("released") or raw.get("release")

        recording_date = raw.get("recording_date") or raw.get("recorded") or raw.get("recorded_date")
        studio_location = raw.get("studio_location") or raw.get("studio") or raw.get("recorded_at")

        duration = raw.get("duration") or raw.get("length") or raw.get("song_length")

        cover_path = (
            raw.get("cover_art")
            or raw.get("cover_art_path")
            or raw.get("artwork")
            or raw.get("artwork_path")
            or raw.get("image")
            or raw.get("image_path")
            or raw.get("image_url")
            or raw.get("artwork_url")
        )

        audio_path = raw.get("path") or raw.get("audio_path") or raw.get("file_path") or raw.get("download_path")
        stream_url = raw.get("stream_url") or raw.get("audio_url") or raw.get("download_url")

        if not stream_url:
            stream_url = self.download_url(audio_path)

        # Streaming links
        streaming_links = raw.get("streaming_links") or raw.get("streaming") or {}
        if isinstance(streaming_links, dict):
            spotify = streaming_links.get("spotify") or raw.get("spotify_url")
            apple_music = streaming_links.get("apple_music") or raw.get("apple_music_url")
            soundcloud = streaming_links.get("soundcloud") or raw.get("soundcloud_url")
        else:
            spotify = apple_music = soundcloud = None

        song_data: Dict[str, Any] = {
            "id": song_id,
            "title": title,
            "artist": artist,
            "album": album or "",
            "release_date": release_date or "",
            "recording_date": recording_date or "",
            "studio_location": studio_location or "",
            "era": era or "",
            "era_id": era_id,
            "status": status or "",
            "duration": duration,
            "producers": producers,
            "features": features,
            "lyrics": raw.get("lyrics") or raw.get("lyric") or raw.get("full_lyrics") or "",
            "description": raw.get("description") or "",
            "cover_art_path": cover_path,
            "audio_path": audio_path,
            "cover_art_url": self.cover_art_url(cover_path),
            "stream_url": stream_url,
            "juice_wrld_url": f"{self.BASE_URL}{self.SONGS_ENDPOINT}{song_id}/" if song_id else "",
            "streaming_links": {
                "spotify": spotify,
                "apple_music": apple_music,
                "soundcloud": soundcloud
            },
            "chart_position": raw.get("chart_position"),
            "play_count": raw.get("play_count") or raw.get("plays"),
            "likes": raw.get("likes") or raw.get("favorites"),
        }

        # Optional: preserve any match snippets returned by lyric search
        if raw.get("matched_lyrics"):
            song_data["matched_lyrics"] = raw.get("matched_lyrics")
        if raw.get("lyrics_match"):
            song_data["matched_lyrics"] = raw.get("lyrics_match")

        return song_data

    def _normalize_era(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        era_id = raw.get("id") or raw.get("era_id") or raw.get("_id")
        name = raw.get("name") or raw.get("title") or raw.get("era") or ""
        start_date = raw.get("start_date") or raw.get("start") or raw.get("from")
        end_date = raw.get("end_date") or raw.get("end") or raw.get("to")
        song_count = raw.get("song_count") or raw.get("songs_count") or raw.get("count") or raw.get("songs")
        if isinstance(song_count, list):
            song_count = len(song_count)

        return {
            "id": era_id,
            "name": name,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "song_count": int(song_count) if isinstance(song_count, (int, float, str)) and str(song_count).isdigit() else song_count or 0,
            "description": raw.get("description") or "",
            "era_type": raw.get("era_type") or raw.get("type"),
        }

    def _normalize_album(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        album_id = raw.get("id") or raw.get("album_id") or raw.get("_id")
        title = raw.get("title") or raw.get("name") or ""
        release_date = raw.get("release_date") or raw.get("released") or raw.get("release")
        
        return {
            "id": album_id,
            "title": title,
            "release_date": release_date or "",
            "track_count": raw.get("track_count") or raw.get("songs_count") or len(raw.get("songs", [])),
            "songs": [self._normalize_song(s) for s in self._extract_list(raw.get("songs"))],
            "cover_art_url": self.cover_art_url(raw.get("cover_art") or raw.get("artwork")),
            "description": raw.get("description") or "",
        }

    def _normalize_artist(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": raw.get("id") or raw.get("artist_id") or raw.get("_id"),
            "name": raw.get("name") or raw.get("artist_name") or "Juice WRLD",
            "followers": raw.get("followers") or raw.get("follower_count"),
            "total_streams": raw.get("total_streams") or raw.get("streams") or raw.get("play_count"),
            "top_songs": [self._normalize_song(s) for s in self._extract_list(raw.get("top_songs"))],
            "albums": [self._normalize_album(a) for a in self._extract_list(raw.get("albums"))],
            "bio": raw.get("bio") or raw.get("biography") or "",
        }

    # ==================== CORE API METHODS ====================

    @cache_decorator()
    async def search_songs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for songs by title or artist"""
        logger.debug(f"Searching songs with query: '{query}' (limit: {limit})")
        data = await self._make_request(self.SONGS_ENDPOINT, params={"search": query, "limit": limit})
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    @cache_decorator()
    async def lyric_search(self, phrase: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for songs by lyrics"""
        logger.debug(f"Searching lyrics with phrase: '{phrase}' (limit: {limit})")
        data = await self._make_request(self.SONGS_ENDPOINT, params={"lyrics": phrase, "limit": limit})
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for filters
    async def filter_songs(
        self,
        *,
        era: Optional[Union[str, int]] = None,
        category: Optional[str] = None,
        producer: Optional[str] = None,
        mood: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filter songs by era, category, producer, or mood"""
        params: Dict[str, Any] = {"limit": limit}
        if era is not None:
            params["era"] = era
        if category:
            params["category"] = category
        if producer:
            params["producer"] = producer
        if mood:
            params["mood"] = mood

        logger.debug(f"Filtering songs with params: {params}")
        data = await self._make_request(self.SONGS_ENDPOINT, params=params)
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    @cache_decorator(ttl_seconds=86400)  # 24 hour TTL for song details
    async def get_song(self, song_id: Union[str, int]) -> Dict[str, Any]:
        """Get detailed information for a specific song"""
        logger.debug(f"Fetching song by ID: {song_id}")
        data = await self._make_request(f"{self.SONGS_ENDPOINT}{song_id}/")
        raw = self._extract_object(data)
        return self._normalize_song(raw) if raw else {}

    @cache_decorator(ttl_seconds=86400)  # 24 hour TTL for lyrics
    async def get_lyrics(self, song_id: Union[str, int]) -> str:
        """Fetch full lyrics for a specific song ID"""
        logger.debug(f"Fetching lyrics for song ID: {song_id}")
        data = await self._make_request(f"{self.SONGS_ENDPOINT}{song_id}/lyrics/")
        if not data:
            return ""

        if isinstance(data, str):
            return data.strip()

        if isinstance(data, dict):
            # Try various common keys for lyrics
            return data.get("lyrics") or data.get("lyric") or data.get("full_lyrics") or ""

        return ""

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for eras
    async def list_eras(self) -> List[Dict[str, Any]]:
        """List all available eras"""
        logger.debug("Listing eras")
        data = await self._make_request(self.ERAS_ENDPOINT)
        eras = [self._normalize_era(r) for r in self._extract_list(data)]
        return eras

    @cache_decorator()
    async def random_song(self) -> Dict[str, Any]:
        """Get a random Juice WRLD song"""
        logger.debug("Fetching random song")
        data = await self._make_request(self.RANDOM_ENDPOINT)
        raw = self._extract_object(data)
        return self._normalize_song(raw) if raw else {}

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for stats
    async def get_stats(self) -> Dict[str, Any]:
        """Get Juice WRLD statistics and global info"""
        logger.debug("Fetching global stats")
        data = await self._make_request(self.STATS_ENDPOINT)
        if isinstance(data, dict):
            return data
        return {}

    # ==================== EXTENDED ENDPOINTS ====================

    @cache_decorator(ttl_seconds=86400)  # 24 hour TTL for albums
    async def get_album(self, album_id: Union[str, int]) -> Dict[str, Any]:
        """Get album information"""
        logger.debug(f"Fetching album by ID: {album_id}")
        data = await self._make_request(f"{self.ALBUMS_ENDPOINT}{album_id}/")
        raw = self._extract_object(data)
        return self._normalize_album(raw) if raw else {}

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for album searches
    async def search_albums(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for albums"""
        logger.debug(f"Searching albums with query: '{query}' (limit: {limit})")
        data = await self._make_request(self.ALBUMS_ENDPOINT, params={"search": query, "limit": limit})
        albums = [self._normalize_album(r) for r in self._extract_list(data)]
        return albums[:limit]

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for featured artists
    async def get_featured_artists(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of artists featured on Juice WRLD songs"""
        logger.debug(f"Fetching featured artists (limit: {limit})")
        data = await self._make_request(self.FEATURED_ENDPOINT, params={"limit": limit})
        artists = []
        for item in self._extract_list(data):
            artists.append({
                "name": item.get("name") or item.get("artist"),
                "song_count": item.get("song_count") or item.get("count"),
                "songs": [self._normalize_song(s) for s in self._extract_list(item.get("songs"))]
            })
        return artists[:limit]

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for producers
    async def get_producers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of producers who worked on Juice WRLD songs"""
        logger.debug(f"Fetching producers (limit: {limit})")
        data = await self._make_request(self.PRODUCERS_ENDPOINT, params={"limit": limit})
        producers = []
        for item in self._extract_list(data):
            producers.append({
                "name": item.get("name") or item.get("producer"),
                "song_count": item.get("song_count") or item.get("count"),
                "songs": [self._normalize_song(s) for s in self._extract_list(item.get("songs"))]
            })
        return producers[:limit]

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for categories
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get available song categories/moods"""
        logger.debug("Fetching categories")
        data = await self._make_request(self.CATEGORIES_ENDPOINT)
        categories = []
        for item in self._extract_list(data):
            categories.append({
                "name": item.get("name") or item.get("category") or item.get("mood"),
                "count": item.get("count") or item.get("song_count"),
                "description": item.get("description") or ""
            })
        return categories

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for streaming links
    async def get_streaming_links(self, song_id: Union[str, int]) -> Dict[str, Any]:
        """Get streaming links for a specific song"""
        logger.debug(f"Fetching streaming links for song ID: {song_id}")
        data = await self._make_request(f"{self.STREAMING_ENDPOINT}{song_id}/")
        raw = self._extract_object(data)
        if not raw:
            return {}
        
        return {
            "spotify": raw.get("spotify") or raw.get("spotify_url"),
            "apple_music": raw.get("apple_music") or raw.get("apple_music_url"),
            "soundcloud": raw.get("soundcloud") or raw.get("soundcloud_url"),
            "youtube": raw.get("youtube") or raw.get("youtube_url"),
            "deezer": raw.get("deezer") or raw.get("deezer_url"),
        }

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for artist info
    async def get_artist_info(self) -> Dict[str, Any]:
        """Get Juice WRLD artist information and statistics"""
        logger.debug("Fetching artist info")
        data = await self._make_request(f"{self.ARTISTS_ENDPOINT}juice-wrld/")
        raw = self._extract_object(data)
        return self._normalize_artist(raw) if raw else {}

    @cache_decorator(ttl_seconds=3600)  # 1 hour TTL for charts
    async def get_charts(self, chart_type: str = "top", limit: int = 10) -> List[Dict[str, Any]]:
        """Get chart rankings"""
        logger.debug(f"Fetching charts (type: {chart_type}, limit: {limit})")
        data = await self._make_request(self.CHARTS_ENDPOINT, params={"type": chart_type, "limit": limit})
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for playlists
    async def get_playlist_recommendations(self, mood: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get playlist recommendations"""
        logger.debug(f"Fetching playlist recommendations (mood: {mood}, limit: {limit})")
        params = {"limit": limit}
        if mood:
            params["mood"] = mood
        
        data = await self._make_request(self.PLAYLISTS_ENDPOINT, params=params)
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    @cache_decorator(ttl_seconds=86400)  # 24 hour TTL for biography
    async def get_biography(self) -> Dict[str, Any]:
        """Get Juice WRLD biography and background information"""
        logger.debug("Fetching biography")
        data = await self._make_request(self.BIOGRAPHY_ENDPOINT)
        raw = self._extract_object(data)
        if not raw:
            return {}
        
        return {
            "full_name": raw.get("full_name") or raw.get("name"),
            "birth_date": raw.get("birth_date") or raw.get("born"),
            "death_date": raw.get("death_date") or raw.get("died"),
            "birth_place": raw.get("birth_place"),
            "genres": self._as_list_of_names(raw.get("genres")),
            "years_active": raw.get("years_active"),
            "labels": self._as_list_of_names(raw.get("labels")),
            "biography": raw.get("biography") or raw.get("bio") or "",
            "legacy": raw.get("legacy") or "",
        }

    @cache_decorator(ttl_seconds=7200)  # 2 hour TTL for related artists
    async def get_related_artists(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get related/similar artists"""
        logger.debug(f"Fetching related artists (limit: {limit})")
        data = await self._make_request(self.RELATED_ENDPOINT, params={"limit": limit})
        artists = []
        for item in self._extract_list(data):
            artists.append({
                "name": item.get("name") or item.get("artist"),
                "similarity_score": item.get("similarity") or item.get("score"),
                "genre": item.get("genre"),
                "reason": item.get("reason") or item.get("why_similar")
            })
        return artists[:limit]

    # ==================== FUZZY MATCHING ====================

    def _calculate_levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._calculate_levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _calculate_similarity_score(self, query: str, target: str) -> float:
        """Calculate similarity score between 0 and 1"""
        query = query.lower().strip()
        target = target.lower().strip()
        
        # Exact match
        if query == target:
            return 1.0
        
        # Query is substring of target
        if query in target:
            return 0.95
        
        # Target is substring of query
        if target in query:
            return 0.9
        
        # Levenshtein distance similarity
        max_len = max(len(query), len(target))
        if max_len == 0:
            return 0.0
        
        distance = self._calculate_levenshtein_distance(query, target)
        similarity = 1 - (distance / max_len)
        
        return max(0.0, similarity)

    async def fuzzy_search_songs(self, query: str, threshold: float = 0.7, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fuzzy search for songs with similarity matching
        
        Args:
            query: Search query (can be misspelled)
            threshold: Minimum similarity score (0-1)
            limit: Maximum number of results
            
        Returns:
            List of songs with similarity scores, sorted by score
        """
        cache_key = f"fuzzy:{query.lower()}:{threshold}"
        
        # Check fuzzy match cache first
        if cache_key in self._fuzzy_match_cache:
            cached = self._fuzzy_match_cache[cache_key]
            if not cached.get("expires") or datetime.now() < datetime.fromisoformat(cached["expires"]):
                logger.debug(f"Fuzzy cache HIT for: '{query}'")
                return cached.get("results", [])
        
        logger.debug(f"Fuzzy searching songs with query: '{query}' (threshold: {threshold})")
        
        # First try exact search
        songs = await self.search_songs(query, limit=20)
        
        # If no results, try variations
        if not songs:
            # Remove special characters
            clean_query = re.sub(r'[^\w\s]', '', query)
            if clean_query != query:
                songs = await self.search_songs(clean_query, limit=20)
            
            # Try splitting by common words
            if not songs:
                words = query.split()
                if len(words) > 1:
                    # Try first few words
                    for i in range(len(words), 0, -1):
                        partial = ' '.join(words[:i])
                        songs = await self.search_songs(partial, limit=20)
                        if songs:
                            break
        
        # Calculate similarity scores
        scored_songs = []
        for song in songs:
            title = song.get("title", "")
            similarity = self._calculate_similarity_score(query, title)
            
            # Also check against artist name
            artist = song.get("artist", "")
            artist_similarity = self._calculate_similarity_score(query, artist)
            
            # Take the maximum similarity
            max_similarity = max(similarity, artist_similarity)
            
            if max_similarity >= threshold:
                song_copy = song.copy()
                song_copy["similarity_score"] = max_similarity
                scored_songs.append(song_copy)
        
        # Sort by similarity score (descending)
        scored_songs.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        # Cache the results
        self._fuzzy_match_cache[cache_key] = {
            "results": scored_songs[:limit],
            "expires": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
        return scored_songs[:limit]

    async def find_best_song_match(self, query: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """Find the best matching song for a query"""
        matches = await self.fuzzy_search_songs(query, threshold=threshold, limit=1)
        return matches[0] if matches else None

    # ==================== ARCHIVE GENERATION ====================

    async def generate_archive(
        self,
        *,
        song_ids: Optional[Sequence[Union[str, int]]] = None,
        era: Optional[Union[str, int]] = None,
        album: Optional[Union[str, int]] = None,
    ) -> Optional[str]:
        """
        Generate an archive (.zip) for multiple songs, an era, or an album
        
        Returns a download URL if one can be determined
        """
        payload: Dict[str, Any] = {}
        if song_ids:
            payload["songs"] = list(song_ids)
        if era is not None:
            payload["era"] = era
        if album is not None:
            payload["album"] = album

        if not payload:
            return None

        logger.debug(f"Generating archive with payload: {payload}")

        # Attempt POST
        data = await self._make_request(self.FILES_ENDPOINT, method="POST", json_body=payload)
        url = self._extract_download_url(data)
        if url:
            return url

        # Attempt GET with params
        data = await self._make_request(self.FILES_ENDPOINT, params=payload)
        url = self._extract_download_url(data)
        if url:
            return url

        # Best-effort: provide the endpoint URL with params
        params = []
        if song_ids:
            songs_param = ",".join(str(s) for s in song_ids)
            params.append(f"songs={quote(songs_param)}")
        if era is not None:
            params.append(f"era={quote(str(era))}")
        if album is not None:
            params.append(f"album={quote(str(album))}")
        
        if params:
            return f"{self.urls.archive}?{'&'.join(params)}"
        
        return None

    @staticmethod
    def _extract_download_url(data: Optional[JsonValue]) -> Optional[str]:
        if not data:
            return None
        if isinstance(data, str):
            # sometimes returns plain URL
            return data.strip() if data.strip().startswith("http") else None
        if not isinstance(data, dict):
            return None
        for key in ("download_url", "url", "archive_url", "link", "download"):
            val = data.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
        # sometimes nested
        for key in ("data", "result", "file"):
            nested = data.get(key)
            if isinstance(nested, dict):
                for k2 in ("download_url", "url", "archive_url", "link", "download"):
                    val = nested.get(k2)
                    if isinstance(val, str) and val.startswith("http"):
                        return val
        return None

    # ==================== UTILITY METHODS ====================

    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._fuzzy_match_cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self._cache),
            "fuzzy_cache_size": len(self._fuzzy_match_cache),
            "max_cache_size": self._max_cache_size,
            "ttl_search": self.CACHE_TTL_SEARCH,
            "ttl_metadata": self.CACHE_TTL_METADATA,
            "ttl_stats": self.CACHE_TTL_STATS,
        }

    async def close(self) -> None:
        if self._created_session and self._session and not self._session.closed:
            await self._session.close()
            logger.info("Juice WRLD API session closed")
        self.clear_cache()


# Singleton instance for easy access
_juice_wrld_api_instance: Optional[JuiceWRLDAPI] = None


def get_juice_wrld_api(session: Optional[aiohttp.ClientSession] = None) -> JuiceWRLDAPI:
    """Get singleton instance of JuiceWRLDAPI"""
    global _juice_wrld_api_instance
    if _juice_wrld_api_instance is None:
        _juice_wrld_api_instance = JuiceWRLDAPI(session)
    return _juice_wrld_api_instance


# Backward compatibility alias
JuiceWrldAPI = JuiceWRLDAPI