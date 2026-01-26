"""
Tests for FileHandler

Tests file type detection, size checking, downloading, caching, and Discord integration.
"""

import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.file_handler import FileHandler


@pytest.fixture
def file_handler():
    """Create a FileHandler instance with a temporary cache directory"""
    import tempfile
    cache_dir = tempfile.mkdtemp()
    handler = FileHandler(cache_dir=cache_dir, cache_ttl=3600)
    yield handler
    # Cleanup
    import shutil
    shutil.rmtree(cache_dir, ignore_errors=True)


class TestFileTypeDetection:
    """Test file type detection from URLs and headers"""
    
    @pytest.mark.asyncio
    async def test_detect_audio_from_extension(self, file_handler):
        """Test detecting audio file from URL extension"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'audio/mpeg'}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            category, ext = await file_handler.detect_file_type(url)
        
        assert category == 'audio'
        assert ext == '.mp3'
    
    @pytest.mark.asyncio
    async def test_detect_image_from_extension(self, file_handler):
        """Test detecting image file from URL extension"""
        url = "https://example.com/cover.jpg"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'image/jpeg'}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            category, ext = await file_handler.detect_file_type(url)
        
        assert category == 'image'
        assert ext == '.jpg'
    
    @pytest.mark.asyncio
    async def test_detect_video_from_extension(self, file_handler):
        """Test detecting video file from URL extension"""
        url = "https://example.com/video.mp4"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'video/mp4'}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            category, ext = await file_handler.detect_file_type(url)
        
        assert category == 'video'
        assert ext == '.mp4'
    
    @pytest.mark.asyncio
    async def test_detect_from_mime_type_when_extension_missing(self, file_handler):
        """Test detecting file type from MIME type when extension is missing"""
        url = "https://example.com/file"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'audio/mpeg'}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            category, ext = await file_handler.detect_file_type(url)
        
        assert category == 'audio'
    
    @pytest.mark.asyncio
    async def test_handle_mismatch_between_extension_and_mime(self, file_handler):
        """Test handling mismatch between file extension and MIME type"""
        url = "https://example.com/song.txt"  # Wrong extension
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'audio/mpeg'}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            category, ext = await file_handler.detect_file_type(url)
        
        # Should trust MIME type over extension
        assert category == 'audio'
    
    @pytest.mark.asyncio
    async def test_handle_unknown_file_type(self, file_handler):
        """Test handling unknown file type"""
        url = "https://example.com/document.pdf"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'application/pdf'}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            category, ext = await file_handler.detect_file_type(url)
        
        assert category is None  # Not a supported media type
        assert ext == '.pdf'
    
    @pytest.mark.asyncio
    async def test_handle_network_timeout_gracefully(self, file_handler):
        """Test graceful handling of network timeout"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.head.side_effect = asyncio.TimeoutError()
            
            category, ext = await file_handler.detect_file_type(url)
        
        # Should fallback to extension detection
        assert category == 'audio'
        assert ext == '.mp3'


