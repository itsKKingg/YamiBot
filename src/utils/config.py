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
        
        # Bot configuration
        self.bot_prefix = self._get_env("BOT_PREFIX", default="!")
        self.sync_commands = self._get_env("SYNC_COMMANDS", default="false").lower() == "true"
        self.debug_mode = self._get_env("DEBUG_MODE", default="false").lower() == "true"
        
        # Conversation settings
        self.max_conversation_history = int(self._get_env("MAX_CONVERSATION_HISTORY", default="10"))
        self.conversation_timeout = int(self._get_env("CONVERSATION_TIMEOUT", default="3600"))
        
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
            "MISTRAL_API_KEY": self.mistral_api_key
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
            error_msg = "No provider API keys configured. At least one provider is required: CEREBRAS_API_KEY, SAMBANOVA_API_KEY, GROQ_API_KEY, or MISTRAL_API_KEY"
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
            "api_keys_configured": {
                "discord": bool(self.discord_token),
                "cerebras": bool(self.cerebras_api_key),
                "sambanova": bool(self.sambanova_api_key),
                "groq": bool(self.groq_api_key),
                "mistral": bool(self.mistral_api_key)
            }
        }