"""
File Handler for YamiBot

This module provides intelligent file detection, download, and embedding
for Discord responses. Handles audio, image, and video files with automatic
fallback to streaming links for files exceeding Discord's embed limits.
"""

import os
import re
import aiohttp
import asyncio
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .utils.logger import setup_logging

logger = setup_logging(__name__)


class FileHandler:
    """
    Handles file detection, download, caching, and embedding for Discord
    """
    
    # Discord file size limits (in bytes)
    DISCORD_AUDIO_LIMIT = 8 * 1024 * 1024      # 8MB
    DISCORD_IMAGE_LIMIT = 8 * 1024 * 1024      # 8MB
    DISCORD_VIDEO_LIMIT = 100 * 1024 * 1024    # 100MB
    
    # Supported file types
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.opus', '.wma'}
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
    VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.wmv'}
    
    # MIME type mappings
    AUDIO_MIMETYPES = {
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/wave',
        'audio/x-m4a', 'audio/m4a', 'audio/flac', 'audio/ogg', 'audio/aac',
        'audio/opus', 'audio/x-ms-wma'
    }
    IMAGE_MIMETYPES = {
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp',
        'image/bmp', 'image/svg+xml'
    }
    VIDEO_MIMETYPES = {
        'video/mp4', 'video/webm', 'video/x-matroska', 'video/quicktime',
        'video/x-msvideo', 'video/x-flv', 'video/x-ms-wmv'
    }
    
    def __init__(self, cache_dir: str = "./file_cache", cache_ttl: int = 86400):
        """
        Initialize file handler
        
        Args:
            cache_dir: Directory to store cached files
            cache_ttl: Time to live for cached files in seconds (default: 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = cache_ttl
        self.timeout = 30  # Request timeout in seconds
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"FileHandler initialized with cache_dir: {self.cache_dir}, ttl: {self.cache_ttl}s")
        
        # Initialize mimetypes
        mimetypes.init()
    
    def _get_cache_key(self, url: str) -> str:
        """
        Generate a cache key from URL
        
        Args:
            url: File URL
            
        Returns:
            MD5 hash of the URL
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cached_file_path(self, cache_key: str, extension: str = "") -> Path:
        """
        Get the path for a cached file
        
        Args:
            cache_key: Cache key (MD5 hash)
            extension: File extension (with dot)
            
        Returns:
            Path to cached file
        """
        filename = f"{cache_key}{extension}"
        return self.cache_dir / filename
    
    async def detect_file_type(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect file type from URL using extension and Content-Type header
        
        Args:
            url: File URL
            
        Returns:
            Tuple of (file_category, extension) where:
            - file_category: 'audio', 'image', 'video', or None
            - extension: File extension with dot (e.g., '.mp3')
        """
        logger.debug(f"Detecting file type for URL: {url}")
        
        # First try to detect from URL extension
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Extract extension from path
        ext = os.path.splitext(path)[1].lower()
        
        category_from_ext = None
        if ext in self.AUDIO_EXTENSIONS:
            category_from_ext = 'audio'
        elif ext in self.IMAGE_EXTENSIONS:
            category_from_ext = 'image'
        elif ext in self.VIDEO_EXTENSIONS:
            category_from_ext = 'video'
        
        # Try to verify with Content-Type header
        try:
            async with aiohttp.ClientSession() as session:
                async with asyncio.timeout(10):
                    async with session.head(url, allow_redirects=True) as response:
                        content_type = response.headers.get('Content-Type', '').lower().split(';')[0].strip()
                        
                        category_from_mime = None
                        if content_type in self.AUDIO_MIMETYPES:
                            category_from_mime = 'audio'
                        elif content_type in self.IMAGE_MIMETYPES:
                            category_from_mime = 'image'
                        elif content_type in self.VIDEO_MIMETYPES:
                            category_from_mime = 'video'
                        
                        # If we got both, verify they match
                        if category_from_ext and category_from_mime:
                            if category_from_ext == category_from_mime:
                                logger.info(f"✅ File type detected: {category_from_ext} ({ext}, {content_type})")
                                return category_from_ext, ext
                            else:
                                logger.warning(
                                    f"⚠️ File type mismatch! Extension suggests {category_from_ext} "
                                    f"but Content-Type suggests {category_from_mime}. Using Content-Type."
                                )
                                # Guess extension from MIME type
                                guessed_ext = mimetypes.guess_extension(content_type) or ext
                                return category_from_mime, guessed_ext
                        
                        # If only one detection method worked, use it
                        if category_from_mime:
                            guessed_ext = mimetypes.guess_extension(content_type) or ext or ''
                            logger.info(f"✅ File type detected from MIME: {category_from_mime} ({content_type})")
                            return category_from_mime, guessed_ext
                        
                        if category_from_ext:
                            logger.info(f"✅ File type detected from extension: {category_from_ext} ({ext})")
                            return category_from_ext, ext
                        
                        logger.warning(f"⚠️ Unknown file type: extension={ext}, content-type={content_type}")
                        return None, ext
        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Timeout detecting file type from headers, using extension only")
            return category_from_ext, ext
        except Exception as e:
            logger.warning(f"⚠️ Error detecting file type from headers: {e}, using extension only")
            return category_from_ext, ext
    
    async def check_file_size(self, url: str) -> Optional[int]:
        """
        Check file size using HEAD request without downloading
        
        Args:
            url: File URL
            
        Returns:
            File size in bytes, or None if unable to determine
        """
        logger.debug(f"Checking file size for: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with asyncio.timeout(10):
                    async with session.head(url, allow_redirects=True) as response:
                        content_length = response.headers.get('Content-Length')
                        
                        if content_length:
                            size = int(content_length)
                            size_mb = size / (1024 * 1024)
                            logger.info(f"📏 File size: {size} bytes ({size_mb:.2f} MB)")
                            return size
                        else:
                            logger.warning("⚠️ Content-Length header not found")
                            return None
        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Timeout checking file size")
            return None
        except Exception as e:
            logger.error(f"❌ Error checking file size: {e}")
            return None
    
    def should_embed(self, file_category: str, file_size: Optional[int]) -> bool:
        """
        Determine if file should be embedded based on type and size
        
        Args:
            file_category: 'audio', 'image', or 'video'
            file_size: File size in bytes (None means unknown)
            
        Returns:
            True if file should be embedded, False if should provide link only
        """
        if file_size is None:
            # Unknown size - be conservative, assume it's too large
            logger.warning(f"⚠️ Unknown file size, defaulting to link-only")
            return False
        
        if file_category == 'audio':
            should = file_size <= self.DISCORD_AUDIO_LIMIT
        elif file_category == 'image':
            should = file_size <= self.DISCORD_IMAGE_LIMIT
        elif file_category == 'video':
            should = file_size <= self.DISCORD_VIDEO_LIMIT
        else:
            should = False
        
        size_mb = file_size / (1024 * 1024)
        if should:
            logger.info(f"✅ File will be embedded ({size_mb:.2f} MB < limit)")
        else:
            logger.info(f"🔗 File too large for embedding ({size_mb:.2f} MB > limit), will provide link")
        
        return should
    
    async def download_file(
        self,
        url: str,
        force_download: bool = False
    ) -> Optional[Tuple[Path, str]]:
        """
        Download file with caching support
        
        Args:
            url: File URL to download
            force_download: If True, skip cache and re-download
            
        Returns:
            Tuple of (file_path, file_category) or None on error
        """
        logger.info(f"📥 Downloading file from: {url}")
        
        # Detect file type
        file_category, extension = await self.detect_file_type(url)
        
        if not file_category:
            logger.error(f"❌ Unable to determine file type for: {url}")
            return None
        
        # Generate cache key
        cache_key = self._get_cache_key(url)
        cached_file_path = self._get_cached_file_path(cache_key, extension)
        
        # Check if file exists in cache and is not expired
        if not force_download and cached_file_path.exists():
            # Check file age
            file_age = datetime.now() - datetime.fromtimestamp(cached_file_path.stat().st_mtime)
            
            if file_age < timedelta(seconds=self.cache_ttl):
                logger.info(f"✅ Using cached file: {cached_file_path}")
                return cached_file_path, file_category
            else:
                logger.info(f"🗑️ Cached file expired, re-downloading")
                cached_file_path.unlink()
        
        # Download file
        try:
            async with aiohttp.ClientSession() as session:
                async with asyncio.timeout(self.timeout):
                    async with session.get(url) as response:
                        if response.status != 200:
                            logger.error(f"❌ HTTP {response.status} when downloading: {url}")
                            return None
                        
                        # Download to temporary file first
                        temp_path = cached_file_path.with_suffix(cached_file_path.suffix + '.tmp')
                        
                        with open(temp_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        # Move to final location
                        temp_path.rename(cached_file_path)
                        
                        file_size = cached_file_path.stat().st_size
                        size_mb = file_size / (1024 * 1024)
                        logger.info(f"✅ Downloaded file: {cached_file_path} ({size_mb:.2f} MB)")
                        
                        return cached_file_path, file_category
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout downloading file from: {url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error downloading file: {e}")
            return None
        except IOError as e:
            logger.error(f"❌ File I/O error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading file: {e}")
            return None
    
    async def get_file_metadata(self, file_path: Path, file_category: str) -> Dict:
        """
        Extract metadata from downloaded file
        
        Args:
            file_path: Path to file
            file_category: 'audio', 'image', or 'video'
            
        Returns:
            Dictionary with metadata
        """
        metadata = {
            'filename': file_path.name,
            'size': file_path.stat().st_size,
            'size_mb': file_path.stat().st_size / (1024 * 1024),
            'extension': file_path.suffix,
            'category': file_category
        }
        
        # Try to extract additional metadata based on category
        # Note: This would require additional libraries like mutagen (audio), PIL (images), or ffprobe (video)
        # For now, we'll just log that metadata extraction would happen here
        
        if file_category == 'audio':
            # TODO: Use mutagen or similar to extract:
            # - duration
            # - bitrate
            # - artist/title tags
            logger.debug(f"Audio metadata extraction not yet implemented")
        
        elif file_category == 'image':
            # TODO: Use PIL to extract:
            # - resolution (width x height)
            # - format details
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    metadata['width'] = img.width
                    metadata['height'] = img.height
                    metadata['resolution'] = f"{img.width}x{img.height}"
                    metadata['format'] = img.format
                    logger.debug(f"📸 Image metadata: {metadata['resolution']}, format: {metadata['format']}")
            except ImportError:
                logger.debug("PIL not available for image metadata extraction")
            except Exception as e:
                logger.warning(f"Could not extract image metadata: {e}")
        
        elif file_category == 'video':
            # TODO: Use ffprobe to extract:
            # - duration
            # - resolution
            # - codec
            # - bitrate
            logger.debug(f"Video metadata extraction not yet implemented")
        
        return metadata
    
    async def cleanup_old_files(self) -> int:
        """
        Remove cached files older than TTL
        
        Returns:
            Number of files removed
        """
        logger.info(f"🗑️ Cleaning up old cached files (TTL: {self.cache_ttl}s)")
        
        removed_count = 0
        cutoff_time = datetime.now() - timedelta(seconds=self.cache_ttl)
        
        try:
            for file_path in self.cache_dir.glob('*'):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            removed_count += 1
                            logger.debug(f"🗑️ Removed old cached file: {file_path.name}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to remove {file_path.name}: {e}")
            
            logger.info(f"✅ Cleanup complete: removed {removed_count} files")
            return removed_count
        
        except Exception as e:
            logger.error(f"❌ Error during cache cleanup: {e}")
            return removed_count
    
    def format_file_info(
        self,
        url: str,
        file_category: str,
        file_size: Optional[int],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Format file information for Discord message
        
        Args:
            url: Original file URL
            file_category: 'audio', 'image', or 'video'
            file_size: File size in bytes
            metadata: Optional metadata dictionary
            
        Returns:
            Formatted string
        """
        lines = []
        
        # Emoji based on category
        emoji = {
            'audio': '🎵',
            'image': '🖼️',
            'video': '🎥'
        }.get(file_category, '📎')
        
        # File info header
        if metadata and metadata.get('filename'):
            lines.append(f"{emoji} **{metadata['filename']}**")
        else:
            filename = os.path.basename(urlparse(url).path) or 'file'
            lines.append(f"{emoji} **{filename}**")
        
        # File size
        if file_size:
            size_mb = file_size / (1024 * 1024)
            lines.append(f"📦 Size: {size_mb:.2f} MB")
        
        # Additional metadata
        if metadata:
            if metadata.get('resolution'):
                lines.append(f"📐 Resolution: {metadata['resolution']}")
            if metadata.get('duration'):
                lines.append(f"⏱️ Duration: {metadata['duration']}")
        
        # Link to original
        lines.append(f"\n🔗 [Download/Stream]({url})")
        
        return "\n".join(lines)
    
    async def prepare_file_for_discord(
        self,
        url: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Prepare a file for Discord response - detects, downloads if needed, and provides embed info
        
        This is the main high-level function to use for handling files in Discord responses.
        It will automatically:
        1. Detect file type and size
        2. Decide whether to embed or link
        3. Download file if it should be embedded
        4. Extract metadata
        5. Return all info needed for Discord response
        
        Args:
            url: File URL
            context: Optional context about the file (e.g., "album cover", "song preview")
            
        Returns:
            Dictionary with:
            - 'should_embed': bool - Whether file should be embedded
            - 'file_category': str - 'audio', 'image', 'video', or None
            - 'file_size': int - Size in bytes (may be None)
            - 'file_path': Path - Local path if downloaded (may be None)
            - 'metadata': dict - File metadata
            - 'info_text': str - Formatted text for Discord
            - 'url': str - Original URL
            - 'error': str - Error message if something failed
        """
        result = {
            'should_embed': False,
            'file_category': None,
            'file_size': None,
            'file_path': None,
            'metadata': {},
            'info_text': '',
            'url': url,
            'error': None,
            'context': context
        }
        
        logger.info(f"🎯 Preparing file for Discord: {url}" + (f" (context: {context})" if context else ""))
        
        try:
            # Step 1: Detect file type
            file_category, extension = await self.detect_file_type(url)
            result['file_category'] = file_category
            
            if not file_category:
                result['error'] = "Unable to determine file type"
                result['info_text'] = f"🔗 [View file]({url})"
                return result
            
            # Step 2: Check file size
            file_size = await self.check_file_size(url)
            result['file_size'] = file_size
            
            # Step 3: Decide if we should embed
            should_embed = self.should_embed(file_category, file_size)
            result['should_embed'] = should_embed
            
            # Step 4: Download if we should embed
            if should_embed:
                download_result = await self.download_file(url)
                
                if download_result:
                    file_path, detected_category = download_result
                    result['file_path'] = file_path
                    result['file_category'] = detected_category
                    
                    # Step 5: Extract metadata
                    metadata = await self.get_file_metadata(file_path, detected_category)
                    result['metadata'] = metadata
                    
                    # Format info text
                    result['info_text'] = self.format_file_info(url, detected_category, file_size, metadata)
                    
                    logger.info(f"✅ File ready for embedding: {file_path}")
                else:
                    # Download failed, fallback to link
                    logger.warning(f"⚠️ Download failed, falling back to link only")
                    result['should_embed'] = False
                    result['error'] = "Download failed"
                    result['info_text'] = self.format_file_info(url, file_category, file_size)
            else:
                # Too large or unable to determine size, provide link
                result['info_text'] = self.format_file_info(url, file_category, file_size)
                
                size_limit_mb = {
                    'audio': self.DISCORD_AUDIO_LIMIT / (1024 * 1024),
                    'image': self.DISCORD_IMAGE_LIMIT / (1024 * 1024),
                    'video': self.DISCORD_VIDEO_LIMIT / (1024 * 1024)
                }.get(file_category, 0)
                
                result['info_text'] += f"\n\n⚠️ File exceeds Discord's {size_limit_mb:.0f}MB limit for {file_category} files. Use the link above to stream/download."
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Error preparing file for Discord: {e}", exc_info=True)
            result['error'] = str(e)
            result['info_text'] = f"❌ Error handling file: {str(e)}\n🔗 [Direct link]({url})"
            return result


# Create global instance
file_handler = FileHandler()
