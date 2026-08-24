"""List issues through the target read-only application boundary."""

from collections import Counter

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.decorators import with_output_support
from roadmap.adapters.cli.planning_resolution import resolve_milestone_id
from roadmap.application.contracts import IssueListQuery, IssueQueryRecord, IssueScope
from roadmap.application.failures import ApplicationFailure
from roadmap.common.console import get_console
from roadmap.common.formatters.tables.column_factory import create_issue_columns
from roadmap.common.logging import verbose_output
from roadmap.common.models import ColumnType, TableData


def _time(hours: float | None) -> str:
    if hours is None:
        return "Not estimated"
    if hours < 1:
        return f"{hours * 60:.0f}m"
    if hours <= 24:
        return f"{hours:.1f}h"
    return f"{hours / 8:.1f}d"


def _progress(record: IssueQueryRecord) -> str:
    value = record.issue.progress_percentage
    return f"{value:g}%" if value is not None else "0%"


def _table(result) -> TableData:
    rows = []
    for record in result.records:
        issue = record.issue
        rows.append(
            [
                str(issue.id),
                str(issue.title),
                issue.priority.value,
                issue.status.value,
                _progress(record),
                issue.assignee or "Unassigned",
                _time(issue.estimated_hours),
                record.milestone_name or str(issue.relations.milestone_id or "Backlog"),
                f"💬 {len(record.comments)}" if record.comments else "",
            ]
        )
    return TableData(
        columns=create_issue_columns(),
        rows=rows,
        title="Issues",
        headline=result.description,
        total_count=len(rows),
        returned_count=len(rows),
    )


def _workload(records: tuple[IssueQueryRecord, ...], assignee: str) -> None:
    total = sum(record.issue.estimated_hours or 0 for record in records)
    breakdown = Counter(record.issue.status.value for record in records)
    console = get_console()
    console.print(
        f"Total estimated time for {assignee}: {_time(total)}", style="bold blue"
    )
    console.print("Workload breakdown:", style="bold")
    for status in sorted(breakdown):
        console.print(f"  {status}: {breakdown[status]} issues")


@click.command("list")
@click.argument(
    "filter_type",
    required=False,
    default=None,
    type=click.Choice(["backlog"], case_sensitive=False),
)
@click.option("--milestone", "-m", help="Filter by milestone ID")
@click.option("--backlog", is_flag=True, help="Show only issues with no milestone")
@click.option("--unassigned", is_flag=True, help="Alias for --backlog")
@click.option("--open", "open_only", is_flag=True, help="Show non-closed issues")
@click.option("--blocked", is_flag=True, help="Show only blocked issues")
@click.option("--next-milestone", is_flag=True, help="Show the next milestone")
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--my-issues", is_flag=True, help="Show issues assigned to me")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
)
@click.option(
    "--issue-type",
    "-t",
    type=click.Choice(["feature", "bug", "other"]),
)
@click.option("--overdue", is_flag=True, help="Show overdue issues")
@click.option("--search", help="Search issue title, headline, and content")
@click.option(
    "--scope",
    type=click.Choice([scope.value for scope in IssueScope]),
    default=IssueScope.VISIBLE.value,
    show_default=True,
    help="Select visible, closed, archived, or all lifecycle records",
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
        "comment_count",
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
        "comment_count": ColumnType.STRING,
    },
)
@verbose_output
@require_initialized
def list_issues(  # noqa: F841
    ctx: click.Context,
    filter_type: str | None,
    milestone: str | None,
    backlog: bool,
    unassigned: bool,
    open_only: bool,
    blocked: bool,
    next_milestone: bool,
    assignee: str | None,
    my_issues: bool,
    status: str | None,
    priority: str | None,
    issue_type: str | None,
    overdue: bool,
    search: str | None,
    scope: str,
    verbose: bool,
):
    """List, filter, search, and sort canonical issues."""
    core = ctx.obj["core"]
    query = IssueListQuery(
        scope=IssueScope(scope),
        milestone=resolve_milestone_id(core, milestone) if milestone else None,
        backlog=backlog or unassigned or filter_type == "backlog",
        next_milestone=next_milestone,
        assignee=assignee,
        current_assignee=my_issues,
        open_only=open_only,
        blocked_only=blocked,
        status=status,
        priority=priority,
        issue_type=issue_type,
        overdue=overdue,
        search=search,
    )
    try:
        result = core.issue_queries.list(query)
    except (ApplicationFailure, ValueError) as error:
        raise click.ClickException(str(error)) from error
    console = get_console()
    if result.next_milestone_missing:
        console.print("📋 No upcoming milestones with due dates found.", style="yellow")
        return None
    if not result.records:
        console.print(f"📋 No {result.description} issues found.", style="yellow")
        console.print(
            "Create one with: roadmap issue create 'Issue title'", style="dim"
        )
        return None
    console.print(
        f"📋 {len(result.records)} {result.description} "
        f"issue{'s' if len(result.records) != 1 else ''}",
        style="bold cyan",
    )
    if assignee or my_issues:
        _workload(result.records, assignee or "you")
    return _table(result)
