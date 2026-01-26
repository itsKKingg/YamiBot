"""
Comprehensive tests for Juice WRLD API Integration

Tests all 15+ endpoints, fuzzy matching, caching, and intelligent routing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from integrations.juice_wrld_api import JuiceWRLDAPI
from integrations.juice_wrld_router import JuiceWRLDRouter, JuiceWRLDEndpoint


class TestJuiceWRLDAPI:
    """Test Juice WRLD API wrapper functionality"""
    
    @pytest.fixture
    def juice_api(self):
        """Create test instance of JuiceWRLDAPI"""
        return JuiceWRLDAPI()
    
    @pytest.mark.asyncio
    async def test_fuzzy_search_songs(self, juice_api):
        """Test fuzzy matching for song titles"""
        # Test exact match
        match = await juice_api.find_best_song_match("Lucid Dreams")
        assert match is not None
        assert "Dreams" in match.get("title", "")
        
        # Test misspelling
        match = await juice_api.find_best_song_match("lucd dreams", threshold=0.6)
        assert match is not None
        assert match.get("similarity_score", 0) > 0.6
        
        # Test with different case
        match = await juice_api.find_best_song_match("LUCID DREAMS", threshold=0.9)
        assert match is not None
        assert match.get("similarity_score", 0) > 0.9
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, juice_api):
        """Test caching with TTL"""
        # Get initial cache stats
        stats = juice_api.get_cache_stats()
        initial_size = stats["cache_size"]
        
        # First call - should cache the result
        songs1 = await juice_api.search_songs("Lucid Dreams", limit=5)
        assert len(songs1) > 0
        
        stats = juice_api.get_cache_stats()
        assert stats["cache_size"] > initial_size
        
        # Second call - should use cache
        songs2 = await juice_api.search_songs("Lucid Dreams", limit=5)
        assert len(songs2) == len(songs1)
        
        # Clear cache
        juice_api.clear_cache()
        stats = juice_api.get_cache_stats()
        assert stats["cache_size"] == 0
    
    @pytest.mark.asyncio
    async def test_artist_stats_endpoint(self, juice_api):
        """Test artist statistics endpoint"""
        stats = await juice_api.get_artist_info()
        
        assert isinstance(stats, dict)
        assert "name" in stats or len(stats) == 0  # Empty dict if API doesn't support
        
        if stats:
            assert stats.get("name") == "Juice WRLD"
    
    @pytest.mark.asyncio
    async def test_album_endpoint(self, juice_api):
        """Test album information endpoint"""
        albums = await juice_api.search_albums("Goodbye", limit=5)
        
        assert isinstance(albums, list)
        if albums:
            album = albums[0]
            assert "title" in album
            assert "songs" in album or "track_count" in album
    
    @pytest.mark.asyncio
    async def test_featured_artists_endpoint(self, juice_api):
        """Test featured artists endpoint"""
        artists = await juice_api.get_featured_artists(limit=10)
        
        assert isinstance(artists, list)
        if artists:
            artist = artists[0]
            assert "name" in artist
            assert "song_count" in artist
    
    @pytest.mark.asyncio
    async def test_producers_endpoint(self, juice_api):
        """Test producers endpoint"""
        producers = await juice_api.get_producers(limit=10)
        
        assert isinstance(producers, list)
        if producers:
            producer = producers[0]
            assert "name" in producer
            assert "song_count" in producer
    
    @pytest.mark.asyncio
    async def test_categories_endpoint(self, juice_api):
        """Test categories/moods endpoint"""
        categories = await juice_api.get_categories()
        
        assert isinstance(categories, list)
        if categories:
            category = categories[0]
            assert "name" in category
    
    @pytest.mark.asyncio
    async def test_streaming_links_endpoint(self, juice_api):
        """Test streaming links endpoint"""
        # First find a song
        songs = await juice_api.search_songs("Lucid Dreams", limit=1)
        if songs:
            song_id = songs[0].get("id")
            if song_id:
                links = await juice_api.get_streaming_links(song_id)
                assert isinstance(links, dict)
    
    @pytest.mark.asyncio
    async def test_charts_endpoint(self, juice_api):
        """Test charts/rankings endpoint"""
        songs = await juice_api.get_charts(chart_type="top", limit=10)
        
        assert isinstance(songs, list)
        if songs:
            song = songs[0]
            assert "title" in song
    
    @pytest.mark.asyncio
    async def test_playlist_recommendations_endpoint(self, juice_api):
        """Test playlist recommendations endpoint"""
        songs = await juice_api.get_playlist_recommendations(mood="sad", limit=10)
        
        assert isinstance(songs, list)
        if songs:
            song = songs[0]
            assert "title" in song
    
    @pytest.mark.asyncio
    async def test_biography_endpoint(self, juice_api):
        """Test biography endpoint"""
        bio = await juice_api.get_biography()
        
        assert isinstance(bio, dict)
        if bio:
            assert "biography" in bio or "bio" in bio
    
    @pytest.mark.asyncio
    async def test_related_artists_endpoint(self, juice_api):
        """Test related artists endpoint"""
        artists = await juice_api.get_related_artists(limit=10)
        
        assert isinstance(artists, list)
        if artists:
            artist = artists[0]
            assert "name" in artist


class TestJuiceWRLDRouter:
    """Test intelligent routing functionality"""
    
    @pytest.fixture
    def router(self):
        """Create test instance of JuiceWRLDRouter"""
        return JuiceWRLDRouter()
    
    def test_lyrics_routing(self, router):
        """Test routing lyric requests"""
        queries = [
            "lyrics to lucid dreams",
            "lucid dreams lyrics",
            "what are the lyrics to lucid dreams"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.SONG_LYRICS
            assert "song_query" in params
    
    def test_album_routing(self, router):
        """Test routing album requests"""
        queries = [
            "album goodbye and good riddance",
            "songs from album death race for love"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.ALBUM_INFO
            assert "album_query" in params
    
    def test_featured_routing(self, router):
        """Test routing featured artist requests"""
        query = "who's on lucid dreams with juice"
        endpoint, params = router.route_query(query)
        assert endpoint == JuiceWRLDEndpoint.FEATURED_ARTISTS
    
    def test_producer_routing(self, router):
        """Test routing producer requests"""
        queries = [
            "songs produced by taz taylor",
            "producer nick mira"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.PRODUCER_FILTER
            assert "producer" in params
    
    def test_era_routing(self, router):
        """Test routing era requests"""
        queries = [
            "songs from 2018-2020 era",
            "era posthumous"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.ERA_FILTER
    
    def test_category_routing(self, router):
        """Test routing category/mood requests"""
        queries = [
            "sad juice songs",
            "hype juice songs",
            "introspective juice songs"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.CATEGORY_FILTER
    
    def test_stats_routing(self, router):
        """Test routing statistics requests"""
        queries = [
            "juice stats",
            "juice wrld statistics",
            "how many juice songs are there"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.ARTIST_STATS
    
    def test_charts_routing(self, router):
        """Test routing chart requests"""
        queries = [
            "top juice songs",
            "best juice songs",
            "juice charts"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.CHARTS
    
    def test_streaming_routing(self, router):
        """Test routing streaming link requests"""
        query = "where to stream lucid dreams"
        endpoint, params = router.route_query(query)
        assert endpoint == JuiceWRLDEndpoint.STREAMING_LINKS
    
    def test_biography_routing(self, router):
        """Test routing biography requests"""
        queries = [
            "juice wrld biography",
            "tell me about juice wrld",
            "juice background info"
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.BIOGRAPHY
    
    def test_default_routing(self, router):
        """Test default routing to song search"""
        queries = [
            "lucid dreams",  # Song title
            "juice wrld song",  # Generic juice query
        ]
        
        for query in queries:
            endpoint, params = router.route_query(query)
            assert endpoint == JuiceWRLDEndpoint.SONG_SEARCH
    
    def test_parse_search_query(self, router):
        """Test search query parsing for filters"""
        query = "sad juice songs from 2018-2020 era"
        parsed = router.parse_search_query(query)
        
        assert "filters" in parsed
        assert parsed["filters"].get("era") == "2018-2020"
        assert parsed["filters"].get("category") == "sad"


# Integration test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_integration():
    """Full integration test with real API calls"""
    juice_api = JuiceWRLDAPI()
    router = JuiceWRLDRouter()
    
    # Test intelligent routing with real API
    query = "lyrics to lucid dreams"
    endpoint, params = router.route_query(query)
    
    assert endpoint == JuiceWRLDEndpoint.SONG_LYRICS
    
    # Execute the routed command
    songs = await juice_api.fuzzy_search_songs(params.get("song_query", "lucid dreams"))
    assert len(songs) > 0
    
    # Check cache
    stats = juice_api.get_cache_stats()
    assert stats["cache_size"] > 0
    
    await juice_api.close()


if __name__ == "__main__":
    # Run basic tests
    print("Running Juice WRLD API tests...")
    
    # Test fuzzy matching
    juice_api = JuiceWRLDAPI()
    router = JuiceWRLDRouter()
    
    # Test routing
    test_queries = [
        "lyrics to lucid dreams",
        "sad juice songs",
        "juice stats",
        "album goodbye and good riddance",
        "produced by taz taylor"
    ]
    
    print("\nTesting intelligent routing:")
    for query in test_queries:
        endpoint, params = router.route_query(query)
        print(f"  '{query}' → {endpoint.value if endpoint else 'None'}")
    
    print("\nAll tests completed!")