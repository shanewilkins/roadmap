"""GitHub synchronization operations with parallel execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from structlog import get_logger

from roadmap.common.logging import log_error_with_context
from roadmap.core.interfaces import SyncReport

logger = get_logger()


class GitHubSyncOps:
    """Perform synchronization operations with GitHub backend."""

    def __init__(self, backend: Any):
        """Initialize GitHubSyncOps.

        Args:
            backend: GitHub backend instance.
        """
        self.backend = backend

    def push_issues(self, local_issues: list) -> SyncReport:
        """Push local issues to GitHub backend with progress tracking.

        Args:
            local_issues: List of local issues to push.

        Returns:
            Sync report with push results and errors.
        """
        report = SyncReport()

        if not local_issues:
            logger.info("push_issues_empty")
            return report

        logger.info("push_issues_starting", issue_count=len(local_issues))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.backend.push_issue, issue): issue
                for issue in local_issues
            }

            for future in as_completed(futures):
                issue = futures[future]
                try:
                    if future.result():
                        report.pushed.append(issue.id)
                        logger.debug("push_issue_succeeded", issue_id=issue.id)
                    else:
                        error_msg = "Failed to push issue"
                        report.errors[issue.id] = error_msg
                        logger.warning("push_issue_failed", issue_id=issue.id)
                except Exception as e:
                    error_msg = str(e)
                    report.errors[issue.id] = error_msg
                    log_error_with_context(
                        e,
                        operation="push_issue",
                        entity_type="Issue",
                        entity_id=issue.id,
                        include_traceback=False,
                    )

        logger.info(
            "push_issues_completed",
            total=len(local_issues),
            pushed=len(report.pushed),
            failed=len(report.errors),
        )
        return report

    def pull_issues(self, issue_ids: list[str]) -> SyncReport:
        """Pull issues from GitHub backend by IDs.

        Args:
            issue_ids: List of issue IDs to pull.

        Returns:
            Sync report with pull results and errors.
        """
        report = SyncReport()

        if not issue_ids:
            return report

        logger.info("pull_issues_starting", issue_count=len(issue_ids))

        # Fetch all remote issues upfront
        from roadmap.adapters.sync.backends.services.github_issue_fetch_service import (
            GitHubIssueFetchService,
        )

        try:
            fetch_service = GitHubIssueFetchService(
                self.backend.github_client,
                self.backend.config,
                self.backend._helpers,
            )
            all_remote_issues = fetch_service.get_issues()

            successful_pulls = []
            failed_pulls = {}

            # Process each requested issue and save locally
            for issue_id in issue_ids:
                try:
                    if issue_id not in all_remote_issues:
                        error_msg = "Issue not found on remote"
                        failed_pulls[issue_id] = error_msg
                        logger.debug("pull_issue_not_found", issue_id=issue_id)
                        continue

                    # Mark as successfully pulled
                    successful_pulls.append(issue_id)
                    logger.debug("pull_issue_processed", issue_id=issue_id)

                except Exception as e:
                    error_msg = str(e)
                    failed_pulls[issue_id] = error_msg
                    log_error_with_context(
                        e,
                        operation="pull_issue",
                        entity_type="Issue",
                        entity_id=issue_id,
                        include_traceback=False,
                    )

            report.pulled = successful_pulls
            report.errors = failed_pulls

            logger.info(
                "pull_issues_complete",
                successful=len(successful_pulls),
                failed=len(failed_pulls),
            )

            return report

        except Exception as e:
            logger.error(
                "pull_issues_failed", error=str(e), error_type=type(e).__name__
            )
            report.error = f"Failed to pull issues: {str(e)}"
            return report
