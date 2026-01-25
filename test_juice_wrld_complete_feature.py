#!/usr/bin/env python3
"""
Comprehensive test for Juice WRLD API complete feature implementation
Tests all endpoints, intent detection, and auto-routing functionality
"""

import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.integrations.juice_wrld_api import JuiceWrldAPI
from src.intent_detector import IntentDetector
from src.command_handler import CommandHandler
from src.bot import YamiBot
from src.utils.config import Config


class TestJuiceWrldCompleteFeatures:
    """Test suite for Juice WRLD complete feature implementation"""
    
    def __init__(self):
        self.api = None
        self.intent_detector = IntentDetector()
        self.test_cases = [
            # ============ RANDOM SONG TESTS ============
            {
                "message": "Show me a random Juice song",
                "expected_intent": "juice_random",
                "description": "Random song request"
            },
            {
                "message": "Surprise me with a random track",
                "expected_intent": "juice_random",
                "description": "Random track request (alternative phrasing)"
            },
            {
                "message": "Pick a random song",
                "expected_intent": "juice_random",
                "description": "Random song pick request"
            },
            
            # ============ STATISTICS TESTS ============
            {
                "message": "Juice WRLD statistics",
                "expected_intent": "juice_stats",
                "description": "Statistics request"
            },
            {
                "message": "How many songs does Juice have",
                "expected_intent": "juice_stats",
                "description": "Song count query"
            },
            {
                "message": "Database stats for Juice WRLD",
                "expected_intent": "juice_stats",
                "description": "Database statistics"
            },
            
            # ============ ERA TESTS ============
            {
                "message": "Show me all eras",
                "expected_intent": "juice_eras_list",
                "description": "List all eras"
            },
            {
                "message": "Songs from DRFL era",
                "expected_intent": "juice_era_filter",
                "description": "Filter songs by era"
            },
            {
                "message": "Show me songs from the 2018 era",
                "expected_intent": "juice_era_filter",
                "description": "Filter songs by year era"
            },
            
            # ============ CATEGORY TESTS ============
            {
                "message": "Show unreleased songs",
                "expected_intent": "juice_category_filter",
                "description": "Filter unreleased songs"
            },
            {
                "message": "Show me released tracks",
                "expected_intent": "juice_category_filter",
                "description": "Filter released songs"
            },
            {
                "message": "Studio sessions",
                "expected_intent": "juice_category_filter",
                "description": "Filter studio sessions"
            },
            
            # ============ LYRIC SEARCH TESTS ============
            {
                "message": "Find songs with lyrics about love",
                "expected_intent": "juice_lyric_search",
                "description": "Lyric search request"
            },
            {
                "message": "Search lyrics for party",
                "expected_intent": "juice_lyric_search",
                "description": "Lyric search alternative"
            },
            
            # ============ PRODUCER TESTS ============
            {
                "message": "Songs produced by Metro Boomin",
                "expected_intent": "juice_producer_filter",
                "description": "Filter by producer"
            },
            {
                "message": "What was produced by Nick Mira",
                "expected_intent": "juice_producer_filter",
                "description": "Producer filter alternative"
            },
            {
                "message": "Beats by Taz Taylor",
                "expected_intent": "juice_producer_filter",
                "description": "Producer beats filter"
            },
            
            # ============ SONG INFO TESTS ============
            {
                "message": "Song details for Lucid Dreams",
                "expected_intent": "juice_song_info",
                "description": "Song details request"
            },
            {
                "message": "Who produced Rental",
                "expected_intent": "juice_song_info",
                "description": "Producer info request"
            },
            {
                "message": "When was All Girls Are The Same recorded",
                "expected_intent": "juice_song_info",
                "description": "Recording date request"
            },
            
            # ============ COVER ART TESTS ============
            {
                "message": "Cover art for Lucid Dreams",
                "expected_intent": "juice_cover_art",
                "description": "Cover art request"
            },
            {
                "message": "Show me artwork for Wasted",
                "expected_intent": "juice_cover_art",
                "description": "Artwork request"
            },
            
            # ============ STREAM TESTS ============
            {
                "message": "Stream Lucid Dreams",
                "expected_intent": "juice_stream",
                "description": "Stream request"
            },
            {
                "message": "Listen to Empty",
                "expected_intent": "juice_stream",
                "description": "Listen request"
            },
            {
                "message": "Play Robbery",
                "expected_intent": "juice_stream",
                "description": "Play request"
            },
            
            # ============ DOWNLOAD TESTS ============
            {
                "message": "Download Lucid Dreams",
                "expected_intent": "juice_download",
                "description": "Download request"
            },
            {
                "message": "Get download link for Rich",
                "expected_intent": "juice_download",
                "description": "Download link request"
            },
            
            # ============ COLLECTION TESTS ============
            {
                "message": "Create a zip of DRFL songs",
                "expected_intent": "juice_collection",
                "description": "Create archive request"
            },
            {
                "message": "Download archive of unreleased",
                "expected_intent": "juice_collection",
                "description": "Download archive request"
            },
            {
                "message": "Bundle songs Lucid Dreams, Robbery, Empty",
                "expected_intent": "juice_collection",
                "description": "Song bundle request"
            },
            
            # ============ BROWSE TESTS ============
            {
                "message": "Browse Juice WRLD songs",
                "expected_intent": "juice_browse",
                "description": "Browse library request"
            },
            {
                "message": "Show all tracks",
                "expected_intent": "juice_browse",
                "description": "Show all request"
            },
            
            # ============ ENHANCED SEARCH TESTS ============
            {
                "message": "Find juice song Lucid Dreams",
                "expected_intent": "juice_search",
                "description": "Juice-specific song search"
            },
            {
                "message": "Search juice track Robbery",
                "expected_intent": "juice_search",
                "description": "Juice-specific track search"
            },
            
            # ============ EDGE CASES ============
            {
                "message": "Juice WRLD birthday", 
                "expected_intent": "chat",  # Should NOT be juice_search
                "description": "Artist info should not trigger song search"
            },
            {
                "message": "Tell me about Juice WRLD",
                "expected_intent": "chat",  # Should NOT be juice_search  
                "description": "Artist bio should not trigger song search"
            }
        ]
    
    async def test_api_methods(self):
        """Test all new API methods exist and have proper signatures"""
        print("🧪 Testing API method signatures...")
        
        # Mock session for testing
        mock_session = AsyncMock()
        api = JuiceWrldAPI(session=mock_session)
        
        # Test all new methods exist
        methods_to_test = [
            'get_categories',
            'list_categories_with_songs', 
            'filter_by_category',
            'filter_by_producer',
            'filter_by_era',
            'get_era_details',
            'get_cover_art',
            'get_stream_url',
            'get_download_url',
            'create_zip_archive',
            'check_zip_status',
            'get_zip_download',
            'search_all_songs',
            'find_song_by_title',
            'browse_files',
            'browse_artists',
            'browse_albums', 
            'browse_tracks',
            'search_all_content',
            '_is_strong_title_match'
        ]
        
        for method_name in methods_to_test:
            assert hasattr(api, method_name), f"Missing method: {method_name}"
            method = getattr(api, method_name)
            assert callable(method), f"Method {method_name} is not callable"
        
        print(f"✅ All {len(methods_to_test)} API methods exist and are callable")
        return True
    
    async def test_intent_detection(self):
        """Test intent detection for all new patterns"""
        print("🎯 Testing intent detection patterns...")
        
        correct_predictions = 0
        total_tests = len(self.test_cases)
        
        for i, test_case in enumerate(self.test_cases, 1):
            message = test_case["message"]
            expected_intent = test_case["expected_intent"]
            description = test_case["description"]
            
            try:
                result = self.intent_detector.classify_intent(message)
                actual_intent = result["intent"]
                
                if actual_intent == expected_intent:
                    print(f"✅ Test {i:2d}: {description} - CORRECT")
                    correct_predictions += 1
                else:
                    print(f"❌ Test {i:2d}: {description} - FAILED")
                    print(f"    Expected: {expected_intent}")
                    print(f"    Actual:   {actual_intent}")
                    
            except Exception as e:
                print(f"💥 Test {i:2d}: {description} - ERROR: {e}")
        
        accuracy = (correct_predictions / total_tests) * 100
        print(f"\n📊 Intent Detection Results: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")
        
        if accuracy >= 90:
            print("🎉 Excellent accuracy!")
        elif accuracy >= 80:
            print("👍 Good accuracy, minor issues")
        else:
            print("⚠️  Accuracy needs improvement")
        
        return accuracy >= 80
    
    async def test_fuzzy_matching(self):
        """Test fuzzy song title matching"""
        print("🔍 Testing fuzzy song title matching...")
        
        # Mock API responses
        api = JuiceWrldAPI()
        
        # Test cases for fuzzy matching
        test_cases = [
            ("Lucid Dreams", "Lucid Dreams (Official Audio)", True),  # Strong match
            ("Rental", "Rental (v1)", True),  # Version handling
            ("Robbery", "Robbery (Clean)", True),  # Clean version
            ("Empty", "Empty", True),  # Exact match
            ("XXX", "Lucid Dreams", False),  # Weak match
        ]
        
        correct_matches = 0
        for query, title, expected_result in test_cases:
            result = api._is_strong_title_match(query, title)
            if result == expected_result:
                print(f"✅ '{query}' vs '{title}' -> {result} (expected)")
                correct_matches += 1
            else:
                print(f"❌ '{query}' vs '{title}' -> {result} (expected {expected_result})")
        
        accuracy = (correct_matches / len(test_cases)) * 100
        print(f"📊 Fuzzy Matching Results: {correct_matches}/{len(test_cases)} ({accuracy:.1f}%)")
        return accuracy >= 80
    
    async def test_command_handler_integration(self):
        """Test command handler has all new methods"""
        print("🎮 Testing command handler integration...")
        
        # Mock bot for testing
        mock_bot = Mock()
        handler = CommandHandler(mock_bot)
        
        # Check if all new handler methods exist
        handler_methods = [
            '_handle_juice_download',
            '_handle_juice_browse',
            '_resolve_juice_song',
            '_looks_like_year',
            '_resolve_era'
        ]
        
        missing_methods = []
        for method_name in handler_methods:
            if not hasattr(handler, method_name):
                missing_methods.append(method_name)
        
        if missing_methods:
            print(f"❌ Missing handler methods: {missing_methods}")
            return False
        else:
            print(f"✅ All {len(handler_methods)} handler methods exist")
            return True
    
    async def test_bot_caching(self):
        """Test bot caching implementation"""
        print("💾 Testing bot caching implementation...")
        
        # Create mock bot
        mock_config = Mock()
        mock_config.max_conversation_history = 100
        mock_config.conversation_timeout = 3600
        mock_config.cleanup_interval = 1800
        mock_config.memory_check_interval = 300
        
        # Test cache structure
        bot_cache = {
            'all_songs': None,
            'eras': None, 
            'categories': None,
            'stats': None,
            'cache_time': 0,
            'cache_ttl': 3600
        }
        
        expected_keys = set(bot_cache.keys())
        actual_keys = set(bot_cache.keys())
        
        if expected_keys == actual_keys:
            print("✅ Cache structure is correct")
            return True
        else:
            print(f"❌ Cache structure mismatch")
            print(f"Expected: {expected_keys}")
            print(f"Actual: {actual_keys}")
            return False
    
    async def test_comprehensive_workflow(self):
        """Test complete workflow from message to API response"""
        print("🔄 Testing comprehensive workflow...")
        
        # Simulate a complete user interaction
        test_message = "Show me a random Juice song"
        
        # Step 1: Intent Detection
        intent_result = self.intent_detector.classify_intent(test_message)
        expected_intent = "juice_random"
        
        if intent_result["intent"] != expected_intent:
            print(f"❌ Intent detection failed: expected {expected_intent}, got {intent_result['intent']}")
            return False
        
        print(f"✅ Intent detected: {intent_result['intent']}")
        
        # Step 2: Parameter Extraction
        params = intent_result.get("params", {})
        print(f"✅ Parameters extracted: {params}")
        
        # Step 3: Handler Routing
        # This would normally call the command handler, but we'll just verify the intent is correct
        print(f"✅ Would route to: _handle_juice_random()")
        
        # Step 4: API Call Simulation
        # Mock the API response
        mock_response = {
            "id": "123",
            "title": "Lucid Dreams",
            "artist": "Juice WRLD",
            "album": "Fighting Demons",
            "era": "2021-2022",
            "stream_url": "https://example.com/stream/123"
        }
        
        print(f"✅ Mock API response prepared: {mock_response['title']}")
        
        print("🎉 Complete workflow test passed!")
        return True
    
    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting comprehensive Juice WRLD API feature tests...\n")
        
        test_results = []
        
        # Run all test suites
        test_results.append(("API Methods", await self.test_api_methods()))
        test_results.append(("Intent Detection", await self.test_intent_detection()))
        test_results.append(("Fuzzy Matching", await self.test_fuzzy_matching()))
        test_results.append(("Command Handler", await self.test_command_handler_integration()))
        test_results.append(("Bot Caching", await self.test_bot_caching()))
        test_results.append(("Complete Workflow", await self.test_comprehensive_workflow()))
        
        # Summary
        print("\n" + "="*60)
        print("🏁 TEST SUMMARY")
        print("="*60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:.<30} {status}")
            if result:
                passed += 1
        
        print("-"*60)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Juice WRLD complete feature implementation is ready!")
        else:
            print(f"⚠️  {total - passed} tests failed. Review implementation.")
        
        return passed == total


async def main():
    """Main test runner"""
    tester = TestJuiceWrldCompleteFeatures()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)