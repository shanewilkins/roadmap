"""Update issue progress through the target Application boundary."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)


@click.command("progress")
@click.argument("issue_id")
@click.argument("percentage", type=click.FloatRange(0, 100))
@click.pass_context
@log_command("issue_progress", entity_type="issue", track_duration=True)
@require_initialized
def update_progress(ctx: click.Context, issue_id: str, percentage: float) -> None:
    """Set an issue's progress percentage from 0 through 100."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    result = invoke(lambda: core.issue_mutations.progress(identity, percentage))
    click.echo(f"Updated issue {identity} progress to {percentage:g}%")
    projection_warning(result)
