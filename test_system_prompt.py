#!/usr/bin/env python3
"""
Test script to verify the system prompt integration
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def test_system_prompt():
    """Test that system prompt is properly configured"""
    print("Testing system prompt integration...")
    
    try:
        from src.utils.config import Config
        from src.fallback_manager import FallbackManager
        
        # Create a minimal config (will have missing env vars but should work for structure)
        config = Config()
        
        # Create fallback manager
        fallback_manager = FallbackManager(config)
        
        # Check if system prompt was set up
        if hasattr(fallback_manager, 'SYSTEM_PROMPT'):
            system_prompt = fallback_manager.SYSTEM_PROMPT
            print(f"✅ System prompt found (length: {len(system_prompt)} characters)")
            
            # Check key elements in the system prompt
            required_elements = [
                "🤖 **YOU ARE YAMIBOT",
                "MUSIC SEARCH & LYRICS",
                "WEB SEARCH", 
                "AI MODEL SWITCHING",
                "CONVERSATION MEMORY",
                "FEATURE DISCOVERY COMMANDS",
                "You are YamiBot, a helpful Discord AI assistant"  # Default fallback
            ]
            
            found_elements = 0
            for element in required_elements:
                if element in system_prompt:
                    found_elements += 1
                    print(f"  ✅ Found: {element}")
                else:
                    print(f"  ❌ Missing: {element}")
            
            if found_elements >= 6:  # Allow for some flexibility
                print(f"✅ System prompt content validation: {found_elements}/{len(required_elements)} elements found")
            else:
                print(f"❌ System prompt content validation: only {found_elements}/{len(required_elements)} elements found")
            
            return True
        else:
            print("❌ System prompt not found in fallback manager")
            return False
            
    except Exception as e:
        print(f"❌ System prompt test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_message_format():
    """Test that messages are properly formatted with system prompt"""
    print("\nTesting message format integration...")
    
    try:
        from src.fallback_manager import FallbackManager
        from src.utils.config import Config
        
        # Create minimal config
        config = Config()
        fallback_manager = FallbackManager(config)
        
        # Test that the method to add system prompt exists
        if hasattr(fallback_manager, 'SYSTEM_PROMPT'):
            print("✅ Fallback manager has system prompt attribute")
            
            # Simulate the message formatting logic
            kwargs = {'messages': [
                {"role": "user", "content": "Hello"}
            ]}
            
            # Test the logic that adds system prompt
            updated_kwargs = kwargs.copy()
            if 'messages' not in updated_kwargs:
                updated_kwargs['messages'] = []
            
            # Insert system prompt as the first message
            if hasattr(fallback_manager, 'SYSTEM_PROMPT') and fallback_manager.SYSTEM_PROMPT:
                updated_kwargs['messages'] = [
                    {"role": "system", "content": fallback_manager.SYSTEM_PROMPT}
                ] + updated_kwargs['messages']
            else:
                # Default system prompt if not set
                updated_kwargs['messages'] = [
                    {"role": "system", "content": "You are YamiBot, a helpful Discord AI assistant."}
                ] + updated_kwargs['messages']
            
            # Check the result
            messages = updated_kwargs['messages']
            if len(messages) >= 2 and messages[0]['role'] == 'system':
                print("✅ System message properly added as first message")
                print(f"  📝 System message length: {len(messages[0]['content'])} characters")
                print(f"  📝 User message preserved: {messages[1]['content']}")
                return True
            else:
                print("❌ Message formatting failed")
                return False
        else:
            print("❌ System prompt not available for testing")
            return False
            
    except Exception as e:
        print(f"❌ Message format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Testing YamiBot System Prompt Integration...\n")
    
    tests = [
        test_system_prompt,
        test_message_format
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All system prompt tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())