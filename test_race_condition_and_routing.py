#!/usr/bin/env python3
"""
Comprehensive test script for race condition fix, Gemini default API, and API routing debugging.

Tests:
1. Race condition prevention (duplicate message processing)
2. Gemini as default API for chat
3. API routing logic for different intents
4. Debug logging functionality
5. Intent detection accuracy
"""

import asyncio
import sys
import os
import time
from unittest.mock import Mock, AsyncMock, patch
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.intent_detector import IntentDetector
from src.model_router import ModelRouter
from src.fallback_manager import FallbackManager
from src.model_registry import ModelRegistry
from src.utils.config import Config

# Configure logging to see debug output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockProvider:
    def __init__(self, name, model="default"):
        self.name = name
        self.model = model
        self.available = True
    
    async def check_rate_limit(self):
        return self.available
    
    async def query(self, prompt, **kwargs):
        return f"Response from {self.name}", {"provider": self.name, "tokens": 100}

class TestResults:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_details = []
    
    def add_pass(self, test_name, details=""):
        self.tests_passed += 1
        self.test_details.append(f"✅ PASS: {test_name} - {details}")
        print(f"✅ PASS: {test_name} - {details}")
    
    def add_fail(self, test_name, details=""):
        self.tests_failed += 1
        self.test_details.append(f"❌ FAIL: {test_name} - {details}")
        print(f"❌ FAIL: {test_name} - {details}")
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📊 Success Rate: {self.tests_passed/(self.tests_passed+self.tests_failed)*100:.1f}%")
        print(f"{'='*60}")
        for detail in self.test_details:
            print(detail)

async def test_race_condition_prevention():
    """Test that duplicate messages are properly prevented"""
    results = TestResults()
    
    print("\n🧪 Testing Race Condition Prevention...")
    
    # Import CommandHandler
    from src.command_handler import CommandHandler
    
    # Create mock bot
    mock_bot = Mock()
    mock_bot.conversation_manager = Mock()
    
    # Create CommandHandler
    handler = CommandHandler(mock_bot)
    
    # Create mock message
    mock_message = Mock()
    mock_message.id = 12345
    mock_message.author.id = 67890
    mock_message.attachments = []
    
    # Test 1: First processing should work
    print("  Testing first message processing...")
    try:
        # Mock the intent detector to return chat (so it returns False)
        with patch.object(handler.intent_detector, 'classify_intent') as mock_classify:
            mock_classify.return_value = {"intent": "chat", "params": {}, "api_source": "llm"}
            
            result = await handler.handle_message(mock_message)
            if result == False:  # chat intent returns False
                results.add_pass("First message processing", "Message processed correctly (returned False for chat)")
            else:
                results.add_fail("First message processing", f"Expected False, got {result}")
    except Exception as e:
        results.add_fail("First message processing", f"Exception: {e}")
    
    # Test 2: Duplicate should be prevented
    print("  Testing duplicate message prevention...")
    try:
        result = await handler.handle_message(mock_message)
        if result == True:  # Should return True because it's already processed
            results.add_pass("Duplicate message prevention", "Duplicate correctly detected and skipped")
        else:
            results.add_fail("Duplicate message prevention", f"Expected True for duplicate, got {result}")
    except Exception as e:
        results.add_fail("Duplicate message prevention", f"Exception: {e}")
    
    # Test 3: Different message ID should work
    print("  Testing different message ID...")
    try:
        mock_message2 = Mock()
        mock_message2.id = 54321
        mock_message2.author.id = 67890
        mock_message2.attachments = []
        
        with patch.object(handler.intent_detector, 'classify_intent') as mock_classify:
            mock_classify.return_value = {"intent": "chat", "params": {}, "api_source": "llm"}
            
            result = await handler.handle_message(mock_message2)
            if result == False:  # chat intent returns False
                results.add_pass("Different message ID processing", "Different message processed correctly")
            else:
                results.add_fail("Different message ID processing", f"Expected False, got {result}")
    except Exception as e:
        results.add_fail("Different message ID processing", f"Exception: {e}")
    
    return results

