"""Enhanced dry-run display for sync operations."""

from rich.table import Table

from roadmap.common.console import get_console


def _display_active_filters(
    console,
    milestone_filter: tuple[str, ...] | None,
    milestone_state: str | None,
    since: str | None,
    until: str | None,
) -> None:
    """Display active filters for the sync operation."""
    if not (milestone_filter or milestone_state != "all" or since or until):
        return

    console.print("[bold yellow]Active Filters:[/bold yellow]")
    if milestone_filter:
        console.print(f"  • Milestones: {', '.join(milestone_filter)}", style="yellow")
    if milestone_state and milestone_state != "all":
        console.print(f"  • State: {milestone_state}", style="yellow")
    if since:
        console.print(f"  • Since: {since}", style="yellow")
    if until:
        console.print(f"  • Until: {until}", style="yellow")
    console.print()


def _display_summary_statistics(console, push_changes, pull_changes, conflicts) -> None:
    """Display summary statistics of changes."""
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • Issues to push: [cyan]{len(push_changes)}[/cyan]")
    console.print(f"  • Issues to pull: [green]{len(pull_changes)}[/green]")
    console.print(f"  • Conflicts detected: [red]{len(conflicts)}[/red]")
    console.print()


def display_detailed_dry_run_preview(
    analysis_report,
    milestone_filter: tuple[str, ...] | None = None,
    milestone_state: str | None = None,
    since: str | None = None,
    until: str | None = None,
    verbose: bool = False,
) -> None:
    """Display detailed preview of sync operations in dry-run mode.

    Args:
        analysis_report: Sync analysis report with detected changes
        milestone_filter: Tuple of milestone names to filter by
        milestone_state: Filter milestones by state (open/closed/all)
        since: Filter milestones updated since this date
        until: Filter milestones updated until this date
        verbose: Show detailed information
    """
    console = get_console()

    # Header
    console.print("\n[bold cyan]═══ DRY-RUN PREVIEW ═══[/bold cyan]")
    console.print(
        "[dim]The following changes would be applied if you run sync without --dry-run:[/dim]\n"
    )

    # Show active filters
    _display_active_filters(console, milestone_filter, milestone_state, since, until)

    # Get changes by type
    if not hasattr(analysis_report, "changes") or not analysis_report.changes:
        console.print("[dim]No changes detected[/dim]")
        return

    changes = analysis_report.changes
    push_changes = [c for c in changes if c.requires_push()]
    pull_changes = [c for c in changes if c.requires_pull()]
    conflicts = [c for c in changes if c.has_conflict()]

    # Summary statistics
    _display_summary_statistics(console, push_changes, pull_changes, conflicts)

    # Issues to push
    if push_changes:
        _display_push_operations(push_changes, console, verbose)

    # Issues to pull
    if pull_changes:
        _display_pull_operations(pull_changes, console, verbose)

    # Conflicts
    if conflicts:
        _display_conflicts(conflicts, console, verbose)

    # Footer
    console.print(
        "\n[bold yellow]⚠️  No changes will be applied in dry-run mode[/bold yellow]"
    )
    console.print(
        "[dim]To apply these changes, run: roadmap sync (without --dry-run)[/dim]"
    )


def _display_push_operations(push_changes, console, verbose: bool) -> None:
    """Display issues that would be pushed to remote."""
    console.print("[bold cyan]📤 PUSH Operations (Local → Remote):[/bold cyan]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Issue ID", style="dim", width=12)
    table.add_column("Title", width=40)
    table.add_column("Action", width=15)

    if verbose:
        table.add_column("Changes", width=30)

    for change in push_changes[:20]:  # Limit to first 20
        action = _determine_push_action(change)
        table.add_row(
            change.issue_id[:10],
            change.title[:37] + "..." if len(change.title) > 40 else change.title,
            action,
            _format_changes(change) if verbose else "",
        )

    console.print(table)

    if len(push_changes) > 20:
        console.print(
            f"[dim]  ... and {len(push_changes) - 20} more[/dim]",
            style="cyan",
        )
    console.print()


def _display_pull_operations(pull_changes, console, verbose: bool) -> None:
    """Display issues that would be pulled from remote."""
    console.print("[bold green]📥 PULL Operations (Remote → Local):[/bold green]")

    table = Table(show_header=True, header_style="bold green")
    table.add_column("Issue ID", style="dim", width=12)
    table.add_column("Title", width=40)
    table.add_column("Action", width=15)

    if verbose:
        table.add_column("Changes", width=30)

    for change in pull_changes[:20]:  # Limit to first 20
        action = _determine_pull_action(change)
        table.add_row(
            change.issue_id[:10],
            change.title[:37] + "..." if len(change.title) > 40 else change.title,
            action,
            _format_changes(change) if verbose else "",
        )

    console.print(table)

    if len(pull_changes) > 20:
        console.print(
            f"[dim]  ... and {len(pull_changes) - 20} more[/dim]",
            style="green",
        )
    console.print()


def _display_conflicts(conflicts, console, verbose: bool) -> None:
    """Display detected conflicts."""
    console.print("[bold red]⚠️  CONFLICTS Detected:[/bold red]")
    console.print(
        "[dim]These issues have conflicting changes between local and remote:[/dim]\n"
    )

    table = Table(show_header=True, header_style="bold red")
    table.add_column("Issue ID", style="dim", width=12)
    table.add_column("Title", width=40)
    table.add_column("Conflict Fields", width=25, style="yellow")

    for conflict in conflicts[:10]:  # Limit to first 10
        conflict_fields = _get_conflict_fields(conflict)
        table.add_row(
            conflict.issue_id[:10],
            conflict.title[:37] + "..." if len(conflict.title) > 40 else conflict.title,
            conflict_fields,
        )

    console.print(table)

    if len(conflicts) > 10:
        console.print(f"[dim]  ... and {len(conflicts) - 10} more[/dim]", style="red")

    console.print(
        "\n[yellow]💡 Tip: Use --force-local or --force-remote to auto-resolve conflicts[/yellow]"
    )
    console.print()


def _determine_push_action(change) -> str:
    """Determine the push action type from a change object."""
    if change.is_local_only_change():
        return "[cyan]CREATE[/cyan]"
    elif hasattr(change, "field_changes") and change.field_changes:
        return "[yellow]UPDATE[/yellow]"
    return "[green]SYNC[/green]"


def _determine_pull_action(change) -> str:
    """Determine the pull action type from a change object."""
    if change.is_remote_only_change():
        return "[green]CREATE[/green]"
    elif hasattr(change, "field_changes") and change.field_changes:
        return "[yellow]UPDATE[/yellow]"
    return "[cyan]SYNC[/cyan]"


def _format_changes(change) -> str:
    """Format field changes for display."""
    if not hasattr(change, "field_changes") or not change.field_changes:
        return "[dim]new[/dim]"

    fields = list(change.field_changes.keys())[:3]  # First 3 fields
    if len(fields) == 0:
        return "[dim]metadata[/dim]"

    result = ", ".join(fields)
    if len(change.field_changes) > 3:
        result += f", +{len(change.field_changes) - 3} more"
    return result


def _get_conflict_fields(conflict) -> str:
    """Get the conflicting fields from a conflict object."""
    if hasattr(conflict, "conflicting_fields") and conflict.conflicting_fields:
        fields = list(conflict.conflicting_fields)[:3]
        result = ", ".join(fields)
        if len(conflict.conflicting_fields) > 3:
            result += "..."
        return result
    return "[dim]unknown[/dim]"
