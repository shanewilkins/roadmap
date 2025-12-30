"""Project commands module.

Provides all project management commands:
- create: Create a new project
- list: List all projects with optional filtering
- delete: Delete a project
- view: View detailed information about a project
- update: Update project properties
- close: Close a completed project
- archive: Archive a completed project
- restore: Restore an archived project
"""

import click

from roadmap.adapters.cli.projects.archive import archive_project
from roadmap.adapters.cli.projects.close import close_project
from roadmap.adapters.cli.projects.create import create_project
from roadmap.adapters.cli.projects.delete import delete_project
from roadmap.adapters.cli.projects.list import list_projects
from roadmap.adapters.cli.projects.restore import restore_project
from roadmap.adapters.cli.projects.update import update_project
from roadmap.adapters.cli.projects.view import view_project


@click.group()
def project():
    """Manage projects (top-level planning documents)."""
    pass


# Register all commands
project.add_command(create_project, name="create")
project.add_command(list_projects, name="list")
project.add_command(update_project, name="update")
project.add_command(delete_project, name="delete")
project.add_command(view_project, name="view")
project.add_command(close_project, name="close")
project.add_command(archive_project, name="archive")
project.add_command(restore_project, name="restore")

__all__ = ["project"]
