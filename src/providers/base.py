"""Base provider interface.

All AI provider integrations must implement :class:`BaseProvider`.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Any, Optional

from ..utils.config import Config
from ..utils.logger import setup_logging

logger = setup_logging(__name__)


class BaseProvider(ABC):
    """Abstract base class for all AI providers."""

    def __init__(self, config: Config, shared_session: Optional[Any] = None) -> None:
        """Initialize the provider.

        Args:
            config: Configuration object containing API keys and settings.
            shared_session: Optional shared HTTP session.
        """

        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()
        self.model = self._get_model_name()
        self.timeout = 30
        self.shared_session = shared_session

        self.client = self._initialize_client()
        logger.info("Initialized %s provider with model %s", self.name, self.model)

    def set_shared_session(self, shared_session: Any) -> None:
        """Set the shared HTTP session."""

        self.shared_session = shared_session

    def get_timeout(self, provider_name: str) -> int:
        """Get timeout for specific provider from config."""

        return self.config.provider_timeouts.get(provider_name, self.timeout)

    @abstractmethod
    def _get_model_name(self) -> str:
        """Return the model name for this provider."""

        raise NotImplementedError

    @abstractmethod
    def _initialize_client(self) -> Any:
        """Initialize and return the provider client/SDK instance."""

        raise NotImplementedError

    @abstractmethod
    async def query(self, prompt: str, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        """Send a prompt to the provider.

        Args:
            prompt: The input prompt.
            **kwargs: Provider-specific options.

        Returns:
            A tuple of (response text, metadata).
        """

        raise NotImplementedError

    async def check_rate_limit(self) -> bool:
        """Return whether this provider can be called without violating rate limits."""

        return True

    def get_limits(self) -> dict[str, Any]:
        """Return configured rate limits for this provider."""

        return {"daily": None, "rps": None, "description": "No specific limits configured"}

    def get_remaining_quota(self) -> dict[str, Any]:
        """Return remaining quota information."""

        return {"message": "Quota tracking handled by RateLimiter"}

    async def _handle_api_error(self, error: Exception, provider_name: str) -> None:
        """Handle API errors consistently across providers."""

        error_type = type(error).__name__
        logger.error("%s API error: %s - %s", provider_name, error_type, str(error))

        error_text = str(error).lower()
        if "rate limit" in error_text:
            logger.warning("%s rate limit exceeded", provider_name)
        elif "authentication" in error_text or "api key" in error_text:
            logger.error("%s authentication failed - check API key", provider_name)
        elif "timeout" in error_text:
            logger.warning("%s request timed out", provider_name)

    async def _with_timeout(self, coroutine: Awaitable[Any], timeout: Optional[int] = None) -> Any:
        """Execute a coroutine with a timeout.

        Args:
            coroutine: The coroutine to execute.
            timeout: Timeout in seconds (defaults to provider timeout).

        Raises:
            TimeoutError: If the coroutine does not complete within the timeout.

        Returns:
            The coroutine result.
        """

        actual_timeout = timeout if timeout is not None else self.timeout

        try:
            return await asyncio.wait_for(coroutine, timeout=actual_timeout)
        except asyncio.TimeoutError as exc:
            logger.warning("%s request timed out after %s seconds", self.name, actual_timeout)
            raise TimeoutError(f"Request to {self.name} timed out") from exc
        except Exception:
            logger.exception("Error in %s request", self.name)
            raise
