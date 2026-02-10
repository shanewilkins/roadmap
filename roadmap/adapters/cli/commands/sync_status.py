"""Sync status dashboard - comprehensive sync health reporting."""

import click
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.common.console import get_console
from roadmap.core.services.sync.sync_metadata_service import SyncMetadataService


def _build_health_overview_panel(stats: dict, console) -> Panel:
    """Build health overview panel with key metrics."""
    health_table = Table(show_header=False, box=None, padding=(0, 2))
    health_table.add_column(style="bold")
    health_table.add_column(justify="right")

    # Calculate health score
    total_attempts = stats.get("total_sync_attempts", 0)
    successful = stats.get("successful_syncs", 0)
    conflicts = stats.get("total_conflicts_resolved", 0)

    if total_attempts > 0:
        success_rate = (successful / total_attempts) * 100
        health_emoji = (
            "🟢" if success_rate >= 90 else "🟡" if success_rate >= 70 else "🔴"
        )
        health_text = (
            "Healthy"
            if success_rate >= 90
            else "Degraded"
            if success_rate >= 70
            else "Unhealthy"
        )
    else:
        success_rate = 0
        health_emoji = "⚪"
        health_text = "No Data"

    health_table.add_row(
        f"{health_emoji} Overall Health",
        Text(
            health_text,
            style="bold green"
            if success_rate >= 90
            else "bold yellow"
            if success_rate >= 70
            else "bold red",
        ),
    )
    health_table.add_row("Success Rate", f"{success_rate:.1f}%")
    health_table.add_row("Total Syncs", str(total_attempts))
    health_table.add_row("Successful", f"[green]{successful}[/green]")
    health_table.add_row("Conflicts", f"[yellow]{conflicts}[/yellow]")
    health_table.add_row("Never Synced", f"[dim]{stats.get('never_synced', 0)}[/dim]")

    return Panel(
        health_table,
        title="[bold cyan]📊 Sync Health Overview[/bold cyan]",
        border_style="cyan",
    )


def _build_recent_activity_panel(core, metadata_service, console) -> Panel:
    """Build recent activity panel showing last 5 syncs."""
    all_issues = core.issues.all()
    github_issues = [i for i in all_issues if getattr(i, "github_issue", None)]

    # Collect all recent sync records
    recent_syncs = []
    for issue in github_issues:
        metadata = metadata_service.get_metadata(issue)
        for record in metadata.sync_history[-5:]:  # Last 5 per issue
            recent_syncs.append((issue, record))

    # Sort by timestamp, most recent first
    recent_syncs.sort(key=lambda x: x[1].sync_timestamp, reverse=True)
    recent_syncs = recent_syncs[:10]  # Top 10 overall

    if not recent_syncs:
        return Panel(
            Text("No recent sync activity", style="dim"),
            title="[bold cyan]🕐 Recent Activity[/bold cyan]",
            border_style="cyan",
        )

    activity_table = Table(show_header=True, header_style="bold", box=None)
    activity_table.add_column("Time", style="dim", width=12)
    activity_table.add_column("Issue", width=12)
    activity_table.add_column("Status", width=10)
    activity_table.add_column("Details", width=30)

    for issue, record in recent_syncs:
        time_str = record.sync_timestamp[11:19]  # HH:MM:SS
        issue_id = issue.id[:10]

        if record.success:
            status = "[green]✓ Success[/green]"
        elif record.conflict_resolution:
            status = "[yellow]⚠ Conflict[/yellow]"
        else:
            status = "[red]✗ Error[/red]"

        details = ""
        if record.conflict_resolution:
            details = f"Resolved: {record.conflict_resolution}"
        elif record.error_message:
            details = record.error_message[:27] + "..."
        elif record.local_changes:
            details = f"{len(record.local_changes)} changes"

        activity_table.add_row(time_str, issue_id, status, details)

    return Panel(
        activity_table,
        title="[bold cyan]🕐 Recent Sync Activity (Last 10)[/bold cyan]",
        border_style="cyan",
    )


def _build_error_trends_panel(core, metadata_service, console) -> Panel:
    """Build error trends panel showing common issues."""
    all_issues = core.issues.all()
    github_issues = [i for i in all_issues if getattr(i, "github_issue", None)]

    # Collect error stats
    error_types = {}
    conflict_types = {}

    for issue in github_issues:
        metadata = metadata_service.get_metadata(issue)
        for record in metadata.sync_history:
            if record.error_message:
                # Simple categorization
                error_key = _categorize_error(record.error_message)
                error_types[error_key] = error_types.get(error_key, 0) + 1

            if record.conflict_resolution:
                conflict_types[record.conflict_resolution] = (
                    conflict_types.get(record.conflict_resolution, 0) + 1
                )

    if not error_types and not conflict_types:
        return Panel(
            Text("No errors or conflicts detected 🎉", style="green"),
            title="[bold cyan]📈 Error Trends[/bold cyan]",
            border_style="cyan",
        )

    trends_table = Table(show_header=True, header_style="bold", box=None)
    trends_table.add_column("Type", style="yellow")
    trends_table.add_column("Category", width=20)
    trends_table.add_column("Count", justify="right", width=8)

    for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]:
        trends_table.add_row("Error", error, str(count))

    for resolution, count in sorted(
        conflict_types.items(), key=lambda x: x[1], reverse=True
    )[:3]:
        trends_table.add_row("Conflict", resolution, str(count))

    return Panel(
        trends_table,
        title="[bold cyan]📈 Error & Conflict Trends[/bold cyan]",
        border_style="cyan",
    )


