"""Session-level caching for performance optimization.

This module provides a thread-safe cache for storing results during a single
command execution. The cache is designed to be cleared between commands to
ensure data freshness while reducing redundant operations.
"""

import time
from threading import Lock
from typing import Any, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class SessionCache:
    """Thread-safe cache for session-level (single command) data.

    This cache stores results with optional TTL (time-to-live) to balance
    performance with data freshness. It's intended to be used within a
    single command execution and cleared afterward.

    Example:
        cache = SessionCache()
        cache.set("team_members", members, ttl=60)
        result = cache.get("team_members")  # Returns cached value if not expired

    Attributes:
        _cache: Dictionary mapping cache keys to (value, timestamp) tuples
        _ttl: Dictionary mapping cache keys to their TTL in seconds
        _lock: Thread lock for concurrent access safety
    """

    def __init__(self) -> None:
        """Initialize an empty cache with no stored values."""
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl: dict[str, float] = {}
        self._lock = Lock()
        logger.debug("session_cache_initialized")

    def get(self, key: str) -> Any | None:
        """Retrieve a value from cache if it exists and hasn't expired.

        Args:
            key: The cache key to retrieve

        Returns:
            The cached value if found and not expired, None otherwise

        Example:
            value = cache.get("issues")
            if value is not None:
                # Use cached value
                print(value)
        """
        with self._lock:
            if key not in self._cache:
                logger.debug("cache_miss", key=key)
                return None

            value, timestamp = self._cache[key]
            ttl = self._ttl.get(key, float("inf"))

            # Check if cached value has expired
            if time.time() - timestamp > ttl:
                logger.debug("cache_expired", key=key)
                del self._cache[key]
                if key in self._ttl:
                    del self._ttl[key]
                return None

            logger.debug("cache_hit", key=key)
            return value

    def set(self, key: str, value: Any, ttl: float = float("inf")) -> None:
        """Store a value in cache with optional TTL.

        Args:
            key: The cache key to store under
            value: The value to cache
            ttl: Time-to-live in seconds (default: infinite)

        Example:
            cache.set("team_members", members, ttl=60)  # Expires after 60s
            cache.set("config", config)  # Never expires
        """
        with self._lock:
            self._cache[key] = (value, time.time())
            self._ttl[key] = ttl
            logger.debug("cache_set", key=key, ttl=ttl)

    def clear(self) -> None:
        """Clear all cached values.

        Use this at the end of a command to reset for the next execution.

        Example:
            # After command completes
            cache.clear()
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._ttl.clear()
            logger.debug("cache_cleared", entries_cleared=count)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache.

        Useful for invalidating stale data without clearing entire cache.

        Args:
            key: The cache key to remove

        Example:
            cache.invalidate("team_members")  # Force refresh on next access
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._ttl:
                    del self._ttl[key]
                logger.debug("cache_invalidated", key=key)

    def get_stats(self) -> dict[str, Any]:
        """Get current cache statistics.

        Returns:
            Dictionary with cache metrics:
                - entries: Number of cached items
                - keys: List of all cache keys

        Example:
            stats = cache.get_stats()
            print(f"Cached {stats['entries']} items")
        """
        with self._lock:
            return {
                "entries": len(self._cache),
                "keys": list(self._cache.keys()),
            }


# Global session cache instance
_session_cache = SessionCache()


def get_session_cache() -> SessionCache:
    """Get the global session cache instance.

    Returns:
        The singleton SessionCache instance

    Example:
        cache = get_session_cache()
        cache.set("data", value)
    """
    return _session_cache


def clear_session_cache() -> None:
    """Clear the global session cache.

    Call this at the beginning of each command execution to ensure
    a clean slate while allowing intra-command caching benefits.

    Example:
        # In CLI command entry point
        clear_session_cache()
        # ... run command
    """
    _session_cache.clear()


def cache_result(key: str, ttl: float = float("inf")):
    """Decorator to cache function results in session cache.

    Args:
        key: The cache key to use (can contain {arg_name} placeholders)
        ttl: Time-to-live in seconds

    Example:
        @cache_result("team_members", ttl=60)
        def get_team_members() -> list[str]:
            # ... fetch from API
            return members

        # Second call within 60s returns cached result
        members = get_team_members()
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to get from cache first
            cached = get_session_cache().get(key)
            if cached is not None:
                return cached

            # Call function and cache result
            result = func(*args, **kwargs)
            get_session_cache().set(key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
