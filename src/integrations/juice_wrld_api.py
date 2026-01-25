"""\
Juice WRLD API Wrapper for YamiBot

Primary music data source using https://juicewrldapi.com/juicewrld

Implements:
- Song search, lyric search, filters (era/category/producer)
- Song details, eras listing, random radio, global stats
- Cover art / streaming / archive URL helpers
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union
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


class JuiceWrldAPI:
    """Async wrapper for the Juice WRLD API."""

    BASE_URL = "https://juicewrldapi.com/juicewrld"

    SONGS_ENDPOINT = "/songs/"
    ERAS_ENDPOINT = "/eras/"
    STATS_ENDPOINT = "/stats/"
    RANDOM_ENDPOINT = "/radio/random/"
    CATEGORIES_ENDPOINT = "/categories/"
    BROWSE_ENDPOINT = "/files/browse/"
    STREAM_ENDPOINT = "/stream/"
    ZIP_CREATE_ENDPOINT = "/zip/create/"
    ZIP_STATUS_ENDPOINT = "/zip/status/"
    SEARCH_ENDPOINT = "/search/"
    BROWSE_ARTIST_ENDPOINT = "/browse/"
    BROWSE_ALBUM_ENDPOINT = "/browse/"
    BROWSE_TRACK_ENDPOINT = "/browse/"

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

        self.urls = JuiceWrldApiUrls(
            cover_art=f"{self.BASE_URL}{self.COVER_ART_ENDPOINT}",
            download=f"{self.BASE_URL}{self.DOWNLOAD_ENDPOINT}",
            archive=f"{self.BASE_URL}{self.FILES_ENDPOINT}",
        )

        logger.info("Juice WRLD API wrapper initialized")

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
                                wait_time = self.retry_delay * (attempt + 1)
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
            for key in ("results", "songs", "data", "items", "collection"):
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
            for key in ("song", "data", "result"):
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
                    name = item.get("name") or item.get("title")
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

        status = raw.get("status") or raw.get("category") or raw.get("type")
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
        }

    async def search_songs(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        data = await self._make_request(self.SONGS_ENDPOINT, params={"search": query})
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    async def lyric_search(self, phrase: str, limit: int = 10) -> List[Dict[str, Any]]:
        data = await self._make_request(self.SONGS_ENDPOINT, params={"lyrics": phrase})
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    async def filter_songs(
        self,
        *,
        era: Optional[Union[str, int]] = None,
        category: Optional[str] = None,
        producer: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if era is not None:
            params["era"] = era
        if category:
            params["category"] = category
        if producer:
            params["producer"] = producer

        data = await self._make_request(self.SONGS_ENDPOINT, params=params)
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs[:limit]

    async def get_song(self, song_id: Union[str, int]) -> Dict[str, Any]:
        data = await self._make_request(f"{self.SONGS_ENDPOINT}{song_id}/")
        raw = self._extract_object(data)
        return self._normalize_song(raw) if raw else {}

    async def get_lyrics(self, song_id: Union[str, int]) -> str:
        """Fetch full lyrics for a specific song ID."""
        data = await self._make_request(f"{self.SONGS_ENDPOINT}{song_id}/lyrics/")
        if not data:
            return ""

        if isinstance(data, str):
            return data.strip()

        if isinstance(data, dict):
            # Try various common keys for lyrics
            return data.get("lyrics") or data.get("lyric") or data.get("full_lyrics") or ""

        return ""

    async def list_eras(self) -> List[Dict[str, Any]]:
        data = await self._make_request(self.ERAS_ENDPOINT)
        eras = [self._normalize_era(r) for r in self._extract_list(data)]
        return eras

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all song categories"""
        data = await self._make_request(self.CATEGORIES_ENDPOINT)
        return self._extract_list(data)

    async def list_categories_with_songs(self) -> Dict[str, Any]:
        """Get categories + songs in each"""
        data = await self._make_request(self.CATEGORIES_ENDPOINT, params={"include_songs": "true"})
        if isinstance(data, dict):
            return data
        return {}

    async def filter_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get songs from specific category"""
        return await self.filter_songs(category=category, limit=limit)

    async def filter_by_producer(self, producer: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all songs produced by X"""
        return await self.filter_songs(producer=producer, limit=limit)

    async def filter_by_era(self, era: Union[str, int], limit: int = 50) -> List[Dict[str, Any]]:
        """Get all songs from specific era"""
        return await self.filter_songs(era=era, limit=limit)

    async def get_era_details(self, era_id: str) -> Dict[str, Any]:
        """Get era metadata + song count"""
        data = await self._make_request(f"{self.ERAS_ENDPOINT}{era_id}/")
        return self._normalize_era(self._extract_object(data))

    async def get_cover_art(self, song_id: Union[str, int]) -> str:
        """Get cover art image URL"""
        song = await self.get_song(song_id)
        return song.get("cover_art_url", "")

    async def get_stream_url(self, song_id: Union[str, int]) -> str:
        """Get streaming URL (with HTTP 206 support)"""
        data = await self._make_request(f"{self.STREAM_ENDPOINT}{song_id}/")
        if isinstance(data, dict):
            return data.get("stream_url", "") or data.get("url", "")
        return data if isinstance(data, str) else ""

    async def get_download_url(self, song_id: Union[str, int]) -> str:
        """Get direct download URL"""
        data = await self._make_request(f"{self.SONGS_ENDPOINT}{song_id}/", params={"download": "true"})
        if isinstance(data, dict):
            return data.get("download_url", "") or data.get("url", "")
        return data if isinstance(data, str) else ""

    async def get_stats(self) -> Dict[str, Any]:
        data = await self._make_request(self.STATS_ENDPOINT)
        if isinstance(data, dict):
            return data
        return {}

    async def create_zip_archive(self, song_ids: List[Union[str, int]], name: str) -> str:
        """Create ZIP job, return job_id"""
        payload = {
            "songs": [str(sid) for sid in song_ids],
            "name": name
        }
        data = await self._make_request(self.ZIP_CREATE_ENDPOINT, method="POST", json_body=payload)
        if isinstance(data, dict):
            return data.get("job_id", "") or data.get("id", "")
        return str(data) if data else ""

    async def check_zip_status(self, job_id: str) -> Dict[str, Any]:
        """Check ZIP creation status"""
        data = await self._make_request(f"{self.ZIP_STATUS_ENDPOINT}{job_id}/")
        return self._extract_object(data)

    async def get_zip_download(self, job_id: str) -> str:
        """Get ZIP download URL when ready"""
        data = await self._make_request(f"{self.ZIP_STATUS_ENDPOINT}{job_id}/")
        if isinstance(data, dict):
            return data.get("download_url", "") or data.get("url", "")
        return str(data) if data else ""

    # Utility methods
    async def search_all_songs(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all songs for caching/indexing"""
        data = await self._make_request(self.SONGS_ENDPOINT, params={"limit": str(limit)})
        songs = [self._normalize_song(r) for r in self._extract_list(data)]
        return songs

    async def find_song_by_title(self, title: str) -> Dict[str, Any]:
        """Smart song title matching (for fuzzy search)"""
        results = await self.search_songs(title, limit=10)
        if results:
            # Check if top result is strong match
            if self._is_strong_title_match(title, results[0].get("title", "")):
                song_id = results[0].get("id")
                return await self.get_song(song_id)
        return results[0] if results else {}

    async def browse_files(self, path: str = "") -> Dict[str, Any]:
        """Browse directory structure"""
        params = {}
        if path:
            params["path"] = path
        data = await self._make_request(self.BROWSE_ENDPOINT, params=params)
        return self._extract_object(data)

    async def browse_artists(self) -> List[Dict[str, Any]]:
        """Browse available artists"""
        data = await self._make_request(self.BROWSE_ARTIST_ENDPOINT, params={"type": "artists"})
        return self._extract_list(data)

    async def browse_albums(self) -> List[Dict[str, Any]]:
        """Browse available albums"""
        data = await self._make_request(self.BROWSE_ALBUM_ENDPOINT, params={"type": "albums"})
        return self._extract_list(data)

    async def browse_tracks(self) -> List[Dict[str, Any]]:
        """Browse available tracks"""
        data = await self._make_request(self.BROWSE_TRACK_ENDPOINT, params={"type": "tracks"})
        return self._extract_list(data)

    async def search_all_content(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search across all content (songs, albums, artists)"""
        data = await self._make_request(self.SEARCH_ENDPOINT, params={"q": query, "limit": str(limit)})
        if isinstance(data, dict):
            return data
        return {"results": []}

    @staticmethod
    def _is_strong_title_match(query: str, title: str) -> bool:
        """Check if song title matches query strongly enough"""
        if not query or not title:
            return False
        
        query_lower = query.lower().strip()
        title_lower = title.lower().strip()
        
        # Exact match
        if query_lower == title_lower:
            return True
        
        # Very close match (ignore punctuation, extra spaces)
        import re
        query_clean = re.sub(r'[^\w\s]', '', query_lower)
        title_clean = re.sub(r'[^\w\s]', '', title_lower)
        query_clean = re.sub(r'\s+', ' ', query_clean)
        title_clean = re.sub(r'\s+', ' ', title_clean)
        
        if query_clean == title_clean:
            return True
        
        # If query is much shorter than title, likely not a strong match
        if len(query_clean) < len(title_clean) * 0.5:
            return False
        
        # Check if query is contained in title
        if query_clean in title_clean:
            return True
        
        return False

    async def random_song(self) -> Dict[str, Any]:
        data = await self._make_request(self.RANDOM_ENDPOINT)
        raw = self._extract_object(data)
        return self._normalize_song(raw) if raw else {}

    async def get_stats(self) -> Dict[str, Any]:
        data = await self._make_request(self.STATS_ENDPOINT)
        if isinstance(data, dict):
            return data
        return {}

    async def generate_archive(
        self,
        *,
        song_ids: Optional[Sequence[Union[str, int]]] = None,
        era: Optional[Union[str, int]] = None,
    ) -> Optional[str]:
        """Generate an archive (.zip) for multiple songs or an era.

        The public API spec only states `/files/` is used for archive generation.
        This method tries a POST first and falls back to GET if needed.

        Returns a download URL if one can be determined.
        """
        payload: Dict[str, Any] = {}
        if song_ids:
            payload["songs"] = list(song_ids)
        if era is not None:
            payload["era"] = era

        if not payload:
            return None

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

        # Best-effort: provide the endpoint URL with params so the user can try it
        # (useful if API returns file directly)
        if song_ids:
            songs_param = ",".join(str(s) for s in song_ids)
            return f"{self.urls.archive}?songs={quote(songs_param)}"
        if era is not None:
            return f"{self.urls.archive}?era={quote(str(era))}"
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
        for key in ("download_url", "url", "archive_url", "link"):
            val = data.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
        # sometimes nested
        for key in ("data", "result"):
            nested = data.get(key)
            if isinstance(nested, dict):
                for k2 in ("download_url", "url", "archive_url", "link"):
                    val = nested.get(k2)
                    if isinstance(val, str) and val.startswith("http"):
                        return val
        return None

    async def close(self) -> None:
        if self._created_session and self._session and not self._session.closed:
            await self._session.close()
            logger.info("Juice WRLD API session closed")
