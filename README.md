# 🤖 YamiBot - AI Discord Agent

A production-ready AI Discord bot that responds naturally to @mentions with intelligent conversation. Features multi-provider API fallback, conversation context management, and cloud deployment support.

## ✨ Features

### Core Functionality
- 🗣️ **Natural Conversation**: No slash commands - just @mention the bot
- 🧠 **Context Aware**: Maintains conversation history within threads
- 🔄 **Multi-Provider Fallback**: Automatic failover across 4 AI providers
- ⚡ **Fast Response**: Typing indicator while processing
- 🧵 **Thread Support**: Reply in threads for organized conversations
- 📊 **Smart Rate Limiting**: Prevents hitting API limits
- 🚀 **Cloud Ready**: Deploy to Koyeb, Railway, or any Docker platform

### Security Features 🔒
- 🛡️ **Input Validation**: Blocks injection attacks, spam, and malicious content
- ⏱️ **Per-User Rate Limiting**: Prevents abuse (5/min, 30/hour configurable)
- 👥 **Permission System**: Admin, trusted, whitelist, and blacklist support
- 🚫 **Spam Protection**: Detects excessive special characters and repeated patterns
- 🔍 **Message Validation**: Sanitizes and validates all input/output
- 📏 **Length Enforcement**: Respects Discord's 2000 character limit

### AI Providers (Priority Order)
1. **Cerebras** (Primary) - `gpt-oss-120b`
2. **SambaNova** (Backup) - `gpt-oss-120b`
3. **Groq** (Fallback) - `openai/gpt-oss-120b`
4. **Mistral** (Safety) - `mistral-small-latest`
5. **Google Gemini** (Latest) - `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`

### Natural Language Commands & Slash Commands

The bot supports both natural language commands and traditional slash commands for power users.

#### Natural Language Commands

Simply @mention the bot with natural language:

```
@YamiBot clear my memory              # Clear conversation
@YamiBot what do you remember         # View conversation history
@YamiBot search for quantum physics    # Search with Google Gemini
@YamiBot use model gemini-1.5-pro     # Switch AI model
@YamiBot available models              # List all models
@YamiBot how are you                   # Bot status
@YamiBot forget last 3 messages        # Clear specific messages
@YamiBot remember that I prefer short answers  # Set preference
```

#### Slash Commands

Power users can use slash commands for quick access:

- `/status` - Show bot uptime, current model, memory usage, API provider health
- `/forget` - Trigger memory clear confirmation
- `/model <model_name>` - Switch to specific model
- `/models` - List all available models with descriptions
- `/stats` - Show conversation stats (messages processed, tokens used, model usage)

#### Reaction Confirmation

Destructive actions (like clearing memory) require confirmation:

```
User: @YamiBot clear my memory
Bot: Are you sure? React with ✅ to confirm or ❌ to cancel
    - User reacts ✅ → Memory cleared
    - User reacts ❌ → Cancelled
    - No reaction → Timeout (30 seconds)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- API keys for AI providers (see [Getting API Keys](#getting-api-keys))

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/yamibot.git
cd yamibot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run the bot**
```bash
python -m src.bot
# or
python main.py
```

### Docker Setup

1. **Build the image**
```bash
cd deployment
docker-compose up --build
```

2. **Or use Docker directly**
```bash
docker build -f deployment/Dockerfile -t yamibot .
docker run --env-file .env yamibot
```

## 🔑 Getting API Keys

### Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the token
5. Enable "Message Content Intent" under Privileged Gateway Intents

### Cerebras API Key
1. Sign up at [Cerebras AI](https://cerebras.ai/)
2. Navigate to API section
3. Generate a new API key

### SambaNova API Key
1. Sign up at [SambaNova AI](https://sambanova.ai/)
2. Access your dashboard
3. Create an API key

### Groq API Key
1. Sign up at [Groq Console](https://console.groq.com/)
2. Go to API Keys section
3. Create a new API key

### Mistral API Key
1. Sign up at [Mistral AI Console](https://console.mistral.ai/)
2. Navigate to API keys
3. Generate a new key

### Google Gemini API Key
1. Sign up at [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new project or select existing
3. Generate an API key
4. Note: You may need to enable to Generative Language API

## 💬 Using the Bot

### Basic Usage

Simply @mention the bot in any channel or DM:

```
@YamiBot What is the capital of France?
@YamiBot Can you explain quantum computing?
@YamiBot Write me a poem about coding
```

### Thread Conversations

The bot maintains context within threads:

```
User: @YamiBot What is Python?
Bot: Python is a high-level programming language...

