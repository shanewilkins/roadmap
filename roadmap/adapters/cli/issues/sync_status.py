"""Sync status command - View sync history and statistics for GitHub-linked issues."""

import sys

import click
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.adapters.cli.helpers import ensure_entity_exists
from roadmap.common.console import get_console
from roadmap.common.datetime_parser import UnifiedDateTimeParser
from roadmap.core.services.sync.sync_metadata_service import SyncMetadataService


def _get_console():
    """Get a fresh console instance for test compatibility."""
    return get_console()


console = get_console()


def _format_timestamp(iso_str: str) -> str:
    """Format ISO timestamp to human-readable format."""
    try:
        dt = UnifiedDateTimeParser.parse_iso_datetime(iso_str)
        if dt:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return iso_str
    except Exception:
        return iso_str


def _build_sync_status_header(issue, metadata):
    """Build header text with issue title and sync status."""
    header = Text()
    header.append(f"#{issue.id}", style="bold cyan")
    header.append(" • ", style="dim")
    header.append(issue.title, style="bold white")
    header.append("\n")

    # Add sync status
    status_color_map = {
        "success": "green",
        "conflict": "yellow",
        "error": "red",
        "never": "dim",
    }
    status_color = status_color_map.get(metadata.last_sync_status, "white")
    header.append(
        f"[{metadata.last_sync_status.upper()}]", style=f"bold {status_color}"
    )

    if metadata.last_sync_time:
        header.append(" • ", style="dim")
        header.append(
            f"Last synced: {_format_timestamp(metadata.last_sync_time)}",
            style="dim",
        )

    return header


def _build_sync_metadata_table(issue, metadata):
    """Build metadata table showing sync statistics."""
    table = Table(show_header=False, box=None, padding=(0, 1))

    if metadata.github_issue_id:
        table.add_row("GitHub Issue", f"#{metadata.github_issue_id}")

    table.add_row("Total Syncs", str(metadata.sync_count))
    table.add_row("Successful", str(metadata.successful_syncs))

    if metadata.sync_count > 0:
        success_rate = metadata.get_success_rate()
        rate_color = (
            "green"
            if success_rate == 100
            else "yellow"
            if success_rate >= 75
            else "red"
        )
        table.add_row(
            "Success Rate", f"[{rate_color}]{success_rate:.1f}%[/{rate_color}]"
        )

        conflict_count = sum(
            1 for record in metadata.sync_history if record.conflict_resolution
        )
        if conflict_count > 0:
            table.add_row("Conflicts Resolved", str(conflict_count))

    return table


