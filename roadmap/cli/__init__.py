"""
Modular CLI architecture for the Roadmap tool.

This module provides the main CLI entry point and lazy-loads command groups
to improve performance and maintainability.
"""

import click
from rich.console import Console
from typing import Optional

# Initialize console for rich output
console = Console()

@click.group()
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)


def register_commands():
    """
    Lazy load and register all command groups.
    This improves startup performance by only importing modules when needed.
    """
    # Register standalone commands
    from .core import init, status
    main.add_command(init)
    main.add_command(status)
    
    # Register command groups with lazy loading
    from .team import team
    from .user import user
    from .data import data
    from .project import project
    from .issue import issue
    from .git_integration import git
    from .analytics import analytics
    from .deprecated import register_deprecated_commands
    
    main.add_command(team)
    main.add_command(user)
    main.add_command(data)
    main.add_command(project)
    main.add_command(issue)
    main.add_command(git)
    main.add_command(analytics)
    
    # Register deprecated commands for backward compatibility
    register_deprecated_commands(main)


# Register all commands when module is imported
register_commands()


if __name__ == "__main__":
    main()