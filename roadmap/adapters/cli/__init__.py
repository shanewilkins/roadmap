"""Modular CLI architecture for the Roadmap tool.

This module provides the main CLI entry point and implements plugin-style
lazy-loading of command groups to improve performance and maintainability.

## Architecture

Commands are registered via a plugin registry that specifies:
- Command name/group name
- Module path where the command is defined
- Variable name of the command in that module

This allows commands to be imported only when actually invoked, reducing
startup time and improving modularity.
"""

import importlib
from typing import Any

import click

from roadmap import __version__
from roadmap.adapters.cli.exception_handler import handle_cli_exception

# Initialize console for rich output
from roadmap.common.console import get_console
from roadmap.common.errors.exceptions import RoadmapException

# Initialize OpenTelemetry tracing
from roadmap.common.observability.otel_init import initialize_tracing

# Import core classes for backward compatibility with tests
from roadmap.infrastructure.coordination.core import RoadmapCore

console = get_console()

# Plugin registry: maps command names to their import locations
# Format: "command_name": ("module_path", "variable_name")
# This allows lazy loading of commands - they're only imported when invoked
_COMMAND_REGISTRY: dict[str, tuple[str, str]] = {
    # Core v1.0 standalone commands
    "init": ("roadmap.adapters.cli.core", "init"),
    "status": ("roadmap.adapters.cli.core", "status"),
    "health": ("roadmap.adapters.cli.core", "health"),
    "today": ("roadmap.adapters.cli.today", "today"),
    "cleanup": ("roadmap.infrastructure.maintenance", "cleanup"),
    # Command groups
    "analysis": ("roadmap.adapters.cli.analysis", "analysis"),
    "comment": ("roadmap.adapters.cli.comment", "comment"),
    "config": ("roadmap.adapters.cli.config", "config"),
    "data": ("roadmap.adapters.cli.data", "data"),
    "git": ("roadmap.adapters.cli.git", "git"),
    "issue": ("roadmap.adapters.cli.issues", "issue"),
    "milestone": ("roadmap.adapters.cli.milestones", "milestone"),
    "project": ("roadmap.adapters.cli.projects", "project"),
    "sync": ("roadmap.adapters.cli.sync", "sync"),
    "validate-links": ("roadmap.adapters.cli.sync_validation", "validate_links"),
}

# Cache for loaded commands to avoid re-importing
_command_cache: dict[str, Any] = {}


def _load_command(command_name: str) -> Any:
    """Lazily load a command from the registry.

    Args:
        command_name: Name of command to load

    Returns:
        The Click command/group object

    Raises:
        ValueError: If command not found in registry
    """
    if command_name in _command_cache:
        return _command_cache[command_name]

    if command_name not in _COMMAND_REGISTRY:
        raise ValueError(f"Unknown command: {command_name}")

    module_path, var_name = _COMMAND_REGISTRY[command_name]
    module = importlib.import_module(module_path)
    command = getattr(module, var_name)

    _command_cache[command_name] = command
    return command


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
        import os

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
    import os

    return os.environ.get("USER") or os.environ.get("USERNAME")


def _detect_project_context():
    """Detect project context from current directory."""
    import pathlib

    context = {
        "project_name": pathlib.Path.cwd().name,
        "has_git": False,
    }

    # Check if we're in a git repository
    if gitpython is not None:
        try:
            gitpython.Repo(search_parent_directories=True)  # type: ignore[attr-defined]
            context["has_git"] = True
        except Exception:
            pass

    return context


@click.group(cls=RoadmapClickGroup)
@click.version_option(version=__version__)
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
    """Register all commands from the plugin registry.

    Commands are loaded lazily from the registry, which maps command names
    to their module paths. This approach:
    - Reduces startup time by deferring imports
    - Makes it easy to add/remove commands
    - Provides a single source of truth for command list
    """
    for command_name, _ in _COMMAND_REGISTRY.items():
        try:
            command = _load_command(command_name)
            main.add_command(command, name=command_name)
        except Exception as e:
            console.print(
                f"⚠️  Failed to register command '{command_name}': {e}", style="yellow"
            )


# Register commands at module load time
# This ensures CLI commands are available for tests and direct usage
try:
    register_commands()
    _commands_registered = True
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
