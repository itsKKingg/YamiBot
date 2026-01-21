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
        self.groq_api_key = self._get_env("GROQ_API_KEY")
        self.cerebras_api_key = self._get_env("CEREBRAS_API_KEY")
        self.google_ai_api_key = self._get_env("GOOGLE_AI_API_KEY")
        self.openrouter_api_key = self._get_env("OPENROUTER_API_KEY")
        self.mistral_api_key = self._get_env("MISTRAL_API_KEY")
        
        # Bot configuration
        self.bot_prefix = self._get_env("BOT_PREFIX", default="!")
        self.sync_commands = self._get_env("SYNC_COMMANDS", default="true").lower() == "true"
        self.debug_mode = self._get_env("DEBUG_MODE", default="false").lower() == "true"
        
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
        required_vars = {
            "DISCORD_TOKEN": self.discord_token,
            "GROQ_API_KEY": self.groq_api_key,
            "CEREBRAS_API_KEY": self.cerebras_api_key,
            "GOOGLE_AI_API_KEY": self.google_ai_api_key,
            "OPENROUTER_API_KEY": self.openrouter_api_key,
            "MISTRAL_API_KEY": self.mistral_api_key
        }
        
        missing_vars = []
        for var_name, var_value in required_vars.items():
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            error_msg = f"Missing required configuration: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("All required configuration variables are present")
    
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
            "api_keys_configured": {
                "discord": bool(self.discord_token),
                "groq": bool(self.groq_api_key),
                "cerebras": bool(self.cerebras_api_key),
                "google": bool(self.google_ai_api_key),
                "openrouter": bool(self.openrouter_api_key),
                "mistral": bool(self.mistral_api_key)
            }
        }