"""
Async utilities for handling concurrent operations with timeouts
Prevents hanging requests and provides better error handling
"""

import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)


async def run_with_timeout(coro: Coroutine, timeout: int = 30) -> Any:
    """
    Run a coroutine with a timeout

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds (default 30)

    Returns:
        Result of the coroutine

    Raises:
        asyncio.TimeoutError: If coroutine takes longer than timeout
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        logger.debug(f"Async operation completed within {timeout}s")
        return result
    except asyncio.TimeoutError:
        logger.error(f"Async operation timed out after {timeout}s")
        raise TimeoutError(f"Operation timed out after {timeout} seconds")


async def run_multiple_with_timeout(
    coros: list,
    timeout: int = 30,
    return_exceptions: bool = True
) -> list:
    """
    Run multiple coroutines with a timeout for all

    Args:
        coros: List of coroutines to run
        timeout: Timeout in seconds for all operations
        return_exceptions: If True, return exceptions as results instead of raising

    Returns:
        List of results (may include exceptions if return_exceptions=True)

    Raises:
        asyncio.TimeoutError: If not all operations complete within timeout
    """
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*coros, return_exceptions=return_exceptions),
            timeout=timeout
        )
        logger.debug(f"All {len(coros)} operations completed within {timeout}s")
        return results
    except asyncio.TimeoutError:
        logger.error(f"Not all operations completed within {timeout}s timeout")
        raise TimeoutError(f"Operations timed out after {timeout} seconds")


def run_until_complete_with_timeout(
    loop: asyncio.AbstractEventLoop,
    coro: Coroutine,
    timeout: int = 30
) -> Any:
    """
    Run coroutine in Flask context with timeout protection

    Args:
        loop: Event loop
        coro: Coroutine to run
        timeout: Timeout in seconds

    Returns:
        Result of the coroutine

    Raises:
        TimeoutError: If operation exceeds timeout
    """
    try:
        # Create a task with timeout
        task = loop.create_task(coro)
        # Wait with timeout
        result = loop.run_until_complete(
            asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        )
        logger.debug(f"Operation completed successfully")
        return result
    except asyncio.TimeoutError:
        task.cancel()
        logger.error(f"Operation timed out after {timeout}s")
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    except Exception as e:
        logger.error(f"Error during async operation: {e}")
        raise


async def gather_with_limits(
    *coros,
    timeout: int = 30,
    return_exceptions: bool = True,
    max_concurrent: int = None
) -> list:
    """
    Run multiple coroutines with concurrency limits and timeout

    Args:
        *coros: Coroutines to run
        timeout: Timeout for all operations
        return_exceptions: If True, return exceptions as results
        max_concurrent: Maximum concurrent operations (None = no limit)

    Returns:
        List of results
    """
    if max_concurrent is None:
        # No limit, use regular gather
        return await run_multiple_with_timeout(
            list(coros),
            timeout=timeout,
            return_exceptions=return_exceptions
        )

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_coro(coro):
        async with semaphore:
            try:
                return await coro
            except Exception as e:
                if return_exceptions:
                    return e
                raise

    # Run all with semaphore limit
    return await run_multiple_with_timeout(
        [limited_coro(coro) for coro in coros],
        timeout=timeout,
        return_exceptions=return_exceptions
    )
