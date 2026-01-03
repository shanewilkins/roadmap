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
from roadmap.core.services.sync_state_manager import SyncStateManager
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
        self.state_manager = SyncStateManager(core.roadmap_dir)

    def _filter_unchanged_issues_from_base(
        self,
        issues: list,
        current_local: dict,
        base_state_issues: dict,
    ) -> list:
        """Filter local issues that haven't actually changed from base state.

        Only returns issues that have changed locally since the last sync.
        This prevents pushing issues that haven't been modified.

        Args:
            issues: List of Issue objects detected as needing push
            current_local: Current local issues dict (id -> Issue)
            base_state_issues: Base state from last sync (id -> IssueBaseState)

        Returns:
            Filtered list containing only locally changed issues
        """
        if not base_state_issues:
            # No base state, include everything
            logger.debug(
                "filter_no_base_state",
                input_count=len(issues),
                reason="first_sync_no_previous_state",
            )
            return issues

        filtered = []
        skipped_count = 0
        new_count = 0
        changed_count = 0

        for issue in issues:
            issue_id = issue.id if hasattr(issue, "id") else issue

            # If not in current local, skip it
            if issue_id not in current_local:
                logger.debug(
                    "filter_issue_not_in_local",
                    issue_id=issue_id,
                    reason="might_be_stale",
                )
                continue

            # If not in base state, it's new - include it
            if issue_id not in base_state_issues:
                logger.debug(
                    "filter_new_local_issue",
                    issue_id=issue_id,
                    reason="not_in_previous_sync",
                )
                new_count += 1
                filtered.append(issue)
                continue

            local_issue = current_local[issue_id]
            base_state = base_state_issues[issue_id]

            # Compare local issue with base state
            # If they match, the issue hasn't changed locally - skip it
            # NOTE: Only compare fields that are actually stored in IssueBaseState
            # Title is intentionally excluded as it's display metadata
            fields_to_check = {
                "status": lambda obj: obj.status.value
                if hasattr(obj.status, "value")
                else str(obj.status),
                "assignee": lambda obj: obj.assignee,
                "content": lambda obj: obj.content,
                "labels": lambda obj: sorted(obj.labels or []),
            }

            has_local_changes = False
            changed_fields = []

            for field_name, getter in fields_to_check.items():
                try:
                    local_value = getter(local_issue)
                except Exception as e:
                    logger.warning(
                        "filter_field_extraction_failed",
                        issue_id=issue_id,
                        field=field_name,
                        error=str(e),
                    )
                    local_value = None

                # Get base value - map field names appropriately
                if field_name == "content":
                    base_value = base_state.description
                else:
                    base_value = getattr(base_state, field_name, None)

                if local_value != base_value:
                    logger.debug(
                        "filter_local_change_detected",
                        issue_id=issue_id,
                        field=field_name,
                        base_value=base_value,
                        local_value=local_value,
                    )
                    changed_fields.append(field_name)
                    has_local_changes = True

            if has_local_changes:
                logger.debug(
                    "filter_issue_has_local_changes",
                    issue_id=issue_id,
                    changed_fields=changed_fields,
                )
                changed_count += 1
                filtered.append(issue)
            else:
                logger.debug(
                    "filter_issue_unchanged_since_sync",
                    issue_id=issue_id,
                    reason="no_local_modifications",
                )
                skipped_count += 1

        logger.info(
            "filter_complete",
            input_count=len(issues),
            output_count=len(filtered),
            skipped_count=skipped_count,
            new_count=new_count,
            changed_count=changed_count,
            filtered_out_percentage=round((skipped_count / len(issues) * 100), 1)
            if len(issues) > 0
            else 0,
        )
        return filtered

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
                "sync_all_issues_starting",
                dry_run=dry_run,
                force_local=force_local,
                force_remote=force_remote,
                sync_mode="analysis" if dry_run else "apply",
            )

            # 1. Authenticate with backend
            try:
                if not self.backend.authenticate():
                    report.error = "Backend authentication failed"
                    logger.error(
                        "backend_authentication_failed",
                        backend_type=type(self.backend).__name__,
                    )
                    return report
                logger.info("backend_authenticated_successfully")
            except Exception as e:
                report.error = f"Backend authentication error: {str(e)}"
                logger.error(
                    "backend_authentication_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return report

            # 2. Get remote issues (dict format)
            try:
                logger.debug("fetching_remote_issues")
                remote_issues_data = self.backend.get_issues()
                if remote_issues_data is None:
                    report.error = "Failed to fetch remote issues"
                    logger.error("remote_issues_fetch_returned_none")
                    return report
                logger.info(
                    "remote_issues_fetched",
                    remote_count=len(remote_issues_data),
                )
            except Exception as e:
                report.error = f"Failed to fetch remote issues: {str(e)}"
                logger.error(
                    "remote_issues_fetch_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return report

            # 3. Get local issues
            try:
                logger.debug("fetching_local_issues")
                local_issues = self.core.issues.list()
                if not local_issues:
                    local_issues = []
                logger.info(
                    "local_issues_fetched",
                    local_count=len(local_issues),
                )
            except Exception as e:
                report.error = f"Failed to fetch local issues: {str(e)}"
                logger.error(
                    "local_issues_fetch_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return report

            # Convert to dict for comparator
            local_issues_dict = {issue.id: issue for issue in local_issues}

            logger.info(
                "sync_state_detected",
                local_count=len(local_issues_dict),
                remote_count=len(remote_issues_data),
            )

            # 4. Load previous sync state (base state for three-way merge)
            try:
                logger.debug("loading_sync_state")
                base_state = self.state_manager.load_sync_state()
                if base_state:
                    logger.info(
                        "previous_sync_state_loaded",
                        base_issues_count=len(base_state.issues),
                        last_sync=base_state.last_sync.isoformat()
                        if base_state.last_sync
                        else None,
                    )
                else:
                    logger.info(
                        "no_previous_sync_state_found",
                        reason="first_sync_or_state_cleared",
                    )
            except Exception as e:
                logger.warning(
                    "sync_state_load_warning",
                    error=str(e),
                    reason="will_treat_as_first_sync",
                )
                base_state = None

            # 4. Use state comparator to identify changes
            # The comparator compares local vs remote, but we need to be smarter:
            # - If an issue hasn't changed locally AND hasn't changed remotely
            #   since the base state, it's truly up-to-date
            # - If it changed only locally, it needs to be pushed
            # - If it changed only remotely, it needs to be pulled
            # - If it changed both ways, it's a conflict

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

            # Filter out issues that are truly unchanged since last sync
            # Only include issues that have actually changed from the base state
            if base_state:
                # For updates: only push if local has changed since last sync
                updates = self._filter_unchanged_issues_from_base(
                    updates, local_issues_dict, base_state.issues
                )
                # For pulls: only pull if remote has changed since last sync
                # This is trickier because we need to compare remote format with base state
                # For now, we'll include all pulls (the backend will handle deduplication)
                # A future optimization could cache remote state too

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
        logger.info(
            "applying_changes_starting",
            updates=len(updates),
            resolved=len(resolved_issues),
            pulls=len(pulls),
        )

        pushed_count = 0
        pulled_count = 0
        push_errors = []
        pull_errors = []

        try:
            # Push local updates and resolved conflicts
            issues_to_push = updates + resolved_issues
            if issues_to_push:
                issue_ids = [issue.id for issue in issues_to_push]
                logger.info(
                    "pushing_issues_start",
                    count=len(issue_ids),
                    ids=",".join(issue_ids[:5]),  # Log first 5 IDs for debugging
                    total_ids=len(issue_ids),
                )

                try:
                    if len(issues_to_push) == 1:
                        issue = issues_to_push[0]
                        logger.debug(
                            "pushing_single_issue",
                            issue_id=issue.id,
                            issue_title=issue.title[:50],
                        )
                        success = self.backend.push_issue(issue)
                        if not success:
                            report.error = "Failed to push issue"
                            logger.error(
                                "push_single_issue_failed",
                                issue_id=issue.id,
                                issue_title=issue.title,
                            )
                            push_errors.append(issue.id)
                        else:
                            # Update sync state for successfully pushed issue
                            try:
                                self.state_manager.save_base_state(
                                    issue, remote_version=True
                                )
                                pushed_count = 1
                                logger.debug(
                                    "single_issue_sync_state_updated",
                                    issue_id=issue.id,
                                )
                            except Exception as e:
                                logger.warning(
                                    "single_issue_state_update_failed",
                                    issue_id=issue.id,
                                    error=str(e),
                                )
                    else:
                        logger.debug(
                            "pushing_batch_issues",
                            batch_size=len(issues_to_push),
                        )
                        push_report = self.backend.push_issues(issues_to_push)
                        if push_report and push_report.errors:
                            report.error = f"Push failed: {push_report.errors}"
                            logger.error(
                                "push_batch_failed",
                                error_count=len(push_report.errors),
                                errors=str(push_report.errors)[:200],
                            )
                            push_errors = list(push_report.errors.keys())
                        else:
                            # Update sync state for all successfully pushed issues
                            state_update_failures = 0
                            for issue in issues_to_push:
                                try:
                                    self.state_manager.save_base_state(
                                        issue, remote_version=True
                                    )
                                    pushed_count += 1
                                except Exception as e:
                                    logger.warning(
                                        "batch_issue_state_update_failed",
                                        issue_id=issue.id,
                                        error=str(e),
                                    )
                                    state_update_failures += 1

                            logger.info(
                                "batch_issues_pushed",
                                pushed_count=pushed_count,
                                state_update_failures=state_update_failures,
                            )
                except Exception as e:
                    report.error = f"Error during push operation: {str(e)}"
                    logger.error(
                        "push_operation_exception",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    pushed_count = 0

            # Pull remote updates
            if pulls:
                logger.info(
                    "pulling_remote_updates_start",
                    count=len(pulls),
                )
                try:
                    successful_pulls = 0
                    failed_pulls = 0
                    for pull_issue_id in pulls:
                        try:
                            logger.debug(
                                "pulling_single_issue",
                                issue_id=pull_issue_id,
                            )
                            success = self.backend.pull_issue(pull_issue_id)
                            if not success:
                                logger.warning(
                                    "pull_single_issue_failed",
                                    issue_id=pull_issue_id,
                                )
                                pull_errors.append(pull_issue_id)
                                failed_pulls += 1
                            else:
                                successful_pulls += 1
                        except Exception as e:
                            logger.warning(
                                "pull_issue_exception",
                                issue_id=pull_issue_id,
                                error=str(e),
                                error_type=type(e).__name__,
                            )
                            pull_errors.append(pull_issue_id)
                            failed_pulls += 1

                    pulled_count = successful_pulls
                    logger.info(
                        "pulling_complete",
                        successful_count=successful_pulls,
                        failed_count=failed_pulls,
                    )
                except Exception as e:
                    report.error = f"Error during pull operation: {str(e)}"
                    logger.error(
                        "pull_operation_exception",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    pulled_count = 0

            report.issues_pushed = pushed_count
            report.issues_pulled = pulled_count

            logger.info(
                "changes_applied_complete",
                pushed=pushed_count,
                pulled=pulled_count,
                push_errors=len(push_errors),
                pull_errors=len(pull_errors),
            )
            return report

        except Exception as e:
            report.error = f"Error applying changes: {str(e)}"
            logger.exception(
                "apply_changes_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return report
