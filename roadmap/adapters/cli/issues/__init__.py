"""Issue commands module.

Provides all issue management commands:
- list: List issues with various filters
- create: Create a new issue
- update: Update an existing issue
- close: Close an issue (Git-aligned terminology)
- start: Start work on an issue
- progress: Update issue progress percentage
- block: Mark an issue as blocked
- unblock: Unblock a blocked issue
- delete: Delete an issue
- deps: Manage issue dependencies
- view: View detailed information about an issue
- archive: Archive an issue to .roadmap/archive/issues/
- comment: Manage comments and discussions on issues
- link: Link internal issue to GitHub issue
- lookup-github: Look up internal issue by GitHub issue number
- sync-status: View sync history and statistics for GitHub-linked issues
"""

import click

from roadmap.adapters.cli.issues.archive import archive_issue
from roadmap.adapters.cli.issues.block import block_issue
from roadmap.adapters.cli.issues.close import close_issue
from roadmap.adapters.cli.issues.comment import comment_group
from roadmap.adapters.cli.issues.create import create_issue
from roadmap.adapters.cli.issues.delete import delete_issue
from roadmap.adapters.cli.issues.deps import deps
from roadmap.adapters.cli.issues.link import link_github_issue
from roadmap.adapters.cli.issues.list import list_issues
from roadmap.adapters.cli.issues.lookup import lookup_github_issue
from roadmap.adapters.cli.issues.progress import update_progress
from roadmap.adapters.cli.issues.restore import restore_issue
from roadmap.adapters.cli.issues.start import start_issue
from roadmap.adapters.cli.issues.sync_status import sync_status
from roadmap.adapters.cli.issues.unblock import unblock_issue
from roadmap.adapters.cli.issues.unlink import unlink_github_issue
from roadmap.adapters.cli.issues.update import update_issue
from roadmap.adapters.cli.issues.view import view_issue


@click.group()
def issue():
    """Manage issues."""
    pass


# Register all commands
issue.add_command(list_issues, name="list")
issue.add_command(create_issue, name="create")
issue.add_command(update_issue, name="update")
issue.add_command(close_issue, name="close")
issue.add_command(start_issue, name="start")
issue.add_command(update_progress, name="progress")
issue.add_command(block_issue, name="block")
issue.add_command(unblock_issue, name="unblock")
issue.add_command(delete_issue, name="delete")
issue.add_command(deps, name="deps")
issue.add_command(view_issue, name="view")
issue.add_command(archive_issue, name="archive")
issue.add_command(restore_issue, name="restore")
issue.add_command(comment_group, name="comment")
issue.add_command(link_github_issue, name="link-github")
issue.add_command(unlink_github_issue, name="unlink-github")
issue.add_command(lookup_github_issue, name="lookup-github")
issue.add_command(sync_status, name="sync-status")

__all__ = ["issue"]
