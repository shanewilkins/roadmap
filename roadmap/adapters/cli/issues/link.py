"""Link GitHub issue command - link internal issue to GitHub issue."""

from typing import Any

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

    # Validate internal issue
    issue = _validate_internal_issue(ctx, issue_id)

    # Validate GitHub ID is positive
    _validate_github_id(ctx, github_id)

    # Check if already linked
    if issue.github_issue is not None:
        if issue.github_issue == github_id:
            _display_already_linked(issue, issue_id)
            return
        else:
            _display_already_linked_different(ctx, issue_id, issue.github_issue)

    # Get owner/repo from config or command-line
    config_owner, config_repo = _resolve_github_config(ctx, core, owner, repo)

    # Validate GitHub issue exists
    _validate_github_issue_exists(ctx, config_owner, config_repo, github_id)

    # Perform the link
    _perform_link(ctx, core, issue, issue_id, github_id, config_owner, config_repo)


def _validate_internal_issue(ctx: click.Context, issue_id: str) -> Any:
    """Validate that an internal issue exists.

    Args:
        ctx: Click context
        issue_id: Issue ID to validate

    Returns:
        Issue object

    Raises:
        SystemExit: If issue not found
    """
    core = ctx.obj["core"]
    try:
        issue = core.issues.get_by_id(issue_id)
        if not issue:
            lines = format_operation_failure("link issue", issue_id, "Issue not found")
            for line in lines:
                console.print(line)
            ctx.exit(1)
        return issue
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="retrieve issue",
            entity_type="issue",
            entity_id=issue_id,
            fatal=True,
        )


def _validate_github_id(ctx: click.Context, github_id: int) -> None:
    """Validate GitHub ID is positive.

    Args:
        ctx: Click context
        github_id: GitHub issue ID to validate

    Raises:
        SystemExit: If ID is invalid
    """
    if github_id <= 0:
        lines = format_operation_failure(
            "link issue", "", "Invalid GitHub issue number"
        )
        for line in lines:
            console.print(line)
        ctx.exit(1)


def _display_already_linked(issue: Any, issue_id: str) -> None:
    """Display message when issue is already linked to same GitHub ID.

    Args:
        issue: Issue object
        issue_id: Issue ID
    """
    lines = format_operation_success("✅", "Linked", issue.title, issue_id)
    for line in lines:
        console.print(line)


def _display_already_linked_different(
    ctx: click.Context, issue_id: str, existing_github_id: int
) -> None:
    """Display error when issue is already linked to different GitHub ID.

    Args:
        ctx: Click context
        issue_id: Issue ID
        existing_github_id: Existing GitHub issue ID

    Raises:
        SystemExit: Always exits
    """
    lines = format_operation_failure(
        "link issue",
        issue_id,
        f"Already linked to GitHub issue #{existing_github_id}",
    )
    for line in lines:
        console.print(line)
    ctx.exit(1)


def _resolve_github_config(
    ctx: click.Context,
    core: Any,
    owner: str | None,
    repo: str | None,
) -> tuple[str, str]:
    """Resolve GitHub owner and repo from config or arguments.

    Args:
        ctx: Click context
        core: RoadmapCore instance
        owner: Optional owner override
        repo: Optional repo override

    Returns:
        Tuple of (owner, repo)

    Raises:
        SystemExit: If config cannot be resolved
    """
    config_owner = owner
    config_repo = repo

    if not config_owner or not config_repo:
        try:
            from pathlib import Path

            from roadmap.core.services.github_integration_service import (
                GitHubIntegrationService,
            )

            config_path = Path(core.root_path) / "config.yaml"
            gh_service = GitHubIntegrationService(Path(core.root_path), config_path)
            _, config_owner, config_repo = gh_service.get_github_config()

            if not config_owner or not config_repo:
                lines = format_operation_failure(
                    "configure GitHub", None, "GitHub repository not configured"
                )
                for line in lines:
                    console.print(line)
                ctx.exit(1)
        except Exception as e:
            lines = format_operation_failure("get GitHub configuration", None, str(e))
            for line in lines:
                console.print(line)
            ctx.exit(1)

    # Type narrowing: at this point these must be non-None
    assert config_owner is not None
    assert config_repo is not None

    return config_owner, config_repo


def _validate_github_issue_exists(
    ctx: click.Context, owner: str, repo: str, github_id: int
) -> None:
    """Validate that a GitHub issue exists.

    Args:
        ctx: Click context
        owner: GitHub repository owner
        repo: GitHub repository name
        github_id: GitHub issue ID

    Raises:
        SystemExit: If GitHub issue doesn't exist
    """
    try:
        gh_client = GitHubIssueClient()
        exists = gh_client.issue_exists(owner, repo, github_id)
        if not exists:
            lines = format_operation_failure(
                "verify GitHub issue",
                str(github_id),
                f"GitHub issue #{github_id} not found",
            )
            for line in lines:
                console.print(line)
            ctx.exit(1)
    except Exception as e:
        lines = format_operation_failure("verify GitHub issue", str(github_id), str(e))
        for line in lines:
            console.print(line)
        ctx.exit(1)


def _perform_link(
    ctx: click.Context,
    core: Any,
    issue: Any,
    issue_id: str,
    github_id: int,
    owner: str,
    repo: str,
) -> None:
    """Perform the actual link operation.

    Args:
        ctx: Click context
        core: RoadmapCore instance
        issue: Issue object
        issue_id: Issue ID
        github_id: GitHub issue ID
        owner: GitHub repository owner
        repo: GitHub repository name

    Raises:
        SystemExit: If link fails
    """
    try:
        issue.github_issue = github_id
        core.issues.update(issue)

        # Success message with link details
        lines = format_operation_success("✅", "Linked", issue.title, issue_id)
        for line in lines:
            console.print(line)
        console.print(
            f"   Repository: {owner}/{repo}",
            style="cyan",
        )
        console.print(
            f"   You can now use 'roadmap issue sync-github {issue_id}' to sync changes",
            style="dim",
        )
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="link issue",
            entity_type="issue",
            entity_id=issue_id,
            fatal=True,
        )
