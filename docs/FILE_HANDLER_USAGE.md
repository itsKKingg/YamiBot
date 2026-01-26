# File Handler Usage Guide

## Overview

The File Handler system provides intelligent file detection, download, and embedding for Discord responses. It automatically handles file type detection, size checking, caching, and provides fallback to streaming links for files that exceed Discord's size limits.

## Features

- **Automatic File Type Detection**: Identifies audio, image, and video files from URLs
- **Size-Based Routing**: Checks file sizes and decides whether to embed or link
- **Smart Caching**: Downloads and caches files locally to avoid repeated downloads
- **Discord Integration**: Creates proper Discord embeds and attachments
- **Graceful Fallback**: Provides streaming/download links for files that are too large
- **Error Handling**: Handles network timeouts, 404s, and corrupted downloads

## Discord File Size Limits

The handler respects Discord's file size limits:
- **Audio**: 8MB max for embeds
- **Images**: 8MB max for embeds  
- **Videos**: 100MB max for embeds

## Basic Usage

### High-Level API (Recommended)

The simplest way to use the file handler is through the high-level `prepare_file_for_discord()` function:

```python
from src.file_handler import file_handler

# Prepare a file for Discord
result = await file_handler.prepare_file_for_discord(
    url="https://example.com/song.mp3",
    context="song preview"  # Optional context
)

# Check if file should be embedded
if result['should_embed'] and result['file_path']:
    # Send as Discord attachment
    file = discord.File(str(result['file_path']))
    await message.channel.send(file=file)
else:
    # Send as link with info
    await message.channel.send(result['info_text'])
```

### Using Music Formatter Helpers

For music responses, use the convenient helper functions:

```python
from src.formatting.music_formatter import (
    prepare_audio_file_for_discord,
    prepare_image_file_for_discord,
    get_file_info_text
)

# Prepare audio file
audio_file = await prepare_audio_file_for_discord(
    url="https://example.com/song.mp3",
    context="song preview"
)

if audio_file:
    await message.channel.send(file=audio_file)
else:
    # Get formatted info text as fallback
    info_text = await get_file_info_text("https://example.com/song.mp3")
    await message.channel.send(info_text)

# Prepare image file (e.g., album cover)
cover_image = await prepare_image_file_for_discord(
    url="https://example.com/cover.jpg",
    context="album cover"
)

if cover_image:
    embed = discord.Embed(title="Album Cover")
    embed.set_image(url="attachment://cover.jpg")
    await message.channel.send(embed=embed, file=cover_image)
```

## Low-Level API

For more control, you can use individual functions:

### 1. Detect File Type

```python
from src.file_handler import file_handler

# Detect file type from URL
category, extension = await file_handler.detect_file_type(
    "https://example.com/song.mp3"
)

print(f"Category: {category}")  # 'audio', 'image', 'video', or None
print(f"Extension: {extension}")  # '.mp3'
```

### 2. Check File Size

```python
# Check file size without downloading (HEAD request)
file_size = await file_handler.check_file_size(
    "https://example.com/song.mp3"
)

if file_size:
    size_mb = file_size / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")
```

### 3. Decide If Should Embed

```python
# Determine if file should be embedded based on size
should_embed = file_handler.should_embed('audio', file_size)

if should_embed:
    print("File will be embedded in Discord")
else:
    print("File too large, will provide link only")
```

### 4. Download File

```python
# Download file with caching
result = await file_handler.download_file(
    url="https://example.com/song.mp3",
    force_download=False  # Use cache if available
)

if result:
    file_path, category = result
    print(f"Downloaded to: {file_path}")
```

### 5. Extract Metadata

```python
from pathlib import Path

# Extract metadata from downloaded file
metadata = await file_handler.get_file_metadata(
    file_path=Path("./file_cache/abc123.mp3"),
    file_category='audio'
)

print(f"Filename: {metadata['filename']}")
print(f"Size: {metadata['size_mb']:.2f} MB")
```

## Integration Examples

### Example 1: Music Search with Audio Preview

```python
async def handle_music_search(message, query):
    # Search for song
    song = await music_api.search(query)
    
    if song and song.get('preview_url'):
        # Try to embed audio preview
        audio_file = await prepare_audio_file_for_discord(
            song['preview_url'],
            context="preview"
        )
        
        if audio_file:
            embed = discord.Embed(
                title=song['title'],
                description="🎵 Preview attached"
            )
            await message.channel.send(embed=embed, file=audio_file)
        else:
            # Fallback to link
            info = await get_file_info_text(song['preview_url'])
            embed = discord.Embed(
                title=song['title'],
                description=info
            )
            await message.channel.send(embed=embed)
```

### Example 2: Album Cover with Download Link

```python
async def show_album_cover(message, album_url):
    result = await file_handler.prepare_file_for_discord(
        album_url,
        context="album cover"
    )
    
    if result['should_embed'] and result['file_path']:
        # Embed the image
        file = discord.File(str(result['file_path']))
        embed = discord.Embed(title="Album Cover")
        embed.set_image(url=f"attachment://{result['file_path'].name}")
        await message.channel.send(embed=embed, file=file)
    else:
        # Too large, provide link
        await message.channel.send(result['info_text'])
```

