"""View canonical milestone details and issues."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import invoke


@click.command("view")
@click.argument("milestone_name")
@click.option(
    "--status",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
    multiple=True,
)
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"]),
    multiple=True,
)
@click.option("--only-open", is_flag=True)
@click.pass_context
@require_initialized
def view_milestone(
    ctx,
    milestone_name: str,
    status: tuple[str, ...],
    priority: tuple[str, ...],
    only_open: bool,
) -> None:
    """Display a milestone with filtered canonical issues."""
    planning = ctx.obj["core"].planning
    summary = invoke(lambda: planning.milestone(milestone_name))
    milestone = summary.milestone
    issues = [
        item
        for item in planning.snapshot().issues
        if item.relations.milestone_id == milestone.id
        and (not status or item.status.value in status)
        and (not priority or item.priority.value in priority)
        and (not only_open or item.status.value != "closed")
    ]
    click.echo(f"Milestone: {milestone.name}")
    click.echo(f"ID: {milestone.id}")
    click.echo(f"Status: {milestone.status.value}")
    click.echo(
        f"Due: {milestone.due_at.value.date().isoformat() if milestone.due_at else 'None'}"
    )
    click.echo(f"Progress: {summary.progress:.1f}%")
    click.echo(f"Issues: {summary.closed_count}/{summary.issue_count} closed")
    click.echo(
        f"Estimate: {summary.estimated_hours:.1f}h ({summary.remaining_hours:.1f}h remaining)"
    )
    if milestone.content:
        click.echo("\n" + milestone.content)
    if issues:
        click.echo("\nIssues:")
        for issue in issues:
            click.echo(
                f"- [{issue.id}] {issue.title} ({issue.status.value}, {issue.priority.value})"
            )
