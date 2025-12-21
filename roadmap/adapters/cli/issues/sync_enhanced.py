"""Enhanced sync GitHub issue command with batch operations and validation."""

import sys
from pathlib import Path

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.core.services.github_config_validator import GitHubConfigValidator
from roadmap.core.services.github_integration_service import GitHubIntegrationService
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.infrastructure.logging import log_command
from roadmap.shared.formatters.text.operations import (
    format_operation_failure,
)

console = get_console()


def _validate_github_config(roadmap_root: Path) -> bool:
    """Validate GitHub configuration before operations.

    Args:
        roadmap_root: Root path of roadmap

    Returns:
        True if config is valid, False otherwise
    """
    validator = GitHubConfigValidator(roadmap_root)
    is_valid, error = validator.validate_config()

    if not is_valid:
        format_operation_failure(
            console,
            "GitHub configuration invalid",
            error,
        )
        return False

    return True


def _get_linked_issues(core, _filter_type: str | None = None) -> list:  # noqa: ARG001
    """Get all issues linked to GitHub, with optional filtering.

    Args:
        core: Core services
        _filter_type: Optional filter (all, milestone, status, unlinked)

    Returns:
        List of issues matching criteria
    """
    try:
        all_issues = core.issues.list()
        linked_issues = [
            issue
            for issue in all_issues
            if hasattr(issue, "github_issue") and issue.github_issue
        ]
        return linked_issues
    except Exception:
        return []


@click.command("sync-github")
@click.argument("issue_id", required=False)
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
@click.option(
    "--all",
    "sync_all",
    is_flag=True,
    help="Sync all linked issues",
)
@click.option(
    "--milestone",
    type=str,
    help="Sync all linked issues in specific milestone",
)
@click.option(
    "--status",
    type=str,
    help="Sync all linked issues with specific status",
)
@click.option(
    "--validate-only",
    is_flag=True,
    help="Only validate config without syncing",
)
@click.pass_context
@log_command("issue_sync_github", entity_type="issue", track_duration=True)
@require_initialized
def sync_github_issue(
    ctx: click.Context,
    issue_id: str | None,
    owner: str | None,
    repo: str | None,
    auto_confirm: bool,
    sync_all: bool,
    milestone: str | None,
    status: str | None,
    validate_only: bool,
) -> None:
    """Sync issue(s) with GitHub.

    Fetches latest information from GitHub and applies changes to local issues.
    Can sync single issue or batch sync multiple linked issues.

    Examples:
        # Sync single issue
        roadmap issue sync-github abc123

        # Sync all linked issues
        roadmap issue sync-github --all --auto-confirm

        # Sync issues in specific milestone
        roadmap issue sync-github --milestone v1.0.0 --auto-confirm

        # Just validate config
        roadmap issue sync-github --validate-only
    """
    core = ctx.obj["core"]
    roadmap_root = Path(core.root_path)

    # Validate GitHub config first
    if not _validate_github_config(roadmap_root):
        sys.exit(1)

    if validate_only:
        console.print("✅ GitHub configuration is valid", style="green")
        return

    # Determine which issues to sync
    issues_to_sync = []

    if sync_all:
        issues_to_sync = _get_linked_issues(core)
    elif milestone:
        # Sync all linked issues in milestone
        try:
            all_issues = core.issues.list()
            issues_to_sync = [
                issue
                for issue in all_issues
                if (
                    hasattr(issue, "github_issue")
                    and issue.github_issue
                    and hasattr(issue, "milestone_name")
                    and issue.milestone_name == milestone
                )
            ]
        except Exception as e:
            format_operation_failure(
                console,
                f"Failed to get issues for milestone {milestone}",
                str(e),
            )
            sys.exit(1)
    elif status:
        # Sync all linked issues with specific status
        try:
            all_issues = core.issues.list()
            issues_to_sync = [
                issue
                for issue in all_issues
                if (
                    hasattr(issue, "github_issue")
                    and issue.github_issue
                    and hasattr(issue, "status")
                    and issue.status.value == status
                )
            ]
        except Exception as e:
            format_operation_failure(
                console,
                f"Failed to get issues with status {status}",
                str(e),
            )
            sys.exit(1)
    elif issue_id:
        # Single issue sync
        try:
            issue = core.issues.get_by_id(issue_id)
            if issue:
                issues_to_sync = [issue]
        except Exception:
            pass
    else:
        console.print(
            "❌ Must specify issue_id, --all, --milestone, or --status",
            style="red",
        )
        sys.exit(1)

    if not issues_to_sync:
        console.print("⚠️  No issues to sync", style="yellow")
        return

    # Display what will be synced
    console.print(f"🔄 Will sync {len(issues_to_sync)} issue(s)", style="bold cyan")
    for issue in issues_to_sync[:5]:  # Show first 5
        github_id = getattr(issue, "github_issue", "?")
        title = getattr(issue, "title", "Untitled")
        console.print(f"   • #{github_id}: {title}")
    if len(issues_to_sync) > 5:
        console.print(f"   ... and {len(issues_to_sync) - 5} more")
    console.print()

    # Prompt for confirmation
    if not auto_confirm:
        if not click.confirm("Proceed with sync"):
            console.print("❌ Sync cancelled", style="red")
            return

    # Perform syncs
    success_count = 0
    error_count = 0

    for issue in issues_to_sync:
        try:
            _sync_single_issue(
                core,
                issue,
                owner,
                repo,
                roadmap_root,
            )
            success_count += 1
        except Exception as e:
            console.print(f"   ❌ {issue.id}: {str(e)}", style="red")
            error_count += 1

    # Summary
    console.print()
    console.print(f"✅ Synced {success_count} issue(s)", style="green")
    if error_count > 0:
        console.print(f"❌ Failed to sync {error_count} issue(s)", style="red")


