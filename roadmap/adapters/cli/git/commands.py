"""Git integration and workflow commands."""

import sys
from typing import Literal

import click
import structlog
from rich.console import Console

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.git.handlers.git_authentication_handler import (
    GitAuthenticationHandler,
)
from roadmap.adapters.cli.git.handlers.git_branch_handler import GitBranchHandler
from roadmap.adapters.cli.git.handlers.git_connectivity_handler import (
    GitConnectivityHandler,
)
from roadmap.adapters.cli.git.handlers.git_hooks_handler import GitHooksHandler
from roadmap.adapters.cli.git.hooks_config import hooks_config
from roadmap.common.console import get_console
from roadmap.core.services.github.github_integration_service import (
    GitHubIntegrationService,
)

from .status_display import GitStatusDisplay

console = Console()
log = structlog.get_logger()


@click.group()
def git():
    """Git integration and workflow management."""
    pass


# Basic git commands - full implementation would be extracted from main CLI
@git.command("setup")
@click.option(
    "--auth",
    is_flag=True,
    help="Set up GitHub authentication for sync operations",
)
@click.option(
    "--update-token",
    is_flag=True,
    help="Update stored GitHub token",
)
@click.option(
    "--git-auth",
    is_flag=True,
    help="Test and verify Git repository connectivity for self-hosting",
)
@click.pass_context
@require_initialized
def setup_git(ctx: click.Context, auth: bool, update_token: bool, git_auth: bool):
    """Set up Git integration and authentication.

    Configure GitHub authentication for sync operations or manage git workflow.
    Supports both GitHub PAT tokens and vanilla Git self-hosting.
    """
    core = ctx.obj["core"]

    try:
        if auth or update_token:
            _setup_github_auth(core, update_token)
        elif git_auth:
            _test_git_connectivity(core)
        else:
            console.print("⚙️  Git setup", style="green")
            console.print("\nAvailable options:")
            console.print(
                "  roadmap git setup --auth          Set up GitHub authentication"
            )
            console.print(
                "  roadmap git setup --update-token  Update stored GitHub token"
            )
            console.print(
                "  roadmap git setup --git-auth      Test Git repository connectivity"
            )
            console.print("  roadmap git hooks-install        Install git hooks")
    except Exception as e:
        log.error("git_setup_failed", error=str(e), error_type=type(e).__name__)
        console.print(f"❌ Setup failed: {e}", style="bold red")
        ctx.exit(1)


def _setup_github_auth(core, update_token: bool = False):
    """Set up or update GitHub authentication.

    Args:
        core: RoadmapCore instance
        update_token: If True, force update token; otherwise ask if exists

    Raises:
        Exception: If authentication setup fails
    """
    handler = GitAuthenticationHandler(console)
    handler.setup_github_auth(update_token)


def _test_git_connectivity(core):
    """Test and verify Git repository connectivity for self-hosting.

    Args:
        core: RoadmapCore instance

    Raises:
        Exception: If git connectivity test fails
    """
    handler = GitConnectivityHandler(console)
    handler.test_git_connectivity(core)


@git.command("hooks-install")
@click.pass_context
@require_initialized
def install_hooks(ctx: click.Context):
    """Install Git hooks for roadmap integration.

    Installs hooks that automatically track commits, branch changes, and integrate
    with your roadmap workflow.
    """
    core = ctx.obj["core"]

    try:
        handler = GitHooksHandler(console)
        handler.install_hooks(core)
    except Exception:
        ctx.exit(1)


@git.command("hooks-uninstall")
@click.pass_context
@require_initialized
def uninstall_hooks(ctx: click.Context):
    """Remove Git hooks for roadmap integration."""
    core = ctx.obj["core"]

    try:
        handler = GitHooksHandler(console)
        handler.uninstall_hooks(core)
    except Exception:
        ctx.exit(1)


