"""
Configuration Utility for YamiBot

This module handles loading and validating configuration from environment variables.
"""

import os
from typing import Optional
from dotenv import load_dotenv

from .logger import setup_logging

logger = setup_logging(__name__)

class Config:
    """
    Configuration manager for YamiBot
    """
    
    def __init__(self):
        """
        Initialize configuration by loading environment variables
        """
        # Load .env file if it exists
        load_dotenv()
        
        # Load all configuration values
        self.discord_token = self._get_env("DISCORD_TOKEN")
        self.cerebras_api_key = self._get_env("CEREBRAS_API_KEY")
        self.sambanova_api_key = self._get_env("SAMBANOVA_API_KEY")
        self.groq_api_key = self._get_env("GROQ_API_KEY")
        self.mistral_api_key = self._get_env("MISTRAL_API_KEY")
        self.google_api_key = self._get_env("GOOGLE_API_KEY")
        self.google_model = self._get_env("GOOGLE_MODEL", default="gemini-2.0-flash")

        # Music API keys
        self.genius_access_token = self._get_env("GENIUS_ACCESS_TOKEN")
        self.soundcloud_client_id = self._get_env("SOUNDCLOUD_CLIENT_ID")
        self.soundcloud_client_secret = self._get_env("SOUNDCLOUD_CLIENT_SECRET")
        
        # Bot configuration
        self.bot_prefix = self._get_env("BOT_PREFIX", default="!")
        self.sync_commands = self._get_env("SYNC_COMMANDS", default="false").lower() == "true"
        self.debug_mode = self._get_env("DEBUG_MODE", default="false").lower() == "true"
        
        # Conversation settings
        self.max_conversation_history = int(self._get_env("MAX_CONVERSATION_HISTORY", default="10"))
        self.conversation_timeout = int(self._get_env("CONVERSATION_TIMEOUT", default="3600"))
        
        # Resource management settings
        self.cleanup_interval = int(self._get_env("CLEANUP_INTERVAL", default="300"))  # 5 minutes
        self.memory_check_interval = int(self._get_env("MEMORY_CHECK_INTERVAL", default="600"))  # 10 minutes
        
        # Provider timeout configuration (seconds)
        self.provider_timeouts = {
            'cerebras': int(self._get_env("CEREBRAS_TIMEOUT", default="120")),      # 2 minutes
            'sambanova': int(self._get_env("SAMBANOVA_TIMEOUT", default="120")),    # 2 minutes
            'groq': int(self._get_env("GROQ_TIMEOUT", default="90")),              # 90 seconds
            'mistral': int(self._get_env("MISTRAL_TIMEOUT", default="60")),       # 60 seconds
            'google': int(self._get_env("GOOGLE_TIMEOUT", default="120"))         # 2 minutes
        }
        
        # Permission & Security settings
        self.admin_user_ids = self._get_env("ADMIN_USER_IDS", default="")
        self.trusted_user_ids = self._get_env("TRUSTED_USER_IDS", default="")
        self.whitelist_user_ids = self._get_env("WHITELIST_USER_IDS", default="")
        self.blacklist_user_ids = self._get_env("BLACKLIST_USER_IDS", default="")
        
        # User Rate Limiting settings
        self.max_requests_per_minute = int(self._get_env("MAX_REQUESTS_PER_MINUTE", default="5"))
        self.max_requests_per_hour = int(self._get_env("MAX_REQUESTS_PER_HOUR", default="30"))
        self.cooldown_seconds = int(self._get_env("COOLDOWN_SECONDS", default="5"))
        self.trusted_user_multiplier = int(self._get_env("TRUSTED_USER_MULTIPLIER", default="2"))
        
        # Input Validation settings
        self.max_message_length = int(self._get_env("MAX_MESSAGE_LENGTH", default="2000"))
        self.min_message_length = int(self._get_env("MIN_MESSAGE_LENGTH", default="1"))
        self.max_response_length = int(self._get_env("MAX_RESPONSE_LENGTH", default="2000"))
        
        # Validate required configuration
        self._validate_config()
        
        logger.info("Configuration loaded successfully")
    
    def _get_env(self, key: str, default: Optional[str] = None) -> str:
        """
        Get environment variable with optional default
        
        Args:
            key: Environment variable key
            default: Default value if key not found
            
        Returns:
            Value of environment variable or default
        """
        return os.environ.get(key, default) or ""
    
    def _validate_config(self) -> None:
        """
        Validate that required configuration is present
        
        Raises:
            ValueError: If required configuration is missing
        """
        # DISCORD_TOKEN is absolutely required
        if not self.discord_token:
            error_msg = "Missing required configuration: DISCORD_TOKEN"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Check which provider API keys are present
        provider_keys = {
            "CEREBRAS_API_KEY": self.cerebras_api_key,
            "SAMBANOVA_API_KEY": self.sambanova_api_key,
            "GROQ_API_KEY": self.groq_api_key,
            "MISTRAL_API_KEY": self.mistral_api_key,
            "GOOGLE_API_KEY": self.google_api_key
        }

        # Check music API keys
        music_api_keys = {
            "GENIUS_ACCESS_TOKEN": self.genius_access_token,
            "SOUNDCLOUD_CLIENT_ID": self.soundcloud_client_id,
            "SOUNDCLOUD_CLIENT_SECRET": self.soundcloud_client_secret
        }
        
        missing_providers = []
        available_providers = []
        
        for var_name, var_value in provider_keys.items():
            if not var_value:
                missing_providers.append(var_name)
            else:
                available_providers.append(var_name)
        
        # At least one provider API key must be present
        if not available_providers:
            error_msg = "No provider API keys configured. At least one provider is required: CEREBRAS_API_KEY, SAMBANOVA_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, or GOOGLE_API_KEY"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log configuration status
        logger.info(f"Discord token configured: ✓")
        logger.info(f"Available provider API keys: {len(available_providers)}/{len(provider_keys)}")

        if missing_providers:
            logger.warning(f"Missing provider API keys: {', '.join(missing_providers)}")
            logger.info("Bot will attempt to initialize with available providers")
        else:
            logger.info("All provider API keys are present")

        # Log music API configuration
        music_apis_configured = [name for name, value in music_api_keys.items() if value]
        logger.info(f"Music API keys configured: {len(music_apis_configured)}/{len(music_api_keys)}")

        missing_music_apis = [name for name, value in music_api_keys.items() if not value]
        if missing_music_apis:
            logger.warning(f"Missing music API keys: {', '.join(missing_music_apis)}")
            logger.info("Music features will be unavailable until keys are provided")
    
    def get_debug_info(self) -> dict:
        """
        Get configuration info for debugging (without sensitive data)

        Returns:
            Dictionary with non-sensitive configuration info
        """
        return {
            "bot_prefix": self.bot_prefix,
            "sync_commands": self.sync_commands,
            "debug_mode": self.debug_mode,
            "max_conversation_history": self.max_conversation_history,
            "conversation_timeout": self.conversation_timeout,
            "cleanup_interval": self.cleanup_interval,
            "memory_check_interval": self.memory_check_interval,
            "provider_timeouts": self.provider_timeouts,
            "api_keys_configured": {
                "discord": bool(self.discord_token),
                "cerebras": bool(self.cerebras_api_key),
                "sambanova": bool(self.sambanova_api_key),
                "groq": bool(self.groq_api_key),
                "mistral": bool(self.mistral_api_key),
                "google": bool(self.google_api_key),
                "genius": bool(self.genius_access_token),
                "soundcloud": bool(self.soundcloud_client_id) and bool(self.soundcloud_client_secret)
            }
        }