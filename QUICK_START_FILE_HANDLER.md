# File Handler Quick Start Guide

## 🚀 5-Minute Quick Start

### Basic Usage (Recommended)

```python
from src.file_handler import file_handler

# Prepare any file for Discord
result = await file_handler.prepare_file_for_discord(
    url="https://example.com/file.mp3",
    context="optional context"
)

# Embed if small, link if large
if result['should_embed'] and result['file_path']:
    file = discord.File(str(result['file_path']))
    await message.channel.send(file=file)
else:
    await message.channel.send(result['info_text'])
```

### Music-Specific Helpers

```python
from src.formatting.music_formatter import (
    prepare_audio_file_for_discord,
    prepare_image_file_for_discord,
    get_file_info_text
)

# Audio files
audio = await prepare_audio_file_for_discord(url)
if audio:
    await message.channel.send(file=audio)

# Images (cover art, etc.)
image = await prepare_image_file_for_discord(url)
if image:
    await message.channel.send(file=image)

# Just get formatted info text
info = await get_file_info_text(url)
await message.channel.send(info)
```

## 📋 What It Does

✅ **Detects** file types (audio, image, video)
✅ **Checks** file size (without downloading)
✅ **Embeds** small files in Discord
✅ **Links** large files (with info)
✅ **Caches** downloads (24h)
✅ **Handles** errors gracefully

## 🎯 Supported Files

- **Audio (8MB limit)**: MP3, WAV, M4A, FLAC, OGG, AAC, Opus, WMA
- **Images (8MB limit)**: PNG, JPG, JPEG, GIF, WebP, BMP, SVG
- **Video (100MB limit)**: MP4, WebM, MKV, AVI, MOV, FLV, WMV

## 💡 Common Use Cases

### Use Case 1: Music Preview

```python
if song.get('preview_url'):
    audio = await prepare_audio_file_for_discord(
        song['preview_url'],
        context="song preview"
    )
    if audio:
        await message.channel.send(
            f"🎵 {song['title']} - Preview:",
            file=audio
        )
```

### Use Case 2: Album Cover

```python
if album.get('cover_url'):
    cover = await prepare_image_file_for_discord(
        album['cover_url'],
        context="album cover"
    )
    if cover:
        embed = discord.Embed(title=album['title'])
        embed.set_image(url="attachment://cover.jpg")
        await message.channel.send(embed=embed, file=cover)
```

### Use Case 3: Any URL

```python
# For any file URL
result = await file_handler.prepare_file_for_discord(url)

# Always works (embed or link)
if result['file_path']:
    await message.channel.send(file=discord.File(str(result['file_path'])))
else:
    await message.channel.send(result['info_text'])
```

## 🔧 Configuration

Default config works out of box. To customize:

```python
from src.file_handler import FileHandler

custom_handler = FileHandler(
    cache_dir="./my_cache",
    cache_ttl=3600  # 1 hour
)
```

## 🗑️ Cache Cleanup

Automatic cleanup (optional background task):

```python
from discord.ext import tasks
from src.file_handler import file_handler

@tasks.loop(hours=24)
async def cleanup_cache():
    removed = await file_handler.cleanup_old_files()
    logger.info(f"Removed {removed} old files")

cleanup_cache.start()
```

## 📊 What You Get Back

```python
result = await file_handler.prepare_file_for_discord(url)

# Result dictionary:
{
    'should_embed': True/False,        # Whether to embed
    'file_category': 'audio',          # 'audio', 'image', 'video', None
    'file_size': 5242880,              # Size in bytes (may be None)
    'file_path': Path('...'),          # Local path if downloaded
    'metadata': {...},                 # File metadata (size, resolution, etc.)
    'info_text': '🎵 **song.mp3**...', # Formatted Discord text
    'url': 'https://...',              # Original URL
    'error': None                      # Error message if failed
}
```

## ⚠️ Error Handling

Always provides a response:

```python
result = await file_handler.prepare_file_for_discord(url)

# Always safe to use
await message.channel.send(result['info_text'])  # Works even on errors

# Check for errors if needed
if result['error']:
    logger.warning(f"File handling error: {result['error']}")
```

## 📖 Full Documentation

- **Usage Guide**: `docs/FILE_HANDLER_USAGE.md`
- **Implementation**: `FILE_HANDLER_README.md`
- **Demo**: Run `python test_file_handler_demo.py`

## 🎉 That's It!

You're ready to use the file handler. Just import and use the high-level API:

```python
from src.file_handler import file_handler

result = await file_handler.prepare_file_for_discord(url)
# ✅ Done! It handles everything else.
```

---

**Quick Tips**:
- Use high-level API (`prepare_file_for_discord()`)
- Always check `result['should_embed']` before embedding
- Use `result['info_text']` as fallback
- Cache is automatic (24h TTL)
- All errors handled gracefully
- Supports 22+ file types
- Respects Discord size limits

Happy coding! 🚀
