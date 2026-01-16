"""Service for fetching issues from GitHub API."""

from structlog import get_logger

from roadmap.adapters.sync.backends.github_backend_helpers import GitHubBackendHelpers
from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
from roadmap.common.logging import log_error_with_context
from roadmap.core.models.sync_models import SyncIssue

logger = get_logger()


class GitHubIssueFetchService:
    """Handles fetching issues from GitHub API."""

    def __init__(
        self,
        github_client: GitHubClientWrapper,
        config: dict,
        helpers: GitHubBackendHelpers,
    ):
        """Initialize fetch service.

        Args:
            github_client: GitHubClientWrapper for API access
            config: Configuration dict with 'owner', 'repo'
            helpers: GitHubBackendHelpers for conversions
        """
        self.github_client = github_client
        self.config = config
        self.helpers = helpers

    def get_issues(self) -> dict[str, SyncIssue]:
        """Fetch all remote issues from GitHub.

        Returns:
            Dict mapping remote issue IDs (as strings) to SyncIssue objects,
            or empty dict if fetch fails.
        """
        if not self.github_client:
            logger.warning("github_fetch_no_client")
            return {}

        owner = self.config.get("owner")
        repo = self.config.get("repo")

        if not owner or not repo:
            logger.warning("github_fetch_missing_config", owner=owner, repo=repo)
            return {}

        try:
            logger.debug("github_fetching_issues", owner=owner, repo=repo)
            issues_data = self.github_client.get_issues(owner, repo, state="all") or []
            logger.info("github_issues_fetched", count=len(issues_data))

            # Convert each GitHub issue to SyncIssue
            result = {}
            failed_conversions = 0
            for issue_dict in issues_data:
                try:
                    sync_issue = self._dict_to_sync_issue(issue_dict)
                    remote_id = str(issue_dict.get("number", ""))
                    result[remote_id] = sync_issue
                except Exception as e:
                    failed_conversions += 1
                    issue_number = issue_dict.get("number")
                    log_error_with_context(
                        e,
                        operation="convert_github_issue_to_sync",
                        entity_type="Issue",
                        entity_id=str(issue_number),
                        additional_context={
                            "owner": owner,
                            "repo": repo,
                            "total_issues": len(issues_data),
                        },
                        include_traceback=False,
                    )
            if failed_conversions > 0:
                logger.warning(
                    "github_issue_conversions_failed",
                    total=len(issues_data),
                    failed=failed_conversions,
                    successful=len(result),
                )
            return result

        except Exception as e:
            log_error_with_context(
                e,
                operation="fetch_github_issues",
                entity_type="Repository",
                entity_id=f"{owner}/{repo}",
                additional_context={"suggested_action": "check_connectivity"},
                include_traceback=True,
            )
            return {}

    @staticmethod
    def _dict_to_sync_issue(issue_dict: dict) -> SyncIssue:
        """Convert GitHub issue dict to SyncIssue object.

        Args:
            issue_dict: GitHub issue data from API

        Returns:
            SyncIssue with normalized data
        """
        backend_id = issue_dict.get("number")
        return SyncIssue(
            id=f"github-{backend_id}" if backend_id else "unknown",
            title=issue_dict.get("title") or "Untitled",
            headline=issue_dict.get("body") or "",
            status="open" if issue_dict.get("state") == "open" else "closed",
            labels=issue_dict.get("labels", []),
            assignee=issue_dict.get("assignee", {}).get("login"),
            milestone=issue_dict.get("milestone", {}).get("title")
            if issue_dict.get("milestone")
            else None,
            backend_id=backend_id,
        )
