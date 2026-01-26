#!/usr/bin/env python3
"""
File Handler Demo Script

Demonstrates the file handler functionality with real-world scenarios.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.file_handler import file_handler
from src.formatting.music_formatter import (
    prepare_audio_file_for_discord,
    prepare_image_file_for_discord,
    get_file_info_text
)


async def test_file_type_detection():
    """Test file type detection from various URLs"""
    print("\n" + "=" * 60)
    print("TEST: File Type Detection")
    print("=" * 60)
    
    test_urls = [
        "https://example.com/song.mp3",
        "https://example.com/cover.jpg",
        "https://example.com/video.mp4",
        "https://example.com/audio.wav",
        "https://example.com/image.png",
        "https://example.com/file.unknown",
    ]
    
    for url in test_urls:
        try:
            category, ext = await file_handler.detect_file_type(url)
            print(f"✅ {url}")
            print(f"   Category: {category or 'Unknown'}, Extension: {ext}")
        except Exception as e:
            print(f"❌ {url}: {e}")
    
    print("\n✅ File type detection test completed\n")


async def test_size_detection():
    """Test file size detection using HEAD requests"""
    print("\n" + "=" * 60)
    print("TEST: File Size Detection")
    print("=" * 60)
    
    # These are example URLs - in real scenario, use actual file URLs
    test_urls = [
        "https://httpbin.org/image/jpeg",  # Public test endpoint
    ]
    
    for url in test_urls:
        try:
            size = await file_handler.check_file_size(url)
            if size:
                size_mb = size / (1024 * 1024)
                print(f"✅ {url}")
                print(f"   Size: {size} bytes ({size_mb:.2f} MB)")
            else:
                print(f"⚠️ {url}: Size unknown (no Content-Length header)")
        except Exception as e:
            print(f"❌ {url}: {e}")
    
    print("\n✅ File size detection test completed\n")


async def test_embed_decision():
    """Test embed vs link decision logic"""
    print("\n" + "=" * 60)
    print("TEST: Embed Decision Logic")
    print("=" * 60)
    
    test_cases = [
        ('audio', 5 * 1024 * 1024, True),      # 5MB audio - should embed
        ('audio', 10 * 1024 * 1024, False),    # 10MB audio - too large
        ('image', 3 * 1024 * 1024, True),      # 3MB image - should embed
        ('image', 15 * 1024 * 1024, False),    # 15MB image - too large
        ('video', 50 * 1024 * 1024, True),     # 50MB video - should embed
        ('video', 150 * 1024 * 1024, False),   # 150MB video - too large
        ('audio', None, False),                # Unknown size - conservative
    ]
    
    for category, size, expected in test_cases:
        result = file_handler.should_embed(category, size)
        status = "✅" if result == expected else "❌"
        size_str = f"{size / (1024 * 1024):.1f}MB" if size else "Unknown"
        print(f"{status} {category} ({size_str}): {'Embed' if result else 'Link'}")
    
    print("\n✅ Embed decision test completed\n")


async def test_file_metadata_extraction():
    """Test metadata extraction from files"""
    print("\n" + "=" * 60)
    print("TEST: File Metadata Extraction")
    print("=" * 60)
    
    # Create a test file
    test_file = file_handler.cache_dir / "test_image.png"
    test_file.parent.mkdir(exist_ok=True)
    
    # Create a small PNG image for testing
    try:
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_file)
        
        metadata = await file_handler.get_file_metadata(test_file, 'image')
        
        print(f"✅ Test file created: {test_file}")
        print(f"   Filename: {metadata['filename']}")
        print(f"   Size: {metadata['size_mb']:.2f} MB")
        print(f"   Category: {metadata['category']}")
        if metadata.get('resolution'):
            print(f"   Resolution: {metadata['resolution']}")
        
        # Cleanup
        test_file.unlink()
        print(f"   Cleaned up test file")
    
    except ImportError:
        print("⚠️ PIL not available, skipping image metadata test")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✅ File metadata extraction test completed\n")


async def test_cache_management():
    """Test cache management functionality"""
    print("\n" + "=" * 60)
    print("TEST: Cache Management")
    print("=" * 60)
    
    # Create some test cached files
    cache_dir = file_handler.cache_dir
    cache_dir.mkdir(exist_ok=True)
    
    test_files = [
        cache_dir / "test1.mp3",
        cache_dir / "test2.jpg",
        cache_dir / "test3.mp4",
    ]
    
    for f in test_files:
        f.write_bytes(b"test data")
        print(f"✅ Created test file: {f.name}")
    
    # Set old modification time
    import time
    old_time = time.time() - (file_handler.cache_ttl + 3600)
    for f in test_files[:2]:  # Make first 2 files old
        import os
        os.utime(f, (old_time, old_time))
        print(f"   Set {f.name} as old (will be cleaned)")
    
    # Run cleanup
    removed = await file_handler.cleanup_old_files()
    print(f"\n✅ Cleanup removed {removed} old files")
    
    # Check remaining files
    remaining = list(cache_dir.glob("test*.mp3")) + list(cache_dir.glob("test*.jpg")) + list(cache_dir.glob("test*.mp4"))
    print(f"✅ Remaining files: {len(remaining)}")
    
    # Cleanup all test files
    for f in remaining:
        f.unlink()
    
    print("\n✅ Cache management test completed\n")


async def test_format_file_info():
    """Test file info formatting"""
    print("\n" + "=" * 60)
    print("TEST: File Info Formatting")
    print("=" * 60)
    
    test_cases = [
        {
            'url': 'https://example.com/song.mp3',
            'category': 'audio',
            'size': 5 * 1024 * 1024,
            'metadata': {'filename': 'song.mp3'}
        },
        {
            'url': 'https://example.com/cover.jpg',
            'category': 'image',
            'size': 3 * 1024 * 1024,
            'metadata': {'filename': 'cover.jpg', 'resolution': '1920x1080'}
        },
    ]
    
    for test_case in test_cases:
        info = file_handler.format_file_info(
            test_case['url'],
            test_case['category'],
            test_case['size'],
            test_case['metadata']
        )
        print(f"✅ {test_case['category'].upper()} File Info:")
        print(info)
        print()
    
    print("✅ File info formatting test completed\n")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("FILE HANDLER DEMO - Testing All Features")
    print("=" * 60)
    
    try:
        # Run all tests
        await test_file_type_detection()
        await test_size_detection()
        await test_embed_decision()
        await test_file_metadata_extraction()
        await test_cache_management()
        await test_format_file_info()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"\nCache directory: {file_handler.cache_dir}")
        print(f"Cache TTL: {file_handler.cache_ttl} seconds ({file_handler.cache_ttl / 3600:.1f} hours)")
        print(f"\nThe file handler is ready for use in Discord responses!")
        print("\nSupported file types:")
        print(f"  Audio: {len(file_handler.AUDIO_EXTENSIONS)} types")
        print(f"  Image: {len(file_handler.IMAGE_EXTENSIONS)} types")
        print(f"  Video: {len(file_handler.VIDEO_EXTENSIONS)} types")
        print("\nDiscord size limits:")
        print(f"  Audio: {file_handler.DISCORD_AUDIO_LIMIT / (1024 * 1024):.0f}MB")
        print(f"  Image: {file_handler.DISCORD_IMAGE_LIMIT / (1024 * 1024):.0f}MB")
        print(f"  Video: {file_handler.DISCORD_VIDEO_LIMIT / (1024 * 1024):.0f}MB")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
