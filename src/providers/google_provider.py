"""
Google Gemini Provider for YamiBot

AI provider using Google's Gemini API with multiple model support.
Models:
- gemini-2.0-flash (latest, fast)
- gemini-1.5-pro (most powerful reasoning)
- gemini-1.5-flash (cost-effective)
"""

from typing import Tuple, Dict, Any, Optional
import aiohttp
import json

from .base import BaseProvider
from ..utils.logger import setup_logging

logger = setup_logging(__name__)


class GoogleProvider(BaseProvider):
    """
    Google Gemini AI provider implementation
    """

    def __init__(self, config, shared_session=None):
        super().__init__(config, shared_session)
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def _get_model_name(self) -> str:
        """Get model name from config or default to gemini-2.0-flash"""
        return getattr(self.config, 'google_model', 'gemini-2.0-flash')

    def _initialize_client(self) -> Any:
        """
        Initialize the Google Gemini HTTP client
        Uses shared session if available, otherwise creates one for compatibility
        """
        api_key = self.config.google_api_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not configured")

        # Use shared session if available, otherwise create a session for this provider
        if self.shared_session:
            logger.debug("Using shared aiohttp session for Google Gemini")
            return self.shared_session
        else:
            # Fallback for backward compatibility - create our own session
            logger.warning("No shared session available, creating Google-specific session")
            return aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json"
                }
            )

    def get_limits(self) -> Dict[str, Any]:
        """
        Get Google Gemini rate limits
        """
        return {
            "daily": 1500,
            "rps": None,
            "description": "1,500 requests per day (varies by model)"
        }

    async def query(self, prompt: str, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Query Google Gemini API with the given prompt

        Args:
            prompt: The input prompt for the AI
            **kwargs: Additional arguments (temperature, max_tokens, model, etc.)

        Returns:
            Tuple containing response text and metadata
        """
        if not self.client:
            raise ValueError("Google client not initialized")

        # Use configured timeout
        timeout = self.get_timeout("google")

        # Get model from kwargs or use default
        model = kwargs.get("model", self.model)

        # Set default parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1024)

        metadata: Dict[str, Any] = {
            "provider": "google",
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }

        try:
            # Get conversation history if provided
            messages = kwargs.get("messages", None)

            # Prepare payload based on whether we have conversation history
            if messages and len(messages) > 1:
                # Multi-turn conversation
                contents = []
                for msg in messages:
                    if msg["role"] == "user":
                        contents.append({
                            "role": "user",
                            "parts": [{"text": msg["content"]}]
                        })
                    elif msg["role"] == "assistant":
                        contents.append({
                            "role": "model",
                            "parts": [{"text": msg["content"]}]
                        })
            else:
                # Single prompt
                contents = [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }]

            # Prepare payload
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }

            # Build API URL with model and API key
            api_url = f"{self.api_url}/{model}:generateContent?key={self.config.google_api_key}"

            # Use shared session or create one temporarily
            session = self.shared_session if self.shared_session else self.client

            # Make the API call with timeout
            async with session.post(
                api_url,
                data=json.dumps(payload),
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Google Gemini API error {response.status}: {error_text}")
                    raise Exception(f"Google Gemini API returned status {response.status}: {error_text}")

                response_data = await response.json()

                # Extract response from Gemini format
                if "candidates" not in response_data or len(response_data["candidates"]) == 0:
                    raise Exception("No response candidates returned from Gemini API")

                full_response = response_data["candidates"][0]["content"]["parts"][0]["text"]

                # Extract token usage if available
                if "usageMetadata" in response_data:
                    usage = response_data["usageMetadata"]
                    metadata.update({
                        "input_tokens": usage.get("promptTokenCount", 0),
                        "output_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0)
                    })

                logger.info(f"Google Gemini response received: {len(full_response)} characters")

                return full_response, metadata

        except Exception as e:
            await self._handle_api_error(e, "Google Gemini")
            raise

    async def close(self):
        """
        Close the aiohttp session
        Note: For shared sessions, this should be handled by the bot
        """
        # Only close if we're not using a shared session
        if not self.shared_session and self.client:
            await self.client.close()
            logger.info("Google Gemini session closed")
