"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

from structlog import get_logger

from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.services.sync_conflict_resolver import (
    Conflict,
    ConflictField,
    ConflictStrategy,
    SyncConflictResolver,
)
from roadmap.core.services.sync_report import SyncReport
from roadmap.core.services.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync_state_manager import SyncStateManager
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class SyncMergeOrchestrator:
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
        # Pass backend to comparator for key normalization
        self.state_comparator = state_comparator or SyncStateComparator(backend=backend)
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

    def _convert_issue_changes_to_conflicts(
        self,
        issue_changes: list,
    ) -> list[Conflict]:
        """Convert three-way IssueChange objects to Conflict objects.

        For compatibility with the existing conflict resolver,
        converts the new IssueChange format to the legacy Conflict format.

        Args:
            issue_changes: List of IssueChange objects with conflicts

        Returns:
            List of Conflict objects
        """
        conflicts = []

        for change in issue_changes:
            if (
                not change.has_conflict
                or not change.local_state
                or not change.remote_state
            ):
                continue

            try:
                # Build list of conflicting fields
                conflicting_fields = []

                # Check each field in local_changes
                if change.local_changes:
                    for field_name, _change_info in change.local_changes.items():
                        # Only include if also changed in remote (true conflict)
                        if field_name in change.remote_changes:
                            conflict_field = ConflictField(
                                field_name=field_name,
                                local_value=change.local_state.__dict__.get(
                                    field_name.replace("status", "status").replace(
                                        "content", "content"
                                    ),
                                    None,
                                ),
                                remote_value=change.remote_state.get(field_name),
                                local_updated=change.local_state.updated,
                                remote_updated=self.state_comparator._extract_timestamp(
                                    change.remote_state, "updated_at"
                                ),
                            )
                            conflicting_fields.append(conflict_field)

                if conflicting_fields:
                    conflict = Conflict(
                        issue_id=change.issue_id,
                        local_issue=change.local_state,
                        remote_issue=change.remote_state,
                        fields=conflicting_fields,
                        local_updated=change.local_state.updated,
                        remote_updated=self.state_comparator._extract_timestamp(
                            change.remote_state, "updated_at"
                        ),
                    )
                    conflicts.append(conflict)

            except Exception as e:
                logger.warning(
                    "conflict_conversion_failed",
                    issue_id=change.issue_id,
                    error=str(e),
                )
                continue

        return conflicts

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

            # Count active vs archived issues based on file_path
            active_issues_count = 0
            archived_issues_count = 0
            for issue in local_issues:
                if issue.file_path and "archive" in issue.file_path:
                    archived_issues_count += 1
                else:
                    active_issues_count += 1

            # Count active vs archived milestones
            try:
                all_milestones = self.core.milestones.list()
                active_milestones_count = 0
                archived_milestones_count = 0
                for milestone in all_milestones:
                    if (
                        hasattr(milestone, "file_path")
                        and milestone.file_path
                        and "archive" in milestone.file_path
                    ):
                        archived_milestones_count += 1
                    else:
                        active_milestones_count += 1
            except Exception as e:
                logger.debug("milestone_count_failed", error=str(e))
                all_milestones = []
                active_milestones_count = 0
                archived_milestones_count = 0

            # Count remote issues and milestones
            try:
                remote_issues_count = (
                    len(remote_issues_data) if remote_issues_data else 0
                )
                # Try to fetch remote milestones
                remote_milestones = self.backend.get_milestones()
                remote_milestones_count = (
                    len(remote_milestones) if remote_milestones else 0
                )
                logger.debug(
                    "remote_items_counted",
                    remote_issues=remote_issues_count,
                    remote_milestones=remote_milestones_count,
                )
            except Exception as e:
                logger.debug("remote_items_count_failed", error=str(e))
                remote_issues_count = 0
                remote_milestones_count = 0

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

            # 4. Use state comparator for three-way merge analysis
            # The NEW comparator provides complete baseline context:
            # - baseline_state: state from last sync
            # - local_state: current local state
            # - remote_state: current remote state
            # - local_changes: what changed locally since baseline
            # - remote_changes: what changed remotely since baseline
            # This gives us the complete picture for intelligent merging

            changes = self.state_comparator.analyze_three_way(
                local_issues_dict,
                remote_issues_data,
                base_state.issues if base_state else None,
            )

            logger.debug(
                "three_way_analysis_complete",
                total_changes=len(changes),
                conflicts=len([c for c in changes if c.has_conflict]),
                local_only=len([c for c in changes if c.is_local_only_change()]),
                remote_only=len([c for c in changes if c.is_remote_only_change()]),
                no_change=len([c for c in changes if c.conflict_type == "no_change"]),
            )

            # Extract different change types from the three-way analysis
            conflicts = [c for c in changes if c.has_conflict]
            local_only_changes = [c for c in changes if c.is_local_only_change()]
            remote_only_changes = [c for c in changes if c.is_remote_only_change()]
            no_changes = [c for c in changes if c.conflict_type == "no_change"]

            # Build updates list (local-only changes that need pushing)
            updates = [c.local_state for c in local_only_changes if c.local_state]

            # Build pulls list (remote-only changes that need pulling)
            pulls = [c.issue_id for c in remote_only_changes]

            # Up-to-date issues (no changes in either direction)
            up_to_date = [c.issue_id for c in no_changes]

            logger.debug(
                "sync_analysis_complete",
                conflicts=len(conflicts),
                updates=len(updates),
                pulls=len(pulls),
                up_to_date=len(up_to_date),
            )

            # 5. Report findings
            report.total_issues = len(local_issues)
            report.active_issues = active_issues_count
            report.archived_issues = archived_issues_count
            report.total_milestones = len(all_milestones)
            report.active_milestones = active_milestones_count
            report.archived_milestones = archived_milestones_count
            report.remote_total_issues = remote_issues_count
            report.remote_total_milestones = remote_milestones_count
            report.conflicts_detected = len(conflicts)
            report.issues_up_to_date = len(up_to_date)
            report.issues_needs_push = len(local_only_changes)
            report.issues_needs_pull = len(remote_only_changes)

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
                    # Convert IssueChange conflicts to Conflict objects for resolver
                    conflict_objects = self._convert_issue_changes_to_conflicts(
                        conflicts
                    )
                    resolved_issues = self.conflict_resolver.resolve_batch(
                        conflict_objects, strategy
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
            updates_count = len(updates)
            resolved_count = len(resolved_issues)
            pulls_count = len(pulls)
            should_apply = not dry_run and bool(updates or resolved_issues or pulls)

            logger.info(
                "applying_changes_check",
                dry_run=dry_run,
                updates_count=updates_count,
                resolved_count=resolved_count,
                pulls_count=pulls_count,
                condition_result=should_apply,
            )

            if should_apply:
                report = self._apply_changes(report, updates, resolved_issues, pulls)
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
