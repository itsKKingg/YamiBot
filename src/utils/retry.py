"""
Retry Logic with Exponential Backoff for YamiBot

This module provides retry functionality with exponential backoff to handle
transient failures gracefully.
"""

import asyncio
from typing import Callable, Awaitable, Any, Optional
from .logger import setup_logging

logger = setup_logging(__name__)

async def retry_with_backoff(
    coro_func: Callable[[], Awaitable[Any]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_delay: float = 60.0
) -> Any:
    """
    Retry a coroutine with exponential backoff
    
    Args:
        coro_func: Async function to call (must return Awaitable)
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        backoff_multiplier: Multiplier for exponential backoff
        max_delay: Maximum delay between retries
        
    Returns:
        Result of the coroutine function
        
    Raises:
        Exception: The last exception raised after all retries exhausted
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                logger.debug(f"Retry attempt {attempt}/{max_attempts}")
            else:
                logger.debug(f"Attempt 1/{max_attempts}")
                
            result = await coro_func()
            
            if attempt > 1:
                logger.info(f"Retry attempt {attempt} succeeded")
                
            return result
            
        except Exception as e:
            last_exception = e
            
            if attempt == max_attempts:
                logger.error(f"All {max_attempts} attempts failed: {str(e)}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (backoff_multiplier ** (attempt - 1)), max_delay)
            
            logger.warning(
                f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}. "
                f"Retrying in {delay:.1f}s..."
            )
            
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    else:
        raise Exception("All retry attempts failed without catching exception")