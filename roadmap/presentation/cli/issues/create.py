"""Create issue command."""

import click

from roadmap.cli.issue_creation import (
    AssigneeResolver,
    GitBranchCreator,
    IssueDisplayFormatter,
)
from roadmap.domain import IssueType, Priority
from roadmap.presentation.cli.error_logging import log_error_with_context
from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.presentation.cli.performance_tracking import track_database_operation
from roadmap.shared.console import get_console
from roadmap.shared.errors import ErrorHandler, ValidationError

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
@click.pass_context
@log_command("issue_create", entity_type="issue", track_duration=True)
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
):
    """Create a new issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Resolve assignee with auto-detection and validation
        assignee_resolver = AssigneeResolver(core)
        canonical_assignee = assignee_resolver.resolve_assignee(assignee)

        # Create the issue
        with track_database_operation("create", "issue", warn_threshold_ms=2000):
            issue = core.create_issue(
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
        IssueDisplayFormatter.display_created_issue(issue, milestone, assignee)

        # Create Git branch if requested
        if git_branch:
            branch_creator = GitBranchCreator(core)
            branch_creator.create_branch(issue, branch_name, checkout, force)

    except click.Abort:
        raise
    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_create",
            entity_type="issue",
            additional_context={"title": title, "priority": priority},
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
