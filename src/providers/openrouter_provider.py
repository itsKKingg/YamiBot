"""
OpenRouter Provider for YamiBot

Backup AI provider using the OpenRouter API with flexible model routing.
"""

from typing import Tuple, Dict, Any
import os

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

try:
    from openai import AsyncOpenAI
    OPENROUTER_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI library not available - OpenRouterProvider will not work")
    OPENROUTER_AVAILABLE = False

class OpenRouterProvider(BaseProvider):
    """
    OpenRouter AI provider implementation
    """
    
    def _get_model_name(self) -> str:
        # OpenRouter supports many models - we'll use a flexible approach
        return "openrouter/flexible"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the OpenRouter client
        """
        if not OPENROUTER_AVAILABLE:
            raise ImportError("OpenAI library is not installed")
        
        api_key = self.config.openrouter_api_key
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        
        # Create OpenRouter client (OpenAI-compatible)
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        return client
    
    def get_limits(self) -> Dict[str, Any]:
        """
        Get OpenRouter rate limits
        """
        return {
            "daily": None,
            "rps": None,
            "description": "Flexible routing, no specific daily limits"
        }
    
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query OpenRouter API with the given prompt
        
        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments (model, temperature, max_tokens, etc.)
            
        Returns:
            Tuple containing response text and metadata
        """
        if not OPENROUTER_AVAILABLE:
            raise ImportError("OpenAI library is not installed")
        
        # Set default parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)
        model = kwargs.get("model", "mistralai/mistral-7b-instruct:free")  # Default free model
        
        metadata: Dict[str, Any] = {
            "provider": "openrouter",
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        try:
            # Prepare messages
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Make the API call
            response = await self._with_timeout(
                self.client.chat.completions.create(
                    model=model,
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
            
            logger.info(f"OpenRouter response received: {len(full_response)} characters")
            
            return full_response, metadata
            
        except Exception as e:
            await self._handle_api_error(e, "OpenRouter")
            raise