"""Tests for sync metrics repository persistence and query behavior."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.adapters.persistence.sync_metrics_repository import SyncMetricsRepository
from roadmap.core.observability.sync_metrics import SyncMetrics


def _metrics(operation_id: str, backend: str = "github") -> SyncMetrics:
    return SyncMetrics(
        operation_id=operation_id,
        backend_type=backend,
        start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        duration_seconds=2.5,
        duplicates_detected=3,
        conflicts_detected=1,
        errors_count=0,
    )


def test_save_and_get_latest_roundtrip(tmp_path) -> None:
    db = DatabaseManager(tmp_path / "sync_metrics.db")
    repo = SyncMetricsRepository(db)

    assert repo.save(_metrics("op-1", "github")) is True

    latest = repo.get_latest()
    assert latest is not None
    assert latest.operation_id == "op-1"
    assert latest.backend_type == "github"
    assert latest.duration_seconds == 2.5


def test_get_latest_with_backend_filter(tmp_path) -> None:
    db = DatabaseManager(tmp_path / "sync_metrics.db")
    repo = SyncMetricsRepository(db)

    repo.save(_metrics("op-gh", "github"))
    repo.save(_metrics("op-vg", "vanilla_git"))

    latest_gh = repo.get_latest("github")
    latest_vg = repo.get_latest("vanilla_git")
    latest_none = repo.get_latest("missing")

    assert latest_gh is not None and latest_gh.operation_id == "op-gh"
    assert latest_vg is not None and latest_vg.operation_id == "op-vg"
    assert latest_none is None


def test_list_by_date_and_get_by_operation_id(tmp_path) -> None:
    db = DatabaseManager(tmp_path / "sync_metrics.db")
    repo = SyncMetricsRepository(db)

    repo.save(_metrics("op-lookup", "github"))

    listed = repo.list_by_date(days=30)
    by_id = repo.get_by_operation_id("op-lookup")
    missing = repo.get_by_operation_id("does-not-exist")

    assert len(listed) >= 1
    assert by_id is not None
    assert by_id.operation_id == "op-lookup"
    assert missing is None


def test_get_statistics_and_parse_failures_are_tolerated(tmp_path) -> None:
    db = DatabaseManager(tmp_path / "sync_metrics.db")
    repo = SyncMetricsRepository(db)

    repo.save(_metrics("op-1", "github"))
    repo.save(_metrics("op-2", "github"))

    conn = db._get_connection()
    conn.execute(
        """
        INSERT INTO sync_metrics (id, operation_id, backend_type, duration_seconds, metrics_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "bad-row",
            "bad-op",
            "github",
            0.0,
            "{bad-json",
            datetime.now(UTC).isoformat(),
        ),
    )

    stats = repo.get_statistics(backend_type="github", days=30)

    assert stats["total_syncs"] == 2
    assert stats["total_duplicates_detected"] == 6
    assert stats["total_conflicts_detected"] == 2
    assert stats["total_errors"] == 0
    assert stats["backends"] == "github"


def test_delete_old_metrics_and_empty_stats(tmp_path) -> None:
    db = DatabaseManager(tmp_path / "sync_metrics.db")
    repo = SyncMetricsRepository(db)
    repo.save(_metrics("op-new", "github"))

    conn = db._get_connection()
    old_metrics_json = json.dumps(_metrics("op-old", "github").to_dict())
    conn.execute(
        """
        INSERT INTO sync_metrics (id, operation_id, backend_type, duration_seconds, metrics_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "old-row",
            "op-old",
            "github",
            2.5,
            old_metrics_json,
            (datetime.now(UTC) - timedelta(days=365)).isoformat(),
        ),
    )

    deleted = repo.delete_old_metrics(days=90)
    assert deleted >= 1

    empty_stats = repo.get_statistics(backend_type="missing", days=1)
    assert empty_stats["total_syncs"] == 0
    assert empty_stats["avg_duration_seconds"] == 0.0


def test_dict_to_metrics_sets_known_attributes_only() -> None:
    payload = {
        "operation_id": "op-x",
        "backend_type": "github",
        "duration_seconds": 1.25,
        "duplicates_detected": 4,
        "unknown_field": "ignored",
    }

    metrics = SyncMetricsRepository._dict_to_metrics(payload)
    assert metrics.operation_id == "op-x"
    assert metrics.backend_type == "github"
    assert metrics.duration_seconds == 1.25
    assert metrics.duplicates_detected == 4
    assert not hasattr(metrics, "unknown_field")
