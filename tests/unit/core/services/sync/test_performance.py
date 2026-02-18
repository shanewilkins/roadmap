"""Tests for sync performance helpers (cache and issue indexer)."""

from __future__ import annotations

from datetime import datetime, timedelta

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync import performance


def test_sync_cache_get_set_and_stats() -> None:
    cache = performance.SyncCache(ttl_seconds=300)

    assert cache.get("missing") is None
    cache.set("k", {"value": 1})
    assert cache.get("k") == {"value": 1}

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["total_requests"] == 2
    assert stats["cached_items"] == 1


def test_sync_cache_expires_items() -> None:
    cache = performance.SyncCache(ttl_seconds=1)
    cache._cache["k"] = ("v", datetime.utcnow() - timedelta(seconds=5))

    assert cache.get("k") is None
    assert "k" not in cache._cache


def test_sync_cache_clear_resets_state() -> None:
    cache = performance.SyncCache(ttl_seconds=300)
    cache.set("k", "v")
    _ = cache.get("k")

    cache.clear()

    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["cached_items"] == 0


def test_cache_result_decorator_uses_cache(monkeypatch) -> None:
    local_cache = performance.SyncCache(ttl_seconds=300)
    monkeypatch.setattr(
        "roadmap.core.services.sync.performance.get_sync_cache",
        lambda: local_cache,
    )

    calls = {"count": 0}

    @performance.cache_result(ttl_seconds=300)
    def _compute(a: int, b: int = 0) -> int:
        calls["count"] += 1
        return a + b

    assert _compute(2, b=3) == 5
    assert _compute(2, b=3) == 5
    assert calls["count"] == 1


def test_issue_indexer_indexes_and_retrieves() -> None:
    issue1 = Issue(
        id="id1", title="Issue 1", remote_ids={"github": "101"}, milestone="M1"
    )
    issue2 = Issue(id="id2", title="Issue 2", remote_ids={}, milestone="M1")
    issue3 = Issue(
        id="id3", title="Issue 3", remote_ids={"github": 202}, milestone=None
    )

    indexer = performance.IssueIndexer()
    indexer.index_issues([issue1, issue2, issue3])

    assert indexer.get_by_id("id1") is issue1
    assert indexer.get_by_github_number(101) is issue1
    assert indexer.get_by_github_number(202) is issue3
    assert indexer.get_by_milestone("M1") == [issue1, issue2]
    assert indexer.get_by_milestone("missing") == []
    assert indexer.is_stale(max_age_seconds=300) is False


def test_issue_indexer_stale_and_clear() -> None:
    indexer = performance.IssueIndexer()

    assert indexer.is_stale() is True

    issue = Issue(id="id1", title="Issue", remote_ids={}, milestone=None)
    indexer.index_issues([issue])
    indexer._indexed_at = datetime.utcnow() - timedelta(seconds=301)
    assert indexer.is_stale(max_age_seconds=300) is True

    indexer.clear()
    assert indexer.get_by_id("id1") is None
    assert indexer.get_by_github_number(1) is None
    assert indexer.get_by_milestone("M1") == []
    assert indexer.is_stale() is True


def test_global_accessors_return_singletons() -> None:
    cache_a = performance.get_sync_cache()
    cache_b = performance.get_sync_cache()
    index_a = performance.get_issue_indexer()
    index_b = performance.get_issue_indexer()

    assert cache_a is cache_b
    assert index_a is index_b
