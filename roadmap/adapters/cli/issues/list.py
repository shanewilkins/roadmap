"""List issues command."""

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.decorators import with_output_support
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.cli_models import IssueListParams
from roadmap.common.console import get_console
from roadmap.common.errors import ErrorHandler, ValidationError
from roadmap.common.output_models import ColumnType
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
    assignee: str | None,
    my_issues: bool,
    unassigned: bool,
    next_milestone: bool,
    milestone: str | None,
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


def _apply_additional_filters(
    core,
    issues: list,
    filter_description: str | None,
    open_flag: bool,
    blocked: bool,
    status: str | None,
    priority: str | None,
    issue_type: str | None,
) -> tuple[list, str]:
    """Apply additional filters to issues.

    Args:
        core: RoadmapCore instance
        issues: List of issues to filter
        filter_description: Current filter description
        open_flag: Show only open issues
        blocked: Show only blocked issues
        status: Filter by status
        priority: Filter by priority
        issue_type: Filter by issue type

    Returns:
        Tuple of (filtered issues, updated filter description)
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
    return issues, filter_description


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
@with_output_support(
    available_columns=[
        "id",
        "title",
        "priority",
        "status",
        "progress",
        "assignee",
        "estimate",
        "milestone",
    ],
    column_types={
        "id": ColumnType.STRING,
        "title": ColumnType.STRING,
        "priority": ColumnType.ENUM,
        "status": ColumnType.ENUM,
        "progress": ColumnType.STRING,
        "assignee": ColumnType.STRING,
        "estimate": ColumnType.STRING,
        "milestone": ColumnType.STRING,
    },
)
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

    Supports output formatting with --format, --columns, --sort-by, --filter flags.
    """
    core = ctx.obj["core"]

    # Create structured parameter object
    params = IssueListParams(
        filter_type=filter_type,
        milestone=milestone,
        backlog=backlog,
        unassigned=unassigned,
        open=open,
        blocked=blocked,
        next_milestone=next_milestone,
        assignee=assignee,
        my_issues=my_issues,
        status=status,
        priority=priority,
        issue_type=issue_type,
        overdue=overdue,
    )

    try:
        # Handle positional filter_type argument
        if params.filter_type and params.filter_type.lower() == "backlog":
            params.backlog = True

        # Validate and get issues
        issues, filter_description = _validate_and_get_issues(
            core,
            params.backlog,
            params.assignee,
            params.my_issues,
            params.unassigned,
            params.next_milestone,
            params.milestone,
            params.overdue,
        )

        if issues is None:
            return

        # Handle next milestone not found
        if next_milestone and not issues and not filter_description:
            _handle_no_upcoming_milestones()
            return

        # Apply additional filters
        issues, filter_description = _apply_additional_filters(
            core,
            issues,
            filter_description,
            params.open,
            params.blocked,
            params.status,
            params.priority,
            params.issue_type,
        )

        # Handle no issues found
        if not issues:
            _get_console().print(
                f"📋 No {filter_description} issues found.", style="yellow"
            )
            _get_console().print(
                "Create one with: roadmap issue create 'Issue title'", style="dim"
            )
            return

        # Display header with count
        issue_count = len(issues)
        header_text = f"📋 {issue_count} {filter_description} issue{'s' if issue_count != 1 else ''}"
        _get_console().print(header_text, style="bold cyan")

        # Convert issues to TableData for structured output
        table_data = IssueTableFormatter.issues_to_table_data(
            issues,
            title="Issues",
            description=filter_description,
        )

        # Display workload summary if applicable
        if (params.assignee or params.my_issues) and issues:
            assignee_name = params.assignee if params.assignee else "you"
            workload = WorkloadCalculator.calculate_workload(issues)
            IssueTableFormatter.display_workload_summary(
                assignee_name,
                workload["total_hours"],
                workload["status_breakdown"],
            )

        # Return TableData for decorator to handle formatting
        return table_data

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="list_issues",
            entity_type="issue",
            entity_id="all",
            context={
                "backlog": params.backlog,
                "assignee": params.assignee,
                "my_issues": params.my_issues,
                "filter": params.status,
            },
            fatal=True,
        )
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to list issues", context={"command": "list"}, cause=e
            ),
            exit_on_critical=False,
        )
