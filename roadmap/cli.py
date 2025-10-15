"""
Main CLI entry point - now using modular architecture.

This file imports and registers all command groups from the modular CLI structure.
The original monolithic CLI has been split into focused modules for better performance
and maintainability.
"""

import click
from rich.console import Console

from roadmap.core import RoadmapCore

# Initialize console for rich output
console = Console()

# Import all the modular command groups
from roadmap.cli.core import init, status
from roadmap.cli.team import team
from roadmap.cli.user import user
from roadmap.cli.data import data
from roadmap.cli.project import project
from roadmap.cli.issue import issue
from roadmap.cli.git_integration import git
from roadmap.cli.analytics import analytics
from roadmap.cli.deprecated import register_deprecated_commands

@click.group()
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    
    # Initialize core with default roadmap directory
    ctx.obj["core"] = RoadmapCore()

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

# Register deprecated commands for backward compatibility
register_deprecated_commands(main)

if __name__ == "__main__":
    main()
