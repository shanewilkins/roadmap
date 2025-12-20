"""Link GitHub issue command - link internal issue to GitHub issue."""

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.infrastructure.logging import (
    log_command,
)
from roadmap.shared.formatters.text.operations import (
    format_operation_failure,
    format_operation_success,
)

console = get_console()


@click.command("link")
@click.argument("issue_id")
@click.option(
    "--github-id",
    type=int,
    required=True,
    help="GitHub issue number to link (must be positive integer)",
)
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
@click.pass_context
@log_command("issue_link", entity_type="issue", track_duration=True)
@require_initialized
def link_github_issue(
    ctx: click.Context,
    issue_id: str,
    github_id: int,
    owner: str | None,
    repo: str | None,
) -> None:
    """Link an internal issue to a GitHub issue.

    Links the internal issue identified by ISSUE_ID to a GitHub issue
    identified by the GitHub issue number provided via --github-id.

    Once linked, you can use other commands like sync-github to fetch
    updates from GitHub.

    Example:
        roadmap issue link abc123 --github-id 456
        roadmap issue link abc123 --github-id 456 --owner owner-name --repo repo-name
    """
    core = ctx.obj["core"]

    # Validate the internal issue exists
    try:
        issue = core.issues.get_by_id(issue_id)
        if not issue:
            format_operation_failure(
                console,
                f"Issue {issue_id} not found",
                "Cannot link non-existent issue",
            )
            ctx.exit(1)
    except Exception as e:
        handle_cli_error(
            ctx,
            e,
            "Failed to retrieve issue",
            f"Could not get issue {issue_id}: {str(e)}",
        )

    # Validate GitHub ID is positive
    if github_id <= 0:
        format_operation_failure(
            console,
            f"Invalid GitHub issue number: {github_id}",
            "GitHub issue numbers must be positive integers",
        )
        ctx.exit(1)

    # Check if already linked to a different GitHub issue
    if issue.github_issue is not None and issue.github_issue != github_id:
        format_operation_failure(
            console,
            f"Issue {issue_id} is already linked to GitHub issue #{issue.github_issue}",
            f"Use 'roadmap issue update {issue_id} --github-id {github_id}' to change the link",
        )
        ctx.exit(1)

    # If already linked to same ID, nothing to do
    if issue.github_issue == github_id:
        format_operation_success(
            console,
            f"Issue {issue_id} is already linked to GitHub issue #{github_id}",
        )
        return

    # Get owner/repo from config or command-line
    config_owner = owner
    config_repo = repo

    if not config_owner or not config_repo:
        # Try to get from GitHub integration service
        try:
            from pathlib import Path

            from roadmap.core.services.github_integration_service import (
                GitHubIntegrationService,
            )

            config_path = Path(core.root_path) / "config.yaml"
            gh_service = GitHubIntegrationService(Path(core.root_path), config_path)
            token, config_owner, config_repo = gh_service.get_github_config()

            if not config_owner or not config_repo:
                format_operation_failure(
                    console,
                    "GitHub repository not configured",
                    "Provide --owner and --repo options, or configure GitHub in config.yaml",
                )
                ctx.exit(1)
        except Exception as e:
            format_operation_failure(
                console,
                "Could not get GitHub configuration",
                f"Error: {str(e)}",
            )
            ctx.exit(1)

    # Validate GitHub issue exists
    try:
        gh_client = GitHubIssueClient()
        exists = gh_client.issue_exists(config_owner, config_repo, github_id)
        if not exists:
            format_operation_failure(
                console,
                f"GitHub issue #{github_id} not found",
                f"Repository: {config_owner}/{config_repo}",
            )
            ctx.exit(1)
    except Exception as e:
        format_operation_failure(
            console,
            "Could not verify GitHub issue",
            f"Error: {str(e)}",
        )
        ctx.exit(1)

    # Update the issue with GitHub ID
    try:
        issue.github_issue = github_id
        core.issues.update(issue)

        # Success message with link details
        format_operation_success(
            console,
            f"✅ Linked issue {issue_id} to GitHub issue #{github_id}",
        )
        console.print(f"   Title: {issue.title}", style="cyan")
        console.print(
            f"   Repository: {config_owner}/{config_repo}",
            style="cyan",
        )
        console.print(
            f"   You can now use 'roadmap issue sync-github {issue_id}' to sync changes",
            style="dim",
        )
    except Exception as e:
        handle_cli_error(
            ctx,
            e,
            "Failed to link issue",
            f"Could not update issue {issue_id}: {str(e)}",
        )