User: What can I build with it?  [in thread]
Bot: With Python, you can build... [remembers context]
```

### Conversation Context

- Bot remembers the last 10 messages in each conversation
- Context expires after 1 hour of inactivity
- Each thread/channel has separate context
- Context resets automatically on timeout

## 📁 Project Structure

```
YamiBot/
├── src/
│   ├── __init__.py
│   ├── bot.py                      # Main Discord bot with @mention handling
│   ├── fallback_manager.py        # Provider fallback orchestration
│   ├── rate_limiter.py             # Rate limiting (provider + per-user)
│   ├── conversation_manager.py    # Conversation context management
│   ├── message_validator.py       # Discord message validation
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract provider class
│   │   ├── cerebras_provider.py   # Cerebras AI implementation
│   │   ├── sambanova_provider.py  # SambaNova AI implementation
│   │   ├── groq_provider.py       # Groq AI implementation
│   │   └── mistral_provider.py    # Mistral AI implementation
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging configuration
│       ├── config.py              # Environment configuration
│       ├── input_validator.py     # Input validation & sanitization
│       └── permissions.py         # Permission management system
├── deployment/
│   ├── Dockerfile                 # Production Docker image
│   ├── docker-compose.yml         # Local development setup
│   ├── .dockerignore
│   └── koyeb-deploy.md           # Koyeb deployment guide
├── .github/workflows/
│   └── deploy.yml                # CI/CD pipeline
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── test_validation.py            # Security feature test suite
├── README.md                     # This file
├── SECURITY.md                   # Security documentation
├── IMPROVEMENTS.md               # Phase 2 enhancement suggestions
└── .gitignore
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DISCORD_TOKEN` | Yes | Discord bot token | - |
| `CEREBRAS_API_KEY` | Yes | Cerebras API key | - |
| `SAMBANOVA_API_KEY` | Yes | SambaNova API key | - |
| `GROQ_API_KEY` | Yes | Groq API key | - |
| `MISTRAL_API_KEY` | Yes | Mistral API key | - |
| `GOOGLE_API_KEY` | No | Google Gemini API key | - |
| `BOT_PREFIX` | No | Command prefix (not used in MVP) | `!` |
| `SYNC_COMMANDS` | No | Sync slash commands (not used) | `false` |
| `DEBUG_MODE` | No | Enable debug logging | `false` |
| `MAX_CONVERSATION_HISTORY` | No | Max messages to remember | `10` |
| `CONVERSATION_TIMEOUT` | No | Context timeout (seconds) | `3600` |

### Security Settings

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ADMIN_USER_IDS` | No | Comma-separated admin Discord user IDs | - |
| `TRUSTED_USER_IDS` | No | Trusted users (higher rate limits) | - |
| `WHITELIST_USER_IDS` | No | If set, only these users can use bot | - |
| `BLACKLIST_USER_IDS` | No | Banned users | - |
| `MAX_REQUESTS_PER_MINUTE` | No | Per-user rate limit | `5` |
| `MAX_REQUESTS_PER_HOUR` | No | Per-user hourly limit | `30` |
| `COOLDOWN_SECONDS` | No | Cooldown after rate limit hit | `5` |
| `TRUSTED_USER_MULTIPLIER` | No | Rate limit multiplier for trusted users | `2` |

**See [SECURITY.md](SECURITY.md) for complete security documentation.**

### Conversation Settings

**MAX_CONVERSATION_HISTORY**: Controls how many messages are kept in context
- Minimum: 2 (current exchange only)
- Maximum: 50 (may hit token limits)
- Recommended: 10-20 for good context without token bloat

**CONVERSATION_TIMEOUT**: How long before context expires
- Minimum: 300 (5 minutes)
- Maximum: 86400 (24 hours)
- Recommended: 3600 (1 hour) for active conversations

### Memory Management

The bot includes automatic memory management features:

