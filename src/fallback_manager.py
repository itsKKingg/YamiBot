"""
Fallback Manager for YamiBot

This module orchestrates the multi-provider API fallback system.
It maintains a list of providers in priority order and handles
fallback logic when providers are rate-limited or unavailable.
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
import time
from datetime import datetime, timedelta

from .providers.base import BaseProvider
from .utils.logger import setup_logging
from .utils.config import Config

logger = setup_logging(__name__)

class ProviderStatus:
    """
    Enum-like class for provider status tracking
    """
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

class FallbackManager:
    """
    Manages multiple AI providers with fallback capability
    """
    
    def __init__(self, config: Config):
        """
        Initialize the fallback manager with configuration
        
        Args:
            config: Configuration object containing provider settings
        """
        self.config = config
        self.providers: List[BaseProvider] = []
        self.provider_status: Dict[str, str] = {}
        self.last_fallback_reason: Optional[str] = None
        self.last_used_provider: Optional[str] = None
        
        # Provider priority order (from highest to lowest)
        self.provider_priority = [
            "groq",
            "cerebras", 
            "google",
            "openrouter",
            "mistral"
        ]
    
    async def initialize(self) -> None:
        """
        Initialize all providers and set their initial status
        """
        logger.info("Initializing providers...")
        
        # Import and initialize providers dynamically
        try:
            # Import provider modules
            from .providers.groq_provider import GroqProvider
            from .providers.cerebras_provider import CerebrasProvider
            from .providers.google_provider import GoogleProvider
            from .providers.openrouter_provider import OpenRouterProvider
            from .providers.mistral_provider import MistralProvider
            
            # Initialize providers in priority order
            self.providers = [
                GroqProvider(self.config),
                CerebrasProvider(self.config),
                GoogleProvider(self.config),
                OpenRouterProvider(self.config),
                MistralProvider(self.config)
            ]
            
            # Set initial status for all providers
            for provider in self.providers:
                self.provider_status[provider.name] = ProviderStatus.AVAILABLE
                
            logger.info(f"Initialized {len(self.providers)} providers: {[p.name for p in self.providers]}")
            
        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}", exc_info=True)
            raise
    
    async def query(self, prompt: str, **kwargs) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Query the AI providers with fallback capability
        
        Args:
            prompt: The user's input prompt
            **kwargs: Additional arguments to pass to providers
            
        Returns:
            Tuple containing:
            - response text (or None if all providers failed)
            - metadata dictionary with provider info, tokens, timing, etc.
        """
        start_time = time.time()
        attempted_providers = []
        fallback_reasons = []
        
        logger.info(f"Processing query: {prompt[:100]}...")
        
        # Try providers in priority order
        for provider in self.providers:
            provider_name = provider.name
            attempted_providers.append(provider_name)
            
            # Check if provider is available
            status = self.provider_status.get(provider_name, ProviderStatus.AVAILABLE)
            
            if status != ProviderStatus.AVAILABLE:
                reason = f"Provider {provider_name} is {status}"
                fallback_reasons.append(reason)
                logger.warning(reason)
                continue
            
            try:
                # Check rate limits before making the call
                if not await provider.check_rate_limit():
                    self.provider_status[provider_name] = ProviderStatus.RATE_LIMITED
                    reason = f"Provider {provider_name} rate limited"
                    fallback_reasons.append(reason)
                    logger.warning(reason)
                    continue
                
                logger.info(f"Attempting query with {provider_name} provider")
                
                # Make the API call
                response, metadata = await provider.query(prompt, **kwargs)
                
                # Update metadata with provider info
                metadata.update({
                    "provider": provider_name,
                    "attempted_providers": attempted_providers,
                    "fallback_reasons": fallback_reasons,
                    "response_time": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Update last used provider
                self.last_used_provider = provider_name
                self.last_fallback_reason = None if not fallback_reasons else "; ".join(fallback_reasons)
                
                logger.info(f"Successfully got response from {provider_name}")
                
                return response, metadata
                
            except Exception as e:
                # Mark provider as failed
                self.provider_status[provider_name] = ProviderStatus.FAILED
                reason = f"Provider {provider_name} failed: {str(e)}"
                fallback_reasons.append(reason)
                logger.error(reason, exc_info=True)
                
                # Continue to next provider
                continue
        
        # If we get here, all providers failed
        error_msg = "All providers failed to respond"
        metadata = {
            "error": error_msg,
            "attempted_providers": attempted_providers,
            "fallback_reasons": fallback_reasons,
            "response_time": time.time() - start_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.error(error_msg)
        return None, metadata
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get the current status of all providers
        
        Returns:
            Dictionary with provider status information
        """
        status_info = {}
        
        for provider in self.providers:
            status_info[provider.name] = {
                "status": self.provider_status.get(provider.name, ProviderStatus.AVAILABLE),
                "model": provider.model,
                "limits": provider.get_limits(),
                "remaining": provider.get_remaining_quota()
            }
        
        return status_info
    
    def get_last_fallback_info(self) -> Dict[str, Any]:
        """
        Get information about the last fallback event
        
        Returns:
            Dictionary with fallback information
        """
        return {
            "last_used_provider": self.last_used_provider,
            "last_fallback_reason": self.last_fallback_reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def reset_failed_providers(self) -> None:
        """
        Reset the status of failed providers
        This can be called periodically to give failed providers another chance
        """
        reset_count = 0
        
        for provider in self.providers:
            if self.provider_status.get(provider.name) == ProviderStatus.FAILED:
                self.provider_status[provider.name] = ProviderStatus.AVAILABLE
                reset_count += 1
                logger.info(f"Reset failed status for {provider.name}")
        
        if reset_count > 0:
            logger.info(f"Reset {reset_count} failed providers")