"""Retry logic with exponential backoff for handling transient failures."""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
):
    """Retry decorator with exponential backoff.

    This decorator automatically retries a function if it raises one of the
    specified exceptions. The delay between retries increases exponentially
    using the backoff factor.

    Args:
        max_attempts: Maximum number of attempts (including the first try)
        delay: Initial delay in seconds between retries
        backoff: Multiplier for delay after each retry (exponential backoff)
        exceptions: Tuple of exception types to catch and retry on
        on_retry: Optional callback function called before each retry.
                 Takes (exception, attempt_number) as arguments.

    Example:
        @retry(max_attempts=5, delay=1.0, backoff=2.0, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            # ... make network request
            pass

        The retry delays will be: 1s, 2s, 4s, 8s
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            current_delay = delay
            last_exception: Exception | None = None

            while attempt < max_attempts:
                attempt += 1

                try:
                    result = func(*args, **kwargs)

                    # Log success if we had previous failures
                    if attempt > 1:
                        logger.info(
                            "retry_succeeded",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Don't retry if we've exhausted attempts
                    if attempt >= max_attempts:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise

                    # Log retry attempt
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=current_delay,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error(
                                "retry_callback_failed",
                                function=func.__name__,
                                error=str(callback_error),
                            )

                    # Wait before retrying
                    time.sleep(current_delay)

                    # Exponential backoff
                    current_delay *= backoff

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Retry logic failed for {func.__name__}")

        return wrapper  # type: ignore

    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
):
    """Async version of retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the first try)
        delay: Initial delay in seconds between retries
        backoff: Multiplier for delay after each retry (exponential backoff)
        exceptions: Tuple of exception types to catch and retry on
        on_retry: Optional callback function called before each retry

    Example:
        @async_retry(max_attempts=5, delay=1.0, backoff=2.0)
        async def fetch_data():
            # ... make async network request
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio

            attempt = 0
            current_delay = delay
            last_exception: Exception | None = None

            while attempt < max_attempts:
                attempt += 1

                try:
                    result = await func(*args, **kwargs)

                    # Log success if we had previous failures
                    if attempt > 1:
                        logger.info(
                            "async_retry_succeeded",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Don't retry if we've exhausted attempts
                    if attempt >= max_attempts:
                        logger.error(
                            "async_retry_exhausted",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise

                    # Log retry attempt
                    logger.warning(
                        "async_retry_attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=current_delay,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                    # Call on_retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error(
                                "async_retry_callback_failed",
                                function=func.__name__,
                                error=str(callback_error),
                            )

                    # Wait before retrying (async sleep)
                    await asyncio.sleep(current_delay)

                    # Exponential backoff
                    current_delay *= backoff

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Async retry logic failed for {func.__name__}")

        return wrapper  # type: ignore

    return decorator


class RetryConfig:
    """Configuration for retry behavior.

    This class provides a convenient way to share retry configuration
    across multiple operations.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of attempts
            delay: Initial delay in seconds
            backoff: Exponential backoff multiplier
            exceptions: Exception types to retry on
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def __call__(self, func: F) -> F:
        """Use config as a decorator."""
        return retry(
            max_attempts=self.max_attempts,
            delay=self.delay,
            backoff=self.backoff,
            exceptions=self.exceptions,
        )(func)

    def async_decorator(self, func: F) -> F:
        """Use config as an async decorator."""
        return async_retry(
            max_attempts=self.max_attempts,
            delay=self.delay,
            backoff=self.backoff,
            exceptions=self.exceptions,
        )(func)


# Predefined retry configurations for common scenarios
NETWORK_RETRY = RetryConfig(
    max_attempts=5,
    delay=1.0,
    backoff=2.0,
    exceptions=(ConnectionError, TimeoutError, OSError),
)

API_RETRY = RetryConfig(
    max_attempts=3,
    delay=0.5,
    backoff=1.5,
    exceptions=(ConnectionError, TimeoutError),
)

DATABASE_RETRY = RetryConfig(
    max_attempts=3,
    delay=0.1,
    backoff=2.0,
    exceptions=(Exception,),  # Database-specific exceptions would go here
)
