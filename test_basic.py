#!/usr/bin/env python3
"""
Basic test script to verify YamiBot functionality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test core imports
        from src.bot import YamiBot, create_bot
        from src.fallback_manager import FallbackManager
        from src.rate_limiter import RateLimiter
        from src.conversation_manager import ConversationManager
        from src.utils.config import Config
        from src.utils.logger import setup_logging
        from src.utils.cache import cache
        
        print("✅ Core imports successful")
        
        # Test provider imports
        from src.providers.base import BaseProvider
        from src.providers.cerebras_provider import CerebrasProvider
        from src.providers.sambanova_provider import SambanovaProvider
        from src.providers.groq_provider import GroqProvider
        from src.providers.mistral_provider import MistralProvider
        
        print("✅ Provider imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        # This will fail without .env file, but we can test the structure
        from src.utils.config import Config
        
        # Test that config class can be instantiated (will fail without env vars)
        try:
            config = Config()
            print("✅ Config loaded successfully")
            return True
        except ValueError as e:
            if "Missing required configuration" in str(e):
                print("⚠️  Config validation working (missing env vars - expected)")
                return True
            else:
                print(f"❌ Config error: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_cache():
    """Test caching functionality"""
    print("\nTesting cache...")
    
    try:
        from src.utils.cache import cache
        
        # Test cache operations
        cache.clear()
        cache.set("test_key", "test_value", ttl=60)
        value = cache.get("test_key")
        
        if value == "test_value":
            print("✅ Cache working correctly")
            cache.delete("test_key")
            return True
        else:
            print("❌ Cache test failed")
            return False
            
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

def test_rate_limiter():
    """Test rate limiter functionality"""
    print("\nTesting rate limiter...")
    
    try:
        from src.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        
        # Test basic functionality
        result = limiter.get_all_quotas()
        if isinstance(result, dict):
            print("✅ Rate limiter working correctly")
            return True
        else:
            print("❌ Rate limiter test failed")
            return False
            
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        return False

def test_conversation_manager():
    """Test conversation manager functionality"""
    print("\nTesting conversation manager...")
    
    try:
        from src.conversation_manager import ConversationManager
        
        manager = ConversationManager(max_history=5, context_timeout=60)
        
        # Test adding messages
        manager.add_message(channel_id=123, role="user", content="Hello")
        manager.add_message(channel_id=123, role="assistant", content="Hi there!")
        
        # Test getting history
        history = manager.get_conversation_history(channel_id=123)
        
        if len(history) == 2 and history[0]["content"] == "Hello":
            print("✅ Conversation manager working correctly")
            manager.clear_conversation(channel_id=123)
            return True
        else:
            print("❌ Conversation manager test failed")
            return False
            
    except Exception as e:
        print(f"❌ Conversation manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Running YamiBot basic tests...\n")
    
    tests = [
        test_imports,
        test_config,
        test_cache,
        test_rate_limiter,
        test_conversation_manager
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