def _build_sync_history_table(records):
    """Build table showing recent sync history."""
    table = Table(
        title="Sync History (Most Recent First)",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Time", style="dim", width=20)
    table.add_column("Status", width=12)
    table.add_column("Details", width=30)

    for record in records:
        time_str = _format_timestamp(record.sync_timestamp)

        # Status
        if record.success:
            status_text = "[green]✓ SUCCESS[/green]"
        elif record.conflict_resolution:
            status_text = "[yellow]⚠ CONFLICT[/yellow]"
        else:
            status_text = "[red]✗ ERROR[/red]"

        # Details
        details_parts = []
        if record.local_changes:
            details_parts.append(f"Local: {len(record.local_changes)} changes")
        if record.github_changes:
            details_parts.append(f"GitHub: {len(record.github_changes)} changes")
        if record.conflict_resolution:
            details_parts.append(f"Resolved: {record.conflict_resolution}")
        if record.error_message:
            # Truncate long error messages
            error = record.error_message
            if len(error) > 40:
                error = error[:37] + "..."
            details_parts.append(f"Error: {error}")

        details_text = " • ".join(details_parts) if details_parts else "—"

        table.add_row(time_str, status_text, details_text)

    return table


def _build_aggregate_stats_table(stats):
    """Build table showing aggregate statistics across issues."""
    table = Table(show_header=False, box=None, padding=(0, 1))

    table.add_row("Total Issues", str(stats["total_issues"]))
    table.add_row("Total Sync Attempts", str(stats["total_sync_attempts"]))
    table.add_row("Successful Syncs", str(stats["successful_syncs"]))

    if stats["total_sync_attempts"] > 0:
        rate_color = (
            "green"
            if stats["success_rate"] == 100
            else "yellow"
            if stats["success_rate"] >= 75
            else "red"
        )
        table.add_row(
            "Overall Success Rate",
            f"[{rate_color}]{stats['success_rate']:.1f}%[/{rate_color}]",
        )

        if stats["total_conflicts"] > 0:
            conflict_color = (
                "green"
                if stats["conflict_rate"] < 5
                else "yellow"
                if stats["conflict_rate"] < 20
                else "red"
            )
            table.add_row(
                "Conflict Rate",
                f"[{conflict_color}]{stats['conflict_rate']:.1f}%[/{conflict_color}]",
            )

    table.add_row("Never Synced", str(stats["never_synced"]))

    return table


@click.command(name="sync-status")
@click.argument("issue_id", default="", required=False)
@click.option("--history", "show_history", is_flag=True, help="Show full sync history")
@click.option(
    "--statistics",
    "show_statistics",
    is_flag=True,
    help="Show aggregate statistics across all issues",
)
@click.option(
    "--all",
    "show_all_issues",
    is_flag=True,
    help="Show sync status for all GitHub-linked issues",
)
@click.pass_context
def sync_status(
    ctx: click.Context,
    issue_id: str,
    show_history: bool,
    show_statistics: bool,
    show_all_issues: bool,
) -> None:
    """Show sync status and history for GitHub-linked issues.

    Examples:
        # Show status for a single issue
        roadmap issue sync-status ISSUE_ID

        # Show full sync history
        roadmap issue sync-status ISSUE_ID --history

        # Show aggregate statistics
        roadmap issue sync-status --statistics

        # Show status for all linked issues
        roadmap issue sync-status --all

    The command displays:
        - Last sync time and status
        - Total sync attempts and success rate
        - Recent sync history with change details
        - Conflict resolution information
    """
    core = ctx.obj
    console_inst = get_console()

    # Initialize metadata service
    metadata_service = SyncMetadataService(core)

    # Handle different modes
    if show_statistics:
        # Show aggregate statistics across all issues
        all_issues = core.issues.all()
        github_issues = [
            issue for issue in all_issues if getattr(issue, "github_issue", None)
        ]

        if not github_issues:
            console_inst.print("[yellow]⚠️  No GitHub-linked issues found[/yellow]")
            return

        stats = metadata_service.get_statistics(github_issues)

        # Display statistics
        panel = Panel(
            _build_aggregate_stats_table(stats),
            title="[bold cyan]GitHub Sync Statistics[/bold cyan]",
            expand=False,
        )
        console_inst.print(panel)
        return

    if show_all_issues:
        # Show status for all linked issues (brief overview)
        all_issues = core.issues.all()
        github_issues = [
            issue for issue in all_issues if getattr(issue, "github_issue", None)
        ]

        if not github_issues:
            console_inst.print("[yellow]⚠️  No GitHub-linked issues found[/yellow]")
            return

        # Create summary table
        table = Table(
            title=f"GitHub Sync Status ({len(github_issues)} issues)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Issue ID", style="cyan")
        table.add_column("GitHub", width=10)
        table.add_column("Title", width=35)
        table.add_column("Status", width=12)
        table.add_column("Last Sync", width=20)
        table.add_column("Success %", width=12)

        for issue in github_issues:
            metadata = metadata_service.get_metadata(issue)
            status_color_map = {
                "success": "green",
                "conflict": "yellow",
                "error": "red",
                "never": "dim",
            }
            status_color = status_color_map.get(metadata.last_sync_status, "white")

            last_sync = (
                _format_timestamp(metadata.last_sync_time)
                if metadata.last_sync_time
                else "Never"
            )

            success_rate = (
                f"{metadata.get_success_rate():.0f}%"
                if metadata.sync_count > 0
                else "—"
            )

            table.add_row(
                issue.id,
                f"#{metadata.github_issue_id}",
                issue.title[:32],
                f"[{status_color}]{metadata.last_sync_status}[/{status_color}]",
                last_sync,
                success_rate,
            )

        console_inst.print(table)
        return

    # Single issue sync status (default)
    if not issue_id:
        console_inst.print(
            "[red]❌ Must provide ISSUE_ID or use --all or --statistics[/red]"
        )
        sys.exit(1)

    # Get the issue
    issue = ensure_entity_exists(core.issues, issue_id, "Issue")
    if not issue:
        return

    # Check if linked to GitHub
    if not getattr(issue, "github_issue", None):
        console_inst.print(
            f"[yellow]⚠️  Issue #{issue_id} is not linked to GitHub[/yellow]"
        )
        return

    # Get sync metadata
    metadata = metadata_service.get_metadata(issue)

    # Display header with issue title
    console_inst.print()
    header_panel = Panel(
        _build_sync_status_header(issue, metadata),
        expand=False,
    )
    console_inst.print(header_panel)
    console_inst.print()

    # Display sync statistics
    stats_panel = Panel(
        _build_sync_metadata_table(issue, metadata),
        title="[bold cyan]Sync Statistics[/bold cyan]",
        expand=False,
    )
    console_inst.print(stats_panel)
    console_inst.print()

    # Display sync history if available
    if metadata.sync_history:
        if show_history:
            # Show all history
            history_records = list(reversed(metadata.sync_history))
        else:
            # Show last 5 syncs
            history_records = list(reversed(metadata.sync_history))[:5]

        history_table = _build_sync_history_table(history_records)
        console_inst.print(history_table)

        if not show_history and len(metadata.sync_history) > 5:
            console_inst.print(
                f"\n[dim]... showing last 5 of {len(metadata.sync_history)} syncs. "
                f"Use --history to see all[/dim]"
            )
    else:
        console_inst.print(
            Panel(
                "[dim]No sync history recorded yet[/dim]",
                title="[bold cyan]Sync History[/bold cyan]",
                expand=False,
            )
        )

    console_inst.print()
