"""
Mistral Provider for YamiBot

Final fallback AI provider using the Mistral API with mistral-small model.
"""

from typing import Tuple, Dict, Any
import os
import time

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
    MISTRAL_AVAILABLE = True
except ImportError:
    logger.warning("Mistral AI library not available - MistralProvider will not work")
    MISTRAL_AVAILABLE = False

class MistralProvider(BaseProvider):
    """
    Mistral AI provider implementation
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.last_request_time = 0  # For RPS tracking
    
    def _get_model_name(self) -> str:
        return "mistral-small"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the Mistral client
        """
        if not MISTRAL_AVAILABLE:
            raise ImportError("Mistral AI library is not installed")
        
        api_key = self.config.mistral_api_key
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not configured")
        
        client = MistralClient(api_key=api_key)
        return client
    
    def get_limits(self) -> Dict[str, Any]:
        """
        Get Mistral rate limits
        """
        return {
            "daily": None,
            "rps": 1,
            "description": "1 request per second limit"
        }
    
    async def check_rate_limit(self) -> bool:
        """
        Check Mistral RPS limit (1 request per second)
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < 1.0:
            logger.warning(f"Mistral RPS limit: {1.0 - time_since_last:.2f} seconds until next request allowed")
            return False
        
        return True
    
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query Mistral API with the given prompt
        
        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
            
        Returns:
            Tuple containing response text and metadata
        """
        if not MISTRAL_AVAILABLE:
            raise ImportError("Mistral AI library is not installed")
        
        # Set default parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)
        
        metadata: Dict[str, Any] = {
            "provider": "mistral",
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        try:
            # Create chat messages
            messages = [ChatMessage(role="user", content=prompt)]
            
            # Make the API call
            response = await self._with_timeout(
                self.client.chat(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
            
            # Extract response
            full_response = response.choices[0].message.content
            
            # Get token usage
            if response.usage:
                metadata.update({
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                })
            
            # Update last request time for RPS tracking
            self.last_request_time = time.time()
            
            logger.info(f"Mistral response received: {len(full_response)} characters")
            
            return full_response, metadata
            
        except Exception as e:
            await self._handle_api_error(e, "Mistral")
            raise