"""Start issue command."""

import click

from roadmap.cli.utils import get_console

console = get_console()


def _safe_create_branch(git, issue, checkout=True, force=False):
    """Call create_branch_for_issue with best-effort compatibility for older signatures.

    Tries the newest signature (checkout, force) first, falls back to older ones.
    """
    try:
        return git.create_branch_for_issue(issue, checkout=checkout, force=force)
    except TypeError:
        # Try without force
        try:
            return git.create_branch_for_issue(issue, checkout=checkout)
        except TypeError:
            # Try fully positional (issue only)
            try:
                return git.create_branch_for_issue(issue)
            except Exception:
                return False


@click.command("start")
@click.argument("issue_id")
@click.option("--date", help="Start date (YYYY-MM-DD HH:MM, defaults to now)")
@click.option(
    "--git-branch/--no-git-branch",
    default=False,
    help="Create a Git branch for this issue when starting",
)
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the created branch (when --git-branch is used)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.pass_context
def start_issue(
    ctx: click.Context,
    issue_id: str,
    date: str,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Start work on an issue by recording the actual start date."""
    from roadmap.cli.start_issue_helpers import (
        StartDateParser,
        StartIssueDisplay,
        StartIssueWorkflow,
    )

    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Parse start date
        start_date = StartDateParser.parse_start_date(date)
        if start_date is None:
            console.print(
                "❌ Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM",
                style="bold red",
            )
            return

        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Start work on issue
        success = StartIssueWorkflow.start_work(core, issue_id, start_date)

        if success:
            StartIssueDisplay.show_started(issue, start_date, console)

            # Handle git branch creation
            if StartIssueWorkflow.should_create_branch(git_branch, core):
                _handle_git_branch_creation(
                    core, issue, branch_name, checkout, force, console
                )
        else:
            console.print(f"❌ Failed to start issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to start issue: {e}", style="bold red")


def _handle_git_branch_creation(core, issue, branch_name, checkout, force, console):
    """Handle git branch creation for started issue."""
    from roadmap.cli.start_issue_helpers import StartIssueDisplay

    try:
        if hasattr(core, "git") and core.git.is_git_repository():
            resolved_branch_name = branch_name or core.git.suggest_branch_name(issue)
            branch_success = _safe_create_branch(
                core.git, issue, checkout=checkout, force=force
            )
            if branch_success:
                StartIssueDisplay.show_branch_created(
                    resolved_branch_name, checkout, console
                )
            else:
                StartIssueDisplay.show_branch_warning(core, console)
        else:
            console.print(
                "⚠️  Not in a Git repository, skipping branch creation",
                style="yellow",
            )
    except Exception as e:
        console.print(
            f"⚠️  Git branch creation skipped due to error: {e}", style="yellow"
        )
