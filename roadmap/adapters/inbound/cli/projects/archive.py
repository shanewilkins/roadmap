"""Archive projects through lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command, verbose_output
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning
from roadmap.domain.types import RetentionState


@click.command("archive")
@click.argument("project_name", required=False)
@click.option("--all-closed", is_flag=True)
@click.option("--list", "list_archived", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@verbose_output
@log_command("project_archive", entity_type="project", track_duration=True)
@require_initialized
def archive_project(
    ctx,
    project_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
) -> None:  # noqa: ARG001
    """Archive projects in place without cascading to milestones or issues."""
    core = ctx.obj["core"]
    if list_archived:
        values = [
            item
            for item in core.planning.all_projects()
            if item.retention is RetentionState.ARCHIVED
        ]
        if not values:
            click.echo("No archived projects.")
        for item in values:
            click.echo(f"{item.id}  {item.name}")
        return
    if (project_name is None) == (not all_closed):
        raise click.UsageError("Specify exactly one of PROJECT_NAME or --all-closed")
    if not dry_run and not force:
        click.confirm("Archive the selected project(s)?", abort=True)
    result = invoke(
        lambda: core.planning.archive_project(
            project_name, all_closed=all_closed, dry_run=dry_run, force=force
        )
    )
    verb = "Would archive" if dry_run else "Archived"
    for item in result.aggregates:
        click.echo(f"{verb} project {item.id}: {item.name}")
    if not result.aggregates:
        click.echo("No matching projects.")
    projection_warning(result)