def _categorize_error(error_message: str) -> str:
    """Categorize error message into a type."""
    error_lower = error_message.lower()

    if "rate limit" in error_lower or "429" in error_lower:
        return "Rate Limit"
    elif "auth" in error_lower or "401" in error_lower or "403" in error_lower:
        return "Authentication"
    elif (
        "network" in error_lower
        or "connection" in error_lower
        or "timeout" in error_lower
    ):
        return "Network"
    elif "not found" in error_lower or "404" in error_lower:
        return "Not Found"
    elif "validation" in error_lower or "invalid" in error_lower:
        return "Validation"
    else:
        return "Other"


def _build_issue_health_panel(core, metadata_service, console) -> Panel:
    """Build issue health breakdown panel."""
    all_issues = core.issues.all()
    github_issues = [i for i in all_issues if getattr(i, "github_issue", None)]

    # Categorize issues by sync health
    healthy = []
    at_risk = []
    failing = []
    never_synced = []

    for issue in github_issues:
        metadata = metadata_service.get_metadata(issue)

        if metadata.sync_count == 0:
            never_synced.append(issue)
        else:
            success_rate = metadata.get_success_rate()
            if success_rate >= 90:
                healthy.append(issue)
            elif success_rate >= 70:
                at_risk.append(issue)
            else:
                failing.append(issue)

    health_breakdown = Table(show_header=True, header_style="bold", box=None)
    health_breakdown.add_column("Category", style="bold")
    health_breakdown.add_column("Count", justify="right", width=8)
    health_breakdown.add_column("Percentage", width=12)

    total = len(github_issues)
    if total > 0:
        health_breakdown.add_row(
            "[green]✓ Healthy (90%+)[/green]",
            str(len(healthy)),
            f"{(len(healthy) / total) * 100:.1f}%",
        )
        health_breakdown.add_row(
            "[yellow]⚠ At Risk (70-89%)[/yellow]",
            str(len(at_risk)),
            f"{(len(at_risk) / total) * 100:.1f}%",
        )
        health_breakdown.add_row(
            "[red]✗ Failing (<70%)[/red]",
            str(len(failing)),
            f"{(len(failing) / total) * 100:.1f}%",
        )
        health_breakdown.add_row(
            "[dim]○ Never Synced[/dim]",
            str(len(never_synced)),
            f"{(len(never_synced) / total) * 100:.1f}%",
        )

    return Panel(
        health_breakdown,
        title="[bold cyan]💊 Issue Health Breakdown[/bold cyan]",
        border_style="cyan",
    )


@click.command(name="status")
@click.pass_context
def sync_status_dashboard(ctx: click.Context) -> None:
    """Display comprehensive sync health dashboard.

    Shows an overview of sync operations, health metrics, recent activity,
    error trends, and issue-level health breakdown.

    Examples:
        # Show sync health dashboard
        roadmap sync status
    """
    core = ctx.obj["core"]
    console = get_console()

    # Initialize metadata service
    metadata_service = SyncMetadataService(core)

    # Get all GitHub-linked issues
    all_issues = core.issues.all()
    github_issues = [i for i in all_issues if getattr(i, "github_issue", None)]

    if not github_issues:
        console.print("[yellow]⚠️  No GitHub-linked issues found[/yellow]")
        console.print(
            "\n[dim]Hint: Link issues with: roadmap issue link <issue-id> <github-issue-number>[/dim]"
        )
        return

    # Get aggregate statistics
    stats = metadata_service.get_statistics(github_issues)

    # Build dashboard layout
    console.print("\n[bold cyan]════ Sync Health Dashboard ════[/bold cyan]")
    console.print(f"[dim]Tracking {len(github_issues)} GitHub-linked issues[/dim]\n")

    # Show health overview
    console.print(_build_health_overview_panel(stats, console))
    console.print()

    # Show issue health breakdown
    console.print(_build_issue_health_panel(core, metadata_service, console))
    console.print()

    # Show recent activity
    console.print(_build_recent_activity_panel(core, metadata_service, console))
    console.print()

    # Show error trends
    console.print(_build_error_trends_panel(core, metadata_service, console))
    console.print()

    console.print(
        "[dim]💡 Tip: Use 'roadmap issue sync-status <id>' for detailed issue-level sync history[/dim]"
    )
