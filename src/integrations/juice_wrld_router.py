"""
Juice WRLD API Router

Intelligent request routing for Juice WRLD API endpoints.
Parses user queries to determine which endpoint and parameters to use.
"""

import re
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from ..utils.logger import setup_logging

logger = setup_logging(__name__)


class JuiceWRLDEndpoint(Enum):
    """Available Juice WRLD API endpoints"""
    SONG_SEARCH = "song_search"
    SONG_LYRICS = "song_lyrics"
    ARTIST_STATS = "artist_stats"
    ALBUM_INFO = "album_info"
    FEATURED_ARTISTS = "featured_artists"
    ERA_FILTER = "era_filter"
    PRODUCER_FILTER = "producer_filter"
    CATEGORY_FILTER = "category_filter"
    STREAMING_LINKS = "streaming_links"
    COVER_ART = "cover_art"
    RELATED_ARTISTS = "related_artists"
    CHARTS = "charts"
    PLAYLIST_RECOMMENDATIONS = "playlist_recommendations"
    BIOGRAPHY = "biography"
    RANDOM_SONG = "random_song"
    ARCHIVE = "archive"


class JuiceWRLDRouter:
    """Intelligent router for Juice WRLD API endpoints"""
    
    def __init__(self):
        # Pattern matchers for different query types
        self.patterns = {
            # Song-related
            "lyrics": [
                r"\b(lyrics?|lyric)\b.*\b(?:to|for)\s+(.+)",
                r"\b(.+?)\s+lyrics?\b",
            ],
            "album": [
                r"\b(?:album|mixtape|ep|project)\s+(.+)",
                r"\bfrom\s+(?:the\s+)?(?:album|mixtape|project)\s+(.+)",
                r"\b(?:album|mixtape)\s+by\s+juice\s+wrld\s+(.+)",
            ],
            "featured": [
                r"\bwho'?s?\s+on\s+(.+?)\s+with\s+juice",
                r"\bwho'?s?\s+featured\s+on\s+(.+)",
                r"\bfeaturing\s+on\s+(.+)",
                r"\bcollaborations?\s+(.+)",
            ],
            "producer": [
                r"\bproduced\s+by\s+(.+)",
                r"\bproducer\s+(.+)",
                r"\bbeat\s+by\s+(.+)",
                r"\bbeats?\s+by\s+(.+)",
            ],
            "era": [
                r"\b(?:era|period|time|year)\s+(.+)",
                r"\bfrom\s+(.+?)\s+era",
                r"\b(2015-2018|2018-2020|posthumous|early|late)\b",
            ],
            "category": [
                r"\b(sad|hype|introspective|emotional|party|chill|melodic|aggressive)\s+juice\s+songs?\b",
                r"\bjuice\s+songs?\s+(that|which)\s+are\s+(.+)",
            ],
            "stats": [
                r"\b(stats?|statistics|numbers|info)\b.*\bjuice",
                r"\bjuice\s+wrld\s+(stats?|statistics|numbers)",
                r"\b(how many|total|count)\b.*\b(songs|albums|streams)",
            ],
            "charts": [
                r"\b(top|chart|ranking|most\s+popular)\b",
                r"\b(best\s+songs?|greatest|hits)\b",
            ],
            "streaming": [
                r"\b(stream|play|listen|spotify|apple\s+music|soundcloud)\b.*\b(.+)",
                r"\bwhere\s+to\s+(stream|listen)\s+to\s+(.+)",
            ],
            "related": [
                r"\b(similar|related|like|artists?\s+like)\b",
                r"\bwho\s+sounds?\s+like\s+juice",
            ],
            "biography": [
                r"\b(bio|biography|life|story|background|about)\b.*\bjuice",
                r"\btell\s+me\s+about\s+juice\s+wrld",
                r"\bwho\s+is\s+juice\s+wrld",
            ],
            "archive": [
                r"\b(zip|archive|download\s+all|discography)\b",
                r"\bdownload\s+(.+?)\s+(collection|songs)",
            ],
            "random": [
                r"\b(random|surprise|any|unexpected)\b.*\bjuice\s+songs?\b",
            ],
            "playlist": [
                r"\b(playlist|recommendations?|suggestions?)\b",
                r"\bwhat\s+should\s+i\s+listen\s+to",
            ],
            "cover_art": [
                r"\b(cover\s+art|album\s+art|picture|image|photo)\b.*\b.+\b",
            ],
        }
        
        # Category mappings
        self.category_mappings = {
            "sad": ["sad", "depressing", "melancholy", "emotional", "heartbreak", "crying"],
            "hype": ["hype", "energetic", "upbeat", "exciting", "turn up", "party"],
            "introspective": ["introspective", "deep", "thoughtful", "meaningful", "reflective"],
            "emotional": ["emotional", "feelings", "sentimental", "touching"],
            "party": ["party", "celebration", "turn up", "club"],
            "chill": ["chill", "relaxed", "mellow", "calm", "smooth"],
            "melodic": ["melodic", "harmonious", "tuneful", "musical"],
            "aggressive": ["aggressive", "angry", "intense", "fierce", "hard"],
        }
        
        # Era mappings
        self.era_mappings = {
            "2015-2018": ["2015-2018", "early", "beginning", "start", "first", "old"],
            "2018-2020": ["2018-2020", "middle", "peak", "prime", "main"],
            "posthumous": ["posthumous", "after death", "2020+", "2021", "2022", "2023", "2024", "new", "recent"],
        }
        
        logger.info("Juice WRLD Router initialized")

    def route_query(self, query: str) -> Tuple[JuiceWRLDEndpoint, Dict[str, Any]]:
        """
        Route a user query to the appropriate endpoint
        
        Returns:
            Tuple of (endpoint, params)
        """
        query_lower = query.lower().strip()
        
        # Try each pattern category
        
        # 1. Lyrics requests
        if self._match_pattern(query, "lyrics"):
            song_title = self._extract_song_title(query, "lyrics")
            if song_title:
                logger.debug(f"Routing to SONG_LYRICS: {song_title}")
                return JuiceWRLDEndpoint.SONG_LYRICS, {"song_query": song_title}
        
        # 2. Album requests
        if self._match_pattern(query, "album"):
            album_name = self._extract_song_title(query, "album")
            if album_name:
                logger.debug(f"Routing to ALBUM_INFO: {album_name}")
                return JuiceWRLDEndpoint.ALBUM_INFO, {"album_query": album_name}
        
        # 3. Featured artist queries
        if self._match_pattern(query, "featured"):
            song_title = self._extract_song_title(query, "featured")
            logger.debug(f"Routing to FEATURED_ARTISTS: {song_title or 'general'}")
            return JuiceWRLDEndpoint.FEATURED_ARTISTS, {"song_query": song_title}
        
        # 4. Producer/beatmaker queries
        producer_match = self._match_pattern(query, "producer")
        if producer_match:
            producer_name = producer_match.group(1) if hasattr(producer_match, 'group') else None
            if producer_name:
                logger.debug(f"Routing to PRODUCER_FILTER: {producer_name}")
                return JuiceWRLDEndpoint.PRODUCER_FILTER, {"producer": producer_name}
        
        # 5. Era queries
        era_match = self._match_pattern(query, "era")
        if era_match:
            era_name = self._extract_era_name(query)
            if era_name:
                logger.debug(f"Routing to ERA_FILTER: {era_name}")
                return JuiceWRLDEndpoint.ERA_FILTER, {"era": era_name}
        
        # 6. Category/mood queries
        category_name = self._extract_category_name(query_lower)
        if category_name:
            logger.debug(f"Routing to CATEGORY_FILTER: {category_name}")
            return JuiceWRLDEndpoint.CATEGORY_FILTER, {"category": category_name, "mood": category_name}
        
        # 7. Statistics queries
        if self._match_pattern(query, "stats"):
            logger.debug("Routing to ARTIST_STATS")
            return JuiceWRLDEndpoint.ARTIST_STATS, {}
        
        # 8. Chart/top songs queries
        if self._match_pattern(query, "charts"):
            limit = self._extract_limit(query) or 10
            logger.debug(f"Routing to CHARTS (limit: {limit})")
            return JuiceWRLDEndpoint.CHARTS, {"limit": limit}
        
        # 9. Streaming link requests
        if self._match_pattern(query, "streaming"):
            song_title = self._extract_song_title(query, "streaming")
            if song_title:
                logger.debug(f"Routing to STREAMING_LINKS: {song_title}")
                return JuiceWRLDEndpoint.STREAMING_LINKS, {"song_query": song_title}
        
        # 10. Related artists
        if self._match_pattern(query, "related"):
            logger.debug("Routing to RELATED_ARTISTS")
            return JuiceWRLDEndpoint.RELATED_ARTISTS, {}
        
        # 11. Biography requests
        if self._match_pattern(query, "biography"):
            logger.debug("Routing to BIOGRAPHY")
            return JuiceWRLDEndpoint.BIOGRAPHY, {}
        
        # 12. Archive/download requests
        if self._match_pattern(query, "archive"):
            # Try to extract specific query
            archive_match = re.search(r"\b(zip|archive|download all|discography)\s+(.+?)(?:\s+songs?|\s+collection)?\b", query_lower)
            if archive_match and archive_match.group(2):
                query_text = archive_match.group(2).strip()
                logger.debug(f"Routing to ARCHIVE: {query_text}")
                return JuiceWRLDEndpoint.ARCHIVE, {"query": query_text}
            logger.debug("Routing to ARCHIVE: general")
            return JuiceWRLDEndpoint.ARCHIVE, {}
        
        # 13. Random song
        if self._match_pattern(query, "random"):
            logger.debug("Routing to RANDOM_SONG")
            return JuiceWRLDEndpoint.RANDOM_SONG, {}
        
        # 14. Playlist recommendations
        if self._match_pattern(query, "playlist"):
            mood = self._extract_category_name(query_lower)
            logger.debug(f"Routing to PLAYLIST_RECOMMENDATIONS (mood: {mood})")
            return JuiceWRLDEndpoint.PLAYLIST_RECOMMENDATIONS, {"mood": mood}
        
        # 15. Cover art requests
        if self._match_pattern(query, "cover_art"):
            song_title = self._extract_song_title(query, "cover_art")
            if song_title:
                logger.debug(f"Routing to COVER_ART: {song_title}")
                return JuiceWRLDEndpoint.COVER_ART, {"song_query": song_title}
        
        # Default: song search
        # If query contains "juice" or is likely a song title, search for songs
        if self._is_likely_song_query(query):
            logger.debug(f"Routing to SONG_SEARCH (default): {query}")
            return JuiceWRLDEndpoint.SONG_SEARCH, {"query": query}
        
        # If nothing matches, return None (let other handlers deal with it)
        logger.debug(f"No specific Juice WRLD routing found for: {query}")
        return None, {}

    def _match_pattern(self, query: str, pattern_type: str) -> Optional[re.Match]:
        """Check if query matches patterns of a given type"""
        if pattern_type not in self.patterns:
            return None
        
        query_lower = query.lower()
        for pattern in self.patterns[pattern_type]:
            match = re.search(pattern, query_lower)
            if match:
                return match
        return None

    def _extract_song_title(self, query: str, pattern_type: str) -> Optional[str]:
        """Extract song title from query based on pattern type"""
        match = self._match_pattern(query, pattern_type)
        if not match:
            return None
        
        # Try different capture groups
        for i in range(1, min(4, len(match.groups()) + 1)):
            try:
                title = match.group(i)
                if title and title.strip():
                    # Clean up common words
                    title = self._clean_song_title(title)
                    return title
            except IndexError:
                continue
        
        return None

    def _clean_song_title(self, title: str) -> str:
        """Clean extracted song title"""
        # Remove common words/phrases at the end
        words_to_remove = ["by", "with", "featuring", "ft", "feat", "explicit", "clean", "lyrics", "official"]
        
        title = title.strip()
        title_lower = title.lower()
        
        for word in words_to_remove:
            if title_lower.endswith(f" {word}"):
                title = title[:-(len(word) + 1)].strip()
                title_lower = title.lower()
        
        return title.strip()

    def _extract_era_name(self, query: str) -> Optional[str]:
        """Extract era name from query"""
        query_lower = query.lower()
        
        for era_key, synonyms in self.era_mappings.items():
            for synonym in synonyms:
                if synonym in query_lower:
                    return era_key
        
        # Extract from "era" patterns
        match = self._match_pattern(query, "era")
        if match:
            # Return the matched era text
            for i in range(1, len(match.groups()) + 1):
                try:
                    era_text = match.group(i)
                    if era_text and era_text.strip():
                        return era_text.strip()
                except IndexError:
                    continue
        
        return None

    def _extract_category_name(self, query: str) -> Optional[str]:
        """Extract category/mood name from query"""
        query_lower = query.lower()
        
        # Check direct category names
        for category_key, synonyms in self.category_mappings.items():
            if category_key in query_lower:
                return category_key
            
            for synonym in synonyms:
                if synonym in query_lower:
                    return category_key
        
        # Extract from "category" patterns
        match = self._match_pattern(query, "category")
        if match:
            for i in range(1, len(match.groups()) + 1):
                try:
                    category_text = match.group(i)
                    if category_text and category_text.strip():
                        # Map the extracted text to a category
                        return self._map_category_text(category_text)
                except IndexError:
                    continue
        
        return None

    def _map_category_text(self, category_text: str) -> Optional[str]:
        """Map extracted category text to standard category name"""
        category_text = category_text.lower().strip()
        
        for category_key, synonyms in self.category_mappings.items():
            if category_key in category_text:
                return category_key
            
            for synonym in synonyms:
                if synonym in category_text:
                    return category_key
        
        return None

    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract limit number from query"""
        # Look for numbers that could be limits
        match = re.search(r"\b(\d{1,2}|10|20|50|100)\b", query)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 100:
                return num
        
        # Look for words indicating quantity
        if "top 10" in query.lower() or "best 10" in query.lower():
            return 10
        if "top 5" in query.lower() or "best 5" in query.lower():
            return 5
        if "top 20" in query.lower() or "best 20" in query.lower():
            return 20
        
        return None

    def _is_likely_song_query(self, query: str) -> bool:
        """Determine if query is likely a song title search"""
        query_lower = query.lower()
        
        # If it mentions juice, it's likely a song query
        if "juice" in query_lower or "wrld" in query_lower:
            return True
        
        # If it's short (1-5 words), likely a song title
        words = query.split()
        if 1 <= len(words) <= 5:
            return True
        
        # If it contains song-related words
        song_words = ["song", "track", "single", "record", "music", "tune"]
        if any(word in query_lower for word in song_words):
            return True
        
        return False

    def parse_search_query(self, query: str) -> Dict[str, Any]:
        """
        Parse a search query to extract filters and search terms
        
        Returns:
            Dict containing: query, filters (era, category, producer, mood), and other parameters
        """
        result = {
            "query": query,
            "filters": {},
            "search_type": "general"
        }
        
        query_lower = query.lower()
        
        # Extract era filter
        era = self._extract_era_name(query)
        if era:
            result["filters"]["era"] = era
            # Remove era from query to improve search
            for synonym in self.era_mappings.get(era, []):
                query_lower = query_lower.replace(synonym, "")
        
        # Extract category/mood filter
        category = self._extract_category_name(query_lower)
        if category:
            result["filters"]["category"] = category
            result["filters"]["mood"] = category
        
        # Extract producer filter
        producer_match = self._match_pattern(query, "producer")
        if producer_match:
            try:
                producer = producer_match.group(1)
                if producer and producer.strip():
                    result["filters"]["producer"] = producer.strip()
            except IndexError:
                pass
        
        # Update cleaned query
        result["clean_query"] = query_lower.strip()
        
        return result


# Global router instance
_router_instance: Optional[JuiceWRLDRouter] = None


def get_juice_wrld_router() -> JuiceWRLDRouter:
    """Get singleton instance of JuiceWRLDRouter"""
    global _router_instance
    if _router_instance is None:
        _router_instance = JuiceWRLDRouter()
    return _router_instance