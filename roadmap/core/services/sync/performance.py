"""Performance optimizations for sync operations."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from structlog import get_logger

if TYPE_CHECKING:
    from roadmap.core.domain.issue import Issue

logger = get_logger(__name__)


class SyncCache:
    """In-memory cache for sync operation results."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize sync cache.

        Args:
            ttl_seconds: Time-to-live for cached items in seconds (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            return None

        value, timestamp = self._cache[key]
        if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl_seconds):
            # Expired
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, datetime.utcnow())

    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dict with hits, misses, and hit rate
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100.0) if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_items": len(self._cache),
        }


# Global cache instance
_sync_cache = SyncCache()


def get_sync_cache() -> SyncCache:
    """Get the global sync cache instance.

    Returns:
        SyncCache instance
    """
    return _sync_cache


def cache_result(ttl_seconds: int = 300):
    """Decorator to cache function results.

    Args:
        ttl_seconds: Time-to-live for cached results

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.sha256(":".join(key_parts).encode()).hexdigest()[:16]

            cache = get_sync_cache()
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                logger.debug(
                    "cache_hit",
                    function=func.__name__,
                    key=cache_key,
                    action="cache_lookup",
                )
                return cached_value

            # Cache miss - compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result)

            logger.debug(
                "cache_miss",
                function=func.__name__,
                key=cache_key,
                action="cache_store",
            )

            return result

        return wrapper

    return decorator


class IssueIndexer:
    """Indexes issues for fast lookup during sync operations."""

    def __init__(self):
        """Initialize issue indexer."""
        self._by_id: dict[str, Issue] = {}
        self._by_github_number: dict[int, Issue] = {}
        self._by_milestone: dict[str, list[Issue]] = {}
        self._indexed_at: datetime | None = None

    def index_issues(self, issues: list[Issue]) -> None:
        """Build indexes for fast lookups.

        Args:
            issues: List of issues to index
        """
        self._by_id.clear()
        self._by_github_number.clear()
        self._by_milestone.clear()

        for issue in issues:
            # Index by ID
            self._by_id[issue.id] = issue

            # Index by GitHub issue number
            github_number = issue.remote_ids.get("github")
            if github_number:
                self._by_github_number[int(github_number)] = issue

            # Index by milestone
            if issue.milestone:
                if issue.milestone not in self._by_milestone:
                    self._by_milestone[issue.milestone] = []
                self._by_milestone[issue.milestone].append(issue)

        self._indexed_at = datetime.utcnow()

        logger.info(
            "issues_indexed",
            total_issues=len(issues),
            by_id=len(self._by_id),
            by_github=len(self._by_github_number),
            milestones=len(self._by_milestone),
            action="index_issues",
        )

    def get_by_id(self, issue_id: str) -> Issue | None:
        """Get issue by ID.

        Args:
            issue_id: Issue ID

        Returns:
            Issue or None if not found
        """
        return self._by_id.get(issue_id)

    def get_by_github_number(self, github_number: int) -> Issue | None:
        """Get issue by GitHub issue number.

        Args:
            github_number: GitHub issue number

        Returns:
            Issue or None if not found
        """
        return self._by_github_number.get(github_number)

    def get_by_milestone(self, milestone: str) -> list[Issue]:
        """Get all issues for a milestone.

        Args:
            milestone: Milestone name

        Returns:
            List of issues (empty if none found)
        """
        return self._by_milestone.get(milestone, [])

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if index is stale and needs rebuilding.

        Args:
            max_age_seconds: Maximum age in seconds before index is stale

        Returns:
            True if index should be rebuilt
        """
        if self._indexed_at is None:
            return True

        age = (datetime.utcnow() - self._indexed_at).total_seconds()
        return age > max_age_seconds

    def clear(self) -> None:
        """Clear all indexes."""
        self._by_id.clear()
        self._by_github_number.clear()
        self._by_milestone.clear()
        self._indexed_at = None


# Global indexer instance
_issue_indexer = IssueIndexer()


def get_issue_indexer() -> IssueIndexer:
    """Get the global issue indexer instance.

    Returns:
        IssueIndexer instance
    """
    return _issue_indexer
