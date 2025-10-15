"""
Modular CLI architecture for the Roadmap tool.

This module provides the main CLI entry point and lazy-loads command groups
to improve performance and maintainability.
"""

import click
from typing import Optional
import os

# Initialize console for rich output
from roadmap.cli.utils import get_console
console = get_console()

# Import core classes for backward compatibility with tests
from roadmap.core import RoadmapCore
from roadmap.sync import SyncManager

# Import functions that tests expect to be available
# These are imported for backward compatibility and should be considered deprecated
def curate_orphaned():
    """Placeholder function for backward compatibility."""
    click.echo("curate_orphaned command not yet implemented in modular CLI")
    return click.Context(main)

# Import utility functions that tests need
import os
try:
    import git
except ImportError:
    git = None

def _get_current_user():
    """Get current user from git config."""
    if git is None:
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'
        
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
    return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'


def _detect_project_context():
    """Detect project context from current directory."""
    import pathlib
    
    current_dir = pathlib.Path.cwd()
    
    # Look for common project indicators
    indicators = [
        '.git',
        'package.json',
        'pyproject.toml',
        'Cargo.toml',
        'pom.xml',
        'build.gradle',
        'composer.json'
    ]
    
    for indicator in indicators:
        if (current_dir / indicator).exists():
            return {
                'type': indicator,
                'path': str(current_dir),
                'name': current_dir.name
            }
    
    return None

@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    
    # Initialize core with default roadmap directory
    ctx.obj["core"] = RoadmapCore()
    
    # If no subcommand was provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


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
    from .milestone import milestone
    from .sync import sync
    from .git_integration import git
    from .analytics import analytics
    from .comment import comment
    from .deprecated import register_deprecated_commands
    
    # Register activity and utility commands
    from .activity import (
        activity, broadcast, handoff, dashboard, notifications, export_data,
        handoff_context, handoff_list, workload_analysis, smart_assign, capacity_forecast
    )
    main.add_command(activity)
    main.add_command(broadcast) 
    main.add_command(handoff)
    main.add_command(dashboard)
    main.add_command(notifications)
    main.add_command(export_data)
    main.add_command(handoff_context)
    main.add_command(handoff_list)
    main.add_command(workload_analysis)
    main.add_command(smart_assign)
    main.add_command(capacity_forecast)
    
    main.add_command(team)
    main.add_command(user)
    main.add_command(data)
    main.add_command(project)
    main.add_command(issue)
    main.add_command(milestone)
    main.add_command(sync)
    main.add_command(git)
    main.add_command(analytics)
    main.add_command(comment)
    
    # Register deprecated commands for backward compatibility
    register_deprecated_commands(main)


# Register all commands when module is imported
register_commands()


if __name__ == "__main__":
    main()