async def test_gemini_default_api():
    """Test that Gemini is set as the default API"""
    results = TestResults()
    
    print("\n🧪 Testing Gemini as Default API...")
    
    # Test Model Router
    model_registry = ModelRegistry()
    model_router = ModelRouter(model_registry)
    
    # Test 1: Chat intent should default to Gemini
    print("  Testing chat intent default...")
    try:
        provider, model, reason = model_router.select_model("chat")
        if provider == "google" and "gemini" in model:
            results.add_pass("Chat intent default", f"Uses {provider}/{model} (reason: {reason})")
        else:
            results.add_fail("Chat intent default", f"Expected google/gemini, got {provider}/{model}")
    except Exception as e:
        results.add_fail("Chat intent default", f"Exception: {e}")
    
    # Test 2: General intent should use Gemini
    print("  Testing general intent default...")
    try:
        provider, model, reason = model_router.select_model("general")
        if provider == "google" and "gemini" in model:
            results.add_pass("General intent default", f"Uses {provider}/{model} (reason: {reason})")
        else:
            results.add_fail("General intent default", f"Expected google/gemini, got {provider}/{model}")
    except Exception as e:
        results.add_fail("General intent default", f"Exception: {e}")
    
    # Test 3: Fallback model should be Gemini
    print("  Testing emergency fallback...")
    try:
        provider, model, reason = model_router._get_fallback_model()
        if provider == "google" and "gemini" in model:
            results.add_pass("Emergency fallback", f"Uses {provider}/{model} (reason: {reason})")
        else:
            results.add_fail("Emergency fallback", f"Expected google/gemini, got {provider}/{model}")
    except Exception as e:
        results.add_fail("Emergency fallback", f"Exception: {e}")
    
    return results

async def test_api_routing_logic():
    """Test API routing for different intents"""
    results = TestResults()
    
    print("\n🧪 Testing API Routing Logic...")
    
    intent_detector = IntentDetector()
    
    # Test cases: (message, expected_intent, expected_api_source)
    test_cases = [
        ("find juice song lucid dreams", "juice_search", "juice_wrld"),
        ("search lyrics for be here", "music_lyrics", "genius"),
        ("search for latest AI news", "search", "llm"),
        ("who is juice wrld", "chat", "llm"),
        ("what is the meaning of life", "chat", "llm"),
        ("find track rental by juice", "juice_search", "juice_wrld"),
        ("soundcloud search electronic music", "music_search", "soundcloud"),
        ("clear my memory", "clear_memory", "unknown"),
        ("use claude for this", "model_switch", "unknown"),
    ]
    
    for i, (message, expected_intent, expected_api) in enumerate(test_cases, 1):
        print(f"  Test {i}: '{message[:30]}...'")
        try:
            result = intent_detector.classify_intent(message)
            actual_intent = result.get("intent", "unknown")
            actual_api = result.get("api_source", "unknown")
            
            intent_match = actual_intent == expected_intent
            api_match = actual_api == expected_api
            
            if intent_match and api_match:
                results.add_pass(f"Routing test {i}", f"Intent: {actual_intent}, API: {actual_api}")
            else:
                details = f"Expected: {expected_intent}/{expected_api}, Got: {actual_intent}/{actual_api}"
                results.add_fail(f"Routing test {i}", details)
                
        except Exception as e:
            results.add_fail(f"Routing test {i}", f"Exception: {e}")
    
    return results

async def test_debug_logging():
    """Test that debug logging is working properly"""
    results = TestResults()
    
    print("\n🧪 Testing Debug Logging...")
    
    # Test intent detector logging
    print("  Testing intent detector debug logs...")
    try:
        # Capture log output
        with patch('src.intent_detector.logger') as mock_logger:
            intent_detector = IntentDetector()
            result = intent_detector.classify_intent("find juice song lucid dreams")
            
            # Check if debug logs were called
            debug_calls = [call for call in mock_logger.debug.call_args_list if "Classifying intent" in str(call)]
            info_calls = [call for call in mock_logger.info.call_args_list if "Intent match" in str(call) or "Selected intent" in str(call)]
            
            if debug_calls and info_calls:
                results.add_pass("Intent detector logging", "Debug and info logs working")
            else:
                results.add_fail("Intent detector logging", "Missing debug/info logs")
                
    except Exception as e:
        results.add_fail("Intent detector logging", f"Exception: {e}")
    
    # Test model router logging
    print("  Testing model router debug logs...")
    try:
        model_registry = ModelRegistry()
        model_router = ModelRouter(model_registry)
        
        with patch('src.model_router.logger') as mock_logger:
            provider, model, reason = model_router.select_model("chat")
            
            # Check if logs were called
            info_calls = [call for call in mock_logger.info.call_args_list if "Selected" in str(call)]
            
            if info_calls:
                results.add_pass("Model router logging", "Selection logs working")
            else:
                results.add_fail("Model router logging", "Missing selection logs")
                
    except Exception as e:
        results.add_fail("Model router logging", f"Exception: {e}")
    
    return results

