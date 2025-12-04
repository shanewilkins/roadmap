"""Git integration and workflow commands."""

import click
from rich.console import Console

from roadmap.domain import Status

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


@git.command("sync")
@click.pass_context
def sync_git(ctx: click.Context):
    """Sync with Git repository."""
    console.print("🔄 Git sync functionality will be implemented", style="green")


@git.command("status")
@click.pass_context
def git_status(ctx: click.Context):
    """Show Git repository status and roadmap integration info."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    display = GitStatusDisplay(console)

    try:
        git_context = core.get_git_context()

        if not git_context.get("is_git_repo", False):
            display.show_not_git_repo()
            return

        display.show_header()
        display.show_repository_info(git_context)
        display.show_current_branch(git_context)

        branch_issues = core.get_branch_linked_issues()
        current_branch = git_context.get("current_branch", "")
        display.show_branch_issue_links(branch_issues, current_branch, core)

        display.show_recent_commits(core)

    except Exception as e:
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

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        branch_name = core.suggest_branch_name_for_issue(issue_id)
        if not branch_name:
            console.print(
                "❌ Could not suggest branch name for issue", style="bold red"
            )
            return

        # Create the branch (use a compatibility wrapper)
        def _safe_create_branch(git, issue, checkout=True):
            try:
                return git.create_branch_for_issue(issue, checkout=checkout)
            except TypeError:
                try:
                    return git.create_branch_for_issue(issue)
                except Exception:
                    return False

        success = _safe_create_branch(core.git, issue, checkout=checkout)

        if success:
            console.print(f"🌿 Created branch: {branch_name}", style="bold green")
            if checkout:
                console.print(f"✅ Checked out branch: {branch_name}", style="green")
            console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")

            # Update issue status to in-progress if it's todo
            if issue.status == Status.TODO:
                core.update_issue(issue_id, status=Status.IN_PROGRESS)
                console.print("📊 Updated issue status to: in-progress", style="yellow")
        else:
            # Try a direct git fallback (useful if create_branch_for_issue is not available or failed)
            fallback = core.git._run_git_command(["checkout", "-b", branch_name])
            if fallback is not None:
                console.print(f"🌿 Created branch: {branch_name}", style="bold green")
                if checkout:
                    console.print(
                        f"✅ Checked out branch: {branch_name}", style="green"
                    )
                console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")
                if issue.status == Status.TODO:
                    core.update_issue(issue_id, status=Status.IN_PROGRESS)
                    console.print(
                        "📊 Updated issue status to: in-progress", style="yellow"
                    )
            else:
                console.print("❌ Failed to create branch", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to create Git branch: {e}", style="bold red")


@git.command("link")
@click.argument("issue_id")
@click.pass_context
def git_link(ctx: click.Context, issue_id: str):
    """Link an issue to the current Git branch."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        current_branch = core.git.get_current_branch()
        if not current_branch:
            console.print("❌ Could not determine current branch", style="bold red")
            return

        # Link the issue to the current branch
        success = core.link_issue_to_current_branch(issue_id)

        if success:
            console.print(
                f"🔗 Linked issue to branch: {current_branch}", style="bold green"
            )
            console.print(f"📋 Issue: {issue.title}", style="cyan")
            console.print(f"🆔 ID: {issue_id}", style="dim")
        else:
            console.print("❌ Failed to link issue to branch", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to link issue to Git branch: {e}", style="bold red")
