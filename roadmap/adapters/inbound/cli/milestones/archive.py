"""Archive milestones through lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning
from roadmap.domain.types import RetentionState


def _list_archived_milestones(core) -> None:
    values = [
        item
        for item in core.planning.all_milestones()
        if item.retention is RetentionState.ARCHIVED
    ]
    if not values:
        click.echo("No archived milestones.")
    for item in values:
        click.echo(f"{item.id}  {item.name}")


def _report_archive_result(result, dry_run: bool) -> None:
    verb = "Would archive" if dry_run else "Archived"
    for item in result.aggregates:
        click.echo(f"{verb} milestone {item.id}: {item.name}")
    if not result.aggregates:
        click.echo("No matching milestones.")
    projection_warning(result)


@click.command("archive")
@click.argument("milestone_name", required=False)
@click.option("--all-closed", is_flag=True)
@click.option("--list", "list_archived", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
def archive_milestone(
    ctx,
    milestone_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
) -> None:  # noqa: ARG001
    """Archive milestones in place without cascading to issues."""
    core = ctx.obj["core"]
    if list_archived:
        _list_archived_milestones(core)
        return
    if (milestone_name is None) == (not all_closed):
        raise click.UsageError("Specify exactly one of MILESTONE_NAME or --all-closed")
    if not dry_run and not force:
        click.confirm("Archive the selected milestone(s)?", abort=True)
    result = invoke(
        lambda: core.planning.archive_milestone(
            milestone_name, all_closed=all_closed, dry_run=dry_run, force=force
        )
    )
    _report_archive_result(result, dry_run)
