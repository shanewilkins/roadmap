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

    def _persist_issue_before_linking(self, issue: Any, issue_id: str) -> bool:
        """Persist issue to database before linking to GitHub.

        Args:
            issue: The Issue domain object
            issue_id: The ID to use for persistence

        Returns:
            True if persist succeeded or was skipped, False on hard error
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True

        try:
            issue_repo = self.backend.core.db.get_issue_repository()
            existing = issue_repo.get(issue_id)

            if not existing:
                issue_data = {
                    "id": issue_id,
                    "title": issue.title,
                    "headline": getattr(issue, "headline", ""),
                    "description": issue.content or "",
                    "status": str(issue.status),
                    "priority": str(issue.priority),
                    "issue_type": str(issue.type) if hasattr(issue, "type") else "task",
                    "assignee": issue.assignee,
                    "estimate_hours": issue.estimated_hours
                    if hasattr(issue, "estimated_hours")
                    else None,
                    "due_date": None,
                    "project_id": None,
                }
                issue_repo.create(issue_data)
                logger.info(
                    "persisted_issue_for_linking",
                    issue_id=issue_id,
                    title=issue.title,
                )
        except Exception as e:
            logger.warning(
                "failed_to_persist_issue_before_linking",
                issue_id=issue_id,
                error=str(e),
                severity="operational",
            )
            # Continue with linking even if persist fails

        return True

    def _link_issue_to_github(
        self, issue_uuid: str, github_number: int
    ) -> tuple[bool, str | None]:
        """Link issue to GitHub in database.

        Args:
            issue_uuid: The local issue UUID
            github_number: The GitHub issue number

        Returns:
            Tuple of (success: bool, error_message: str | None)
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True, None

        try:
            self.backend.core.db.remote_links.link_issue(
                issue_uuid=issue_uuid,
                backend_name="github",
                remote_id=str(github_number),
            )
            logger.info(
                "github_issue_linked",
                issue_id=issue_uuid,
                github_number=github_number,
            )
            return True, None
        except Exception as e:
            logger.warning(
                "github_issue_link_failed",
                issue_id=issue_uuid,
                github_number=github_number,
                error=str(e),
                severity="operational",
            )
            return False, str(e)

    def _handle_push_error(self, issue: Any, error_msg: str) -> tuple[bool, str]:
        """Handle and categorize push errors.

        Args:
            issue: The Issue domain object
            error_msg: The error message

        Returns:
            Tuple of (success: bool, categorized_error_message: str)
        """
        if "Access forbidden" in error_msg or "403" in error_msg:
            logger.debug(
                "github_push_issue_skipped_due_to_permissions",
                issue_id=issue.id,
                error=error_msg,
                severity="config",
            )
            return False, f"Permission denied (check token scope): {error_msg}"
        elif "Gone" in error_msg or "410" in error_msg:
            logger.info(
                "github_push_issue_skipped_resource_deleted",
                issue_id=issue.id,
                error=error_msg,
                severity="operational",
            )
            return False, f"Remote issue deleted: {error_msg}"
        elif "not found" in error_msg.lower() or "404" in error_msg:
            logger.warning(
                "github_push_issue_failed_not_found",
                issue_id=issue.id,
                error=error_msg,
                severity="operational",
            )
            return False, error_msg
        elif "Rate limit exceeded" in error_msg or "429" in error_msg:
            logger.warning(
                "github_push_issue_rate_limited",
                issue_id=issue.id,
                error=error_msg,
                severity="operational",
            )
            return False, f"Rate limited: {error_msg}"
        elif "Validation error" in error_msg:
            logger.warning(
                "github_push_issue_validation_error",
                issue_id=issue.id,
                error=error_msg,
                severity="data_error",
            )
            return False, error_msg
        else:
            logger.warning(
                "github_push_issue_failed",
                issue_id=issue.id,
                error=error_msg,
                error_type=type(error_msg).__name__,
                severity="operational",
            )
            return False, error_msg

    def _push_single_issue(self, issue: Any) -> tuple[bool, str | None]:
        """Push a single issue to GitHub API.

        Args:
            issue: The Issue domain object to push

        Returns:
            Tuple of (success: bool, error_message: str | None)
        """
        try:
            from roadmap.adapters.sync.backends.converters import (
                IssueToGitHubPayloadConverter,
            )

            client = self.backend.get_api_client()
            github_number = IssueToGitHubPayloadConverter.get_github_number(issue)
            payload = IssueToGitHubPayloadConverter.to_payload(issue, github_number)

            if github_number:
                # Update existing issue
                client.update_issue(github_number, **payload)
                logger.info(
                    "github_issue_updated",
                    issue_id=issue.id,
                    github_number=github_number,
                    title=issue.title,
                )
                return True, None

            # Create new issue
            result = client.create_issue(**payload)
            github_number = result.get("number")

            if github_number:
                self._persist_issue_before_linking(issue, issue.id)
                self._link_issue_to_github(issue.id, github_number)
                logger.info(
                    "github_issue_created",
                    issue_id=issue.id,
                    github_number=github_number,
                    title=issue.title,
                )

            return True, None

        except Exception as e:
            error_msg = str(e)
            return self._handle_push_error(issue, error_msg)

    def push_issues(self, local_issues: list) -> SyncReport:
        """Push local issues to GitHub backend with parallel execution.

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
                executor.submit(self._push_single_issue, issue): issue
                for issue in local_issues
            }

            for future in as_completed(futures):
                issue = futures[future]
                try:
                    success, error_msg = future.result()
                    if success:
                        report.pushed.append(issue.id)
                        logger.debug("push_issue_succeeded", issue_id=issue.id)
                    else:
                        report.errors[issue.id] = error_msg or "Failed to push issue"
                        logger.debug(
                            "push_issue_failed", issue_id=issue.id, error=error_msg
                        )
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

    def _get_project_id_for_synced_issue(self) -> str | None:
        """Get default project ID for synced issues.

        Returns:
            Project ID or None
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return None

        try:
            projects = list(self.backend.core.projects.list())
            return projects[0].id if projects else None
        except Exception as e:
            logger.warning(
                "failed_to_get_projects_for_issue",
                error=str(e),
                severity="operational",
            )
            return None

    def _create_or_update_issue_locally(
        self, sync_issue: Any, local_issue: Any, github_id: str
    ) -> bool:
        """Create or update issue in local database.

        Args:
            sync_issue: The SyncIssue from GitHub
            local_issue: The converted local Issue domain object
            github_id: The GitHub issue ID

        Returns:
            True if successful
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True

        issue_repo = self.backend.core.db.get_issue_repository()
        existing = issue_repo.get(github_id)
        project_id = self._get_project_id_for_synced_issue()

        if existing:
            local_issue.id = github_id
            issue_repo.update(local_issue)
            logger.info(
                "github_issue_updated_locally",
                github_number=github_id,
                title=local_issue.title,
            )
        else:
            issue_data = {
                "id": github_id,
                "title": local_issue.title,
                "headline": local_issue.headline,
                "description": local_issue.content or "",
                "status": str(local_issue.status),
                "priority": str(local_issue.priority),
                "issue_type": str(local_issue.issue_type),
                "project_id": project_id,
                "assignee": local_issue.assignee,
                "estimate_hours": local_issue.estimated_hours,
                "due_date": None,
            }
            issue_repo.create(issue_data)
            logger.info(
                "github_issue_created_locally",
                github_number=github_id,
                title=local_issue.title,
            )

        return True

    def _link_pulled_issue_locally(self, sync_issue: Any) -> bool:
        """Link pulled issue to GitHub in local database.

        Args:
            sync_issue: The SyncIssue from GitHub

        Returns:
            True if linking succeeded or was skipped
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True

        try:
            github_id = sync_issue.remote_ids.get("github") or sync_issue.backend_id
            self.backend.core.db.remote_links.link_issue(
                issue_uuid=github_id,
                backend_name="github",
                remote_id=str(github_id),
            )
            logger.info(
                "github_issue_linked_locally",
                github_number=github_id,
            )
            return True
        except Exception as e:
            logger.warning(
                "github_issue_link_failed",
                github_number=getattr(sync_issue, "backend_id", "unknown"),
                error=str(e),
                severity="operational",
            )
            return True  # Don't fail the pull on link errors

    def _handle_pull_error(self, sync_issue: Any, error_msg: str) -> tuple[bool, str]:
        """Handle and categorize pull errors.

        Args:
            sync_issue: The SyncIssue from GitHub
            error_msg: The error message

        Returns:
            Tuple of (success: bool, categorized_error_message: str)
        """
        remote_id = getattr(sync_issue, "backend_id", "unknown")

        if "Access forbidden" in error_msg or "403" in error_msg:
            logger.debug(
                "github_pull_issue_skipped_due_to_permissions",
                github_number=remote_id,
                error=error_msg,
                severity="config",
            )
            return False, f"Permission denied (check token scope): {error_msg}"
        elif "Gone" in error_msg or "410" in error_msg:
            logger.info(
                "github_pull_issue_skipped_resource_deleted",
                github_number=remote_id,
                error=error_msg,
                severity="operational",
            )
            return False, f"Remote issue deleted: {error_msg}"
        elif "not found" in error_msg.lower() or "404" in error_msg:
            logger.debug(
                "github_pull_issue_failed_not_found",
                github_number=remote_id,
                error=error_msg,
                severity="operational",
            )
            return False, error_msg
        elif "Rate limit exceeded" in error_msg or "429" in error_msg:
            logger.debug(
                "github_pull_issue_rate_limited",
                github_number=remote_id,
                error=error_msg,
                severity="operational",
            )
            return False, f"Rate limited: {error_msg}"
        else:
            logger.debug(
                "github_pull_issue_failed",
                github_number=remote_id,
                error=error_msg,
                error_type=type(error_msg).__name__,
                severity="operational",
            )
            return False, error_msg

    def _pull_single_issue(self, sync_issue: Any) -> tuple[bool, str | None]:
        """Pull a single issue from GitHub and create/update locally.

        Args:
            sync_issue: The SyncIssue from GitHub fetch

        Returns:
            Tuple of (success: bool, error_message: str | None)
        """
        try:
            from roadmap.adapters.sync.backends.converters import (
                GitHubPayloadToIssueConverter,
            )

            local_issue = GitHubPayloadToIssueConverter.from_sync_issue(sync_issue)
            github_id = sync_issue.remote_ids.get("github") or sync_issue.backend_id

            self._create_or_update_issue_locally(sync_issue, local_issue, github_id)
            self._link_pulled_issue_locally(sync_issue)

            return True, None

        except Exception as e:
            error_msg = str(e)
            return self._handle_pull_error(sync_issue, error_msg)

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

                    # Pull the issue and create/update locally
                    sync_issue = all_remote_issues[issue_id]
                    success, error = self._pull_single_issue(sync_issue)

                    if success:
                        successful_pulls.append(issue_id)
                        logger.debug("pull_issue_processed", issue_id=issue_id)
                    else:
                        failed_pulls[issue_id] = error or "Unknown error"

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
