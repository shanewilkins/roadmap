"""Git integration and workflow commands."""

import sys
from typing import Literal

import click
import structlog
from rich.console import Console

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.git.hooks_config import hooks_config
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.adapters.github.github import GitHubClient
from roadmap.common.console import get_console
from roadmap.core.domain import Issue, Status
from roadmap.core.services.github_integration_service import GitHubIntegrationService
from roadmap.infrastructure.security.credentials import CredentialManager

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
    """Setup Git integration and authentication.

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
    cred_manager = CredentialManager()
    existing_token = None

    if not update_token:
        try:
            existing_token = cred_manager.get_token()
            if existing_token:
                console.print("🔍 Found existing GitHub credentials")
                if click.confirm("Use existing GitHub token?"):
                    log.info("github_auth_using_existing")
                    console.print("✅ GitHub authentication configured")
                    return
                elif not click.confirm("Update GitHub token?"):
                    console.print("Skipped GitHub authentication setup")
                    return
        except Exception:
            pass  # No existing token

    # Get new token from user
    console.print("🔑 GitHub Authentication Setup", style="bold cyan")
    console.print()
    console.print(
        "You'll need a Personal Access Token with 'repo' scope to sync with GitHub."
    )
    console.print("Create one here: https://github.com/settings/tokens/new")
    console.print()
    console.print(
        "Required scopes: repo (full control of private repositories)",
        style="dim",
    )
    console.print()

    token = click.prompt("Enter your GitHub Personal Access Token", hide_input=True)

    if not token or len(token.strip()) == 0:
        console.print("❌ Token cannot be empty", style="bold red")
        log.warning("github_auth_empty_token")
        return

    # Validate token
    console.print("🧪 Validating GitHub token...", style="cyan")
    log.debug("github_token_validating")

    try:
        client = GitHubClient(token)
        # Test connection and authentication
        user_data = client.test_authentication()
        username = user_data.get("login", "user")
        console.print(f"✅ Token valid (authenticated as @{username})", style="green")
        log.info("github_token_valid", username=username)
    except Exception as e:
        console.print(f"❌ Token validation failed: {e}", style="bold red")
        log.error(
            "github_token_validation_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return

    # Store token
    try:
        if cred_manager.store_token(token):
            console.print("✅ GitHub authentication configured", style="green")
            console.print(
                "Token stored securely in system keychain",
                style="dim",
            )
            log.info("github_token_stored")
        else:
            console.print(
                "⚠️  Token validation succeeded but storage failed",
                style="yellow",
            )
            log.warning("github_token_storage_failed")
    except Exception as e:
        console.print(
            f"⚠️  Token validation succeeded but could not store: {e}",
            style="yellow",
        )
        log.warning(
            "github_token_storage_error",
            error=str(e),
            error_type=type(e).__name__,
        )


def _test_git_connectivity(core):
    """Test and verify Git repository connectivity for self-hosting.

    Args:
        core: RoadmapCore instance

    Raises:
        Exception: If git connectivity test fails
    """
    from roadmap.adapters.cli.services.sync_service import (
        get_sync_backend,
        test_backend_connectivity,
    )

    console.print("🔌 Git Repository Connectivity Test", style="bold cyan")
    console.print()

    # Try to create vanilla git backend to test connectivity
    console.print("🧪 Testing Git repository connectivity...", style="cyan")
    log.debug("git_connectivity_testing")

    try:
        # Use sync service to create vanilla git backend
        backend = get_sync_backend("git", core, {})

        if backend is None:
            console.print(
                "❌ Could not initialize Git backend (not in a git repository?)",
                style="bold red",
            )
            log.warning("git_backend_initialization_failed")
            return

        # Test authentication (connectivity check)
        success, message = test_backend_connectivity(backend, "git")
        if success:
            console.print(message, style="green")
            console.print(
                "Your git repository is accessible and ready for syncing",
                style="dim",
            )
            log.info("git_connectivity_verified")
        else:
            console.print(
                "⚠️  Could not verify git remote access",
                style="yellow",
            )
            console.print()
            console.print(
                "This might be due to:",
                style="dim",
            )
            console.print("  • SSH key not configured", style="dim")
            console.print("  • HTTPS credentials needed", style="dim")
            console.print("  • Network connectivity issues", style="dim")
            console.print(
                "  • Remote repository doesn't exist yet",
                style="dim",
            )
            console.print()
            console.print(
                "For SSH: Make sure your SSH key is in ~/.ssh/",
                style="dim",
            )
            console.print(
                "For HTTPS: Configure git credentials with: git config credential.helper",
                style="dim",
            )
            log.warning("git_connectivity_verification_failed")

    except ValueError as e:
        console.print(
            f"❌ Git repository error: {e}",
            style="bold red",
        )
        log.error(
            "git_repository_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        console.print()
        console.print(
            "Make sure you're in a git repository directory",
            style="dim",
        )
    except Exception as e:
        console.print(
            f"❌ Connectivity test failed: {e}",
            style="bold red",
        )
        log.error(
            "git_connectivity_error",
            error=str(e),
            error_type=type(e).__name__,
        )


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
        manager = GitHookManager(core)
        if manager.install_hooks():
            console.print("✅ Git hooks installed successfully", style="bold green")
            console.print(
                "Hooks will now automatically track commits and branch changes",
                style="green",
            )
        else:
            console.print(
                "❌ Failed to install hooks. Not a git repository?", style="bold red"
            )
            ctx.exit(1)
    except Exception as e:
        console.print(f"❌ Error installing hooks: {e}", style="bold red")
        ctx.exit(1)


@git.command("hooks-uninstall")
@click.pass_context
@require_initialized
def uninstall_hooks(ctx: click.Context):
    """Remove Git hooks for roadmap integration."""
    core = ctx.obj["core"]

    try:
        manager = GitHookManager(core)
        if manager.uninstall_hooks():
            console.print("✅ Git hooks removed successfully", style="bold green")
        else:
            console.print("❌ Failed to remove hooks", style="bold red")
            ctx.exit(1)
    except Exception as e:
        console.print(f"❌ Error removing hooks: {e}", style="bold red")
        ctx.exit(1)


@git.command("hooks-status")
@click.pass_context
@require_initialized
def hooks_status(ctx: click.Context):
    """Show status of installed Git hooks."""
    core = ctx.obj["core"]

    try:
        manager = GitHookManager(core)
        status = manager.get_hooks_status()

        if not status:
            console.print("No hooks installed", style="yellow")
            return

        console.print("Git Hooks Status:", style="bold")
        console.print()

        for hook_name, hook_info in status.items():
            installed = "✅" if hook_info.get("is_roadmap_hook") else "❌"
            executable = "✓" if hook_info.get("executable") else "✗"
            console.print(f"{installed} {hook_name:20} [executable: {executable}]")

        console.print()
        console.print(
            "Run 'roadmap git hooks-install' to install all hooks", style="dim"
        )
    except Exception as e:
        console.print(f"❌ Error checking hooks: {e}", style="bold red")
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
        from roadmap.adapters.sync import GenericSyncOrchestrator
        from roadmap.core.services.sync_conflict_resolver import SyncConflictResolver
        from roadmap.core.services.sync_state_comparator import SyncStateComparator

        # Create service instances
        state_comparator = SyncStateComparator()
        conflict_resolver = SyncConflictResolver()

        # Create orchestrator with services
        orchestrator = GenericSyncOrchestrator(
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
        console_inst.print(f"   • {apply_report.issues_updated} updated")
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

    if not _validate_branch_environment(core):
        return

    try:
        issue = _get_and_validate_issue(core, issue_id)
        if not issue:
            return

        branch_name = core.git.suggest_branch_name(issue_id)
        if not branch_name:
            console.print(
                "❌ Could not suggest branch name for issue", style="bold red"
            )
            return

        # Create the branch (use a compatibility wrapper)
        success = _safe_create_branch(core.git, issue, checkout=checkout)

        if success:
            _display_branch_success(branch_name, issue, checkout)
            _update_issue_status_if_needed(core, issue, issue_id)
        else:
            # Try a direct git fallback (useful if create_branch_for_issue is not available or failed)
            fallback = core.git._run_git_command(["checkout", "-b", branch_name])
            if fallback is not None:
                _display_branch_success(branch_name, issue, checkout)
                _update_issue_status_if_needed(core, issue, issue_id)
            else:
                console.print("❌ Failed to create branch", style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="create_git_branch",
            entity_type="issue",
            entity_id=issue_id,
            context={"checkout": checkout},
            fatal=True,
        )
        console.print(f"❌ Failed to create Git branch: {e}", style="bold red")


def _validate_branch_environment(core) -> bool:
    """Validate roadmap and git environment for branch creation.

    Args:
        core: RoadmapCore instance

    Returns:
        True if environment is valid
    """
    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return False

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return False

    return True


def _get_and_validate_issue(core, issue_id: str):
    """Get and validate issue exists.

    Args:
        core: RoadmapCore instance
        issue_id: Issue ID to retrieve

    Returns:
        Issue object or None if not found
    """
    issue = core.issues.get(issue_id)
    if not issue:
        console.print(f"❌ Issue not found: {issue_id}", style="bold red")
        return None
    return issue


def _safe_create_branch(git, issue, checkout=True) -> bool:
    """Safely create branch with fallback attempts.

    Args:
        git: Git executor
        issue: Issue object
        checkout: Whether to checkout the new branch

    Returns:
        True if branch was created
    """
    try:
        return git.create_branch_for_issue(issue, checkout=checkout)
    except TypeError as e:
        handle_cli_error(
            error=e,
            operation="create_branch_for_issue",
            entity_type="issue",
            entity_id=issue.id,
            context={"checkout": checkout, "error_type": "TypeError"},
            fatal=False,
        )
        try:
            return git.create_branch_for_issue(issue)
        except Exception as e:
            handle_cli_error(
                error=e,
                operation="create_branch_for_issue_fallback",
                entity_type="issue",
                entity_id=issue.id,
                context={},
                fatal=False,
            )
            return False


def _display_branch_success(branch_name: str, issue, checkout: bool) -> None:
    """Display success messages for branch creation.

    Args:
        branch_name: Name of created branch
        issue: Issue object
        checkout: Whether branch was checked out
    """
    console.print(f"🌿 Created branch: {branch_name}", style="bold green")
    if checkout:
        console.print(f"✅ Checked out branch: {branch_name}", style="green")
    console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")


def _update_issue_status_if_needed(core, issue: Issue, issue_id: str) -> None:
    """Update issue status to in-progress if it's todo.

    Args:
        core: RoadmapCore instance
        issue: Issue object
        issue_id: Issue ID
    """
    if issue.status == Status.TODO:
        core.issues.update(issue_id, status=Status.IN_PROGRESS)
        console.print("📊 Updated issue status to: in-progress", style="yellow")


@git.command("link")
@click.argument("issue_id")
@click.pass_context
@require_initialized
def git_link(ctx: click.Context, issue_id: str):
    """Link an issue to the current Git branch."""
    core = ctx.obj["core"]

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        issue = core.issues.get(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        current_branch = core.git.get_current_branch()
        if not current_branch:
            console.print("❌ Could not determine current branch", style="bold red")
            return

        # Link the issue to the current branch
        success = core.git.link_issue_to_branch(issue_id)

        if success:
            console.print(
                f"🔗 Linked issue to branch: {current_branch}", style="bold green"
            )
            console.print(f"📋 Issue: {issue.title}", style="cyan")
            console.print(f"🆔 ID: {issue_id}", style="dim")
        else:
            console.print("❌ Failed to link issue to branch", style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="link_issue_to_branch",
            entity_type="issue",
            entity_id=issue_id,
            context={},
            fatal=True,
        )
        console.print(f"❌ Failed to link issue to Git branch: {e}", style="bold red")


# Register hooks-config command
git.add_command(hooks_config, name="hooks-config")