@git.command("hooks-status")
@click.pass_context
@require_initialized
def hooks_status(ctx: click.Context):
    """Show status of installed Git hooks."""
    core = ctx.obj["core"]

    try:
        handler = GitHooksHandler(console)
        handler.show_hooks_status(core)
    except Exception:
        ctx.exit(1)


@git.command("sync")
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
@click.option(
    "--backend",
    type=click.Choice(["github", "git"]),
    help="Sync backend to use (github or git)",
)
@click.pass_context
@require_initialized
def sync_git(
    ctx: click.Context,
    dry_run: bool,
    verbose: bool,
    force_local: bool,
    force_github: bool,
    backend: str | None,
) -> None:
    """Sync roadmap with remote repository.

    Supports multiple backends:
    - github: GitHub issues API (requires GitHub config)
    - git: Vanilla Git push/pull (works with any Git hosting)

    Two-way sync:
    - Push local changes to remote
    - Pull remote changes to local
    - Detect and resolve conflicts

    Examples:
        # Preview what will be synced
        roadmap git sync --dry-run

        # Sync all changes
        roadmap git sync

        # Sync with specific backend
        roadmap git sync --backend=git

        # Sync with conflict resolution
        roadmap git sync --force-local
    """
    from roadmap.adapters.cli.services.sync_service import (
        get_sync_backend,
    )
    from roadmap.adapters.sync import (
        detect_backend_from_config,
    )

    core = ctx.obj["core"]
    console_inst = get_console()

    try:
        # Load config from both locations
        gh_service = GitHubIntegrationService(core, core.roadmap_dir / "config.yaml")
        config_result = gh_service.get_github_config()

        # Handle both tuple (real code) and dict (mocked code) returns
        if isinstance(config_result, tuple):
            token, owner, repo = config_result
            config = {
                "owner": owner,
                "repo": repo,
                "token": token,
            }
        else:
            config = config_result or {}

        # Determine backend to use
        if backend:
            backend_type: Literal["github", "git"] = backend  # type: ignore[assignment]
        else:
            backend_type = detect_backend_from_config(config)

        console_inst.print(
            f"🔄 Syncing with {backend_type.upper()} backend",
            style="bold cyan",
        )

        # Create backend
        sync_backend = get_sync_backend(backend_type, core, config)
        if not sync_backend:
            console_inst.print(
                f"❌ Failed to initialize {backend_type} backend",
                style="bold red",
            )
            if backend_type == "git":
                console_inst.print(
                    "   Ensure you're in a Git repository",
                    style="yellow",
                )
            elif backend_type == "github":
                console_inst.print(
                    "   GitHub config may be missing or incomplete",
                    style="yellow",
                )
            sys.exit(1)

        # Use generic orchestrator with the backend
        from roadmap.adapters.sync import SyncMergeOrchestrator
        from roadmap.core.services.sync.sync_conflict_resolver import (
            SyncConflictResolver,
        )
        from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator

        # Create service instances
        state_comparator = SyncStateComparator()
        conflict_resolver = SyncConflictResolver()

        # Create orchestrator with services
        orchestrator = SyncMergeOrchestrator(
            core,
            sync_backend,
            state_comparator=state_comparator,
            conflict_resolver=conflict_resolver,
        )
        report = orchestrator.sync_all_issues(dry_run=True)

        if report.error:
            console_inst.print(f"❌ Sync error: {report.error}", style="bold red")
            sys.exit(1)

        # Display report
        if verbose:
            report.display_verbose()
        else:
            report.display_brief()

        console_inst.print()

        # If dry-run flag, stop here
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
        if report.has_changes():
            if not click.confirm("Apply these changes?"):
                console_inst.print("❌ Sync cancelled", style="red")
                return

        # Apply changes
        console_inst.print("[cyan]🔄 Applying changes...[/cyan]")
        apply_report = orchestrator.sync_all_issues(
            dry_run=False, force_local=force_local, force_remote=force_github
        )

        if apply_report.error:
            console_inst.print(
                f"❌ Error applying sync: {apply_report.error}", style="bold red"
            )
            sys.exit(1)

        # Summary
        console_inst.print()
        console_inst.print("[green]✅ Sync complete![/green]")
        console_inst.print(f"   • {apply_report.issues_up_to_date} up-to-date")
        console_inst.print(f"   • {apply_report.issues_needs_push} pushed")
        console_inst.print(f"   • {apply_report.issues_needs_pull} pulled")
        if apply_report.conflicts_detected > 0:
            console_inst.print(
                f"   • {apply_report.conflicts_detected} conflicts resolved"
            )

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="sync",
            entity_type="git",
            entity_id="repository",
            context={},
        )


