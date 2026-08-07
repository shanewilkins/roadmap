"""Tests for sync metrics formatter utilities and table builders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from rich.console import Console

from roadmap.core.observability.sync_metrics import SyncMetrics
from roadmap.presentation.formatters import sync_metrics_formatter as formatter


def _render(table) -> str:
    console = Console(width=180, record=True)
    console.print(table)
    return console.export_text()


def _metrics(**overrides) -> SyncMetrics:
    metrics = SyncMetrics(
        backend_type="github",
        start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        duration_seconds=2.25,
    )
    for key, value in overrides.items():
        setattr(metrics, key, value)
    return metrics


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.125, "125ms"),
        (2.25, "2.2s"),
        (120.0, "2.0m"),
        (7200.0, "2.0h"),
    ],
)
def test_format_duration_ranges(seconds: float, expected: str) -> None:
    assert formatter.format_duration(seconds) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (10, "10"),
        (10.0, "10"),
        (10.5, "10.5"),
    ],
)
def test_format_count_handles_int_and_float(value: int | float, expected: str) -> None:
    assert formatter.format_count(value) == expected


def test_format_percentage_with_custom_decimals() -> None:
    assert formatter.format_percentage(12.3456) == "12.3%"
    assert formatter.format_percentage(12.3456, decimals=2) == "12.35%"


def test_create_metrics_summary_table_base_rows() -> None:
    table = formatter.create_metrics_summary_table(_metrics(), verbose=False)
    output = _render(table)

    assert "═══ Summary ═══" in output
    assert "Backend" in output
    assert "github" in output
    assert "Started" in output
    assert "Duration" in output


def test_summary_table_shows_operational_sections_when_values_present() -> None:
    table = formatter.create_metrics_summary_table(
        _metrics(
            local_issues_before_dedup=10,
            local_issues_after_dedup=8,
            local_dedup_reduction_pct=20.0,
            remote_issues_before_dedup=5,
            remote_issues_after_dedup=4,
            remote_dedup_reduction_pct=20.0,
            issues_fetched=7,
            issues_pushed=3,
            issues_pulled=2,
            duplicates_detected=2,
            duplicates_auto_resolved=1,
            duplicates_manual_resolved=1,
            conflicts_detected=3,
            sync_links_created=4,
            orphaned_links=1,
        ),
        verbose=False,
    )
    output = _render(table)

    assert "═══ Deduplication ═══" in output
    assert "Local Issues (Before)" in output
    assert "Remote Issues (After)" in output
    assert "═══ Sync Operations ═══" in output
    assert "Issues Fetched" in output
    assert "═══ Duplicates ═══" in output
    assert "Auto-Resolved" in output
    assert "Manual Resolution" in output
    assert "═══ Conflicts ═══" in output
    assert "Conflicts Detected" in output
    assert "═══ Sync Links ═══" in output
    assert "Orphaned Links" in output


def test_summary_table_verbose_shows_performance_and_phase_timings() -> None:
    table = formatter.create_metrics_summary_table(
        _metrics(
            cache_hit_rate=0.5,
            database_query_time=0.25,
            total_api_calls=12,
            circuit_breaker_state="half-open",
            fetch_phase_duration=1.2,
            push_phase_duration=0.8,
            pull_phase_duration=0.7,
            analysis_phase_duration=0.3,
            merge_phase_duration=0.4,
            conflict_resolution_duration=0.2,
        ),
        verbose=True,
    )
    output = _render(table)

    assert "═══ Performance ═══" in output
    assert "Cache Hit Rate" in output
    assert "50.0%" in output
    assert "DB Query Time" in output
    assert "API Calls" in output
    assert "Circuit Breaker" in output
    assert "half-open" in output
    assert "Fetch Time" in output
    assert "Push Time" in output
    assert "Pull Time" in output
    assert "Analysis Time" in output
    assert "Merge Time" in output
    assert "Conflict Resolution Time" in output


def test_summary_table_shows_errors_section_when_errors_present() -> None:
    table = formatter.create_metrics_summary_table(
        _metrics(errors_count=3),
        verbose=False,
    )
    output = _render(table)

    assert "═══ Errors ═══" in output
    assert "Error Count" in output
    assert "3" in output


def test_create_metrics_history_table_respects_limit() -> None:
    metrics_list = [
        _metrics(
            backend_type="github", start_time=datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        ),
        _metrics(
            backend_type="gitlab", start_time=datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        ),
        _metrics(
            backend_type="local", start_time=datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
        ),
    ]

    table = formatter.create_metrics_history_table(metrics_list, limit=2)
    output = _render(table)

    assert "Sync Metrics History" in output
    assert "github" in output
    assert "gitlab" in output
    assert "local" not in output


def test_create_metrics_history_table_time_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(formatter, "datetime", _FixedDateTime)

    metrics_list = [
        _metrics(start_time=fixed_now - timedelta(seconds=30), backend_type="a"),
        _metrics(start_time=fixed_now - timedelta(minutes=10), backend_type="b"),
        _metrics(start_time=fixed_now - timedelta(hours=3), backend_type="c"),
        _metrics(start_time=fixed_now - timedelta(days=2), backend_type="d"),
    ]

    table = formatter.create_metrics_history_table(metrics_list, limit=10)
    output = _render(table)

    assert "just now" in output
    assert "10m ago" in output
    assert "3h ago" in output
    assert "2025-12-31" in output
