"""Update an issue through the target Application boundary."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.adapters.inbound.cli.planning_resolution import (
    date_value,
    resolve_milestone_id,
)
from roadmap.application.contracts import IssueUpdateCommand
from roadmap.domain.types import Priority, Title


@click.command("update")
@click.argument("issue_id")
@click.option("--title", help="Update issue title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
)
@click.option("--assignee", "-a", help="Update assignee")
@click.option("--milestone", "-m", help="Update milestone")
@click.option("--description", "-d", help="Update description")
@click.option("--estimate", "-e", type=float, help="Update estimated hours")
@click.option("--reason", "-r", help="Reason for the update")
@click.option("--clear-assignee", is_flag=True)
@click.option("--clear-milestone", is_flag=True)
@click.option("--clear-estimate", is_flag=True)
@click.option("--due-date")
@click.option("--clear-due-date", is_flag=True)
@click.option("--add-label", "add_labels", multiple=True)
@click.option("--remove-label", "remove_labels", multiple=True)
@click.pass_context
@require_initialized
def update_issue(
    ctx: click.Context,
    issue_id: str,
    title: str | None,
    priority: str | None,
    status: str | None,
    assignee: str | None,
    milestone: str | None,
    description: str | None,
    estimate: float | None,
    reason: str | None,
    clear_assignee: bool,
    clear_milestone: bool,
    clear_estimate: bool,
    due_date: str | None,
    clear_due_date: bool,
    add_labels: tuple[str, ...],
    remove_labels: tuple[str, ...],
) -> None:
    """Update an existing canonical issue."""
    supplied = (
        title,
        priority,
        status,
        assignee,
        milestone,
        description,
        estimate,
        due_date,
    )
    flags = (
        clear_assignee,
        clear_milestone,
        clear_estimate,
        clear_due_date,
        add_labels,
        remove_labels,
    )
    if not any(flags) and not any(value is not None for value in supplied):
        raise click.UsageError("Specify at least one field to update")
    core = ctx.obj["core"]
    command = invoke(
        lambda: IssueUpdateCommand(
            issue_id=resolve_issue_id(core, issue_id),
            title=Title(title) if title is not None else None,
            priority=Priority(priority) if priority is not None else None,
            status=status,
            assignee=assignee,
            milestone_id=resolve_milestone_id(core, milestone) if milestone else None,
            content=description,
            estimated_hours=estimate,
            reason=reason,
            clear_assignee=clear_assignee,
            clear_milestone=clear_milestone,
            clear_estimate=clear_estimate,
            due_at=date_value(due_date),
            clear_due_date=clear_due_date,
            add_labels=add_labels,
            remove_labels=remove_labels,
        )
    )
    result = invoke(lambda: core.issue_mutations.update(command))
    click.echo(f"Updated issue {result.issue.id}: {result.issue.title}")
    projection_warning(result)
