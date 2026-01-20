"""
Cerebras Provider for YamiBot

Backup AI provider using the Cerebras API with llama-3.3-70b model.
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
    
    def __init__(self, config):
        super().__init__(config)
        self.api_url = "https://api.cerebras.ai/v1/chat/completions"
        self.session = None
    
    def _get_model_name(self) -> str:
        return "llama-3.3-70b"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the Cerebras HTTP client
        """
        api_key = self.config.cerebras_api_key
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY not configured")
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        return self.session
    
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
        if not self.session:
            raise ValueError("Cerebras session not initialized")
        
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
            # Prepare payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Make the API call
            async with self.session.post(
                self.api_url,
                data=json.dumps(payload),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
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
        """
        if self.session:
            await self.session.close()