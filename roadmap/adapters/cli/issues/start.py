"""Start issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status in-progress
with optional Git branch creation.
"""

import click

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command
from roadmap.adapters.cli.performance_tracking import track_database_operation
from roadmap.common.console import get_console

console = get_console()


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
@log_command("issue_start", entity_type="issue", track_duration=True)
def start_issue(
    ctx: click.Context,
    issue_id: str,
    date: str,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Start work on an issue (sets status to in-progress and records start date).

    Syntactic sugar for: roadmap issue update <ID> --status in-progress
    """
    from roadmap.adapters.cli.start_issue_helpers import (
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
        issue = core.issues.get(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Start work on issue via core.update_issue
        with track_database_operation("update", "issue", entity_id=issue_id):
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
        log_error_with_context(
            e,
            operation="issue_start",
            entity_type="issue",
            entity_id=issue_id,
        )
        console.print(f"❌ Failed to start issue: {e}", style="bold red")


def _handle_git_branch_creation(core, issue, branch_name, checkout, force, console):
    """Handle git branch creation for started issue."""
    from roadmap.adapters.cli.start_issue_helpers import StartIssueDisplay

    try:
        if hasattr(core, "git") and core.git.is_git_repository():
            resolved_branch_name = branch_name or core.git.suggest_branch_name(issue)
            branch_success = core.git.create_branch_for_issue(
                issue, checkout=checkout, force=force
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
