"""Formatters for displaying sync metrics in the CLI.

This module provides various formatting utilities for presenting sync
metrics in a user-friendly table format.
"""

from datetime import UTC, datetime, timedelta

from rich.table import Table
from rich.text import Text

from roadmap.core.observability.sync_metrics import SyncMetrics


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_count(count: int | float) -> str:
    """Format count as a readable string.

    Args:
        count: Number to format

    Returns:
        Formatted count string
    """
    if isinstance(count, float) and count == int(count):
        count = int(count)
    return str(count)


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format percentage value.

    Args:
        value: Value between 0 and 100
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"


def _add_dedup_rows(table: Table, metrics: SyncMetrics) -> None:
    if (
        metrics.local_issues_before_dedup <= 0
        and metrics.remote_issues_before_dedup <= 0
    ):
        return

    table.add_row("[bold cyan]═══ Deduplication ═══[/bold cyan]", "")

    if metrics.local_issues_before_dedup > 0:
        table.add_row(
            "  Local Issues (Before)",
            format_count(metrics.local_issues_before_dedup),
        )
        table.add_row(
            "  Local Issues (After)",
            format_count(metrics.local_issues_after_dedup),
        )
        if metrics.local_dedup_reduction_pct > 0:
            table.add_row(
                "  Local Dedup Reduction",
                Text(
                    format_percentage(metrics.local_dedup_reduction_pct),
                    style="green",
                ),
            )

    if metrics.remote_issues_before_dedup > 0:
        table.add_row(
            "  Remote Issues (Before)",
            format_count(metrics.remote_issues_before_dedup),
        )
        table.add_row(
            "  Remote Issues (After)",
            format_count(metrics.remote_issues_after_dedup),
        )
        if metrics.remote_dedup_reduction_pct > 0:
            table.add_row(
                "  Remote Dedup Reduction",
                Text(
                    format_percentage(metrics.remote_dedup_reduction_pct),
                    style="green",
                ),
            )


def _add_sync_ops_rows(table: Table, metrics: SyncMetrics) -> None:
    if not (
        metrics.issues_fetched > 0
        or metrics.issues_pushed > 0
        or metrics.issues_pulled > 0
    ):
        return

    table.add_row("[bold cyan]═══ Sync Operations ═══[/bold cyan]", "")

    if metrics.issues_fetched > 0:
        table.add_row(
            "  Issues Fetched",
            format_count(metrics.issues_fetched),
        )
    if metrics.issues_pushed > 0:
        table.add_row(
            "  Issues Pushed",
            format_count(metrics.issues_pushed),
        )
    if metrics.issues_pulled > 0:
        table.add_row(
            "  Issues Pulled",
            format_count(metrics.issues_pulled),
        )


def _add_duplicate_rows(table: Table, metrics: SyncMetrics) -> None:
    if metrics.duplicates_detected <= 0:
        return

    table.add_row("[bold cyan]═══ Duplicates ═══[/bold cyan]", "")
    table.add_row(
        "  Duplicates Detected",
        Text(format_count(metrics.duplicates_detected), style="yellow"),
    )
    if metrics.duplicates_auto_resolved > 0:
        table.add_row(
            "  Auto-Resolved",
            Text(
                format_count(metrics.duplicates_auto_resolved),
                style="green",
            ),
        )
    if metrics.duplicates_manual_resolved > 0:
        table.add_row(
            "  Manual Resolution",
            Text(
                format_count(metrics.duplicates_manual_resolved),
                style="cyan",
            ),
        )


def _add_conflict_rows(table: Table, metrics: SyncMetrics) -> None:
    if metrics.conflicts_detected <= 0:
        return

    table.add_row("[bold cyan]═══ Conflicts ═══[/bold cyan]", "")
    table.add_row(
        "  Conflicts Detected",
        Text(format_count(metrics.conflicts_detected), style="yellow"),
    )


def _add_link_rows(table: Table, metrics: SyncMetrics) -> None:
    if metrics.sync_links_created <= 0 and metrics.orphaned_links <= 0:
        return

    table.add_row("[bold cyan]═══ Sync Links ═══[/bold cyan]", "")
    if metrics.sync_links_created > 0:
        table.add_row(
            "  Links Created",
            format_count(metrics.sync_links_created),
        )
    if metrics.orphaned_links > 0:
        table.add_row(
            "  Orphaned Links",
            Text(
                format_count(metrics.orphaned_links),
                style="yellow",
            ),
        )


