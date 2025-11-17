"""
Main CLI entry point - now using modular architecture.

This file imports and registers all command groups from the modular CLI structure.
The original monolithic CLI has been split into focused modules for better performance
and maintainability.
"""

import click
from rich.console import Console

# Import all the modular command groups
from roadmap.cli.analytics import analytics
from roadmap.cli.ci import ci
from roadmap.cli.core import init, status
from roadmap.cli.data import data
from roadmap.cli.deprecated import register_deprecated_commands
from roadmap.cli.git_integration import git
from roadmap.cli.issue import issue
from roadmap.cli.progress import progress_reports, recalculate_progress
from roadmap.cli.project import project
from roadmap.cli.team import team
from roadmap.cli.user import user
from roadmap.core import RoadmapCore

# Initialize console for rich output
console = Console()


def _auto_sync_callback(
    ctx: click.Context, param: click.Parameter, value: bool
) -> bool:
    """Callback to handle auto-sync when any command is run."""
    return value


@click.group(invoke_without_command=True)
@click.option(
    "--force-rebuild",
    is_flag=True,
    help="Force rebuild of database from .roadmap/ files",
    callback=_auto_sync_callback,
    expose_value=True,
)
@click.option(
    "--no-sync",
    is_flag=True,
    help="Skip automatic database sync on startup",
    callback=_auto_sync_callback,
    expose_value=True,
)
@click.version_option()
@click.pass_context
def main(ctx: click.Context, force_rebuild: bool, no_sync: bool):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Initialize core with default roadmap directory
    ctx.obj["core"] = RoadmapCore()

    # Store flags in context for subcommands
    ctx.obj["force_rebuild"] = force_rebuild
    ctx.obj["no_sync"] = no_sync

    # Auto-sync database unless explicitly disabled - only if we have a subcommand
    if ctx.invoked_subcommand is not None and not no_sync:
        try:
            console.print("[dim]🔄 Checking database sync...[/dim]")
            ctx.obj["core"].ensure_database_synced(
                force_rebuild=force_rebuild, show_progress=True
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Database sync failed: {e}[/yellow]")
            console.print("[dim]You can use --no-sync to skip automatic sync[/dim]")

    # If no subcommand was provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register standalone commands
main.add_command(init)
main.add_command(status)

# Register command groups
main.add_command(team)
main.add_command(user)
main.add_command(data)
main.add_command(project)
main.add_command(issue)
main.add_command(git)
main.add_command(analytics)
main.add_command(recalculate_progress)
main.add_command(progress_reports)
main.add_command(ci)

# Register deprecated commands for backward compatibility
register_deprecated_commands(main)

if __name__ == "__main__":
    main()
