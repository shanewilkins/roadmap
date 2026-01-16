"""Restore project command - move archived projects back to active."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.projects.restore_class import ProjectRestore
from roadmap.common.console import get_console
from roadmap.common.logging import (
    log_command,
    verbose_output,
)


@click.command()
@click.argument("project_name", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived projects",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be restored without actually doing it",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information",
)
@click.pass_context
@verbose_output
@log_command("project_restore", entity_type="project", track_duration=True)
@require_initialized
def restore_project(
    ctx: click.Context,
    project_name: str | None,
    all: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: F841
):
    """Restore an archived project back to active projects.

    This moves a project from .roadmap/archive/projects/ back to
    .roadmap/projects/, making it active again.

    Examples:
        roadmap project restore "Project Name"
        roadmap project restore --all
        roadmap project restore "Project Name" --dry-run
    """
    core = ctx.obj["core"]
    console = get_console()

    restore = ProjectRestore(core, console)

    if not project_name and not all:
        console.print(
            "❌ Error: Specify a project name or use --all",
            style="bold red",
        )
        ctx.exit(1)

    if project_name and all:
        console.print(
            "❌ Error: Cannot specify project name with --all",
            style="bold red",
        )
        ctx.exit(1)

    try:
        restore.execute(
            entity_id=project_name,
            all=all,
            dry_run=dry_run,
            force=force,
        )
    except Exception as e:
        console.print(f"❌ Restore operation failed: {str(e)}", style="bold red")
        ctx.exit(1)
