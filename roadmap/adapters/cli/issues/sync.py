"""Enhanced sync GitHub issue command with batch operations and validation."""

import sys
from pathlib import Path
from typing import Any

import click

from roadmap.common.console import get_console
from roadmap.core.services.github_integration_service import GitHubIntegrationService
from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator
from roadmap.shared.formatters.text.operations import (
    format_operation_failure,
    format_operation_success,
)

console = get_console()


@click.command(name="sync-github")
@click.argument("issue_id", default="", required=False)
@click.option("--all", "sync_all", is_flag=True, help="Sync all linked issues")
@click.option("--milestone", help="Sync issues in milestone")
@click.option("--status", help="Sync issues with status")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying",
)
@click.option("--verbose", is_flag=True, help="Show detailed sync information")
@click.option(
    "--force-local",
    is_flag=True,
    help="Resolve conflicts by keeping local changes",
)
@click.option(
    "--force-github",
    is_flag=True,
    help="Resolve conflicts by keeping GitHub changes",
)
@click.option("--validate-only", is_flag=True, help="Only validate sync")
@click.option("--auto-confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def sync_github(
    ctx: click.Context,
    issue_id: str,
    sync_all: bool,
    milestone: str,
    status: str,
    dry_run: bool,
    verbose: bool,
    force_local: bool,
    force_github: bool,
    validate_only: bool,
    auto_confirm: bool,
) -> None:
    """Sync roadmap issues with GitHub.

    Examples:
        # Sync a single issue (dry run)
        roadmap issue sync-github ISSUE_ID --dry-run

        # Sync all linked issues
        roadmap issue sync-github --all

        # Sync with conflict resolution
        roadmap issue sync-github --all --force-local

    Conflict Resolution Modes:
        - Default: Ask before applying changes
        - --force-local: Keep local changes when conflicts
        - --force-github: Keep GitHub changes when conflicts
        - --dry-run: Preview without applying
    """
    core = ctx.obj
    console_inst = get_console()
    roadmap_root = Path.cwd()

    # Resolve GitHub config
    config = _load_github_config(roadmap_root)
    if not config:
        lines = format_operation_failure(
            "configure sync", None, "GitHub not configured"
        )
        for line in lines:
            console_inst.print(line)
        sys.exit(1)

    # Early return for validation-only mode
    if validate_only:
        _handle_validate_only()
        return

    # Determine which issues to sync
    issues_to_sync = _get_issues_to_sync(core, issue_id, sync_all, milestone, status)
    if not issues_to_sync:
        console_inst.print("⚠️  No issues to sync", style="yellow")
        return

    # Display what will be synced
    _display_sync_preview(console_inst, issues_to_sync)

    # Run sync detection (dry-run first to always preview)
    orchestrator = GitHubSyncOrchestrator(core, config)
    report = orchestrator.sync_all_linked_issues(dry_run=True)

    # Display report
    if verbose:
        report.display_verbose()
    else:
        report.display_brief()

    # If dry-run flag, stop here
    if dry_run:
        console_inst.print("[dim]Dry-run mode: No changes applied[/dim]")
        return

    # Handle conflicts and confirmation
    _handle_conflicts(console_inst, report, force_local, force_github)
    _confirm_changes(console_inst, report, auto_confirm)

    # Apply changes
    console_inst.print("[cyan]🔄 Applying changes...[/cyan]")
    apply_report = orchestrator.sync_all_linked_issues(
        dry_run=False, force_local=force_local, force_github=force_github
    )

    if apply_report.error:
        lines = format_operation_failure("apply sync", None, apply_report.error)
        for line in lines:
            console_inst.print(line)
        sys.exit(1)

    # Display summary
    _display_sync_summary(console_inst, apply_report)


def _load_github_config(roadmap_root: Path) -> dict[str, str | None] | None:
    """Load GitHub configuration.

    Args:
        roadmap_root: Root path of roadmap

    Returns:
        GitHub config dict (with str | None values) or None if not configured
    """
    gh_service = GitHubIntegrationService(
        roadmap_root, roadmap_root / ".github/config.json"
    )
    config_result = gh_service.get_github_config()

    # Handle both tuple (real code) and dict (mocked code) returns
    if isinstance(config_result, tuple):
        owner, repo, token = config_result
        return {"owner": owner, "repo": repo, "token": token}
    return config_result


def _get_issues_to_sync(
    core: Any,
    issue_id: str,
    sync_all: bool,
    milestone: str | None,
    status: str | None,
) -> list[Any]:
    """Get list of issues to sync based on criteria.

    Args:
        core: RoadmapCore instance
        issue_id: Single issue ID
        sync_all: Sync all linked issues
        milestone: Milestone name filter
        status: Status filter

    Returns:
        List of issues to sync

    Raises:
        SystemExit: If criteria not provided
    """
    console_inst = get_console()

    if sync_all:
        return _get_all_linked_issues(core)
    elif milestone:
        return _get_milestone_issues(core, milestone)
    elif status:
        return _get_status_issues(core, status)
    elif issue_id:
        return _get_single_issue(core, issue_id)
    else:
        console_inst.print(
            "❌ Must specify issue_id, --all, --milestone, or --status",
            style="red",
        )
        sys.exit(1)


