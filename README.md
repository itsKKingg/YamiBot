# 🤖 YamiBot - Advanced AI Discord Bot

A sophisticated Discord bot powered by **13 AI models across 5 providers**, with intelligent music search, natural language commands, and multi-API integration. Fully deployed and running on **Koyeb** with real-time uptime monitoring.

---

## ⚡ Quick Feature Overview

| | | |
|---|---|---|
| 🧠 **13 AI Models**<br/>Cerebras, SambaNova, Groq, Mistral, Google | 🎵 **Music APIs**<br/>Juice WRLD, Genius, SoundCloud | 💬 **Natural Language**<br/>Conversational commands (no slash required) |
| 🎯 **Smart Routing**<br/>Auto-selects best model for the task | 🎙️ **Audio Embed**<br/>SoundCloud players in Discord | 🔐 **Secure**<br/>Rate limiting, validation, permissions |

---

## 🧠 AI Models (13 Total)

### Cerebras
- **gpt-oss-120b** — Best for technical/code analysis

### SambaNova
- **gpt-oss-120b** — General purpose

### Groq (4 models)
- **mixtral-8x7b-32768** — Fast general purpose
- **llama-3.1-8b** — Ultra-fast, simple queries
- **llama-3.1-70b** — Coding & reasoning
- **llama-3.1-405b** — Complex reasoning & math

### Mistral (3 models)
- **mistral-small** — Fast & creative
- **mistral-medium** — Balanced general purpose
- **mistral-large-2411** — Advanced reasoning

### Google Gemini (3 models)
- **gemini-2.0-flash** — Multimodal, web search, fastest
- **gemini-1.5-pro** — Best reasoning & multimodal
- **gemini-1.5-flash** — Cost-effective multimodal

---

## 🎵 Music Integration (3 APIs)

### Juice WRLD API
- Search all Juice WRLD songs
- Get song details, features, release info
- Full discography browsing
- Featured artist lookup

### Genius API
- Lyrics for any song (non-Juice WRLD)
- Lyric annotations & explanations
- Artist information & biographies
- Music metadata

### SoundCloud API
- Track search with Discord embed player
- Artist profiles with playable tracks
- Playlist discovery with embeds
- **Direct playable audio in Discord** 🎙️

---

## 💬 Command Features

### Natural Language Commands (Primary)
Just mention the bot naturally:

```text
@bot search for Lucid Dreams
@bot show me the lyrics
@bot what does this lyric mean?
@bot embed this on SoundCloud
@bot Juice WRLD's discography
@bot tell me about the artist
@bot clear my memory
@bot what do you remember?
```

### Slash Commands (Alternative)

```text
/status - Bot uptime, current model, health
/models - List all 13 available models
/model <name> - Switch to specific model
/song <query> - Search songs
/lyrics <song> - Get lyrics with annotations
/artist <name> - Artist information
/discography <artist> - Full discography
/features <artist> - Songs with featured artist
/genius <query> - Genius API search
/soundcloud <query> - SoundCloud with embed player
/forget - Clear conversation memory
/stats - Conversation statistics
```

### Memory Management
- 🧠 Automatic context tracking per thread
- 💬 Natural commands: “clear my memory”, “what do you remember?”
- ✅/❌ Reaction-based confirmation for destructive actions
- 📝 Auto-deletion sync: edits/deletes update memory

---

## 🎯 Intelligent Model Routing

YamiBot automatically selects the best model based on what you ask:

- **Coding/Technical** → Cerebras GPT-OSS 120B (or Llama 405B)
- **Web Search** → Gemini 2.0 Flash (has search built-in)
- **Complex Reasoning** → Gemini 1.5 Pro or Llama 405B
- **Creative Writing** → Mistral Large
- **Fast Response** → Mixtral 8x7B or Mistral Small
- **Music Queries** → Gemini 2.0 Flash (optimized for music)
- **Math/Logic** → Llama 3.1 405B
- **General Chat** → Mixtral 8x7B (balanced)

Manual override available:

```text
@bot use [model_name] for this
```

---

## 🎵 Music API Smart Routing

**When you mention Juice WRLD:**
- → Automatically uses Juice WRLD API (primary source)
- → Falls back to Genius only if explicitly requested

**When you ask for lyrics (non-Juice):**
- → Uses Genius API for comprehensive lyrics + annotations

