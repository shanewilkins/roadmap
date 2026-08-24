"""Close canonical milestones."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import (
    invoke,
    projection_warning,
    resolve_milestone_id,
)
from roadmap.common.logging import log_command


@click.command("close")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip open-issue guard")
@click.pass_context
@require_initialized
@log_command("milestone_close", entity_type="milestone", track_duration=True)
def close_milestone(ctx, milestone_name: str, force: bool) -> None:
    """Close a milestone without changing linked issues."""
    core = ctx.obj["core"]
    identity = resolve_milestone_id(core, milestone_name)
    result = invoke(lambda: core.planning.close_milestone(identity, force=force))
    milestone = result.aggregate
    click.echo(f"Closed milestone: [{milestone.id}] {milestone.name}")
    projection_warning(result)