@git.command("status")
@click.pass_context
@require_initialized
def git_status(ctx: click.Context):
    """Show Git repository status and roadmap integration info."""
    core = ctx.obj["core"]

    display = GitStatusDisplay(console)

    try:
        git_context = core.git.get_context()

        if not git_context.get("is_git_repo", False):
            display.show_not_git_repo()
            return

        display.show_header()
        display.show_repository_info(git_context)
        display.show_current_branch(git_context)

        branch_issues = core.git.get_branch_linked_issues()
        current_branch = git_context.get("current_branch", "")
        display.show_branch_issue_links(branch_issues, current_branch, core)

        display.show_recent_commits(core)

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="git_status",
            entity_type="git",
            entity_id="repository",
            context={},
            fatal=False,
        )
        display.show_error(e)


@git.command("branch")
@click.argument("issue_id")
@click.option(
    "--checkout/--no-checkout", default=True, help="Checkout the branch after creation"
)
@click.pass_context
def git_branch(ctx: click.Context, issue_id: str, checkout: bool):
    """Create a Git branch for an issue."""
    core = ctx.obj["core"]

    handler = GitBranchHandler(console)
    handler.create_branch(core, issue_id, checkout=checkout)


def _validate_branch_environment(core) -> bool:
    """Validate roadmap and git environment for branch creation.

    Args:
        core: RoadmapCore instance

    Returns:
        True if environment is valid
    """
    handler = GitBranchHandler(console)
    return handler.validate_branch_environment(core)


def _get_and_validate_issue(core, issue_id: str):
    """Get and validate issue exists.

    Args:
        core: RoadmapCore instance
        issue_id: Issue ID to retrieve

    Returns:
        Issue object or None if not found
    """
    handler = GitBranchHandler(console)
    return handler.get_and_validate_issue(core, issue_id)


def _safe_create_branch(git, issue, checkout=True) -> bool:
    """Safely create branch with fallback attempts.

    Args:
        git: Git executor
        issue: Issue object
        checkout: Whether to checkout the new branch

    Returns:
        True if branch was created
    """
    handler = GitBranchHandler(console)
    return handler._safe_create_branch(git, issue, checkout=checkout)


def _display_branch_success(branch_name: str, issue, checkout: bool) -> None:
    """Display success messages for branch creation.

    Args:
        branch_name: Name of created branch
        issue: Issue object
        checkout: Whether branch was checked out
    """
    handler = GitBranchHandler(console)
    handler._display_branch_success(branch_name, issue, checkout)


def _update_issue_status_if_needed(core, issue, issue_id: str) -> None:
    """Update issue status to in-progress if it's todo.

    Args:
        core: RoadmapCore instance
        issue: Issue object
        issue_id: Issue ID
    """
    handler = GitBranchHandler(console)
    handler._update_issue_status_if_needed(core, issue, issue_id)


@git.command("link")
@click.argument("issue_id")
@click.pass_context
@require_initialized
def git_link(ctx: click.Context, issue_id: str):
    """Link an issue to the current Git branch."""
    core = ctx.obj["core"]

    handler = GitBranchHandler(console)
    handler.link_issue_to_branch(core, issue_id)


# Register hooks-config command
git.add_command(hooks_config, name="hooks-config")
