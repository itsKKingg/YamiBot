"""
Mistral Provider for YamiBot

Safety fallback AI provider using the Mistral API with mistral-small-latest model.
"""

from typing import Tuple, Dict, Any
import os
import time

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

try:
    from mistralai import Mistral, UserMessage, AssistantMessage, SystemMessage
    MISTRAL_AVAILABLE = True
except ImportError:
    logger.warning("Mistral AI library not available - MistralProvider will not work")
    MISTRAL_AVAILABLE = False

class MistralProvider(BaseProvider):
    """
    Mistral AI provider implementation
    """
    
    def __init__(self, config, shared_session=None):
        super().__init__(config, shared_session)
        self.last_request_time = 0  # For RPS tracking
        self._timeout = self.get_timeout("mistral")
    
    def _get_model_name(self) -> str:
        return "mistral-small-latest"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the Mistral client
        """
        if not MISTRAL_AVAILABLE:
            raise ImportError("Mistral AI library is not installed")
        
        api_key = self.config.mistral_api_key
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not configured")
        
        client = Mistral(api_key=api_key)
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
        
        # Use configured timeout
        timeout = self.get_timeout("mistral")
        
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
            # Get conversation history if provided
            message_list = kwargs.get("messages", [
                {"role": "user", "content": prompt}
            ])
            
            # Convert to Mistral message format
            messages = []
            for msg in message_list:
                role = msg["role"]
                content = msg["content"]
                
                if role == "user":
                    messages.append(UserMessage(content=content))
                elif role == "assistant":
                    messages.append(AssistantMessage(content=content))
                elif role == "system":
                    messages.append(SystemMessage(content=content))
            
            # Make the API call (synchronous in new Mistral SDK)
            # Note: The new SDK uses sync calls, so we need to handle this differently
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.complete(
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