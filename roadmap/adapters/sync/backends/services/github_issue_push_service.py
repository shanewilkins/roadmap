"""Service for pushing issues to GitHub API."""

from structlog import get_logger

from roadmap.adapters.sync.backends.github_backend_helpers import GitHubBackendHelpers
from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
from roadmap.common.logging import log_error_with_context
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import SyncReport

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
            log_error_with_context(
                e,
                operation="push_github_issue",
                entity_type="Issue",
                entity_id=local_issue.id,
                additional_context={
                    "owner": owner,
                    "repo": repo,
                    "title": local_issue.title,
                },
                include_traceback=True,
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
        logger.info("push_issues_starting", issue_count=len(local_issues))
        errors = []

        for issue in local_issues:
            try:
                if self.push_issue(issue):
                    report.pushed.append(issue.id)
                else:
                    error_msg = f"Failed to push issue {issue.id}"
                    report.errors[issue.id] = error_msg
                    errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error pushing issue {issue.id}: {str(e)}"
                report.errors[issue.id] = error_msg
                errors.append(error_msg)
                log_error_with_context(
                    e,
                    operation="push_issues",
                    entity_type="Issue",
                    entity_id=issue.id,
                    additional_context={"issue_count": len(local_issues)},
                    include_traceback=True,
                )

        if errors:
            report.error = "; ".join(errors)

        logger.info(
            "push_issues_completed",
            total=len(local_issues),
            pushed=len(report.pushed),
            failed=len(report.errors),
        )
        return report
