"""GitHub synchronization operations with parallel execution."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from structlog import get_logger

from roadmap.common.logging import log_error_with_context
from roadmap.common.services.retry import API_RETRY
from roadmap.common.utils.timezone_utils import now_utc
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
        self._create_lock = threading.Lock()
        self._last_create_time = 0.0
        self._create_min_interval_seconds = self._get_create_min_interval_seconds()
        self._label_cache: set[str] | None = None
        self._label_support: bool | None = None

    def _get_create_min_interval_seconds(self) -> float:
        """Get minimum interval between issue creations to avoid secondary limits."""
        config = getattr(self.backend, "config", {}) or {}
        sync_settings = (
            config.get("sync_settings", {}) if isinstance(config, dict) else {}
        )
        interval = sync_settings.get("create_min_interval_seconds")
        try:
            if interval is not None:
                return max(0.0, float(interval))
        except (TypeError, ValueError):
            logger.debug(
                "github_create_interval_invalid",
                interval=interval,
                severity="data_error",
            )
        return 1.0

    def _sync_labels_enabled(self) -> bool:
        config = getattr(self.backend, "config", {}) or {}
        sync_settings = (
            config.get("sync_settings", {}) if isinstance(config, dict) else {}
        )
        return bool(sync_settings.get("sync_labels", True))

    def _get_label_color(self, name: str) -> str:
        label_colors = {
            "priority:critical": "FF0000",
            "priority:high": "FF9900",
            "priority:medium": "FFFF00",
            "priority:low": "00FF00",
            "status:todo": "CCCCCC",
            "status:in-progress": "0366D6",
            "status:blocked": "D73A49",
            "status:review": "A371F7",
            "status:done": "28A745",
        }
        return label_colors.get(name, "CCCCCC")

    def _ensure_labels_exist(self, labels: list[str]) -> None:
        if not labels or not self._sync_labels_enabled():
            return

        if self._label_support is False:
            return

        if hasattr(self.backend, "get_label_client"):
            client = self.backend.get_label_client()
        else:
            client = self.backend.get_api_client()

        if client is None:
            self._label_support = False
            return

        if self._label_support is None:
            if not (hasattr(client, "get_labels") and hasattr(client, "create_label")):
                logger.warning(
                    "github_label_client_missing_methods",
                    has_get_labels=hasattr(client, "get_labels"),
                    has_create_label=hasattr(client, "create_label"),
                    severity="operational",
                )
                self._label_support = False
                return
            self._label_support = True
        if self._label_cache is None:
            try:
                existing_labels = client.get_labels()
                self._label_cache = {
                    label["name"]
                    for label in existing_labels
                    if isinstance(label, dict) and label.get("name")
                }
            except Exception as e:
                logger.warning(
                    "github_labels_fetch_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    severity="operational",
                )
                self._label_cache = set()
                return

        missing = [label for label in labels if label not in self._label_cache]
        for label in missing:
            try:
                client.create_label(label, self._get_label_color(label))
                self._label_cache.add(label)
                logger.info("github_label_created", label=label)
            except Exception as e:
                logger.warning(
                    "github_label_create_failed",
                    label=label,
                    error=str(e),
                    error_type=type(e).__name__,
                    severity="operational",
                )

    def _throttle_issue_creation(self) -> None:
        """Throttle issue creation to reduce secondary rate limit errors."""
        if self._create_min_interval_seconds <= 0:
            return

        with self._create_lock:
            now = time.monotonic()
            elapsed = now - self._last_create_time
            delay = self._create_min_interval_seconds - elapsed
            if delay > 0:
                logger.debug(
                    "github_issue_create_throttle",
                    delay_seconds=round(delay, 3),
                )
                time.sleep(delay)
            self._last_create_time = time.monotonic()

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
        """Push a single issue to GitHub API with retry logic.

        Args:
            issue: The Issue domain object to push

        Returns:
            Tuple of (success: bool, error_message: str | None)
        """

        @API_RETRY
        def _push_with_retry():
            """Inner function with retry decorator for API calls."""
            from roadmap.adapters.sync.backends.converters import (
                IssueToGitHubPayloadConverter,
            )

            client = self.backend.get_api_client()
            github_number = IssueToGitHubPayloadConverter.get_github_number(issue)
            payload = IssueToGitHubPayloadConverter.to_payload(issue, github_number)

            labels = payload.get("labels") if isinstance(payload, dict) else None
            if isinstance(labels, list) and labels:
                self._ensure_labels_exist(labels)

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

            # Create new issue (throttled to avoid secondary rate limits)
            self._throttle_issue_creation()
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

        try:
            return _push_with_retry()
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

    def _resolve_local_issue_id(
        self, github_id: str | int | None, local_issue: Any
    ) -> str:
        """Resolve the local issue ID for a pulled GitHub issue.

        Prefers an existing remote link mapping; falls back to the local issue ID.
        """
        if github_id is None:
            return local_issue.id

        if not hasattr(self.backend, "core") or not self.backend.core:
            return local_issue.id

        try:
            issue_uuid = self.backend.core.db.remote_links.get_issue_uuid(
                backend_name="github", remote_id=github_id
            )
            if issue_uuid:
                return issue_uuid
        except Exception as e:
            logger.warning(
                "github_remote_link_lookup_failed",
                github_number=github_id,
                error=str(e),
                severity="operational",
            )

        return local_issue.id

    def _create_or_update_issue_locally(
        self, sync_issue: Any, local_issue: Any, github_id: str | int | None
    ) -> str | None:
        """Create or update issue in local database.

        Args:
            sync_issue: The SyncIssue from GitHub
            local_issue: The converted local Issue domain object
            github_id: The GitHub issue ID

        Returns:
            Local issue ID if successful
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return local_issue.id

        issue_repo = self.backend.core.db.get_issue_repository()
        local_issue_id = self._resolve_local_issue_id(github_id, local_issue)
        existing = issue_repo.get(local_issue_id)
        project_id = (
            existing.get("project_id")
            if existing
            else self._get_project_id_for_synced_issue()
        )

        if existing:
            updates = {
                "title": local_issue.title,
                "headline": local_issue.headline,
                "description": local_issue.content or "",
                "status": str(local_issue.status),
                "priority": str(local_issue.priority),
                "issue_type": str(local_issue.issue_type),
                "assignee": local_issue.assignee,
                "estimate_hours": local_issue.estimated_hours,
                "due_date": None,
            }
            if project_id:
                updates["project_id"] = project_id

            issue_repo.update(local_issue_id, updates)
            logger.info(
                "github_issue_updated_locally",
                issue_id=local_issue_id,
                github_number=github_id,
                title=local_issue.title,
            )
        else:
            issue_data = {
                "id": local_issue_id,
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
                issue_id=local_issue_id,
                github_number=github_id,
                title=local_issue.title,
            )

        return local_issue_id

    def _link_pulled_issue_locally(
        self, local_issue_id: str | None, github_id: str | int | None
    ) -> bool:
        """Link pulled issue to GitHub in local database.

        Args:
            sync_issue: The SyncIssue from GitHub

        Returns:
            True if linking succeeded or was skipped
        """
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True

        if not local_issue_id or github_id is None:
            logger.warning(
                "github_issue_link_skipped_missing_ids",
                issue_id=local_issue_id,
                github_number=github_id,
                severity="data_error",
            )
            return True

        try:
            self.backend.core.db.remote_links.link_issue(
                issue_uuid=local_issue_id,
                backend_name="github",
                remote_id=str(github_id),
            )
            logger.info(
                "github_issue_linked_locally",
                issue_id=local_issue_id,
                github_number=github_id,
            )
            return True
        except Exception as e:
            logger.warning(
                "github_issue_link_failed",
                issue_id=local_issue_id,
                github_number=github_id,
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

            matching_local_issue = self.backend._find_matching_local_issue(
                local_issue.title, github_id
            )
            updates = {
                "title": local_issue.title,
                "description": local_issue.content or "",
                "status": local_issue.status,
                "priority": local_issue.priority,
                "assignee": local_issue.assignee,
                "milestone": local_issue.milestone,
                "labels": local_issue.labels,
            }
            self.backend._apply_or_create_local_issue(
                local_issue.id,
                matching_local_issue,
                updates,
                github_id,
                remote_issue=sync_issue,
            )

            return True, None

        except Exception as e:
            log_error_with_context(
                e,
                operation="pull_issue",
                entity_type="Issue",
                entity_id=str(getattr(sync_issue, "backend_id", "unknown")),
                include_traceback=True,
            )
            error_msg = str(e)
            return self._handle_pull_error(sync_issue, error_msg)

    def pull_issues(self, issue_ids: list[str]) -> SyncReport:
        """Pull issues from GitHub backend by IDs with dependency resolution.

        This method now handles dependencies by:
        1. Fetching all milestones referenced by the requested issues
        2. Pulling those milestones first
        3. Then pulling the issues with proper milestone references

        Args:
            issue_ids: List of issue IDs to pull.

        Returns:
            Sync report with pull results and errors.
        """
        report = SyncReport()

        if not issue_ids:
            return report

        logger.info(
            "pull_issues_with_dependencies_starting", issue_count=len(issue_ids)
        )

        # Fetch all remote data
        all_remote_issues, all_remote_milestones = self._fetch_remote_data()

        # Analyze dependencies and build pull list
        issues_to_pull, milestones_needed, report = self._analyze_issue_dependencies(
            issue_ids, all_remote_issues, all_remote_milestones, report
        )

        # Phase 1: Pull milestones
        milestone_pull_report = self._pull_milestone_dependencies(milestones_needed)

        # Phase 2: Pull issues
        return self._pull_issues_phase(
            issues_to_pull,
            all_remote_milestones,
            milestone_pull_report,
            report,
        )

    def _fetch_remote_data(self) -> tuple[dict, dict]:
        """Fetch issues and milestones from GitHub."""
        from roadmap.adapters.sync.backends.services.github_issue_fetch_service import (
            GitHubIssueFetchService,
        )
        from roadmap.adapters.sync.backends.services.github_milestone_fetch_service import (
            GitHubMilestoneFetchService,
        )

        issue_fetch_service = GitHubIssueFetchService(
            self.backend.github_client,
            self.backend.config,
            self.backend._helpers,
        )
        all_remote_issues = issue_fetch_service.get_issues()

        milestone_fetch_service = GitHubMilestoneFetchService(
            self.backend.github_client,
            self.backend.config,
        )
        all_remote_milestones = milestone_fetch_service.get_milestones()

        return all_remote_issues, all_remote_milestones

    def _analyze_issue_dependencies(
        self,
        issue_ids: list[str],
        all_remote_issues: dict,
        all_remote_milestones: dict,
        report: SyncReport,
    ) -> tuple[list, set, SyncReport]:
        """Build list of issues to pull and their milestone dependencies."""
        issues_to_pull = []
        milestones_needed = set()

        for issue_id in issue_ids:
            # Strip _remote_ prefix if present
            lookup_id = issue_id[8:] if issue_id.startswith("_remote_") else issue_id

            if lookup_id not in all_remote_issues:
                report.errors[issue_id] = "Issue not found on remote"
                continue

            sync_issue = all_remote_issues[lookup_id]
            issues_to_pull.append((issue_id, lookup_id, sync_issue))

            # Check if issue references a milestone
            if sync_issue.milestone:
                for milestone_num, sync_milestone in all_remote_milestones.items():
                    if sync_milestone.name == sync_issue.milestone:
                        milestones_needed.add(milestone_num)
                        break

        logger.info(
            "dependency_analysis_complete",
            issues_requested=len(issue_ids),
            issues_found=len(issues_to_pull),
            milestones_needed=len(milestones_needed),
        )

        return issues_to_pull, milestones_needed, report

    def _pull_milestone_dependencies(self, milestones_needed: set) -> SyncReport:
        """Pull milestone dependencies first."""
        milestone_pull_report = SyncReport()
        if milestones_needed:
            logger.info("pulling_dependencies_milestones", count=len(milestones_needed))
            milestone_ids = list(milestones_needed)
            milestone_pull_report = self.pull_milestones(milestone_ids)

            if milestone_pull_report.errors:
                logger.warning(
                    "milestone_pull_failures",
                    failed_count=len(milestone_pull_report.errors),
                    errors=list(milestone_pull_report.errors.keys())[:5],
                )

        return milestone_pull_report

    def _pull_issues_phase(
        self,
        issues_to_pull: list,
        all_remote_milestones: dict,
        milestone_pull_report: SyncReport,
        report: SyncReport,
    ) -> SyncReport:
        """Pull issues after their dependencies are satisfied."""
        successful_pulls = []
        failed_pulls = {}

        logger.info("pulling_issues_phase", issue_count=len(issues_to_pull))

        for issue_id, _lookup_id, sync_issue in issues_to_pull:
            try:
                # Check if issue's milestone was successfully pulled
                if sync_issue.milestone:
                    milestone_num = self._find_milestone_number(
                        sync_issue.milestone, all_remote_milestones
                    )

                    if milestone_num and milestone_num in milestone_pull_report.errors:
                        failed_pulls[issue_id] = (
                            f"Milestone '{sync_issue.milestone}' pull failed: "
                            f"{milestone_pull_report.errors[milestone_num]}"
                        )
                        logger.debug(
                            "issue_skipped_milestone_failed",
                            issue_id=issue_id,
                            milestone=sync_issue.milestone,
                        )
                        continue

                # Pull the issue and create/update locally
                success, error = self._pull_single_issue(sync_issue)

                if success:
                    successful_pulls.append(issue_id)
                    logger.debug("pull_issue_processed", issue_id=issue_id)
                else:
                    failed_pulls[issue_id] = error or "Unknown error"

            except Exception as e:
                failed_pulls[issue_id] = str(e)
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
            milestones_pulled=len(milestone_pull_report.pulled)
            if hasattr(milestone_pull_report, "pulled")
            else 0,
            issues_successful=len(successful_pulls),
            issues_failed=len(failed_pulls),
        )

        return report

    def _find_milestone_number(
        self, milestone_name: str, all_remote_milestones: dict
    ) -> int | None:
        """Find milestone number by name."""
        for milestone_num, sync_milestone in all_remote_milestones.items():
            if sync_milestone.name == milestone_name:
                return milestone_num
        return None

    def pull_milestones(self, milestone_ids: list[str]) -> SyncReport:
        """Pull milestones from GitHub backend by IDs.

        Args:
            milestone_ids: List of milestone IDs to pull (GitHub milestone numbers as strings).

        Returns:
            Sync report with pull results and errors.
        """
        report = SyncReport()

        if not milestone_ids:
            return report

        logger.info("pull_milestones_starting", milestone_count=len(milestone_ids))

        # Fetch all remote milestones upfront
        from roadmap.adapters.sync.backends.services.github_milestone_fetch_service import (
            GitHubMilestoneFetchService,
        )

        try:
            fetch_service = GitHubMilestoneFetchService(
                self.backend.github_client,
                self.backend.config,
            )
            all_remote_milestones = fetch_service.get_milestones()

            successful_pulls = []
            failed_pulls = {}

            logger.info(
                "pull_milestones_keys_analysis",
                requested_sample=milestone_ids[:3] if milestone_ids else [],
                remote_keys_sample=list(all_remote_milestones.keys())[:3]
                if all_remote_milestones
                else [],
                requested_count=len(milestone_ids),
                remote_count=len(all_remote_milestones),
            )

            # Process each requested milestone and save locally
            for milestone_id in milestone_ids:
                try:
                    # Strip any prefix if present
                    lookup_id = milestone_id
                    if milestone_id.startswith("_remote_milestone_"):
                        lookup_id = milestone_id[18:]  # Remove prefix

                    if lookup_id not in all_remote_milestones:
                        error_msg = "Milestone not found on remote"
                        failed_pulls[milestone_id] = error_msg
                        logger.debug(
                            "pull_milestone_not_found",
                            milestone_id=milestone_id,
                            lookup_id=lookup_id,
                        )
                        continue

                    # Pull the milestone and create/update locally
                    sync_milestone = all_remote_milestones[lookup_id]
                    success, error = self._pull_single_milestone(sync_milestone)

                    if success:
                        successful_pulls.append(milestone_id)
                        logger.debug(
                            "pull_milestone_processed", milestone_id=milestone_id
                        )
                    else:
                        failed_pulls[milestone_id] = error or "Unknown error"

                except Exception as e:
                    error_msg = str(e)
                    failed_pulls[milestone_id] = error_msg
                    log_error_with_context(
                        e,
                        operation="pull_milestone",
                        entity_type="Milestone",
                        entity_id=milestone_id,
                        include_traceback=False,
                    )

            report.pulled = successful_pulls
            report.errors = failed_pulls

            logger.info(
                "pull_milestones_complete",
                successful=len(successful_pulls),
                failed=len(failed_pulls),
            )

            return report

        except Exception as e:
            logger.error(
                "pull_milestones_failed", error=str(e), error_type=type(e).__name__
            )
            report.error = f"Failed to pull milestones: {str(e)}"
            return report

    def _pull_single_milestone(self, sync_milestone) -> tuple[bool, str | None]:
        """Pull a single milestone and persist it locally.

        Args:
            sync_milestone: SyncMilestone object from GitHub

        Returns:
            Tuple of (success: bool, error_message: str | None)
        """
        try:
            # Create or update milestone locally
            if not hasattr(self.backend, "core") or not self.backend.core:
                return False, "Core not available"

            core = self.backend.core

            # Check if milestone already exists by GitHub milestone number
            github_milestone_num = sync_milestone.backend_id
            existing_milestone = None

            # Try to find existing milestone by name (GitHub milestone title)
            all_milestones = core.milestones.list()
            for ms in all_milestones:
                if ms.name == sync_milestone.name:
                    existing_milestone = ms
                    break

            if existing_milestone:
                # Update existing milestone
                logger.debug(
                    "milestone_exists_updating",
                    milestone_name=sync_milestone.name,
                    github_number=github_milestone_num,
                )

                # Update fields
                updates = {
                    "status": sync_milestone.status,
                    "due_date": sync_milestone.due_date,
                }

                if sync_milestone.headline:
                    updates["headline"] = sync_milestone.headline

                success = core.milestones.update(existing_milestone.name, **updates)

                if not success:
                    return False, "Failed to update milestone"

                # Store GitHub milestone number in database metadata
                self._link_milestone_to_github(
                    existing_milestone.name, github_milestone_num
                )

            else:
                # Create new milestone
                logger.debug(
                    "milestone_creating_new",
                    milestone_name=sync_milestone.name,
                    github_number=github_milestone_num,
                )

                milestone = core.milestones.create(
                    name=sync_milestone.name,
                    headline=sync_milestone.headline or "",
                    due_date=sync_milestone.due_date,
                    status=sync_milestone.status,
                )

                # Store GitHub milestone number in database metadata
                self._link_milestone_to_github(milestone.name, github_milestone_num)

            logger.info(
                "milestone_pulled_successfully",
                milestone_name=sync_milestone.name,
                github_number=github_milestone_num,
            )

            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "pull_single_milestone_failed",
                milestone_name=sync_milestone.name,
                error=error_msg,
                error_type=type(e).__name__,
            )
            return False, error_msg

    def _link_milestone_to_github(
        self, milestone_name: str, github_milestone_number: int
    ) -> bool:
        """Link milestone to GitHub milestone number by updating the milestone.

        Args:
            milestone_name: Local milestone name
            github_milestone_number: GitHub milestone number

        Returns:
            True if successful, False otherwise
        """
        try:
            if not hasattr(self.backend, "core") or not self.backend.core:
                return False

            # Get the milestone using the service layer
            milestone = self.backend.core.milestone_service.get_milestone(
                milestone_name
            )
            if not milestone:
                logger.debug(
                    "milestone_not_found_for_linking",
                    milestone_name=milestone_name,
                )
                return False

            # Update the milestone's github_milestone field directly
            milestone.github_milestone = github_milestone_number
            milestone.updated = now_utc()

            # Save the updated milestone using the repository
            self.backend.core.milestone_service.repository.save(milestone)

            logger.debug(
                "milestone_linked_to_github",
                milestone_name=milestone_name,
                github_number=github_milestone_number,
            )
            return True

        except Exception as e:
            logger.warning(
                "failed_to_link_milestone",
                milestone_name=milestone_name,
                github_number=github_milestone_number,
                error=str(e),
            )
            return False

    def push_milestones(self, local_milestones: list) -> SyncReport:
        """Push multiple local milestones to GitHub.

        Args:
            local_milestones: List of Milestone objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.
        """
        report = SyncReport()

        if not local_milestones:
            return report

        logger.info("push_milestones_starting", milestone_count=len(local_milestones))

        # For now, milestone pushing is not implemented
        # GitHub milestones would need to be created via the API
        # This is a placeholder for future implementation

        for milestone in local_milestones:
            report.errors[milestone.name] = "Milestone pushing not yet implemented"

        logger.warning(
            "push_milestones_not_implemented",
            milestone_count=len(local_milestones),
        )

        return report
