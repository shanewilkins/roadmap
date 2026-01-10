import time
from collections.abc import Iterable
from typing import Any

from structlog import get_logger

from roadmap.core.services.retry_policy import RetryPolicy

logger = get_logger(__name__)


class RemoteFetcher:
    """Utility for fetching remote issue data via an adapter.

    Adds retry/backoff logic and basic rate-limit handling to adapter calls.
    Prefer batch APIs (`pull_issues`) when available; fall back to
    per-item APIs (`pull_issue`) otherwise.
    """

    DEFAULT_RETRY_POLICY = RetryPolicy(max_retries=3, base_delay=0.5, factor=2.0)

    @staticmethod
    def _handle_rate_limit_from_response(resp: Any) -> float:
        """Inspect a response-like object for rate-limit headers and return sleep seconds.

        Returns 0.0 if no rate-limit sleep is required. If the response exposes
        `headers` or `raw_response` with `X-RateLimit-Remaining` and
        `X-RateLimit-Reset`, this will compute the seconds until reset.
        """
        try:
            from collections.abc import Mapping

            headers = None
            if isinstance(resp, Mapping):
                headers = resp.get("headers")
            else:
                headers = getattr(resp, "headers", None)
                if headers is None:
                    raw = getattr(resp, "raw_response", None)
                    if isinstance(raw, Mapping):
                        headers = raw.get("headers")
                    else:
                        headers = getattr(raw, "headers", None)

            if not headers or not isinstance(headers, Mapping):
                return 0.0

            remaining = headers.get("X-RateLimit-Remaining") or headers.get(
                "x-ratelimit-remaining"
            )
            reset = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
            if remaining is not None and str(remaining) == "0" and reset:
                try:
                    reset_ts = int(reset)
                    now_ts = int(time.time())
                    wait = max(0, reset_ts - now_ts)
                    return float(wait)
                except Exception:
                    return 0.0
        except Exception:
            return 0.0
        return 0.0

    @staticmethod
    def fetch_issue(
        adapter: Any, issue_id: str, retry_policy: RetryPolicy | None = None
    ) -> Any:
        if adapter is None:
            return None

        rp = retry_policy or RemoteFetcher.DEFAULT_RETRY_POLICY

        for attempt in range(1, rp.max_retries + 1):
            try:
                if hasattr(adapter, "pull_issue"):
                    result = adapter.pull_issue(issue_id)
                    # Check for rate-limit hints
                    sleep_for = RemoteFetcher._handle_rate_limit_from_response(result)
                    if sleep_for and sleep_for > 0:
                        logger.info(
                            "remote_rate_limited",
                            issue_id=issue_id,
                            wait_seconds=sleep_for,
                        )
                        time.sleep(sleep_for)
                    return result
                return None
            except Exception as e:
                logger.warning(
                    "remote_fetch_issue_error",
                    issue_id=issue_id,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt == rp.max_retries:
                    logger.error(
                        "remote_fetch_issue_failed", issue_id=issue_id, attempts=attempt
                    )
                    return None
                # Backoff
                delay = rp.get_backoff_delay(attempt)
                logger.info(
                    "remote_fetch_retry",
                    issue_id=issue_id,
                    attempt=attempt + 1,
                    delay=delay,
                )
                time.sleep(delay)

        return None

    @staticmethod
    def fetch_issues(
        adapter: Any, issue_ids: Iterable[str], retry_policy: RetryPolicy | None = None
    ) -> list[Any]:
        if adapter is None:
            return []

        rp = retry_policy or RemoteFetcher.DEFAULT_RETRY_POLICY

        ids = list(issue_ids)
        if not ids:
            return []

        # Try batch API first with retries
        if hasattr(adapter, "pull_issues"):
            for attempt in range(1, rp.max_retries + 1):
                try:
                    result = adapter.pull_issues(ids)
                    # If adapter returns report-like object, inspect for rate-limit
                    sleep_for = RemoteFetcher._handle_rate_limit_from_response(result)
                    if sleep_for and sleep_for > 0:
                        logger.info(
                            "remote_rate_limited_batch",
                            count=len(ids),
                            wait_seconds=sleep_for,
                        )
                        time.sleep(sleep_for)
                    return result or []
                except Exception as e:
                    logger.warning(
                        "remote_fetch_issues_error", attempt=attempt, error=str(e)
                    )
                    if attempt == rp.max_retries:
                        logger.error("remote_fetch_issues_failed", attempts=attempt)
                        break
                    delay = rp.get_backoff_delay(attempt)
                    logger.info("remote_fetch_retry", attempt=attempt + 1, delay=delay)
                    time.sleep(delay)

        # Fallback to individual calls with retries per-item
        results: list[Any] = []
        for i in ids:
            res = RemoteFetcher.fetch_issue(adapter, i, retry_policy=rp)
            results.append(res)
        return results
