"""
Groq Provider for YamiBot

Fallback AI provider using the Groq API with openai/gpt-oss-120b model.
"""

from typing import Tuple, Dict, Any
import os

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

try:
    import groq
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    logger.warning("Groq library not available - GroqProvider will not work")
    GROQ_AVAILABLE = False

class GroqProvider(BaseProvider):
    """
    Groq AI provider implementation
    """
    
    def _get_model_name(self) -> str:
        return "openai/gpt-oss-120b"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the Groq client
        """
        if not GROQ_AVAILABLE:
            raise ImportError("Groq library is not installed")
        
        api_key = self.config.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not configured")
        
        return AsyncGroq(api_key=api_key)
    
    def get_limits(self) -> Dict[str, Any]:
        """
        Get Groq rate limits
        """
        return {
            "daily": 14400,
            "rps": None,
            "description": "14,400 requests per day"
        }
    
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query Groq API with the given prompt
        
        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments (stream, temperature, max_tokens, etc.)
            
        Returns:
            Tuple containing response text and metadata
        """
        if not GROQ_AVAILABLE:
            raise ImportError("Groq library is not installed")
        
        # Set default parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)
        stream = kwargs.get("stream", False)
        
        metadata: Dict[str, Any] = {
            "provider": "groq",
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        try:
            # Get conversation history if provided
            messages = kwargs.get("messages", [
                {"role": "user", "content": prompt}
            ])
            
            # Make the API call
            response = await self._with_timeout(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                )
            )
            
            if stream:
                # Handle streaming response
                full_response = ""
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                
                # Get token usage from last chunk
                if hasattr(response, 'usage') and response.usage:
                    metadata.update({
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    })
            else:
                # Handle non-streaming response
                full_response = response.choices[0].message.content
                
                if response.usage:
                    metadata.update({
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    })
            
            logger.info(f"Groq response received: {len(full_response)} characters")
            
            return full_response, metadata
            
        except Exception as e:
            await self._handle_api_error(e, "Groq")
            raise