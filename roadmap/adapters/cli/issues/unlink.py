"""Unlink GitHub issue command."""

import sys

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.infrastructure.logging import log_command


@click.command("unlink-github")
@click.argument("issue_id")
@click.pass_context
@log_command
@require_initialized
def unlink_github_issue(ctx: click.Context, issue_id: str) -> None:
    """Remove GitHub link from a local issue.

    Args:
        issue_id: ID of the local issue to unlink
    """
    core = ctx.obj["core"]

    # Get the issue
    try:
        issue = core.issues.get_by_id(issue_id)
    except ValueError:
        click.secho(f"❌ Issue not found: {issue_id}", fg="red")
        sys.exit(1)

    # Check if issue is linked
    if issue.github_issue is None:
        click.secho(
            f"⚠️  Issue '{issue_id}' is not linked to GitHub",
            fg="yellow",
        )
        sys.exit(1)

    # Store the GitHub ID for display
    github_id = issue.github_issue

    # Remove the link
    try:
        core.issues.update(issue_id, github_issue=None)
        click.secho(
            f"✅ Unlinked issue '{issue_id}' from GitHub issue #{github_id}",
            fg="green",
        )
    except Exception as e:
        click.secho(f"❌ Failed to unlink issue: {str(e)}", fg="red")
        sys.exit(1)
