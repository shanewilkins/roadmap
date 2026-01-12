"""Service for pushing issues to GitHub API."""

from structlog import get_logger

from roadmap.adapters.sync.backends.github_backend_helpers import GitHubBackendHelpers
from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync_report import SyncReport

logger = get_logger()


class GitHubIssuePushService:
    """Handles pushing issues to GitHub API."""

    def __init__(
        self,
        github_client: GitHubClientWrapper,
        config: dict,
        helpers: GitHubBackendHelpers,
    ):
        """Initialize push service.

        Args:
            github_client: GitHubClientWrapper for API access
            config: Configuration dict with 'owner', 'repo'
            helpers: GitHubBackendHelpers for conversions
        """
        self.github_client = github_client
        self.config = config
        self.helpers = helpers

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to GitHub.

        Args:
            local_issue: Issue object to push

        Returns:
            True if push succeeded, False otherwise
        """
        if not self.github_client:
            logger.warning("github_push_no_client", issue_id=local_issue.id)
            return False

        owner = self.config.get("owner")
        repo = self.config.get("repo")

        if not owner or not repo:
            logger.warning(
                "github_push_missing_config",
                owner=owner,
                repo=repo,
                issue_id=local_issue.id,
            )
            return False

        try:
            logger.debug("github_pushing_issue", issue_id=local_issue.id)
            # Build GitHub issue data
            github_data = {
                "title": local_issue.title or "",
                "body": local_issue.headline or "",
                "state": "open" if local_issue.status.value == "todo" else "closed",
                "labels": list(local_issue.labels or []),
            }

            if local_issue.assignee:
                github_data["assignees"] = [local_issue.assignee]

            # Determine if this is a push (update) or a new issue
            remote_id = local_issue.remote_ids.get("github")
            if remote_id:
                # Update existing issue
                result = self.github_client.update_issue(
                    owner, repo, int(remote_id), github_data
                )
                logger.info(
                    "github_issue_updated",
                    issue_id=local_issue.id,
                    remote_id=remote_id,
                )
            else:
                # Create new issue
                result = self.github_client.create_issue(owner, repo, github_data)
                if result:
                    github_number = result.get("number")
                    if github_number:
                        local_issue.remote_ids["github"] = github_number
                    logger.info(
                        "github_issue_created",
                        issue_id=local_issue.id,
                        remote_id=github_number,
                    )

            return result is not None

        except Exception as e:
            logger.error(
                "github_push_error",
                issue_id=local_issue.id,
                error_type=type(e).__name__,
                error=str(e),
            )
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with push results
        """
        report = SyncReport()
        pushed_count = 0
        errors = []

        for issue in local_issues:
            try:
                if self.push_issue(issue):
                    pushed_count += 1
                else:
                    errors.append(f"Failed to push issue {issue.id}")
            except Exception as e:
                logger.error(
                    "github_push_issue_exception",
                    issue_id=issue.id,
                    error=str(e),
                )
                errors.append(f"Error pushing issue {issue.id}: {str(e)}")

        report.issues_pushed = pushed_count
        if errors:
            report.error = "; ".join(errors)

        return report