class TestFileSizeDetection:
    """Test file size detection using HEAD requests"""
    
    @pytest.mark.asyncio
    async def test_check_file_size_success(self, file_handler):
        """Test successful file size check"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Length': '5242880'}  # 5MB
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            size = await file_handler.check_file_size(url)
        
        assert size == 5242880
    
    @pytest.mark.asyncio
    async def test_check_file_size_missing_header(self, file_handler):
        """Test handling missing Content-Length header"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_session.return_value.__aenter__.return_value.head.return_value.__aenter__.return_value = mock_response
            
            size = await file_handler.check_file_size(url)
        
        assert size is None
    
    @pytest.mark.asyncio
    async def test_check_file_size_timeout(self, file_handler):
        """Test handling timeout when checking file size"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.head.side_effect = asyncio.TimeoutError()
            
            size = await file_handler.check_file_size(url)
        
        assert size is None


class TestEmbedDecision:
    """Test logic for deciding whether to embed files"""
    
    def test_should_embed_small_audio(self, file_handler):
        """Test embedding decision for small audio file"""
        size = 5 * 1024 * 1024  # 5MB
        assert file_handler.should_embed('audio', size) is True
    
    def test_should_not_embed_large_audio(self, file_handler):
        """Test embedding decision for large audio file"""
        size = 10 * 1024 * 1024  # 10MB (over 8MB limit)
        assert file_handler.should_embed('audio', size) is False
    
    def test_should_embed_small_image(self, file_handler):
        """Test embedding decision for small image file"""
        size = 3 * 1024 * 1024  # 3MB
        assert file_handler.should_embed('image', size) is True
    
    def test_should_not_embed_large_image(self, file_handler):
        """Test embedding decision for large image file"""
        size = 15 * 1024 * 1024  # 15MB (over 8MB limit)
        assert file_handler.should_embed('image', size) is False
    
    def test_should_embed_small_video(self, file_handler):
        """Test embedding decision for small video file"""
        size = 50 * 1024 * 1024  # 50MB
        assert file_handler.should_embed('video', size) is True
    
    def test_should_not_embed_large_video(self, file_handler):
        """Test embedding decision for large video file"""
        size = 150 * 1024 * 1024  # 150MB (over 100MB limit)
        assert file_handler.should_embed('video', size) is False
    
    def test_should_not_embed_unknown_size(self, file_handler):
        """Test embedding decision for unknown file size"""
        assert file_handler.should_embed('audio', None) is False


class TestFileDownload:
    """Test file download and caching functionality"""
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, file_handler):
        """Test successful file download"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock HEAD request for detection
            mock_head_response = AsyncMock()
            mock_head_response.status = 200
            mock_head_response.headers = {'Content-Type': 'audio/mpeg'}
            
            # Mock GET request for download
            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.content.iter_chunked.return_value = [b'fake audio data']
            
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__.side_effect = [mock_head_response, mock_get_response]
            
            mock_session_instance = MagicMock()
            mock_session_instance.head.return_value = mock_context_manager
            mock_session_instance.get.return_value = mock_context_manager
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            result = await file_handler.download_file(url)
        
        assert result is not None
        file_path, category = result
        assert file_path.exists()
        assert category == 'audio'
    
    @pytest.mark.asyncio
    async def test_use_cached_file(self, file_handler):
        """Test using cached file instead of re-downloading"""
        url = "https://example.com/song.mp3"
        
        # Create a fake cached file
        cache_key = file_handler._get_cache_key(url)
        cached_file = file_handler._get_cached_file_path(cache_key, '.mp3')
        cached_file.write_bytes(b'cached audio data')
        
        with patch('aiohttp.ClientSession'):
            result = await file_handler.download_file(url)
        
        assert result is not None
        file_path, category = result
        assert file_path == cached_file
        assert category == 'audio'
    
    @pytest.mark.asyncio
    async def test_download_handles_404(self, file_handler):
        """Test handling 404 response"""
        url = "https://example.com/missing.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_head_response = AsyncMock()
            mock_head_response.status = 200
            mock_head_response.headers = {'Content-Type': 'audio/mpeg'}
            
            mock_get_response = AsyncMock()
            mock_get_response.status = 404
            
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__.side_effect = [mock_head_response, mock_get_response]
            
            mock_session_instance = MagicMock()
            mock_session_instance.head.return_value = mock_context_manager
            mock_session_instance.get.return_value = mock_context_manager
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            result = await file_handler.download_file(url)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_download_handles_timeout(self, file_handler):
        """Test handling timeout during download"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_head_response = AsyncMock()
            mock_head_response.status = 200
            mock_head_response.headers = {'Content-Type': 'audio/mpeg'}
            
            mock_session_instance = MagicMock()
            mock_session_instance.head.return_value.__aenter__.return_value = mock_head_response
            mock_session_instance.get.side_effect = asyncio.TimeoutError()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            result = await file_handler.download_file(url)
        
        assert result is None


class TestCacheCleanup:
    """Test cache cleanup functionality"""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, file_handler):
        """Test cleaning up old cached files"""
        # Create some fake cached files with old timestamps
        old_file1 = file_handler.cache_dir / "old_file1.mp3"
        old_file2 = file_handler.cache_dir / "old_file2.jpg"
        
        old_file1.write_bytes(b'old data 1')
        old_file2.write_bytes(b'old data 2')
        
        # Set their modification time to old
        import time
        old_time = time.time() - (file_handler.cache_ttl + 3600)  # Older than TTL
        os.utime(old_file1, (old_time, old_time))
        os.utime(old_file2, (old_time, old_time))
        
        # Create a new file
        new_file = file_handler.cache_dir / "new_file.mp3"
        new_file.write_bytes(b'new data')
        
        removed_count = await file_handler.cleanup_old_files()
        
        assert removed_count == 2
        assert not old_file1.exists()
        assert not old_file2.exists()
        assert new_file.exists()


class TestDiscordPreparation:
    """Test high-level Discord preparation function"""
    
    @pytest.mark.asyncio
    async def test_prepare_small_audio_for_embedding(self, file_handler):
        """Test preparing small audio file for embedding"""
        url = "https://example.com/song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock HEAD request
            mock_head_response = AsyncMock()
            mock_head_response.status = 200
            mock_head_response.headers = {
                'Content-Type': 'audio/mpeg',
                'Content-Length': str(5 * 1024 * 1024)  # 5MB
            }
            
            # Mock GET request
            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.content.iter_chunked.return_value = [b'audio data']
            
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__.side_effect = [
                mock_head_response,
                mock_head_response,  # For size check
                mock_get_response
            ]
            
            mock_session_instance = MagicMock()
            mock_session_instance.head.return_value = mock_context_manager
            mock_session_instance.get.return_value = mock_context_manager
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            result = await file_handler.prepare_file_for_discord(url, context="song preview")
        
        assert result['should_embed'] is True
        assert result['file_category'] == 'audio'
        assert result['file_path'] is not None
        assert result['file_path'].exists()
        assert result['error'] is None
    
    @pytest.mark.asyncio
    async def test_prepare_large_audio_for_link_only(self, file_handler):
        """Test preparing large audio file (link only)"""
        url = "https://example.com/large_song.mp3"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_head_response = AsyncMock()
            mock_head_response.status = 200
            mock_head_response.headers = {
                'Content-Type': 'audio/mpeg',
                'Content-Length': str(20 * 1024 * 1024)  # 20MB (over 8MB limit)
            }
            
            mock_session_instance = MagicMock()
            mock_session_instance.head.return_value.__aenter__.return_value = mock_head_response
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            result = await file_handler.prepare_file_for_discord(url)
        
        assert result['should_embed'] is False
        assert result['file_category'] == 'audio'
        assert result['file_path'] is None
        assert 'exceeds Discord' in result['info_text']
    
    @pytest.mark.asyncio
    async def test_prepare_unknown_file_type(self, file_handler):
        """Test preparing unknown file type"""
        url = "https://example.com/document.pdf"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_head_response = AsyncMock()
            mock_head_response.status = 200
            mock_head_response.headers = {'Content-Type': 'application/pdf'}
            
            mock_session_instance = MagicMock()
            mock_session_instance.head.return_value.__aenter__.return_value = mock_head_response
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            result = await file_handler.prepare_file_for_discord(url)
        
        assert result['should_embed'] is False
        assert result['file_category'] is None
        assert result['error'] == "Unable to determine file type"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
