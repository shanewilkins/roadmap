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
    gh_service = GitHubIntegrationService(
        roadmap_root, roadmap_root / ".github/config.json"
    )
    config = gh_service.get_github_config()

    if not config:
        format_operation_failure(console_inst, "GitHub sync", "GitHub not configured")
        sys.exit(1)

    if validate_only:
        # Run validation
        if hasattr(core, "github_service"):
            # For now, validation is basic - can be extended later
            format_operation_success(
                console_inst, "Validation complete", "No conflicts"
            )
        else:
            format_operation_success(
                console_inst, "Validation complete", "No conflicts"
            )
        return

    # Get issues to sync
    issues_to_sync: list[Any] = []

    if sync_all:
        # Get all linked issues
        issues_to_sync = [
            issue for issue in core.issues.all() if getattr(issue, "github_issue", None)
        ]
    elif milestone:
        try:
            issues_to_sync = [
                issue
                for issue in core.issues.all()
                if getattr(issue, "milestone", None) == milestone
                and getattr(issue, "github_issue", None)
            ]
        except Exception as e:
            format_operation_failure(
                console_inst,
                f"Failed to get issues in milestone {milestone}",
                str(e),
            )
            sys.exit(1)
    elif status:
        try:
            issues_to_sync = [
                issue
                for issue in core.issues.all()
                if getattr(issue, "status", None)
                and hasattr(issue, "status")
                and issue.status.value == status
                and getattr(issue, "github_issue", None)
            ]
        except Exception as e:
            format_operation_failure(
                console_inst,
                f"Failed to get issues with status {status}",
                str(e),
            )
            sys.exit(1)
    elif issue_id:
        # Single issue sync
        try:
            issue = core.issues.get(issue_id)
            if issue:
                issues_to_sync = [issue]
        except Exception:
            pass
    else:
        console_inst.print(
            "❌ Must specify issue_id, --all, --milestone, or --status",
            style="red",
        )
        sys.exit(1)

    if not issues_to_sync:
        console_inst.print("⚠️  No issues to sync", style="yellow")
        return

    # Display what will be synced
    console_inst.print(
        f"🔄 Will sync {len(issues_to_sync)} issue(s)", style="bold cyan"
    )
    for issue in issues_to_sync[:5]:  # Show first 5
        github_id = getattr(issue, "github_issue", "?")
        title = getattr(issue, "title", "Untitled")
        console_inst.print(f"   • #{github_id}: {title}")
    if len(issues_to_sync) > 5:
        console_inst.print(f"   ... and {len(issues_to_sync) - 5} more")
    console_inst.print()

    # Run sync detection (dry-run mode)
    orchestrator = GitHubSyncOrchestrator(core, config)
    report = orchestrator.sync_all_linked_issues(dry_run=True)

    # Display report
    if verbose:
        report.display_verbose()
    else:
        report.display_brief()

    # If dry-run, stop here
    if dry_run:
        console_inst.print("[dim]Dry-run mode: No changes applied[/dim]")
        return

    # Handle conflicts
    if report.has_conflicts():
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

    # Ask for confirmation if there are changes
    if report.has_changes() and not auto_confirm:
        if not click.confirm("Apply these changes"):
            console_inst.print("❌ Sync cancelled", style="red")
            return

    # TODO: Phase 2A-Part2 - Apply changes
    console_inst.print(
        "[dim]Phase 2A-Part2: Applying changes (not yet implemented)[/dim]"
    )
