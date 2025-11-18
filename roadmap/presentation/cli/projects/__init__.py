"""Project commands module.

Provides all project management commands:
- create: Create a new project
- list: List all projects with optional filtering
- delete: Delete a project
"""

import click

from roadmap.presentation.cli.projects.create import create_project
from roadmap.presentation.cli.projects.delete import delete_project
from roadmap.presentation.cli.projects.list import list_projects


@click.group()
def project():
    """Manage projects (top-level planning documents)."""
    pass


# Register all commands
project.add_command(create_project, name="create")
project.add_command(list_projects, name="list")
project.add_command(delete_project, name="delete")

__all__ = ["project"]
