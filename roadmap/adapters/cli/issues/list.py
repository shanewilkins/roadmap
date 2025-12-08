"""List issues command."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.errors import ErrorHandler, ValidationError
from roadmap.core.services.issue_helpers import (
    IssueFilterValidator,
    IssueQueryService,
    WorkloadCalculator,
)
from roadmap.infrastructure.logging import verbose_output
from roadmap.shared import IssueTableFormatter


def _get_console():
    """Get console instance at runtime to respect Click's test environment."""
    return get_console()


def _validate_and_get_issues(
    core,
    backlog: bool,
    assignee: str,
    my_issues: bool,
    unassigned: bool,
    next_milestone: bool,
    milestone: str,
    overdue: bool,
) -> tuple[list | None, str | None]:
    """Validate filter combinations and get filtered issues.

    Args:
        core: RoadmapCore instance
        backlog: Show backlog issues
        assignee: Filter by assignee
        my_issues: Show current user's issues
        unassigned: Show unassigned issues
        next_milestone: Show next milestone issues
        milestone: Filter by milestone name
        overdue: Show overdue issues

    Returns:
        Tuple of (issues list or None, filter description or None)
    """
    is_valid, error_msg = IssueFilterValidator.validate_filters(
        assignee, my_issues, backlog, unassigned, next_milestone, milestone
    )
    if not is_valid:
        _get_console().print(f"❌ {error_msg}", style="bold red")
        return None, None

    query_service = IssueQueryService(core)
    issues, filter_description = query_service.get_filtered_issues(
        milestone=milestone,
        backlog=backlog,
        overdue=overdue,
        unassigned=unassigned,
        next_milestone=next_milestone,
        assignee=assignee,
        my_issues=my_issues,
    )

    return issues, filter_description


def _handle_no_upcoming_milestones() -> None:
    """Handle case where no upcoming milestones are found."""
    _get_console().print(
        "📋 No upcoming milestones with due dates found.", style="yellow"
    )
    _get_console().print(
        "Create one with: roadmap milestone create 'Milestone name' --due-date YYYY-MM-DD",
        style="dim",
    )


def _display_issues_with_filters(
    core,
    issues: list,
    filter_description: str | None,
    open_flag: bool,
    blocked: bool,
    status: str,
    priority: str,
    issue_type: str,
    assignee: str,
    my_issues: bool,
) -> None:
    """Display filtered issues and workload summary.

    Args:
        core: RoadmapCore instance
        issues: List of issues to display
        filter_description: Description of applied filters
        open_flag: Show only open issues
        blocked: Show only blocked issues
        status: Filter by status
        priority: Filter by priority
        issue_type: Filter by issue type
        assignee: Filter by assignee
        my_issues: Show current user's issues
    """
    query_service = IssueQueryService(core)
    issues, filter_description = query_service.apply_additional_filters(
        issues,
        filter_description or "",
        open_only=open_flag,
        blocked_only=blocked,
        status=status,
        priority=priority,
        issue_type=issue_type,
    )

    IssueTableFormatter.display_issues(issues, filter_description)

    if (assignee or my_issues) and issues:
        assignee_name = assignee if assignee else "you"
        workload = WorkloadCalculator.calculate_workload(issues)
        IssueTableFormatter.display_workload_summary(
            assignee_name,
            workload["total_hours"],
            workload["status_breakdown"],
        )


@click.command("list")
@click.argument(
    "filter_type",
    required=False,
    default=None,
    type=click.Choice(["backlog"], case_sensitive=False),
)
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option("--backlog", is_flag=True, help="Show only backlog issues (no milestone)")
@click.option(
    "--unassigned",
    is_flag=True,
    help="Show only unassigned issues (alias for --backlog)",
)
@click.option("--open", is_flag=True, help="Show only open issues (not done)")
@click.option("--blocked", is_flag=True, help="Show only blocked issues")
@click.option(
    "--next-milestone", is_flag=True, help="Show issues for the next upcoming milestone"
)
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--my-issues", is_flag=True, help="Show only issues assigned to me")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
    help="Filter by status",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Filter by priority",
)
@click.option(
    "--issue-type",
    "-t",
    type=click.Choice(["feature", "bug", "other"]),
    help="Filter by issue type",
)
@click.option(
    "--overdue", is_flag=True, help="Show only overdue issues (past due date)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
@require_initialized
def list_issues(
    ctx: click.Context,
    filter_type: str,
    milestone: str,
    backlog: bool,
    unassigned: bool,
    open: bool,
    blocked: bool,
    next_milestone: bool,
    assignee: str,
    my_issues: bool,
    status: str,
    priority: str,
    issue_type: str,
    overdue: bool,
    verbose: bool,
):
    """List all issues with various filtering options.

    Optional positional argument 'backlog' shows only backlog issues (no milestone).
    Equivalent to: roadmap issue list --backlog
    """
    core = ctx.obj["core"]

    # Handle positional filter_type argument
    if filter_type and filter_type.lower() == "backlog":
        backlog = True

    try:
        # Validate and get issues
        issues, filter_description = _validate_and_get_issues(
            core,
            backlog,
            assignee,
            my_issues,
            unassigned,
            next_milestone,
            milestone,
            overdue,
        )

        if issues is None:
            return

        # Handle next milestone not found
        if next_milestone and not issues and not filter_description:
            _handle_no_upcoming_milestones()
            return

        # Display issues with filters
        _display_issues_with_filters(
            core,
            issues,
            filter_description,
            open,
            blocked,
            status,
            priority,
            issue_type,
            assignee,
            my_issues,
        )

    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to list issues", context={"command": "list"}, cause=e
            ),
            exit_on_critical=False,
        )
