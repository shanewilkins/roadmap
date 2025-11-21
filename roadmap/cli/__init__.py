"""
Modular CLI architecture for the Roadmap tool.

This module provides the main CLI entry point and lazy-loads command groups
to improve performance and maintainability.
"""

import os

import click

# Import core classes for backward compatibility with tests
from roadmap.application.core import RoadmapCore

# Initialize console for rich output
from roadmap.shared.console import get_console

console = get_console()

# Flag to track if commands have been registered to avoid duplicate registration
_commands_registered = False


# Import utility functions that tests need
try:
    import git
except ImportError:
    git = None


def _get_current_user():
    """Get current user from git config."""
    if git is None:
        return os.environ.get("USER") or os.environ.get("USERNAME")

    try:
        repo = git.Repo(search_parent_directories=True)
        try:
            name = repo.config_reader().get_value("user", "name")
            return name
        except Exception:
            pass
    except Exception:
        pass

    # Fallback to environment variables
    return os.environ.get("USER") or os.environ.get("USERNAME")


@click.group()
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Initialize core with default roadmap directory (skip for init command)
    if ctx.invoked_subcommand != "init":
        ctx.obj["core"] = RoadmapCore()

    # If no subcommand was provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def register_commands():
    """
    Lazy load and register all command groups.
    This improves startup performance by only importing modules when needed.

    Note: Post-1.0 features have been archived to the 'future/' directory
    and are no longer registered. See future/FUTURE_FEATURES.md for details.
    """
    # Register standalone commands
    from .core import health, init, status

    main.add_command(init)
    main.add_command(status)
    main.add_command(health)

    # Register command groups with lazy loading
    # Core v1.0 commands only
    from roadmap.presentation.cli.comment import comment
    from roadmap.presentation.cli.data import data
    from roadmap.presentation.cli.git import git
    from roadmap.presentation.cli.issues import issue
    from roadmap.presentation.cli.milestones import milestone
    from roadmap.presentation.cli.progress import progress_reports, recalculate_progress
    from roadmap.presentation.cli.projects import project

    main.add_command(data)
    main.add_command(project)
    main.add_command(issue)
    main.add_command(milestone)
    main.add_command(git)
    main.add_command(comment)
    main.add_command(recalculate_progress)
    main.add_command(progress_reports)

    # ARCHIVED TO future/ (post-1.0 features):
    # - activity.py, broadcast, capacity_forecast, dashboard, export_data, handoff, etc.
    # - analytics.py and cli/analytics.py
    # - team.py (team commands) -> future/team_management.py
    # - user.py (user commands) -> future/user_management.py
    # - ci.py (CI commands) -> future/ci_commands.py
    # - release.py -> future/release_management.py
    # - timezone.py -> future/timezone_commands.py
    # - deprecated.py -> future/deprecated_commands.py
    #
    # To restore a feature, move it back from future/ and add it here.


# Register commands at module load time
# This ensures CLI commands are available for tests and direct usage
try:
    register_commands()
except ImportError as e:
    # If there's a circular import, commands will still be registered
    # when main() is invoked through Click's mechanism

    if "partially initialized" not in str(e):
        # Re-raise if it's not a circular import issue
        raise
    else:
        # For circular imports, we'll register commands lazily when needed
        _commands_registered = False


if __name__ == "__main__":
    main()
