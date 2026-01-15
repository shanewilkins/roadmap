"""Start issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status in-progress
with optional Git branch creation.
"""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.common.console import get_console
from roadmap.core.services import StartIssueService
from roadmap.infrastructure.logging import (
    log_command,
    track_database_operation,
)
from roadmap.shared.formatters.text.operations import (
    format_operation_failure,
    format_operation_success,
)

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
@require_initialized
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
    core = ctx.obj["core"]

    try:
        # Create start issue service
        service = StartIssueService(core)

        # Parse start date
        try:
            start_date = service.parse_start_date(date)
        except ValueError:
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
            success = service.start_work(issue_id, start_date)

        if success:
            # Build extra details
            extra_details = {
                "Status": "🚀 In Progress",
                "Started": start_date.strftime("%Y-%m-%d %H:%M"),
            }

            # Display success with formatter
            lines = format_operation_success(
                emoji="🚀",
                action="Started",
                entity_title=issue.title,
                entity_id=issue_id,
                extra_details=extra_details,
            )
            for line in lines:
                console.print(line, style="bold green" if "Started" in line else "cyan")

            # Handle git branch creation
            if service.should_create_branch(git_branch):
                _handle_git_branch_creation(
                    core, service, issue, branch_name, checkout, force
                )
        else:
            lines = format_operation_failure(
                action="start",
                entity_id=issue_id,
                error="Failed to update status",
            )
            for line in lines:
                console.print(line, style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="start_issue",
            entity_type="issue",
            entity_id=issue_id,
            context={
                "git_branch": git_branch,
                "checkout": checkout,
                "branch_name": branch_name,
            },
            fatal=True,
        )
        lines = format_operation_failure(
            action="start",
            entity_id=issue_id,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")


def _handle_git_branch_creation(core, service, issue, branch_name, checkout, force):
    """Handle git branch creation for started issue."""
    try:
        if hasattr(core, "git") and core.git.is_git_repository():
            success, resolved_branch_name = service.core.git.create_branch_for_issue(
                issue, checkout=checkout, force=force
            )
            if success and resolved_branch_name:
                service.display_branch_created(resolved_branch_name, checkout)
            else:
                service.display_branch_warning()
        else:
            console.print(
                "⚠️  Not in a Git repository, skipping branch creation",
                style="yellow",
            )
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="create_git_branch",
            entity_type="issue",
            entity_id=issue.id,
            context={"branch_name": branch_name},
            fatal=False,
        )
        console.print(
            f"⚠️  Git branch creation skipped due to error: {e}", style="yellow"
        )
