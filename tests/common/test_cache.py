"""Unit tests for the session cache module."""

import time

from roadmap.common.cache import (
    SessionCache,
    cache_result,
    clear_session_cache,
    get_session_cache,
)


class TestSessionCache:
    """Test SessionCache functionality."""

    def test_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = SessionCache()
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a non-existent key returns None."""
        cache = SessionCache()

        assert cache.get("nonexistent") is None

    def test_cache_expiration(self):
        """Test that cached values expire after TTL."""
        cache = SessionCache()
        cache.set("key1", "value1", ttl=0.1)  # 100ms TTL

        # Should be available immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_without_ttl(self):
        """Test cache with infinite TTL."""
        cache = SessionCache()
        cache.set("key1", "value1")  # No TTL = infinite

        # Should still be available after long wait
        time.sleep(0.1)
        assert cache.get("key1") == "value1"

    def test_clear(self):
        """Test clearing entire cache."""
        cache = SessionCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_invalidate_specific_key(self):
        """Test invalidating a specific cache key."""
        cache = SessionCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.invalidate("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_invalidate_nonexistent_key(self):
        """Test invalidating a non-existent key doesn't raise error."""
        cache = SessionCache()

        # Should not raise
        cache.invalidate("nonexistent")

    def test_get_stats_empty(self):
        """Test stats for empty cache."""
        cache = SessionCache()

        stats = cache.get_stats()

        assert stats["entries"] == 0
        assert stats["keys"] == []

    def test_get_stats_with_entries(self):
        """Test stats with cached entries."""
        cache = SessionCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats["entries"] == 2
        assert set(stats["keys"]) == {"key1", "key2"}

    def test_cache_complex_types(self):
        """Test caching complex types."""
        cache = SessionCache()
        data = {"nested": {"list": [1, 2, 3]}, "count": 42}

        cache.set("complex", data)

        retrieved = cache.get("complex")
        assert retrieved == data

    def test_global_cache(self):
        """Test the global cache instance."""
        cache = get_session_cache()
        cache.set("global_key", "global_value")

        # Same instance
        cache2 = get_session_cache()
        assert cache2.get("global_key") == "global_value"

    def test_clear_global_cache(self):
        """Test clearing the global cache."""
        cache = get_session_cache()
        cache.set("key1", "value1")

        clear_session_cache()

        # Should be cleared
        assert cache.get("key1") is None

    def test_thread_safety(self):
        """Test concurrent access to cache."""
        import threading

        cache = SessionCache()
        results = []

        def writer(i):
            cache.set(f"key{i}", f"value{i}")
            results.append(cache.get(f"key{i}"))

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should have written successfully
        assert len(results) == 10
        assert all(r is not None for r in results)


class TestCacheDecorator:
    """Test the @cache_result decorator."""

    def test_cache_result_decorator(self):
        """Test function result is cached."""
        call_count = 0

        @cache_result("test_func", ttl=60)
        def expensive_function():
            nonlocal call_count
            call_count += 1
            return "result"

        # Clear cache first
        clear_session_cache()

        # First call should execute
        result1 = expensive_function()
        assert result1 == "result"
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function()
        assert result2 == "result"
        assert call_count == 1  # Still 1, not called again

    def test_cache_result_expiration(self):
        """Test cache expiration with decorator."""
        call_count = 0

        @cache_result("test_func", ttl=0.1)
        def function_with_ttl():
            nonlocal call_count
            call_count += 1
            return "result"

        clear_session_cache()

        # First call
        function_with_ttl()
        assert call_count == 1

        # Still cached
        function_with_ttl()
        assert call_count == 1

        # Wait for expiration
        time.sleep(0.15)

        # Cache expired, function called again
        function_with_ttl()
        assert call_count == 2
