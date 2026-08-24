"""Render a milestone board from canonical issues."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import invoke
from roadmap.domain.types import IssueStatus


@click.command("kanban")
@click.argument("milestone_name")
@click.option("--compact", is_flag=True)
@click.option("--no-color", is_flag=True)
@click.pass_context
@require_initialized
def milestone_kanban(ctx, milestone_name: str, compact: bool, no_color: bool) -> None:  # noqa: ARG001
    """Display canonical milestone issues grouped by workflow state."""
    planning = ctx.obj["core"].planning
    summary = invoke(lambda: planning.milestone(milestone_name))
    issues = [
        item
        for item in planning.snapshot().issues
        if item.relations.milestone_id == summary.milestone.id
    ]
    click.echo(f"Kanban Board: {summary.milestone.name}")
    click.echo(
        f"Progress: {summary.closed_count}/{summary.issue_count} issues completed"
    )
    if not issues:
        click.echo(f"No issues found for milestone '{summary.milestone.name}'")
        return
    for status in IssueStatus:
        grouped = [item for item in issues if item.status is status]
        click.echo(f"\n{status.value} ({len(grouped)})")
        for issue in grouped:
            click.echo(f"  [{str(issue.id)[:8]}] {issue.title}")
