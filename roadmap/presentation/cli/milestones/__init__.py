"""Milestone commands module.

Provides all milestone management commands:
- create: Create a new milestone
- list: List all milestones
- assign: Assign an issue to a milestone
- delete: Delete a milestone
- close: Close a milestone
- update: Update milestone properties
- recalculate: Recalculate milestone progress
- kanban: Display milestone in kanban board layout
"""

import click

from roadmap.presentation.cli.milestones.assign import assign_milestone
from roadmap.presentation.cli.milestones.close import close_milestone
from roadmap.presentation.cli.milestones.create import create_milestone
from roadmap.presentation.cli.milestones.delete import delete_milestone
from roadmap.presentation.cli.milestones.kanban import milestone_kanban
from roadmap.presentation.cli.milestones.list import list_milestones
from roadmap.presentation.cli.milestones.recalculate import (
    recalculate_milestone_progress,
)
from roadmap.presentation.cli.milestones.update import update_milestone


@click.group()
def milestone():
    """Manage milestones."""
    pass


# Register all commands
milestone.add_command(create_milestone, name="create")
milestone.add_command(list_milestones, name="list")
milestone.add_command(assign_milestone, name="assign")
milestone.add_command(update_milestone, name="update")
milestone.add_command(delete_milestone, name="delete")
milestone.add_command(close_milestone, name="close")
milestone.add_command(recalculate_milestone_progress, name="recalculate")
milestone.add_command(milestone_kanban, name="kanban")

__all__ = ["milestone"]
