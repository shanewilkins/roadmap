"""Create issue command."""

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.errors import ErrorHandler, ValidationError
from roadmap.core.domain import IssueType, Priority
from roadmap.core.services import IssueCreationService
from roadmap.infrastructure.logging import (
    log_command,
    track_database_operation,
    verbose_output,
)

console = get_console()


@click.command("create")
@click.argument("title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Issue priority",
)
@click.option(
    "--type",
    "-t",
    "issue_type",
    type=click.Choice(["feature", "bug", "other"]),
    default="other",
    help="Issue type",
)
@click.option("--milestone", "-m", help="Assign to milestone")
@click.option("--assignee", "-a", help="Assign to team member")
@click.option("--labels", "-l", multiple=True, help="Add labels")
@click.option(
    "--estimate", "-e", type=float, help="Estimated time to complete (in hours)"
)
@click.option("--depends-on", multiple=True, help="Issue IDs this depends on")
@click.option("--blocks", multiple=True, help="Issue IDs this blocks")
@click.option("--git-branch", is_flag=True, help="Create a Git branch for this issue")
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the branch after creation (with --git-branch)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
@log_command("issue_create", entity_type="issue", track_duration=True)
@require_initialized
def create_issue(
    ctx: click.Context,
    title: str,
    priority: str,
    issue_type: str,
    milestone: str,
    assignee: str,
    labels: tuple,
    estimate: float,
    depends_on: tuple,
    blocks: tuple,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
    verbose: bool,
):
    """Create a new issue."""
    core = ctx.obj["core"]

    try:
        # Create issue creation service
        service = IssueCreationService(core)

        # Resolve assignee with auto-detection and validation
        canonical_assignee = service.resolve_and_validate_assignee(assignee)

        # Create the issue
        with track_database_operation("create", "issue", warn_threshold_ms=2000):
            issue = core.issues.create(
                title=title,
                priority=Priority(priority),
                issue_type=IssueType(issue_type),
                milestone=milestone,
                assignee=canonical_assignee,
                labels=list(labels),
                estimated_hours=estimate,
                depends_on=list(depends_on),
                blocks=list(blocks),
            )

        # Display issue information
        service.format_created_issue_display(issue, milestone)

        # Create Git branch if requested
        if git_branch:
            service.create_branch_for_issue(issue, branch_name, checkout, force)

    except click.Abort:
        raise
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="create_issue",
            entity_type="issue",
            entity_id="new",
            context={"title": title, "priority": priority, "milestone": milestone},
            fatal=True,
        )
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to create issue",
                context={"command": "create", "title": title},
                cause=e,
            ),
            exit_on_critical=False,
        )
