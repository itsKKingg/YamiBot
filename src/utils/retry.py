"""Utilities for retrying operations with exponential backoff.

This module provides decorators for retrying both async and synchronous callables.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from .logger import setup_logging

logger = setup_logging(__name__)

P = ParamSpec("P")
R = TypeVar("R")
ExceptionTypes = tuple[type[BaseException], ...]


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: ExceptionTypes = (Exception,),
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorate an async function to retry on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retries after the initial attempt.
        base_delay: Initial delay between retries (seconds).
        max_delay: Maximum delay between retries (seconds).
        exponential_base: Base for exponential backoff calculation.
        exceptions: Exception types to catch and retry.

    Returns:
        A decorator which wraps an async callable with retry logic.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: BaseException | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - caller controls exceptions tuple
                    last_exception = exc

                    if attempt == max_retries:
                        raise

                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    logger.warning(
                        "Retry %s/%s for %s after %.2fs. Error: %s",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        delay,
                        str(exc)[:100],
                    )
                    await asyncio.sleep(delay)

            if last_exception is not None:
                raise last_exception

            raise RuntimeError("retry_with_backoff reached an unexpected state")

        return wrapper

    return decorator


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: ExceptionTypes = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a sync function to retry on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retries after the initial attempt.
        base_delay: Initial delay between retries (seconds).
        max_delay: Maximum delay between retries (seconds).
        exponential_base: Base for exponential backoff calculation.
        exceptions: Exception types to catch and retry.

    Returns:
        A decorator which wraps a sync callable with retry logic.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: BaseException | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - caller controls exceptions tuple
                    last_exception = exc

                    if attempt == max_retries:
                        raise

                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    logger.warning(
                        "Retry %s/%s for %s after %.2fs. Error: %s",
                        attempt + 1,
                        max_retries,
                        func.__name__,
                        delay,
                        str(exc)[:100],
                    )
                    time.sleep(delay)

            if last_exception is not None:
                raise last_exception

            raise RuntimeError("retry_sync reached an unexpected state")

        return wrapper

    return decorator
