"""
Cerebras Provider for YamiBot

Primary AI provider using the Cerebras API with gpt-oss-120b model.
"""

from typing import Tuple, Dict, Any
import os
import aiohttp
import json

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

class CerebrasProvider(BaseProvider):
    """
    Cerebras AI provider implementation
    """
    
    def __init__(self, config, shared_session=None):
        super().__init__(config, shared_session)
        self.api_url = "https://api.cerebras.ai/v1/chat/completions"
    
    def _get_model_name(self) -> str:
        return "gpt-oss-120b"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the Cerebras HTTP client
        Uses shared session if available, otherwise creates one for compatibility
        """
        api_key = self.config.cerebras_api_key
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY not configured")
        
        # Use shared session if available, otherwise create a session for this provider
        if self.shared_session:
            logger.debug("Using shared aiohttp session for Cerebras")
            return self.shared_session
        else:
            # Fallback for backward compatibility - create our own session
            logger.warning("No shared session available, creating Cerebras-specific session")
            return aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
    
    def get_limits(self) -> Dict[str, Any]:
        """
        Get Cerebras rate limits
        """
        return {
            "daily": 14400,
            "rps": None,
            "description": "14,400 requests per day"
        }
    
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query Cerebras API with the given prompt
        
        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
            
        Returns:
            Tuple containing response text and metadata
        """
        if not self.client:
            raise ValueError("Cerebras client not initialized")
        
        # Use configured timeout
        timeout = self.get_timeout("cerebras")
        
        # Set default parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)
        
        metadata: Dict[str, Any] = {
            "provider": "cerebras",
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        try:
            # Get conversation history if provided
            messages = kwargs.get("messages", [
                {"role": "user", "content": prompt}
            ])
            
            # Prepare payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Use shared session or create one temporarily
            session = self.shared_session if self.shared_session else self.client
            
            # Make the API call with timeout
            async with session.post(
                self.api_url,
                data=json.dumps(payload),
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Cerebras API error {response.status}: {error_text}")
                    raise Exception(f"Cerebras API returned status {response.status}: {error_text}")
                
                response_data = await response.json()
                
                # Extract response
                full_response = response_data["choices"][0]["message"]["content"]
                
                # Extract token usage if available
                if "usage" in response_data:
                    usage = response_data["usage"]
                    metadata.update({
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    })
                
                logger.info(f"Cerebras response received: {len(full_response)} characters")
                
                return full_response, metadata
                
        except Exception as e:
            await self._handle_api_error(e, "Cerebras")
            raise
        
        
    async def close(self):
        """
        Close the aiohttp session
        Note: For shared sessions, this should be handled by the bot
        """
        # Only close if we're not using a shared session
        if not self.shared_session and self.client:
            await self.client.close()
            logger.info("Cerebras session closed")