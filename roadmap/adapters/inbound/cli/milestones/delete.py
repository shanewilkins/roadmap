"""Permanently delete archived milestones."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import (
    invoke,
    resolve_milestone_id,
)


@click.command("delete")
@click.argument("milestone_id")
@click.option("--yes", "-y", is_flag=True)
@click.pass_context
@require_initialized
def delete_milestone(ctx, milestone_id: str, yes: bool) -> None:
    """Purge an archived, unreferenced milestone."""
    core = ctx.obj["core"]
    identity = resolve_milestone_id(core, milestone_id)
    milestone = invoke(
        lambda: core.planning.milestone(str(identity), include_archived=True)
    ).milestone
    if not yes:
        click.confirm(
            f"Permanently delete milestone {identity} ({milestone.name})?", abort=True
        )
    invoke(lambda: core.planning.purge_milestone(identity))
    click.echo(f"Deleted milestone {identity}: {milestone.name}")
