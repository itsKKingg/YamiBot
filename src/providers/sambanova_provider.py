"""
SambaNova Provider for YamiBot

This module implements the SambaNova AI provider using their REST API.
Model: gpt-oss-120b
"""

import aiohttp
from typing import Tuple, Dict, Any, Optional
import time

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

class SambanovaProvider(BaseProvider):
    """
    SambaNova AI provider implementation
    Uses gpt-oss-120b model via REST API
    """
    
    def __init__(self, config, shared_session=None):
        super().__init__(config, shared_session)
        self.api_base = "https://api.sambanova.ai/v1"
    
    def _get_model_name(self) -> str:
        """Get the model name for SambaNova"""
        return "gpt-oss-120b"
    
    def _initialize_client(self) -> Optional[aiohttp.ClientSession]:
        """
        Initialize client for SambaNova API
        Uses shared session if available
        """
        # Validate API key
        if not self.config.sambanova_api_key:
            logger.warning("SambaNova API key not configured")
            return None
        
        # Use shared session if available
        if self.shared_session:
            logger.debug("Using shared aiohttp session for SambaNova")
            return self.shared_session
        else:
            # Fallback for backward compatibility
            logger.warning("No shared session available, creating SambaNova-specific session")
            return aiohttp.ClientSession()
    
    def get_limits(self) -> Dict[str, Any]:
        """Get rate limits for SambaNova"""
        return {
            "daily": 10000,  # Adjust based on actual SambaNova limits
            "rps": 10,
            "description": "SambaNova API limits (adjust as needed)"
        }
    
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query SambaNova API with the given prompt
        
        Args:
            prompt: The user's input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Tuple of (response_text, metadata)
        """
        start_time = time.time()
        
        # Use configured timeout
        timeout = self.get_timeout("sambanova")
        
        try:
            # Get conversation history if provided
            messages = kwargs.get("messages", [
                {"role": "user", "content": prompt}
            ])
            
            # Build request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 2048),
                "top_p": kwargs.get("top_p", 0.9),
            }
            
            # Add stream parameter if requested
            if kwargs.get("stream", False):
                payload["stream"] = True
            
            headers = {
                "Authorization": f"Bearer {self.config.sambanova_api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Querying SambaNova with model {self.model}")
            
            # Use shared session or create one temporarily
            session = self.shared_session if self.shared_session else self.client
            
            # Make API request
            async with session.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"SambaNova API error: {response.status} - {error_text}")
                    raise Exception(f"SambaNova API error: {response.status}")
                
                result = await response.json()
            
            # Extract response
            if "choices" not in result or len(result["choices"]) == 0:
                raise Exception("Invalid response format from SambaNova")
            
            response_text = result["choices"][0]["message"]["content"]
            
            # Extract token usage
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            # Build metadata
            metadata = {
                "provider": self.name,
                "model": self.model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "response_time": time.time() - start_time,
                "finish_reason": result["choices"][0].get("finish_reason", "unknown")
            }
            
            logger.info(f"SambaNova response received: {total_tokens} tokens in {metadata['response_time']:.2f}s")
            
            return response_text, metadata
            
        except aiohttp.ClientError as e:
            await self._handle_api_error(e, "SambaNova")
            raise Exception(f"SambaNova API client error: {str(e)}")
            
        except Exception as e:
            await self._handle_api_error(e, "SambaNova")
            raise