### Example 3: Multiple Files

```python
async def send_song_with_cover(message, song_data):
    files = []
    
    # Try to embed audio
    if song_data.get('audio_url'):
        audio = await prepare_audio_file_for_discord(song_data['audio_url'])
        if audio:
            files.append(audio)
    
    # Try to embed cover
    if song_data.get('cover_url'):
        cover = await prepare_image_file_for_discord(song_data['cover_url'])
        if cover:
            files.append(cover)
    
    if files:
        await message.channel.send(
            content=f"**{song_data['title']}** by {song_data['artist']}",
            files=files
        )
    else:
        # Fallback to links
        info_text = f"**{song_data['title']}** by {song_data['artist']}\n"
        if song_data.get('audio_url'):
            info_text += await get_file_info_text(song_data['audio_url'])
        await message.channel.send(info_text)
```

## Cache Management

### Automatic Cleanup

The file handler automatically manages cache with TTL (Time To Live):

```python
from src.file_handler import file_handler

# Run cleanup to remove old files
removed_count = await file_handler.cleanup_old_files()
print(f"Removed {removed_count} old cached files")
```

### Cache Configuration

```python
from src.file_handler import FileHandler

# Create handler with custom cache settings
handler = FileHandler(
    cache_dir="./my_cache",      # Custom cache directory
    cache_ttl=86400              # 24 hours TTL
)
```

### Manual Cache Control

```python
# Force re-download (skip cache)
result = await file_handler.download_file(
    url="https://example.com/song.mp3",
    force_download=True
)

# Clean up specific files manually
import shutil
shutil.rmtree("./file_cache", ignore_errors=True)
```

## Error Handling

The file handler gracefully handles errors:

```python
result = await file_handler.prepare_file_for_discord(url)

if result['error']:
    print(f"Error: {result['error']}")
    # Still has fallback info_text with link
    await message.channel.send(result['info_text'])
```

Common error scenarios handled:
- Network timeouts
- 404/missing files
- Corrupted downloads
- Permission issues
- Unknown file types
- Files exceeding size limits

## Supported File Types

### Audio
- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- FLAC (.flac)
- OGG (.ogg)
- AAC (.aac)
- Opus (.opus)
- WMA (.wma)

### Images
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)
- SVG (.svg)

### Video
- MP4 (.mp4)
- WebM (.webm)
- MKV (.mkv)
- AVI (.avi)
- MOV (.mov)
- FLV (.flv)
- WMV (.wmv)

## Performance Considerations

1. **HEAD requests**: File size is checked using HEAD requests (fast, no download)
2. **Caching**: Files are cached locally to avoid repeated downloads
3. **TTL**: Old cached files are automatically removed after 24 hours (default)
4. **Concurrent downloads**: Uses asyncio for non-blocking downloads
5. **Chunk downloads**: Files are downloaded in chunks to manage memory

## Best Practices

1. **Always use high-level API** (`prepare_file_for_discord()`) unless you need fine control
2. **Check result['should_embed']** before trying to send as attachment
3. **Always have fallback** - use result['info_text'] if embedding fails
4. **Run periodic cleanup** - call `cleanup_old_files()` periodically (e.g., daily)
5. **Handle errors gracefully** - check result['error'] and provide user feedback
6. **Use context parameter** - helps with logging and debugging
7. **Respect Discord limits** - the handler does this automatically

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_file_handler.py -v
```

Test coverage includes:
- File type detection (10+ scenarios)
- Size detection with HEAD requests
- Embed vs link decisions
- Download functionality
- Caching behavior
- Cache cleanup
- Error handling
- Discord preparation

## Troubleshooting

### Files not embedding

1. Check file size - may exceed Discord limits
2. Check file type - may not be supported
3. Check logs for download errors
4. Try `force_download=True` to bypass cache

### Slow performance

1. Check network connection
2. Increase timeout: `file_handler.timeout = 60`
3. Check if cache is working properly
4. Run cache cleanup if disk is full

### Cache issues

1. Check cache directory permissions
2. Check available disk space
3. Manually clear cache if corrupted
4. Reduce cache TTL if disk space is limited

## Advanced Usage

### Custom File Handler Instance

```python
from src.file_handler import FileHandler

# Create custom instance
my_handler = FileHandler(
    cache_dir="./custom_cache",
    cache_ttl=3600  # 1 hour
)

# Use custom instance
result = await my_handler.prepare_file_for_discord(url)
```

### Adding Custom File Types

To add support for additional file types, modify the FileHandler class constants:

```python
# In file_handler.py
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.custom'}
AUDIO_MIMETYPES = {'audio/mpeg', 'audio/custom'}
```

### Integration with Background Tasks

```python
from discord.ext import tasks

@tasks.loop(hours=24)
async def cleanup_cache():
    """Clean up old cached files daily"""
    from src.file_handler import file_handler
    removed = await file_handler.cleanup_old_files()
    logger.info(f"Cache cleanup: removed {removed} files")

cleanup_cache.start()
```
