"""
Base Provider Class for YamiBot

This module defines the abstract base class that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
import asyncio

from ..utils.logger import setup_logging
from ..utils.config import Config

logger = setup_logging(__name__)

class BaseProvider(ABC):
    """
    Abstract base class for all AI providers
    """
    
    def __init__(self, config: Config, shared_session: Optional[Any] = None):
        """
        Initialize the provider with configuration
        
        Args:
            config: Configuration object containing API keys and settings
            shared_session: Shared aiohttp session (optional)
        """
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        self.model = self._get_model_name()
        self.timeout = 30  # Default timeout in seconds
        self.shared_session = shared_session  # Shared session from bot
        
        # Initialize API client
        self.client = self._initialize_client()
        
        logger.info(f"Initialized {self.name} provider with model {self.model}")
    
    def set_shared_session(self, shared_session):
        """Set the shared aiohttp session"""
        self.shared_session = shared_session
    
    def get_timeout(self, provider_name: str) -> int:
        """Get timeout for specific provider from config"""
        return self.config.provider_timeouts.get(provider_name, self.timeout)
    
    @abstractmethod
    def _get_model_name(self) -> str:
        """
        Get the model name for this provider
        
        Returns:
            String representing the model name
        """
        pass
    
    @abstractmethod
    def _initialize_client(self) -> Any:
        """
        Initialize the API client for this provider
        
        Returns:
            Initialized client object
        """
        pass
    
    @abstractmethod
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query the AI provider with a prompt
        
        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments for the query
            
        Returns:
            Tuple containing:
            - response text from the AI
            - metadata dictionary with additional info (tokens, timing, etc.)
        """
        pass
    
    async def check_rate_limit(self) -> bool:
        """
        Check if this provider is within rate limits
        
        Returns:
            True if within limits, False if rate limited
        """
        # Default implementation - can be overridden by specific providers
        # This will be handled by the RateLimiter class
        return True
    
    def get_limits(self) -> Dict[str, Any]:
        """
        Get the rate limits for this provider
        
        Returns:
            Dictionary describing the rate limits
        """
        # Default limits - should be overridden by specific providers
        return {
            "daily": None,
            "rps": None,
            "description": "No specific limits configured"
        }
    
    def get_remaining_quota(self) -> Dict[str, Any]:
        """
        Get remaining quota information
        
        Returns:
            Dictionary with remaining quota info
        """
        # This will be handled by the RateLimiter class
        return {"message": "Quota tracking handled by RateLimiter"}
    
    async def _handle_api_error(self, error: Exception, provider_name: str) -> None:
        """
        Handle API errors consistently across providers
        
        Args:
            error: The exception that occurred
            provider_name: Name of the provider for logging
        """
        error_type = type(error).__name__
        logger.error(f"{provider_name} API error: {error_type} - {str(error)}")
        
        # Add provider-specific error handling here
        if "rate limit" in str(error).lower():
            logger.warning(f"{provider_name} rate limit exceeded")
        elif "authentication" in str(error).lower() or "api key" in str(error).lower():
            logger.error(f"{provider_name} authentication failed - check API key")
        elif "timeout" in str(error).lower():
            logger.warning(f"{provider_name} request timed out")
    
    async def _with_timeout(self, coroutine, timeout: Optional[int] = None):
        """
        Execute a coroutine with a timeout
        
        Args:
            coroutine: The coroutine to execute
            timeout: Timeout in seconds (uses provider timeout if None)
            
        Returns:
            Result of the coroutine
            
        Raises:
            TimeoutError if the coroutine doesn't complete in time
        """
        actual_timeout = timeout if timeout is not None else self.timeout
        
        try:
            return await asyncio.wait_for(coroutine, timeout=actual_timeout)
        except asyncio.TimeoutError:
            logger.warning(f"{self.name} request timed out after {actual_timeout} seconds")
            raise TimeoutError(f"Request to {self.name} timed out")
        except Exception as e:
            logger.error(f"Error in {self.name} request: {e}")
            raise