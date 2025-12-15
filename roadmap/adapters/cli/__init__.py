"""
Modular CLI architecture for the Roadmap tool.

This module provides the main CLI entry point and lazy-loads command groups
to improve performance and maintainability.
"""

import os

import click

from roadmap.adapters.cli.exception_handler import handle_cli_exception

# Initialize console for rich output
from roadmap.common.console import get_console
from roadmap.common.errors.exceptions import RoadmapException

# Import core classes for backward compatibility with tests
from roadmap.infrastructure.core import RoadmapCore

# Initialize OpenTelemetry tracing
from roadmap.shared.otel_init import initialize_tracing

console = get_console()

# Flag to track if commands have been registered to avoid duplicate registration
_commands_registered = False


class RoadmapClickGroup(click.Group):
    """Custom Click Group that handles RoadmapException instances."""

    def invoke(self, ctx: click.Context) -> click.Context | None:
        """Invoke the group with centralized exception handling."""
        try:
            # Allow Click to handle help and version flags normally
            result = super().invoke(ctx)
            return result
        except RoadmapException as exc:
            # Handle roadmap exceptions with our formatter
            handle_cli_exception(ctx, exc, show_traceback=False)
        except click.exceptions.Exit:
            # Let Click Exit exceptions propagate (--help, --version)
            raise
        except click.ClickException:
            # Let Click exceptions propagate
            raise
        except click.Abort:
            # Let Click Abort propagate
            raise
        except SystemExit:
            # Let SystemExit propagate (used by Click for --help, --version, etc.)
            raise
        except Exception as exc:
            # Handle unexpected exceptions
            handle_cli_exception(ctx, exc, show_traceback=False)


# Import utility functions that tests need
try:
    import git as gitpython
except ImportError:
    gitpython = None


def _get_current_user():
    """Get current user from git config."""
    if gitpython is None:
        return os.environ.get("USER") or os.environ.get("USERNAME")

    try:
        repo = gitpython.Repo(search_parent_directories=True)  # type: ignore[attr-defined]
        try:
            name = repo.config_reader().get_value("user", "name")
            return name
        except Exception:
            pass
    except Exception:
        pass

    # Fallback to environment variables
    return os.environ.get("USER") or os.environ.get("USERNAME")


@click.group(cls=RoadmapClickGroup)
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Initialize OpenTelemetry tracing
    initialize_tracing()

    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Initialize core with default roadmap directory (skip for init command)
    if ctx.invoked_subcommand != "init":
        try:
            ctx.obj["core"] = RoadmapCore()
        except Exception as exc:
            # Handle exceptions during core initialization
            handle_cli_exception(ctx, exc, show_traceback=False)

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

    # Register today command
    from roadmap.adapters.cli.today import today

    main.add_command(today)

    # Register cleanup command
    from roadmap.infrastructure.maintenance import cleanup

    main.add_command(cleanup)

    # Register command groups with lazy loading
    # Core v1.0 commands only
    from roadmap.adapters.cli.comment import comment
    from roadmap.adapters.cli.data import data
    from roadmap.adapters.cli.git import git as git_cmd
    from roadmap.adapters.cli.issues import issue
    from roadmap.adapters.cli.milestones import milestone

    # progress commands moved to future/ (post-v1.0)
    from roadmap.adapters.cli.projects import project

    main.add_command(data)
    main.add_command(project)
    main.add_command(issue)
    main.add_command(milestone)
    main.add_command(git_cmd)
    main.add_command(comment)
    # recalculate_progress and progress_reports moved to future/

    # ARCHIVED TO future/ (post-1.0 features):
    # - progress.py (progress_reports, recalculate_progress)
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
    main()  # type: ignore[call-arg]