**When you want to embed audio:**
- → Uses SoundCloud API with playable Discord player

**Example**
- `@bot Juice WRLD songs` → Juice WRLD API
- `@bot show me Humble lyrics` → Genius API
- `@bot embed this on SoundCloud` → SoundCloud with player

---

## 🔐 Security & Reliability

### Input Protection
- Injection attack prevention
- Spam detection (special characters, repeated chars)
- Message length enforcement (Discord limits)
- @everyone/@here blocking

### Rate Limiting
- Per-user limits: 5 requests/min, 30/hour
- Trusted user multiplier (2×)
- Provider rate limit tracking
- Circuit breaker pattern for API failures

### Resource Management
- Memory leak prevention (50MB threshold warnings)
- Automatic conversation cleanup
- Connection pooling & keepalive
- Graceful shutdown handlers

### Permissions
- Admin user support
- Trusted user tiers
- Whitelist/blacklist modes
- Permission levels per user

---

## 📊 Complete Feature Matrix

| Feature | Status | Details |
|---------|--------|---------|
| AI Conversation | ✅ | @mention support, context-aware |
| 13 AI Models | ✅ | All major providers + Google |
| Smart Model Routing | ✅ | Auto-selects best model by intent |
| Natural Language Commands | ✅ | No slash commands needed |
| Slash Commands | ✅ | 12+ commands available |
| Juice WRLD API | ✅ | Full song/artist database |
| Genius API | ✅ | Lyrics + annotations |
| SoundCloud API | ✅ | Embeddable players in Discord |
| Memory Management | ✅ | Thread-aware, auto-cleanup |
| Web Search | ✅ | Via Gemini integration |
| Image Analysis | ✅ | Via Gemini multimodal |
| Rate Limiting | ✅ | Per-user + per-provider |
| Input Validation | ✅ | Injection & spam protection |
| Health Monitoring | ✅ | Provider health checks |
| Circuit Breaker | ✅ | Failure prevention |
| Model Analytics | ✅ | Usage tracking per model |
| User Preferences | ✅ | Remember user settings |
| Reaction Confirmations | ✅ | For destructive actions |
| Message Tracking | ✅ | Edit/delete sync |
| 24/7 Uptime | ✅ | Running on Koyeb |

---

## 🏗️ Architecture Highlights

- **Multi-Provider Fallback**: Intelligent failover across 5 AI providers
- **Async/Await**: Full async implementation for performance
- **Connection Pooling**: Optimized HTTP session management
- **Circuit Breakers**: Prevents cascading failures
- **Model Registry**: Centralized model management (13 models)
- **Intent Detection**: NLP-based command classification
- **Response Formatting**: Discord-optimized output
- **Logging**: Comprehensive logging to console + files
- **Memory Safe**: Proper resource cleanup, no leaks

---

## 📈 Bot Statistics

- **AI Models**: 13 across 5 providers
- **Music APIs**: 3 (Juice WRLD, Genius, SoundCloud)
- **Commands**: 12+ slash commands
- **Natural Intents**: 13+ recognized intents
- **Rate Limits**: Per-user + per-provider
- **Memory**: Automatic leak prevention
- **Uptime**: 24/7 on Koyeb with monitoring
- **Code Quality**: Production-grade (type hints, async, error handling)

---

## ✨ What You Can Do

### 🎵 Music Discovery
```text
@bot search for Lucid Dreams
@bot find all Juice WRLD songs with Drake
@bot XXXTentacion's discography
@bot show me Humble lyrics (Genius)
@bot embed songs on SoundCloud
```

### 🧠 AI Conversations
```text
@bot explain quantum computing
@bot help me debug this code
@bot write me a poem
@bot use llama-3.1-405b to solve this math problem
```

### 🧵 Memory & Settings
```text
@bot what do you remember about me?
@bot clear my memory
@bot remember that I prefer concise responses
@bot use Gemini for all my future searches
```

### 🩺 Bot Info
```text
/status - Check bot health
/models - See all available AI models
/stats - Conversation statistics
```

---

**Status**: ✅ Live on Koyeb with uptimebot monitoring  
**Type**: Personal AI Discord Bot  
**Architecture**: Discord.py + FastAPI + Multiple LLM APIs  
**Features**: 60+ integrated capabilities  
**Last Updated**: 2026-01-23

*Built for advanced AI conversations, music discovery, and intelligent command routing.*
