"""Restore projects through lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import (
    echo_batch_result,
    require_initialized,
    verbose_message,
)
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning


@click.command("restore")
@click.argument("project_name", required=False)
@click.option("--all", "restore_all", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation without bypassing lifecycle guards",
)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
def restore_project(
    ctx,
    project_name: str | None,
    restore_all: bool,
    dry_run: bool,
    force: bool,
    yes: bool,
    verbose: bool,
) -> None:  # noqa: ARG001
    """Restore projects without moving canonical files."""
    if (project_name is None) == (not restore_all):
        raise click.UsageError("Specify exactly one of PROJECT_NAME or --all")
    if not dry_run and not (yes or force):
        click.confirm("Restore the selected project(s)?", abort=True)
    result = invoke(
        lambda: ctx.obj["core"].planning.restore_project(
            project_name, restore_all=restore_all, dry_run=dry_run
        )
    )
    echo_batch_result("project", result.aggregates, dry_run, action="restore")
    verbose_message(
        verbose,
        f"Validated {len(result.aggregates)} project(s); {'preview only, no writes' if dry_run else 'canonical restore committed'}.",
    )
    projection_warning(result)
