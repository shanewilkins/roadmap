"""Sync GitHub issue command - fetch and sync updates from GitHub."""

import sys
from pathlib import Path

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.core.services.github_integration_service import GitHubIntegrationService
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.infrastructure.logging import log_command
from roadmap.shared.formatters.text.operations import (
    format_operation_failure,
)

console = get_console()


@click.command("sync-github")
@click.argument("issue_id")
@click.option(
    "--owner",
    type=str,
    help="GitHub repository owner (required if not in config)",
)
@click.option(
    "--repo",
    type=str,
    help="GitHub repository name (required if not in config)",
)
@click.option(
    "--auto-confirm",
    is_flag=True,
    help="Automatically confirm sync without prompting",
)
@click.pass_context
@log_command("issue_sync_github", entity_type="issue", track_duration=True)
@require_initialized
def sync_github_issue(
    ctx: click.Context,
    issue_id: str,
    owner: str | None,
    repo: str | None,
    auto_confirm: bool,
) -> None:
    """Sync an issue with its linked GitHub issue.

    Fetches the latest information from the GitHub issue and displays
    a diff of any changes. You can review the changes before confirming
    the sync operation.

    Only syncs if the issue has been linked to a GitHub issue via
    the 'link' command.

    Example:
        roadmap issue sync-github abc123
        roadmap issue sync-github abc123 --auto-confirm
    """
    core = ctx.obj["core"]

    # Get the issue
    try:
        issue = core.issues.get_by_id(issue_id)
        if not issue:
            format_operation_failure(
                console,
                f"Issue {issue_id} not found",
                "Cannot sync non-existent issue",
            )
            sys.exit(1)
    except Exception as e:
        format_operation_failure(
            console,
            f"Failed to retrieve issue {issue_id}",
            f"Error: {str(e)}",
        )
        sys.exit(1)

    # Check if issue is linked to GitHub
    if not issue.github_issue:
        format_operation_failure(
            console,
            f"Issue {issue_id} is not linked to a GitHub issue",
            f"Use 'roadmap issue link {issue_id} --github-id <number>' to link it first",
        )
        sys.exit(1)

    # Get owner/repo from config or command-line
    config_owner = owner
    config_repo = repo

    if not config_owner or not config_repo:
        try:
            config_path = Path(core.root_path) / "config.yaml"
            gh_service = GitHubIntegrationService(Path(core.root_path), config_path)
            token, config_owner, config_repo = gh_service.get_github_config()

            if not config_owner or not config_repo:
                format_operation_failure(
                    console,
                    "GitHub repository not configured",
                    "Provide --owner and --repo options, or configure GitHub in config.yaml",
                )
                sys.exit(1)
        except Exception as e:
            format_operation_failure(
                console,
                "Could not get GitHub configuration",
                f"Error: {str(e)}",
            )
            sys.exit(1)

    # Fetch GitHub issue details
    try:
        gh_client = GitHubIssueClient()
        github_issue_data = gh_client.fetch_issue(
            config_owner, config_repo, issue.github_issue
        )
        if not github_issue_data:
            format_operation_failure(
                console,
                f"GitHub issue #{issue.github_issue} not found",
                f"Repository: {config_owner}/{config_repo}",
            )
            sys.exit(1)
    except Exception as e:
        format_operation_failure(
            console,
            f"Failed to fetch GitHub issue #{issue.github_issue}",
            f"Error: {str(e)}",
        )
        sys.exit(1)

    # Get diff of changes
    try:
        diff = gh_client.get_issue_diff(
            config_owner, config_repo, issue.github_issue, issue.model_dump()
        )
    except Exception as e:
        format_operation_failure(
            console,
            "Failed to compute diff",
            f"Error: {str(e)}",
        )
        sys.exit(1)

    # Display the diff
    console.print(
        f"📊 Changes from GitHub issue #{issue.github_issue}:", style="bold cyan"
    )
    console.print()

    if not diff:
        console.print("✨ No changes found - issue is already in sync", style="green")
        return

    # Show all diffs
    for field, (local_value, github_value) in diff.items():
        console.print(f"  • {field}:", style="yellow")
        console.print(f"    Local:  {local_value}", style="dim red")
        console.print(f"    GitHub: {github_value}", style="dim green")
        console.print()

    # Prompt for confirmation unless auto-confirm is set
    if not auto_confirm:
        console.print("Apply these changes?", style="bold cyan")
        if not click.confirm("Confirm sync"):
            console.print("❌ Sync cancelled", style="red")
            return

    # Apply the changes
    try:
        # Update the issue with GitHub data
        updates = {
            "title": github_issue_data.get("title", issue.title),
            "content": github_issue_data.get("body", issue.content),
        }

        # Handle optional fields
        if "state" in github_issue_data:
            state = github_issue_data["state"]
            if state == "closed":
                # GitHub uses 'closed', we use 'done'
                updates["status"] = "done"

        if "assignees" in github_issue_data and github_issue_data["assignees"]:
            # Get first assignee's login
            assignees = github_issue_data["assignees"]
            if assignees and isinstance(assignees, list) and len(assignees) > 0:
                first_assignee = assignees[0]
                if isinstance(first_assignee, dict):
                    updates["assignee"] = first_assignee.get("login")
                else:
                    updates["assignee"] = str(first_assignee)

        if "labels" in github_issue_data and github_issue_data["labels"]:
            labels = github_issue_data["labels"]
            if isinstance(labels, list):
                updates["labels"] = [
                    label["name"] if isinstance(label, dict) else str(label)
                    for label in labels
                ]

        # Apply updates
        core.issues.update(issue_id, updates)

        # Print success message
        console.print(
            f"✅ Successfully synced issue {issue_id} with GitHub issue #{issue.github_issue}",
            style="bold green",
        )

    except Exception as e:
        format_operation_failure(
            console,
            f"Failed to apply sync changes to {issue_id}",
            f"Error: {str(e)}",
        )
        sys.exit(1)
