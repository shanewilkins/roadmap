"""Update an issue through the target Application boundary."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.resolution import (
    entity_id,
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.application.contracts import IssueUpdateCommand
from roadmap.common.logging import log_command
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
@click.pass_context
@log_command("issue_update", entity_type="issue", track_duration=True)
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
) -> None:
    """Update an existing canonical issue."""
    if not any(
        value is not None
        for value in (
            title,
            priority,
            status,
            assignee,
            milestone,
            description,
            estimate,
        )
    ):
        raise click.UsageError("Specify at least one field to update")
    core = ctx.obj["core"]
    command = invoke(
        lambda: IssueUpdateCommand(
            issue_id=resolve_issue_id(core, issue_id),
            title=Title(title) if title is not None else None,
            priority=Priority(priority) if priority is not None else None,
            status=status,
            assignee=assignee,
            milestone_id=entity_id(milestone),
            content=description,
            estimated_hours=estimate,
            reason=reason,
        )
    )
    result = invoke(lambda: core.issue_mutations.update(command))
    click.echo(f"Updated issue {result.issue.id}: {result.issue.title}")
    projection_warning(result)