**Automatic Cleanup:**
- Conversations expire after timeout (default: 1 hour)
- Periodic cleanup runs every 5 minutes by default
- Memory usage is monitored to prevent leaks

**Manual Memory Control:**
- Use natural language: "clear my memory" to reset conversation
- Use "forget last N messages" to remove specific messages
- Use "what do you remember" to view current memory
- All destructive actions require reaction confirmation

**Message Tracking:**
- Deleted messages are automatically removed from context
- Edited messages update the conversation context
- Thread conversations are tracked separately from channel conversations

## 🚢 Deployment

### Deploy to Koyeb (Recommended)

See [deployment/koyeb-deploy.md](deployment/koyeb-deploy.md) for detailed instructions.

**Quick steps**:
1. Fork this repository
2. Sign up at [Koyeb](https://www.koyeb.com/)
3. Create a new app from your fork
4. Add environment variables
5. Deploy!

### Deploy to Railway

1. Click the button:
   [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

2. Add environment variables
3. Deploy

### Deploy to Other Platforms

YamiBot works on any platform that supports Docker:
- Heroku
- DigitalOcean App Platform
- Google Cloud Run
- AWS ECS
- Azure Container Instances

## 📊 Monitoring

### Logs

View logs in real-time:
```bash
docker logs -f yamibot
```

Logs include:
- All @mention events
- Provider fallback decisions
- API call timing and token usage
- Error details with context
- Conversation context updates

### Health Check

The bot exposes a health endpoint on port 8080:
```bash
curl http://localhost:8080/health
```

## 🔧 Troubleshooting

### Bot Not Responding

1. **Check bot is online**: Look for green status in Discord
2. **Verify intents**: Ensure "Message Content Intent" is enabled
3. **Check mentions**: Bot only responds to @mentions
4. **Review logs**: Check for API errors or rate limits

### All Providers Failing

1. **Check API keys**: Ensure all keys are valid
2. **Verify network**: Ensure bot can reach provider APIs
3. **Check rate limits**: May have exceeded free tier
4. **Review provider status**: Check provider status pages

### Context Not Working

1. **Check timeout**: Context expires after 1 hour by default
2. **Verify thread ID**: Each thread has separate context
3. **Look for errors**: Check logs for context manager errors

### High API Usage

1. **Check for spam**: May have users spamming bot
2. **Review history size**: Reduce MAX_CONVERSATION_HISTORY
3. **Implement caching**: See IMPROVEMENTS.md for caching suggestions
4. **Add rate limits**: Implement per-user rate limiting

## 🔐 Security Best Practices

- ✅ Never commit `.env` file
- ✅ Rotate API keys regularly
- ✅ Use least-privilege Discord permissions
- ✅ Configure `ADMIN_USER_IDS` with your Discord user ID
- ✅ Enable whitelist mode for private bots (`WHITELIST_USER_IDS`)
- ✅ Monitor rate limit logs for abuse patterns
- ✅ Blacklist abusive users with `BLACKLIST_USER_IDS`
- ✅ Keep dependencies updated

**See [SECURITY.md](SECURITY.md) for comprehensive security documentation including:**
- Input validation and sanitization
- Per-user rate limiting configuration
- Permission system (admin/trusted/whitelist/blacklist)
- Spam and injection attack prevention
- Security testing and monitoring

## 📈 Performance Tips

- Use Redis for caching (future enhancement)
- Enable response caching for common questions
- Adjust MAX_CONVERSATION_HISTORY based on usage
- Monitor token usage per provider
- Use health checks to detect slow providers

## 🎨 Future Enhancements

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for 30+ enhancement ideas including:

- 🎭 Reaction-based controls (👍🔄❌)
- 🌍 Multi-language support
- 💾 Database integration
- 📊 Usage analytics
- 🖼️ Image generation
- 🔍 Web search integration
- 🎤 Voice channel support
- And much more!

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [Groq](https://groq.com/) - Fast AI inference
- [Cerebras](https://cerebras.ai/) - AI model provider
- [SambaNova](https://sambanova.ai/) - AI model provider
- [Mistral AI](https://mistral.ai/) - AI model provider
- [Koyeb](https://www.koyeb.com/) - Cloud deployment platform

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/yamibot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/yamibot/discussions)
- **Email**: your-email@example.com

---

Made with ❤️ by [Your Name]