def _add_performance_rows(table: Table, metrics: SyncMetrics) -> None:
    table.add_row("[bold cyan]═══ Performance ═══[/bold cyan]", "")
    if metrics.cache_hit_rate > 0:
        table.add_row(
            "  Cache Hit Rate",
            Text(
                format_percentage(metrics.cache_hit_rate * 100),
                style="green",
            ),
        )
    if metrics.database_query_time > 0:
        table.add_row(
            "  DB Query Time",
            Text(format_duration(metrics.database_query_time), style="yellow"),
        )
    if metrics.total_api_calls > 0:
        table.add_row(
            "  API Calls",
            Text(format_count(metrics.total_api_calls), style="cyan"),
        )


def create_metrics_summary_table(metrics: SyncMetrics, verbose: bool = False) -> Table:
    """Create a summary table of sync metrics.

    Args:
        metrics: SyncMetrics object to display
        verbose: Include performance and phase timing details

    Returns:
        Rich Table with sync summary metrics
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column(justify="right", style="cyan")

    table.add_row("[bold cyan]═══ Summary ═══[/bold cyan]", "")
    table.add_row("Backend", metrics.backend_type or "unknown")
    table.add_row(
        "Started",
        metrics.start_time.strftime("%Y-%m-%d %H:%M"),
    )
    table.add_row("Duration", format_duration(metrics.duration_seconds))

    _add_dedup_rows(table, metrics)
    _add_sync_ops_rows(table, metrics)
    _add_duplicate_rows(table, metrics)
    _add_conflict_rows(table, metrics)
    _add_link_rows(table, metrics)

    if verbose:
        _add_performance_rows(table, metrics)
        if metrics.circuit_breaker_state:
            state_style = (
                "green"
                if metrics.circuit_breaker_state == "closed"
                else "yellow"
                if metrics.circuit_breaker_state == "half-open"
                else "red"
            )
            table.add_row(
                "  Circuit Breaker",
                Text(metrics.circuit_breaker_state, style=state_style),
            )

        if metrics.fetch_phase_duration > 0:
            table.add_row(
                "  Fetch Time",
                format_duration(metrics.fetch_phase_duration),
            )
        if metrics.push_phase_duration > 0:
            table.add_row(
                "  Push Time",
                format_duration(metrics.push_phase_duration),
            )
        if metrics.pull_phase_duration > 0:
            table.add_row(
                "  Pull Time",
                format_duration(metrics.pull_phase_duration),
            )
        if metrics.analysis_phase_duration > 0:
            table.add_row(
                "  Analysis Time",
                format_duration(metrics.analysis_phase_duration),
            )
        if metrics.merge_phase_duration > 0:
            table.add_row(
                "  Merge Time",
                format_duration(metrics.merge_phase_duration),
            )
        if metrics.conflict_resolution_duration > 0:
            table.add_row(
                "  Conflict Resolution Time",
                format_duration(metrics.conflict_resolution_duration),
            )
    # Errors
    if metrics.errors_count > 0:
        table.add_row("[bold cyan]═══ Errors ═══[/bold cyan]", "")
        table.add_row(
            "  Error Count",
            Text(format_count(metrics.errors_count), style="red"),
        )

    return table


def create_metrics_history_table(
    metrics_list: list[SyncMetrics], limit: int = 10
) -> Table:
    """Create a table showing history of sync metrics.

    Args:
        metrics_list: List of SyncMetrics objects
        limit: Maximum number of rows to show

    Returns:
        Rich Table with metrics history
    """
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        title="Sync Metrics History",
    )
    table.add_column("Time", style="dim")
    table.add_column("Backend", style="green")
    table.add_column("Duration", justify="right")
    table.add_column("Duplicates", justify="right")
    table.add_column("Conflicts", justify="right")
    table.add_column("Errors", justify="right")

    # Reverse to show newest first
    for metrics in reversed(metrics_list[:limit]):
        created_time = metrics.start_time
        time_diff = datetime.now(UTC) - created_time
        time_str = (
            "just now"
            if time_diff < timedelta(seconds=60)
            else (
                f"{int(time_diff.total_seconds() / 60)}m ago"
                if time_diff < timedelta(hours=1)
                else (
                    f"{int(time_diff.total_seconds() / 3600)}h ago"
                    if time_diff < timedelta(days=1)
                    else created_time.strftime("%Y-%m-%d %H:%M")
                )
            )
        )

        error_count = metrics.errors_count
        error_style = "red" if error_count > 0 else "green"

        table.add_row(
            time_str,
            metrics.backend_type,
            format_duration(metrics.duration_seconds),
            format_count(metrics.duplicates_detected),
            format_count(metrics.conflicts_detected),
            Text(format_count(error_count), style=error_style),
        )

    return table
