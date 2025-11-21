"""Issue commands module.

Provides all issue management commands:
- list: List issues with various filters
- create: Create a new issue
- update: Update an existing issue
- done: Mark issue as done
- finish: Finish an issue with time tracking
- start: Start work on an issue
- progress: Update issue progress percentage
- block: Mark an issue as blocked
- unblock: Unblock a blocked issue
- delete: Delete an issue
- deps: Manage issue dependencies
- view: View detailed information about an issue
- archive: Archive an issue to .roadmap/archive/issues/
"""

import click

from roadmap.presentation.cli.issues.archive import archive_issue
from roadmap.presentation.cli.issues.block import block_issue
from roadmap.presentation.cli.issues.create import create_issue
from roadmap.presentation.cli.issues.delete import delete_issue
from roadmap.presentation.cli.issues.deps import deps
from roadmap.presentation.cli.issues.done import done_issue
from roadmap.presentation.cli.issues.finish import finish_issue
from roadmap.presentation.cli.issues.list import list_issues
from roadmap.presentation.cli.issues.progress import update_progress
from roadmap.presentation.cli.issues.restore import restore_issue
from roadmap.presentation.cli.issues.start import start_issue
from roadmap.presentation.cli.issues.unblock import unblock_issue
from roadmap.presentation.cli.issues.update import update_issue
from roadmap.presentation.cli.issues.view import view_issue


@click.group()
def issue():
    """Manage issues."""
    pass


# Register all commands
issue.add_command(list_issues, name="list")
issue.add_command(create_issue, name="create")
issue.add_command(update_issue, name="update")
issue.add_command(done_issue, name="done")
issue.add_command(finish_issue, name="finish")
issue.add_command(start_issue, name="start")
issue.add_command(update_progress, name="progress")
issue.add_command(block_issue, name="block")
issue.add_command(unblock_issue, name="unblock")
issue.add_command(delete_issue, name="delete")
issue.add_command(deps, name="deps")
issue.add_command(view_issue, name="view")
issue.add_command(archive_issue, name="archive")
issue.add_command(restore_issue, name="restore")

__all__ = ["issue"]
