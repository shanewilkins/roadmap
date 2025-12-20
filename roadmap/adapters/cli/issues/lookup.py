"""Lookup issue by GitHub ID command - find internal issue by GitHub issue number."""

import sys

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
)
from roadmap.shared.formatters.text.operations import (
    format_operation_failure,
)

console = get_console()


@click.command("lookup-github")
@click.argument("github_id", type=int)
@click.pass_context
@log_command("issue_lookup_github", entity_type="issue", track_duration=True)
@require_initialized
def lookup_github_issue(ctx: click.Context, github_id: int) -> None:
    """Look up an internal issue by its GitHub issue number.

    Searches for an internal issue linked to the provided GitHub issue number
    and displays its details.

    Example:
        roadmap issue lookup-github 456
    """
    core = ctx.obj["core"]

    # Validate GitHub ID is positive
    if github_id <= 0:
        format_operation_failure(
            console,
            f"Invalid GitHub issue number: {github_id}",
            "GitHub issue numbers must be positive integers",
        )
        sys.exit(1)

    # Get all issues and search for one with matching github_issue
    all_issues = core.issues.get_all()
    matching_issue = None

    for issue in all_issues:
        if issue.github_issue == github_id:
            matching_issue = issue
            break

    if not matching_issue:
        format_operation_failure(
            console,
            f"No issue found linked to GitHub issue #{github_id}",
            f"Use 'roadmap issue link <id> --github-id {github_id}' to link an issue",
        )
        sys.exit(1)

    # Display issue details
    console.print(
        f"✅ Found issue linked to GitHub issue #{github_id}", style="bold green"
    )
    console.print()
    console.print(f"  ID: {matching_issue.id}", style="cyan")
    console.print(f"  Title: {matching_issue.title}", style="bold")
    console.print(f"  Status: {matching_issue.status.value}", style="cyan")
    console.print(f"  Priority: {matching_issue.priority.value}", style="cyan")

    if matching_issue.assignee:
        console.print(f"  Assigned to: {matching_issue.assignee}", style="cyan")

    if matching_issue.milestone:
        console.print(f"  Milestone: {matching_issue.milestone}", style="cyan")

    if matching_issue.labels:
        console.print(f"  Labels: {', '.join(matching_issue.labels)}", style="cyan")

    if matching_issue.estimated_hours:
        console.print(
            f"  Estimated: {matching_issue.estimated_time_display}", style="cyan"
        )

    if matching_issue.content:
        console.print()
        console.print("Description:", style="bold cyan")
        console.print(matching_issue.content, style="dim")

    console.print()
    console.print(
        f"  Use 'roadmap issue view {matching_issue.id}' for full details",
        style="dim",
    )
