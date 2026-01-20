"""
Google Provider for YamiBot

Backup AI provider using the Google Generative AI API with gemini-1.5-flash model.
"""

from typing import Tuple, Dict, Any
import os

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    logger.warning("Google Generative AI library not available - GoogleProvider will not work")
    GOOGLE_AVAILABLE = False

class GoogleProvider(BaseProvider):
    """
    Google Generative AI provider implementation
    """
    
    def _get_model_name(self) -> str:
        return "gemini-1.5-flash"
    
    def _initialize_client(self) -> Any:
        """
        Initialize the Google Generative AI client
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google Generative AI library is not installed")
        
        api_key = self.config.google_ai_api_key
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY not configured")
        
        # Configure the client
        genai.configure(api_key=api_key)
        
        # Create the model instance
        model = genai.GenerativeModel(self.model)
        
        return model
    
    def get_limits(self) -> Dict[str, Any]:
        """
        Get Google rate limits
        """
        return {
            "daily": 1000,
            "rps": None,
            "description": "1,000 requests per day"
        }
    
    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query Google Generative AI API with the given prompt
        
        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
            
        Returns:
            Tuple containing response text and metadata
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google Generative AI library is not installed")
        
        # Set default parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)
        
        metadata: Dict[str, Any] = {
            "provider": "google",
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        try:
            # Generate content
            response = await self._with_timeout(
                self.client.generate_content_async(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens
                    }
                )
            )
            
            # Extract response text
            full_response = response.text
            
            # Get token usage if available
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                metadata.update({
                    "input_tokens": usage.prompt_token_count,
                    "output_tokens": usage.candidates_token_count,
                    "total_tokens": usage.total_token_count
                })
            
            logger.info(f"Google response received: {len(full_response)} characters")
            
            return full_response, metadata
            
        except Exception as e:
            await self._handle_api_error(e, "Google")
            raise