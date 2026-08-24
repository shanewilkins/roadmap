"""Restore projects through lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command, verbose_output
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning


@click.command("restore")
@click.argument("project_name", required=False)
@click.option("--all", "restore_all", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@verbose_output
@log_command("project_restore", entity_type="project", track_duration=True)
@require_initialized
def restore_project(
    ctx,
    project_name: str | None,
    restore_all: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
) -> None:  # noqa: ARG001
    """Restore projects without moving canonical files."""
    if (project_name is None) == (not restore_all):
        raise click.UsageError("Specify exactly one of PROJECT_NAME or --all")
    if not dry_run and not force:
        click.confirm("Restore the selected project(s)?", abort=True)
    result = invoke(
        lambda: ctx.obj["core"].planning.restore_project(
            project_name, restore_all=restore_all, dry_run=dry_run
        )
    )
    verb = "Would restore" if dry_run else "Restored"
    for item in result.aggregates:
        click.echo(f"{verb} project {item.id}: {item.name}")
    if not result.aggregates:
        click.echo("No matching projects.")
    projection_warning(result)
