"""Tests for status aggregation utilities."""

from roadmap.common.utils.status_utils import StatusSummary
from roadmap.core.domain.health import HealthStatus


def test_count_by_status_empty_items_returns_empty_dict():
    """No items should produce an empty counter dict."""
    assert StatusSummary.count_by_status([]) == {}


def test_count_by_status_mixed_values_aggregates_counts():
    """Mixed statuses should be grouped by enum value."""
    items = [
        ("a", HealthStatus.HEALTHY),
        ("b", HealthStatus.DEGRADED),
        ("c", HealthStatus.HEALTHY),
    ]

    assert StatusSummary.count_by_status(items) == {
        "healthy": 2,
        "degraded": 1,
    }


def test_summarize_checks_includes_total_and_missing_enum_members():
    """Summary should include zero-count enum members when enum class provided."""
    checks = {
        "db": (HealthStatus.HEALTHY, "ok"),
    }

    summary = StatusSummary.summarize_checks(checks, HealthStatus)

    assert summary["total"] == 1
    assert summary["healthy"] == 1
    assert summary["degraded"] == 0
    assert summary["unhealthy"] == 0


def test_summarize_checks_infers_enum_from_first_status():
    """When enum class omitted, function should infer class from first status."""
    checks = {
        "db": (HealthStatus.DEGRADED, "lag"),
        "git": (HealthStatus.DEGRADED, "lag"),
    }

    summary = StatusSummary.summarize_checks(checks)

    assert summary["total"] == 2
    assert summary["degraded"] == 2
    assert summary["healthy"] == 0
    assert summary["unhealthy"] == 0


def test_summarize_checks_empty_without_enum_has_only_total():
    """With no checks and no enum class, summary should only expose total."""
    assert StatusSummary.summarize_checks({}) == {"total": 0}
