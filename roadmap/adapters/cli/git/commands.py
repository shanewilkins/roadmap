"""Git integration and workflow commands."""

import click
from rich.console import Console

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.core.domain import Issue, Status

from .status_display import GitStatusDisplay

console = Console()


@click.group()
def git():
    """Git integration and workflow management."""
    pass


# Basic git commands - full implementation would be extracted from main CLI
@git.command("setup")
@click.pass_context
def setup_git(ctx: click.Context):
    """Setup Git integration."""
    console.print("⚙️ Git setup functionality will be implemented", style="green")


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
@click.pass_context
def sync_git(ctx: click.Context):
    """Sync with Git repository."""
    console.print("🔄 Git sync functionality will be implemented", style="green")


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