async def test_intent_classification_accuracy():
    """Test intent classification accuracy"""
    results = TestResults()
    
    print("\n🧪 Testing Intent Classification Accuracy...")
    
    intent_detector = IntentDetector()
    
    # Test Juice WRLD intent detection
    juice_tests = [
        "find juice song lucid dreams",
        "search juice track rental", 
        "juice lyrics for be here",
        "who produced lucid dreams",
        "random juice song"
    ]
    
    print("  Testing Juice WRLD intent detection...")
    for test_msg in juice_tests:
        try:
            result = intent_detector.classify_intent(test_msg)
            intent = result.get("intent", "")
            if intent.startswith("juice_") or intent == "smart_juice_query":
                results.add_pass(f"Juice WRLD intent", f"'{test_msg[:20]}...' → {intent}")
            else:
                results.add_fail(f"Juice WRLD intent", f"'{test_msg[:20]}...' → Expected juice_*, got {intent}")
        except Exception as e:
            results.add_fail(f"Juice WRLD intent", f"Exception for '{test_msg[:20]}...': {e}")
    
    # Test that artist info requests don't trigger juice_search
    print("  Testing artist info rejection...")
    artist_tests = [
        "up the birthday of xxxtentacion",
        "when was juice wrld born", 
        "tell me about juice wrld",
        "juice wrld birthday"
    ]
    
    for test_msg in artist_tests:
        try:
            result = intent_detector.classify_intent(test_msg)
            intent = result.get("intent", "")
            if intent != "juice_search":
                results.add_pass("Artist info rejection", f"'{test_msg[:20]}...' → {intent} (not juice_search)")
            else:
                results.add_fail("Artist info rejection", f"'{test_msg[:20]}...' → Incorrectly classified as juice_search")
        except Exception as e:
            results.add_fail("Artist info rejection", f"Exception for '{test_msg[:20]}...': {e}")
    
    return results

async def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive Test Suite")
    print("="*60)
    
    # Run all test suites
    test_suites = [
        ("Race Condition Prevention", test_race_condition_prevention),
        ("Gemini Default API", test_gemini_default_api), 
        ("API Routing Logic", test_api_routing_logic),
        ("Debug Logging", test_debug_logging),
        ("Intent Classification", test_intent_classification_accuracy),
    ]
    
    all_results = []
    
    for test_name, test_func in test_suites:
        print(f"\n🔬 Running {test_name} Tests...")
        try:
            result = await test_func()
            all_results.append(result)
        except Exception as e:
            print(f"❌ Critical error in {test_name}: {e}")
            # Create a failed result
            result = TestResults()
            result.add_fail(test_name, f"Critical error: {e}")
            all_results.append(result)
    
    # Print final summary
    print(f"\n{'='*60}")
    print(f"🎯 FINAL TEST RESULTS")
    print(f"{'='*60}")
    
    total_passed = sum(r.tests_passed for r in all_results)
    total_failed = sum(r.tests_failed for r in all_results)
    
    print(f"📊 Overall Results:")
    print(f"   ✅ Total Passed: {total_passed}")
    print(f"   ❌ Total Failed: {total_failed}")
    print(f"   📈 Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%")
    
    # Detailed results by category
    print(f"\n📋 Results by Category:")
    for i, (test_name, _) in enumerate(test_suites):
        result = all_results[i]
        print(f"   {test_name}: {result.tests_passed}✅/{result.tests_failed}❌")
    
    print(f"\n{'='*60}")
    
    # Save detailed results to file
    with open('/home/engine/project/test_results.log', 'w') as f:
        f.write("COMPREHENSIVE TEST RESULTS\n")
        f.write("="*60 + "\n\n")
        
        for i, (test_name, _) in enumerate(test_suites):
            result = all_results[i]
            f.write(f"{test_name.upper()}:\n")
            f.write("-" * 40 + "\n")
            for detail in result.test_details:
                f.write(detail + "\n")
            f.write("\n")
        
        f.write(f"\nFINAL SUMMARY:\n")
        f.write(f"Total Passed: {total_passed}\n")
        f.write(f"Total Failed: {total_failed}\n")
        f.write(f"Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%\n")
    
    print(f"📄 Detailed results saved to: /home/engine/project/test_results.log")
    
    return total_failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)