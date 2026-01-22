# Security Features

YamiBot implements comprehensive security measures to prevent abuse, injection attacks, and ensure stability under adversarial conditions.

## Table of Contents

- [Input Validation](#input-validation)
- [Rate Limiting](#rate-limiting)
- [Permission System](#permission-system)
- [Message Validation](#message-validation)
- [Configuration](#configuration)
- [Testing](#testing)

## Input Validation

The bot validates all user input before processing to prevent injection attacks and spam.

### Features

- **Length Validation**: Messages must be between 1 and 2000 characters (Discord limit)
- **Pattern Detection**: Blocks suspicious patterns like `@everyone` and `@here`
- **Spam Detection**: Rejects messages with >70% special characters
- **Repeated Characters**: Blocks messages with >10 repeated characters in a row
- **Control Character Removal**: Strips null bytes and control characters
- **Response Truncation**: Safely truncates AI responses to Discord's 2000 character limit

### Usage

```python
from src.utils.input_validator import InputValidator

validator = InputValidator()

# Validate user message
is_valid, error = validator.validate_message(user_input)
if not is_valid:
    print(f"Invalid: {error}")
    return

# Sanitize message
clean_message = validator.sanitize_message(user_input)

# Validate response before sending
safe_response = validator.validate_response(ai_response)
```

### Examples

```python
# ✅ Valid messages
"Hello, how are you?"
"Can you help me with Python?"

# ❌ Rejected messages
""  # Empty message
"A" * 2001  # Too long (>2000 chars)
"Hey @everyone check this!"  # Injection attempt
"!@#$%^&*" * 50  # Spam (too many special chars)
"AAAAAAAAAAAAA"  # Repeated characters
```

## Rate Limiting

Per-user rate limiting prevents abuse and ensures fair usage.

### Limits

| User Type | Per Minute | Per Hour | Cooldown |
|-----------|-----------|----------|----------|
| Regular   | 5 requests | 30 requests | 5 seconds |
| Trusted   | 10 requests | 60 requests | 5 seconds |
| Admin     | 10 requests | 60 requests | 5 seconds |

### Features

- **Per-Minute Limits**: Prevents rapid-fire spam
- **Per-Hour Limits**: Prevents extended abuse
- **Cooldown System**: Temporary block after hitting limit
- **Trusted User Multiplier**: Higher limits for trusted users (2x by default)
- **Automatic Cleanup**: Old request records are automatically removed

### Configuration

```env
# .env
MAX_REQUESTS_PER_MINUTE=5
MAX_REQUESTS_PER_HOUR=30
COOLDOWN_SECONDS=5
TRUSTED_USER_MULTIPLIER=2
```

### Usage

```python
from src.rate_limiter import RateLimiter

rate_limiter = RateLimiter(config)

# Check if user can make request
can_request, reason = rate_limiter.can_user_request(user_id, is_trusted=False)
if not can_request:
    print(f"Rate limited: {reason}")
    return

# Record successful request
rate_limiter.record_user_request(user_id)

# Get user's rate limit status
status = rate_limiter.get_user_rate_limit_status(user_id)
print(f"Requests this hour: {status['requests_this_hour']}/{status['max_per_hour']}")
```

### Admin Functions

```python
# Reset a user's cooldown
rate_limiter.reset_user_cooldown(user_id)

# Clear a user's request history
rate_limiter.clear_user_history(user_id)
```

## Permission System

Role-based access control with support for admins, trusted users, whitelists, and blacklists.

### Permission Levels

1. **ADMIN**: Full access to bot and admin commands
2. **TRUSTED**: Regular access with higher rate limits
3. **USER**: Regular access with standard rate limits
4. **NONE**: No access (blacklisted or not whitelisted)

### Features

- **Admin List**: Users with full bot access
- **Trusted List**: Users with higher rate limits
- **Whitelist Mode**: When enabled, only whitelisted users can use the bot
- **Blacklist**: Permanently blocks specific users
- **Precedence**: Blacklist > Admin > Trusted > Whitelist > User

### Configuration

```env
# .env
# Comma-separated Discord user IDs
ADMIN_USER_IDS=123456789,987654321
TRUSTED_USER_IDS=111111111,222222222
WHITELIST_USER_IDS=  # Leave empty to allow all
BLACKLIST_USER_IDS=999999999
```

### Usage

```python
from src.utils.permissions import PermissionManager, Permission

perm_manager = PermissionManager(config)

# Check if user can use bot
if not perm_manager.can_use_bot(user_id):
    print("Access denied")
    return

# Check permission level
perm = perm_manager.get_permission(user_id)
if perm == Permission.ADMIN:
    # Admin-only functionality
    pass

# Check if trusted (for rate limiting)
is_trusted = perm_manager.is_trusted(user_id)

# Get detailed user info
info = perm_manager.get_user_info(user_id)
```

### Whitelist Mode

When `WHITELIST_USER_IDS` is configured, **only** users in the whitelist (plus admins/trusted) can use the bot. This is useful for:

- Private/invite-only bots
- Testing phases
- Limited rollouts

Example:
```env
# Only these 3 users can use the bot
WHITELIST_USER_IDS=123456789,987654321,111111111
```

### Admin Functions

```python
# Add user to blacklist
perm_manager.add_to_blacklist(user_id)

# Remove user from blacklist
perm_manager.remove_from_blacklist(user_id)
```

## Message Validation

Discord-specific message validation before processing.

### Features

- **Bot Mention Detection**: Only processes messages that mention the bot
- **Self-Reply Prevention**: Ignores bot's own messages
- **Bot Filter**: Ignores messages from other bots
- **Empty Message Detection**: Rejects empty or whitespace-only messages
- **Mention Extraction**: Cleanly removes bot mentions from message content
- **DM Support**: Optionally handles or rejects direct messages

### Usage

```python
from src.message_validator import MessageValidator

# Check if message should be processed
should_process, reason = MessageValidator.should_process_message(message, bot)
if not should_process:
    return

# Check user permissions
can_proceed, denial_reason = await MessageValidator.check_permissions(message, perm_manager)
if not can_proceed:
    await message.reply(f"❌ {denial_reason}")
    return

# Extract clean message content
content = MessageValidator.extract_message_content(message, bot)
```

## Security Pipeline

When a message is received, it goes through this validation pipeline:

```
1. Basic Message Validation
   ├─ Check if from bot itself → IGNORE
   ├─ Check if from other bots → IGNORE
   ├─ Check if bot is mentioned → IGNORE if not
   └─ Check if empty → IGNORE

2. Permission Check
   ├─ Check if blacklisted → DENY
   ├─ Check if whitelist mode active → CHECK WHITELIST
   └─ Determine permission level → CONTINUE

3. Rate Limiting Check
   ├─ Check if in cooldown → DENY
   ├─ Check per-minute limit → DENY if exceeded
   └─ Check per-hour limit → DENY if exceeded

4. Input Validation
   ├─ Check message length → DENY if invalid
   ├─ Check for suspicious patterns → DENY if found
   ├─ Check for spam indicators → DENY if spam
   └─ Check for repeated characters → DENY if excessive

5. Sanitization
   ├─ Remove control characters
   ├─ Normalize whitespace
   └─ Clean mentions

6. Processing
   ├─ Query AI provider
   ├─ Validate response
   ├─ Truncate if needed
   └─ Record successful request

7. Response Delivery
   └─ Send to Discord
```

## Error Messages

User-friendly error messages for each validation failure:

| Failure Type | Message |
|-------------|---------|
| Empty message | "❌ Message cannot be empty" |
| Too long | "❌ Message too long (max 2000 characters)" |
| Suspicious content | "❌ Message contains suspicious content (@everyone/@here not allowed)" |
| Too many special chars | "❌ Message contains too many special characters" |
| Repeated characters | "❌ Message contains too many repeated characters (X in a row)" |
| Rate limited (per-minute) | "⏱️ Too many requests. You can make up to X requests per minute." |
| Rate limited (per-hour) | "⏱️ Hourly limit reached (X requests/hour). Resets in Y minutes." |
| In cooldown | "⏱️ Rate limited. Please try again in X seconds." |
| Blacklisted | "❌ You are not authorized to use this bot." |
| Not whitelisted | "❌ This bot is currently in restricted mode. Contact an administrator for access." |

## Testing

Run the security test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
python test_validation.py
```

The test suite covers:
- ✅ Input validation (length, patterns, spam, sanitization)
- ✅ Permission system (admin, trusted, whitelist, blacklist)
- ✅ Rate limiting (per-minute, per-hour, cooldowns, trusted multiplier)

## Configuration Example

Complete security configuration in `.env`:

```env
# Permission & Security Settings
ADMIN_USER_IDS=123456789,987654321
TRUSTED_USER_IDS=111111111,222222222
WHITELIST_USER_IDS=  # Leave empty to allow all
BLACKLIST_USER_IDS=999999999

# User Rate Limiting
MAX_REQUESTS_PER_MINUTE=5
MAX_REQUESTS_PER_HOUR=30
COOLDOWN_SECONDS=5
TRUSTED_USER_MULTIPLIER=2

# Input Validation
MAX_MESSAGE_LENGTH=2000
MIN_MESSAGE_LENGTH=1
MAX_RESPONSE_LENGTH=2000
```

## Security Best Practices

1. **Set Admin IDs**: Configure `ADMIN_USER_IDS` with your Discord user ID
2. **Enable Whitelist for Private Bots**: Use `WHITELIST_USER_IDS` for invite-only operation
3. **Monitor Logs**: Watch for rate limit hits and suspicious pattern detections
4. **Adjust Rate Limits**: Tune `MAX_REQUESTS_PER_MINUTE` and `MAX_REQUESTS_PER_HOUR` based on usage
5. **Use Trusted List**: Grant trusted users higher limits to prevent false positives
6. **Regular Blacklist Updates**: Add abusive users to `BLACKLIST_USER_IDS`

## Troubleshooting

### User Getting Rate Limited Too Often

- Check if they're making too many requests
- Consider adding them to `TRUSTED_USER_IDS`
- Increase `MAX_REQUESTS_PER_MINUTE` or `MAX_REQUESTS_PER_HOUR`

### Legitimate Messages Being Blocked

- Check logs for the specific validation failure
- Adjust validation thresholds if needed
- Add user to trusted list for higher limits

### Whitelist Mode Not Working

- Ensure `WHITELIST_USER_IDS` is properly formatted (comma-separated)
- Check that user IDs are correct (they're numeric, not usernames)
- Admins and trusted users automatically have access

## Monitoring

The bot logs all security events:

```
# Permission denials
WARNING - Permission denied for User#1234 (123456789): User not authorized

# Rate limit hits
INFO - Rate limit hit for 123456789: Too many requests

# Suspicious patterns
WARNING - Suspicious pattern detected in message: @everyone

# Spam detection
WARNING - Excessive special characters detected: 85.00%
WARNING - Spam detected from User#1234 (123456789): Too many special characters
```

Monitor these logs to identify:
- Abusive users (frequent rate limits)
- Attack attempts (suspicious patterns)
- Configuration issues (legitimate users blocked)

## API Reference

See individual module documentation:
- `src/utils/input_validator.py` - Input validation and sanitization
- `src/utils/permissions.py` - Permission management
- `src/rate_limiter.py` - Rate limiting (includes per-user limiting)
- `src/message_validator.py` - Discord message validation