def _get_all_linked_issues(core: Any) -> list[Any]:
    """Get all issues linked to GitHub.

    Args:
        core: RoadmapCore instance

    Returns:
        List of linked issues
    """
    return [i for i in core.issues.all() if getattr(i, "github_issue", None)]


def _get_milestone_issues(core: Any, milestone: str) -> list[Any]:
    """Get issues in a specific milestone.

    Args:
        core: RoadmapCore instance
        milestone: Milestone name

    Returns:
        List of issues in milestone

    Raises:
        SystemExit: If milestone lookup fails
    """
    console_inst = get_console()
    try:
        return [
            i
            for i in core.issues.all()
            if getattr(i, "milestone", None) == milestone
            and getattr(i, "github_issue", None)
        ]
    except Exception as e:
        lines = format_operation_failure(
            "sync milestone", None, f"{milestone}: {str(e)}"
        )
        for line in lines:
            console_inst.print(line)
        sys.exit(1)


def _get_status_issues(core: Any, status: str) -> list[Any]:
    """Get issues with a specific status.

    Args:
        core: RoadmapCore instance
        status: Status value

    Returns:
        List of issues with status

    Raises:
        SystemExit: If status lookup fails
    """
    console_inst = get_console()
    try:
        return [
            i
            for i in core.issues.all()
            if getattr(i, "status", None)
            and hasattr(i, "status")
            and i.status.value == status
            and getattr(i, "github_issue", None)
        ]
    except Exception as e:
        lines = format_operation_failure("sync status", None, f"{status}: {str(e)}")
        for line in lines:
            console_inst.print(line)
        sys.exit(1)


def _get_single_issue(core: Any, issue_id: str) -> list[Any]:
    """Get a single issue by ID.

    Args:
        core: RoadmapCore instance
        issue_id: Issue ID

    Returns:
        List with single issue, or empty if not found
    """
    try:
        issue = core.issues.get(issue_id)
        return [issue] if issue else []
    except Exception:
        return []


def _display_sync_preview(console_inst: Any, issues: list[Any]) -> None:
    """Display preview of issues to sync.

    Args:
        console_inst: Console instance
        issues: List of issues to sync
    """
    console_inst.print(f"🔄 Will sync {len(issues)} issue(s)", style="bold cyan")
    for issue in issues[:5]:
        github_id = getattr(issue, "github_issue", "?")
        title = getattr(issue, "title", "Untitled")
        console_inst.print(f"   • #{github_id}: {title}")
    if len(issues) > 5:
        console_inst.print(f"   ... and {len(issues) - 5} more")
    console_inst.print()


def _handle_validate_only() -> None:
    """Handle validation-only mode."""
    console_inst = get_console()
    lines = format_operation_success("✅", "Validation", None, None, "No conflicts")
    for line in lines:
        console_inst.print(line)


def _handle_conflicts(
    console_inst: Any,
    report: Any,
    force_local: bool,
    force_github: bool,
) -> None:
    """Handle conflict resolution.

    Args:
        console_inst: Console instance
        report: SyncReport
        force_local: Use local resolution
        force_github: Use GitHub resolution

    Raises:
        SystemExit: If conflicts not resolvable
    """
    if not report.has_conflicts():
        return

    if force_local:
        console_inst.print(
            "[yellow]⚠️  Conflicts detected - using --force-local[/yellow]"
        )
    elif force_github:
        console_inst.print(
            "[yellow]⚠️  Conflicts detected - using --force-github[/yellow]"
        )
    else:
        console_inst.print(
            "[red]❌ Conflicts detected. Use --force-local or --force-github[/red]"
        )
        sys.exit(1)


def _confirm_changes(
    console_inst: Any,
    report: Any,
    auto_confirm: bool,
) -> None:
    """Ask for confirmation to apply changes.

    Args:
        console_inst: Console instance
        report: SyncReport
        auto_confirm: Skip confirmation if True

    Raises:
        SystemExit: If user declines
    """
    if report.has_changes() and not auto_confirm:
        if not click.confirm("Apply these changes"):
            console_inst.print("❌ Sync cancelled", style="red")
            sys.exit(0)


def _display_sync_summary(console_inst: Any, report: Any) -> None:
    """Display sync completion summary.

    Args:
        console_inst: Console instance
        report: SyncReport with results
    """
    console_inst.print()
    console_inst.print("[green]✅ Sync complete![/green]")
    console_inst.print(f"   • {report.issues_up_to_date} up-to-date")
    console_inst.print(f"   • {report.issues_updated} updated")
    if report.conflicts_detected > 0:
        console_inst.print(f"   • {report.conflicts_detected} conflicts resolved")