def _sync_single_issue(
    core,
    issue,
    owner: str | None,
    repo: str | None,
    roadmap_root: Path,
) -> None:
    """Sync a single issue with GitHub.

    Args:
        core: Core services
        issue: Issue to sync
        owner: Optional GitHub owner
        repo: Optional GitHub repo
        roadmap_root: Root path of roadmap
    """
    issue_id = issue.id
    github_id = issue.github_issue

    if not github_id:
        raise ValueError(f"Issue {issue_id} not linked to GitHub")

    # Get config
    gh_service = GitHubIntegrationService(roadmap_root)
    config = gh_service.get_github_config()

    if not config:
        raise ValueError("GitHub not configured")

    # Use provided values or fall back to config
    owner = owner or config.get("owner")
    repo = repo or config.get("repo")

    if not owner or not repo:
        # Try parsing from repo string (e.g., "owner/repo")
        gh_repo = config.get("repo", "")
        if "/" in gh_repo:
            owner, repo = gh_repo.split("/", 1)
        else:
            raise ValueError("GitHub owner/repo not properly configured")

    # Fetch GitHub issue
    client = GitHubIssueClient(config)
    github_data = client.fetch_issue(github_id)

    if not github_data:
        raise ValueError(f"GitHub issue #{github_id} not found")

    # Get diff
    diff = client.get_issue_diff(
        github_id, issue.model_dump() if hasattr(issue, "model_dump") else {}
    )

    if not diff:
        return  # No changes

    # Apply changes
    updates = {
        "title": github_data.get("title", issue.title),
        "content": github_data.get("body", issue.content),
    }

    # Handle state
    if github_data.get("state") == "closed":
        updates["status"] = "done"

    # Handle assignee
    assignees = github_data.get("assignees", [])
    if assignees and len(assignees) > 0:
        first = assignees[0]
        updates["assignee"] = (
            first.get("login") if isinstance(first, dict) else str(first)
        )

    # Handle labels
    labels = github_data.get("labels", [])
    if labels:
        updates["labels"] = [
            label.get("name") if isinstance(label, dict) else str(label)
            for label in labels
        ]

    core.issues.update(issue_id, **updates)
