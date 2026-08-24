"""Report canonical derived milestone progress."""

import click

from roadmap.adapters.inbound.cli.planning_resolution import invoke


@click.command("recalculate")
@click.argument("milestone_name", required=False)
@click.option(
    "--method",
    type=click.Choice(["effort_weighted", "count_based"]),
    default="effort_weighted",
)
@click.pass_context
def recalculate_milestone_progress(
    ctx, milestone_name: str | None, method: str
) -> None:
    """Recalculate on read; derived progress is never persisted as authority."""
    planning = ctx.obj["core"].planning
    summaries = (
        (invoke(lambda: planning.milestone(milestone_name)),)
        if milestone_name
        else planning.snapshot().milestones
    )
    click.echo(f"Recalculation complete ({method}):")
    for item in summaries:
        progress = (
            item.closed_count / item.issue_count * 100.0
            if method == "count_based" and item.issue_count
            else item.progress
        )
        click.echo(f"  {item.milestone.name}: {progress:.1f}%")
