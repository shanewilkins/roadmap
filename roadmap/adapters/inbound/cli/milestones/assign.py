"""Assign canonical issues to milestones."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command
from roadmap.adapters.inbound.cli.issues.resolution import resolve_issue_id
from roadmap.adapters.inbound.cli.planning_resolution import (
    invoke,
    projection_warning,
    resolve_milestone_id,
)


@click.command("assign")
@click.argument("issue_id")
@click.argument("milestone_name")
@click.pass_context
@require_initialized
@log_command("milestone_assign", entity_type="milestone", track_duration=True)
def assign_milestone(ctx, issue_id: str, milestone_name: str) -> None:
    """Assign an issue and refresh derived planning progress."""
    core = ctx.obj["core"]
    result = invoke(
        lambda: core.planning.assign_issue(
            resolve_issue_id(core, issue_id),
            resolve_milestone_id(core, milestone_name),
        )
    )
    click.echo(f"Assigned issue {result.aggregate.id} to milestone {milestone_name}")
    projection_warning(result)
