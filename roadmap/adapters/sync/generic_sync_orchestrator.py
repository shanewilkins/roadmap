"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

from structlog import get_logger

from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.services.sync_conflict_resolver import (
    ConflictStrategy,
    SyncConflictResolver,
)
from roadmap.core.services.sync_report import SyncReport
from roadmap.core.services.sync_state_comparator import SyncStateComparator
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class GenericSyncOrchestrator:
    """Orchestrates sync using a pluggable backend implementation."""

    def __init__(
        self,
        core: RoadmapCore,
        backend: SyncBackendInterface,
        state_comparator: SyncStateComparator | None = None,
        conflict_resolver: SyncConflictResolver | None = None,
    ):
        """Initialize orchestrator with core services and backend.

        Args:
            core: RoadmapCore instance with access to issues
            backend: SyncBackendInterface implementation (GitHub, vanilla Git, etc.)
            state_comparator: SyncStateComparator for detecting changes (optional, creates default)
            conflict_resolver: SyncConflictResolver for resolving conflicts (optional, creates default)
        """
        self.core = core
        self.backend = backend
        self.state_comparator = state_comparator or SyncStateComparator()
        self.conflict_resolver = conflict_resolver or SyncConflictResolver()

    def sync_all_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_remote: bool = False,
    ) -> SyncReport:
        """Sync all issues using the configured backend.

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_remote: Resolve conflicts by keeping remote changes

        Returns:
            SyncReport with detected changes and conflicts
        """
        report = SyncReport()

        try:
            logger.info(
                "sync_all_issues_started",
                dry_run=dry_run,
                force_local=force_local,
                force_remote=force_remote,
            )

            # 1. Authenticate with backend
            if not self.backend.authenticate():
                report.error = "Backend authentication failed"
                logger.error("backend_authentication_failed")
                return report

            # 2. Get remote issues (dict format)
            remote_issues_data = self.backend.get_issues()
            if remote_issues_data is None:
                report.error = "Failed to fetch remote issues"
                logger.error("failed_to_fetch_remote_issues")
                return report

            # 3. Get local issues
            local_issues = self.core.issues.list()
            if not local_issues:
                local_issues = []

            # Convert to dict for comparator
            local_issues_dict = {issue.id: issue for issue in local_issues}

            logger.debug(
                "sync_state_detected",
                local_count=len(local_issues_dict),
                remote_count=len(remote_issues_data),
            )

            # 4. Use state comparator to identify changes
            conflicts = self.state_comparator.identify_conflicts(
                local_issues_dict, remote_issues_data
            )
            updates = self.state_comparator.identify_updates(
                local_issues_dict, remote_issues_data
            )
            pulls = self.state_comparator.identify_pulls(
                local_issues_dict, remote_issues_data
            )
            up_to_date = self.state_comparator.identify_up_to_date(
                local_issues_dict, remote_issues_data
            )

            logger.debug(
                "sync_analysis_complete",
                conflicts=len(conflicts),
                updates=len(updates),
                pulls=len(pulls),
                up_to_date=len(up_to_date),
            )

            # Filter out conflicted issues from updates list
            # A conflict should be resolved, not treated as a simple update
            conflict_ids = {c.issue_id for c in conflicts}
            updates_filtered = [u for u in updates if u.id not in conflict_ids]

            logger.debug(
                "updates_filtered",
                original_count=len(updates),
                filtered_count=len(updates_filtered),
                conflicts_removed=len(conflict_ids),
            )

            # 5. Report findings
            report.conflicts_detected = len(conflicts)
            report.issues_updated = len(updates_filtered)
            report.issues_up_to_date = len(up_to_date)

            # 6. Resolve conflicts if applicable
            resolved_issues = []
            if conflicts:
                logger.info(
                    "resolving_conflicts_start",
                    conflict_count=len(conflicts),
                )
                strategy = (
                    ConflictStrategy.KEEP_LOCAL
                    if force_local
                    else ConflictStrategy.KEEP_REMOTE
                    if force_remote
                    else ConflictStrategy.AUTO_MERGE
                )
                try:
                    resolved_issues = self.conflict_resolver.resolve_batch(
                        conflicts, strategy
                    )
                    logger.info(
                        "conflicts_resolved",
                        count=len(resolved_issues),
                        strategy=strategy.value,
                    )

                except Exception as e:
                    logger.warning(
                        "conflicts_resolution_failed",
                        error=str(e),
                        strategy=strategy.value,
                        exc_info=True,
                    )
                    resolved_issues = []

            # 7. Apply changes if not dry-run
            updates_count = len(updates_filtered)
            resolved_count = len(resolved_issues)
            pulls_count = len(pulls)
            should_apply = not dry_run and bool(
                updates_filtered or resolved_issues or pulls
            )

            logger.info(
                "applying_changes_check",
                dry_run=dry_run,
                updates_count=updates_count,
                resolved_count=resolved_count,
                pulls_count=pulls_count,
                condition_result=should_apply,
            )

            if should_apply:
                report = self._apply_changes(
                    report, updates_filtered, resolved_issues, pulls
                )
            elif dry_run:
                logger.info("sync_dry_run_mode", skip_apply=True)

            logger.info("sync_all_issues_completed", error=report.error)
            return report

        except Exception as e:
            report.error = str(e)
            logger.exception("sync_all_issues_failed", error=str(e))
            return report

    def _apply_changes(
        self,
        report: SyncReport,
        updates: list,
        resolved_issues: list,
        pulls: list,
    ) -> SyncReport:
        """Apply detected changes using the backend.

        Args:
            report: SyncReport to update
            updates: Issues to push (local updates)
            resolved_issues: Issues resolved from conflicts
            pulls: Issues to pull (remote updates)

        Returns:
            Updated SyncReport with applied changes
        """
        logger.debug(
            "applying_changes",
            updates=len(updates),
            resolved=len(resolved_issues),
            pulls=len(pulls),
        )

        try:
            # Push local updates and resolved conflicts
            issues_to_push = updates + resolved_issues
            if issues_to_push:
                issue_ids = [issue.id for issue in issues_to_push]
                logger.info(
                    "pushing_issues", count=len(issue_ids), ids_str=",".join(issue_ids)
                )
                if len(issues_to_push) == 1:
                    success = self.backend.push_issue(issues_to_push[0])
                    if not success:
                        report.error = "Failed to push issue"
                        logger.warning(
                            "push_issue_failed", issue_id=issues_to_push[0].id
                        )
                else:
                    push_report = self.backend.push_issues(issues_to_push)
                    if push_report and push_report.errors:
                        report.error = f"Push failed: {push_report.errors}"
                        logger.warning(
                            "push_issues_failed", error_count=len(push_report.errors)
                        )

            # Pull remote updates
            if pulls:
                for pull_issue_id in pulls:
                    success = self.backend.pull_issue(pull_issue_id)
                    if not success:
                        logger.warning("pull_issue_failed", issue_id=pull_issue_id)

            logger.info(
                "changes_applied", pushed=len(issues_to_push), pulled=len(pulls)
            )
            return report

        except Exception as e:
            report.error = f"Error applying changes: {str(e)}"
            logger.exception("apply_changes_failed", error=str(e))
            return report
