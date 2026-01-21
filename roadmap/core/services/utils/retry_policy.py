import time


class RetryPolicy:
    """Simple exponential backoff retry policy.

    Example:
        rp = RetryPolicy(max_retries=3, base_delay=0.5, factor=2.0)
        for attempt in range(1, rp.max_retries + 1):
            try:
                ...
            except Exception:
                if attempt == rp.max_retries:
                    raise
                time.sleep(rp.get_backoff_delay(attempt))
    """

    def __init__(
        self, max_retries: int = 3, base_delay: float = 0.5, factor: float = 2.0
    ):
        """Initialize RetryPolicy.

        Args:
            max_retries: Maximum number of retry attempts.
            base_delay: Initial delay in seconds.
            factor: Exponential factor for delay increase.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.factor = factor

    def get_backoff_delay(self, attempt: int) -> float:
        """Get delay in seconds for a given attempt (1-based)."""
        if attempt <= 1:
            return 0.0
        return self.base_delay * (self.factor ** (attempt - 1))

    def sleep_for_attempt(self, attempt: int) -> None:
        delay = self.get_backoff_delay(attempt)
        if delay > 0:
            time.sleep(delay)


__all__ = ["RetryPolicy"]
