"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

from typing import Any

from structlog import get_logger

from roadmap.adapters.sync.sync_merge_engine import SyncMergeEngine
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync_conflict_resolver import (
    Conflict,
    SyncConflictResolver,
)
from roadmap.core.services.sync_plan import (
    PullAction,
    PushAction,
    ResolveConflictAction,
    SyncPlan,
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
        # Extraction: delegate helper implementations to a dedicated engine
        self._engine = SyncMergeEngine(
            core=self.core,
            backend=self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
            state_manager=self.state_manager,
        )

    # Helper extraction to reduce complexity of sync_all_issues
    def _ensure_authenticated(self, report: SyncReport) -> bool:
        try:
            if not self.backend.authenticate():
                report.error = "Backend authentication failed"
                logger.error(
                    "backend_authentication_failed",
                    operation="authenticate",
                    backend_type=type(self.backend).__name__,
                    suggested_action="check_credentials",
                )
                return False
            logger.info("backend_authenticated_successfully")
            return True
        except (ConnectionError, TimeoutError) as e:
            report.error = f"Backend authentication error: {str(e)}"
            logger.error(
                "backend_authentication_error",
                operation="authenticate",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="retry_connection",
            )
            return False
        except Exception as e:
            report.error = f"Backend authentication error: {str(e)}"
            logger.error(
                "backend_authentication_error",
                operation="authenticate",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_backend_status",
            )
            return False

    def _fetch_remote_issues(self, report: SyncReport):
        try:
            logger.debug("fetching_remote_issues")
            remote_issues_data = self.backend.get_issues()
            if remote_issues_data is None:
                report.error = "Failed to fetch remote issues"
                logger.error(
                    "remote_issues_fetch_returned_none",
                    operation="fetch_remote_issues",
                    suggested_action="check_backend_connectivity",
                )
                return None
            logger.info("remote_issues_fetched", remote_count=len(remote_issues_data))
            return remote_issues_data
        except (ConnectionError, TimeoutError) as e:
            report.error = f"Failed to fetch remote issues: {str(e)}"
            logger.error(
                "remote_issues_fetch_error",
                operation="fetch_remote_issues",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="retry_after_delay",
            )
            return None
        except Exception as e:
            report.error = f"Failed to fetch remote issues: {str(e)}"
            logger.error(
                "remote_issues_fetch_error",
                operation="fetch_remote_issues",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_backend_configuration",
            )
            return None

    def _fetch_local_issues(self, report: SyncReport):
        try:
            logger.debug("fetching_local_issues")
            local_issues = self.core.issues.list_all_including_archived() or []
            logger.info("local_issues_fetched", local_count=len(local_issues))
            return local_issues
        except OSError as e:
            report.error = f"Failed to fetch local issues: {str(e)}"
            logger.error(
                "local_issues_fetch_error",
                operation="fetch_local_issues",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_file_permissions",
            )
            return None
        except Exception as e:
            report.error = f"Failed to fetch local issues: {str(e)}"
            logger.error(
                "local_issues_fetch_error",
                operation="fetch_local_issues",
                error_type=type(e).__name__,
                error=str(e),
                error_classification="sync_error",
            )
            return None

    def _count_active_archived(self, local_issues):
        active_issues_count = 0
        archived_issues_count = 0
        for issue in local_issues:
            if issue.file_path and "archive" in issue.file_path:
                archived_issues_count += 1
            else:
                active_issues_count += 1
        return active_issues_count, archived_issues_count

    def _count_milestones(self):
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
            return all_milestones, active_milestones_count, archived_milestones_count
        except Exception as e:
            logger.debug("milestone_count_failed", error=str(e))
            return [], 0, 0

    def _analyze_changes(self, local_issues_dict, remote_issues_data, base_state):
        return self._engine._analyze_changes(
            local_issues_dict, remote_issues_data, base_state
        )

    def _resolve_conflicts_if_needed(self, conflicts, force_local, force_remote):
        return self._engine._resolve_conflicts_if_needed(
            conflicts, force_local, force_remote
        )

    def _apply_plan(
        self,
        updates,
        resolved_issues,
        pulls,
        dry_run,
        push_only,
        pull_only,
        report: SyncReport,
    ):
        return self._engine._apply_plan(
            updates, resolved_issues, pulls, dry_run, push_only, pull_only, report
        )

    def _push_updates(self, issues_to_push: list, report: SyncReport):
        return self._engine._push_updates(issues_to_push, report)

    def _pull_updates(self, pulls: list):
        return self._engine._pull_updates(pulls)

    def _load_baseline_state(self):
        """Load baseline state from database with fallback to manager.

        Returns:
            SyncState from database, or None if not found
        """
        return self._engine._load_baseline_state()

    def _process_fetched_pull_result(self, fetched):
        return self._engine._process_fetched_pull_result(fetched)

    def _update_baseline_for_pulled(self, pulled_remote_ids: list[str]) -> None:
        return self._engine._update_baseline_for_pulled(pulled_remote_ids)

    def analyze_all_issues(
        self,
        push_only: bool = False,
        pull_only: bool = False,
    ) -> tuple[SyncPlan, SyncReport]:
        """Pure analysis pass that returns a SyncPlan and SyncReport without side-effects.

        This method performs authentication and data retrieval (reads only),
        runs the three-way analysis, and converts the result into a list of
        `Action`s bundled into a `SyncPlan`. No database or file writes are
        performed here — actions are merely declared for an Executor to apply.
        """
        report = SyncReport()
        plan = SyncPlan()

        try:
            # Helper: authenticate and fetch remote issues
            def _auth_and_fetch_remote():
                try:
                    if not self.backend.authenticate():
                        report.error = "Backend authentication failed"
                        return None
                except Exception as e:
                    report.error = f"Backend authentication error: {str(e)}"
                    return None

                try:
                    return self.backend.get_issues() or {}
                except Exception as e:
                    report.error = f"Failed to fetch remote issues: {str(e)}"
                    return None

            # Helper: fetch local issues safely
            def _fetch_local_safe():
                try:
                    return self.core.issues.list_all_including_archived() or []
                except Exception as e:
                    report.error = f"Failed to fetch local issues: {str(e)}"
                    return None

            remote_issues_data = _auth_and_fetch_remote()
            if remote_issues_data is None:
                return plan, report

            local_issues = _fetch_local_safe()
            if local_issues is None:
                return plan, report

            local_issues_dict = {issue.id: issue for issue in local_issues}

            # Load baseline (read-only)
            try:
                base_state = self._load_baseline_state()
            except Exception:
                base_state = None

            # Helper: run comparator and classify changes
            def _run_analysis(local_dict, remote_data, base_state):
                changes = self.state_comparator.analyze_three_way(
                    local_dict, remote_data, base_state.issues if base_state else None
                )
                conflicts = [c for c in changes if c.has_conflict]
                local_only_changes = [c for c in changes if c.is_local_only_change()]
                remote_only_changes = [c for c in changes if c.is_remote_only_change()]
                no_changes = [c for c in changes if c.conflict_type == "no_change"]
                return (
                    changes,
                    conflicts,
                    local_only_changes,
                    remote_only_changes,
                    no_changes,
                )

            (
                changes,
                conflicts,
                local_only_changes,
                remote_only_changes,
                no_changes,
            ) = _run_analysis(local_issues_dict, remote_issues_data, base_state)

            # Helper: build a plan from classified changes
            def _build_plan_from_changes(
                changes, local_only_changes, remote_only_changes, conflicts
            ):
                local_plan = SyncPlan()
                if not pull_only:
                    for c in local_only_changes:
                        if c.local_state:
                            local_plan.add(
                                PushAction(
                                    issue_id=c.issue_id,
                                    issue_payload=c.local_state.__dict__,
                                )
                            )
                if not push_only:
                    for c in remote_only_changes:
                        local_plan.add(
                            PullAction(
                                issue_id=c.issue_id,
                                remote_payload=c.remote_state
                                if hasattr(c, "remote_state")
                                else {},
                            )
                        )
                for c in conflicts:
                    local_plan.add(
                        ResolveConflictAction(
                            issue_id=c.issue_id,
                            resolution={"conflict_fields": c.local_changes or {}},
                        )
                    )
                return local_plan

            plan = _build_plan_from_changes(
                changes, local_only_changes, remote_only_changes, conflicts
            )

            # Fill report metadata similar to existing sync flow
            report.total_issues = len(local_issues)
            report.conflicts_detected = len(conflicts)
            report.issues_up_to_date = len(no_changes)
            report.issues_needs_push = len(local_only_changes)
            report.issues_needs_pull = len(remote_only_changes)
            report.changes = changes

            return plan, report

        except Exception as e:
            report.error = str(e)
            return plan, report

    def _filter_unchanged_issues_from_base(
        self,
        issues: list,
        *_args,
        **_kwargs,
    ) -> list:
        # This helper was removed during refactor: filtering of unchanged
        # issues is now performed inside the `SyncStateComparator` analysis
        # pipeline. Kept as a no-op for backward compatibility in case of
        # external callers expecting the method to exist.
        return issues

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
        return self._engine._convert_issue_changes_to_conflicts(issue_changes)

    def _create_issue_from_remote(
        self, remote_id: str | int, remote_issue: SyncIssue
    ) -> Issue:
        """Create a local Issue from remote SyncIssue data.

        Extracts relevant fields from remote issue and creates a local Issue object.
        Adds "synced:from-github" label to mark as synced from remote.
        Uses remote milestone if available, otherwise defaults to backlog.

        Args:
            remote_id: Remote issue ID (number)
            remote_issue: SyncIssue object with remote data including:
                - title: Issue title
                - headline: Short description
                - status: 'open', 'closed', etc.
                - labels: List of label names
                - assignee: Assignee login
                - milestone: Milestone title or None
                - backend_id: GitHub issue number

        Returns:
            New Issue object ready to be created
        """
        # Delegate to the extracted SyncMergeEngine implementation
        return self._engine._create_issue_from_remote(
            remote_id=remote_id, remote_issue=remote_issue
        )

    def _match_and_link_remote_issues(
        self,
        local_issues_dict: dict,
        remote_issues_data: dict,
        dry_run: bool = False,
    ) -> dict[str, list[Any]]:
        """Match unlinked remote issues to local issues and establish links.

        For remote issues without existing local links, use similarity matching
        to find potential local counterparts and link them.

        Args:
            local_issues_dict: Dict of local Issue objects keyed by ID
            remote_issues_data: Dict of remote issue dicts keyed by ID
            dry_run: If True, don't actually save changes to files

        Returns:
            Dict with keys 'auto_linked', 'potential_duplicates', 'new_remote'
            containing lists of remote issue IDs
        """

        return self._engine._match_and_link_remote_issues(
            local_issues_dict, remote_issues_data, dry_run=dry_run
        )

    def _count_remote_stats(self, remote_issues_data):
        """Return counts for remote issues and milestones in a safe way."""
        return self._engine._count_remote_stats(remote_issues_data)

    def _load_baseline_safe(self):
        """Load baseline state but swallow errors and return None on failure."""
        try:
            logger.debug("loading_sync_state")
            base_state = self._load_baseline_state()
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
                    "no_previous_sync_state_found", reason="first_sync_or_state_cleared"
                )
        except Exception:
            logger.warning("sync_state_load_warning", reason="will_treat_as_first_sync")
            base_state = None

        return base_state

    def _analyze_and_classify(self, local_issues_dict, remote_issues_data, base_state):
        """Run comparator and classify changes into categories used by sync flow."""
        changes = self._analyze_changes(
            local_issues_dict, remote_issues_data, base_state
        )

        conflicts = [c for c in changes if c.has_conflict]
        local_only_changes = [c for c in changes if c.is_local_only_change()]
        remote_only_changes = [c for c in changes if c.is_remote_only_change()]
        no_changes = [c for c in changes if c.conflict_type == "no_change"]

        updates = [c.local_state for c in local_only_changes if c.local_state]
        pulls = [c.issue_id for c in remote_only_changes]
        up_to_date = [c.issue_id for c in no_changes]

        logger.debug(
            "three_way_analysis_complete",
            total_changes=len(changes),
            conflicts=len(conflicts),
            local_only=len(local_only_changes),
            remote_only=len(remote_only_changes),
            no_change=len(no_changes),
        )

        return (
            changes,
            conflicts,
            local_only_changes,
            remote_only_changes,
            no_changes,
            updates,
            pulls,
            up_to_date,
        )

    def _populate_report_fields(
        self,
        report,
        local_issues,
        active_issues_count,
        archived_issues_count,
        all_milestones,
        active_milestones_count,
        archived_milestones_count,
        remote_issues_count,
        remote_open_count,
        remote_closed_count,
        remote_milestones_count,
        conflicts,
        up_to_date,
        local_only_changes,
        remote_only_changes,
        changes,
    ):
        """Populate the SyncReport fields from computed values."""
        report.total_issues = len(local_issues)
        report.active_issues = active_issues_count
        report.archived_issues = archived_issues_count
        report.total_milestones = len(all_milestones)
        report.active_milestones = active_milestones_count
        report.archived_milestones = archived_milestones_count
        report.remote_total_issues = remote_issues_count
        report.remote_open_issues = remote_open_count
        report.remote_closed_issues = remote_closed_count
        report.remote_total_milestones = remote_milestones_count
        report.conflicts_detected = len(conflicts)
        report.issues_up_to_date = len(up_to_date)
        report.issues_needs_push = len(local_only_changes)
        report.issues_needs_pull = len(remote_only_changes)
        report.changes = changes

    def sync_all_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_remote: bool = False,
        push_only: bool = False,
        pull_only: bool = False,
    ) -> SyncReport:
        """Sync all issues using the configured backend.

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_remote: Resolve conflicts by keeping remote changes
            push_only: If True, only push local changes (skip pulling remote)
            pull_only: If True, only pull remote changes (skip pushing local)

        Returns:
            SyncReport with detected changes and conflicts
        """
        from roadmap.common.logging import get_stack_trace

        report = SyncReport()

        try:
            logger.info(
                "sync_all_issues_starting",
                dry_run=dry_run,
                force_local=force_local,
                force_remote=force_remote,
                sync_mode="analysis" if dry_run else "apply",
            )
            logger.debug(
                "sync_triggered_from",
                stack=get_stack_trace(depth=4),
            )

            # 1. Authenticate
            if not self._ensure_authenticated(report):
                return report

            # 2. Remote + local fetch
            remote_issues_data = self._fetch_remote_issues(report)
            if remote_issues_data is None:
                return report

            local_issues = self._fetch_local_issues(report)
            if local_issues is None:
                return report

            local_issues_dict = {issue.id: issue for issue in local_issues}

            logger.info(
                "sync_state_detected",
                local_count=len(local_issues_dict),
                remote_count=len(remote_issues_data),
            )

            active_issues_count, archived_issues_count = self._count_active_archived(
                local_issues
            )

            all_milestones, active_milestones_count, archived_milestones_count = (
                self._count_milestones()
            )

            # Count remote open/closed and milestones
            (
                remote_issues_count,
                remote_open_count,
                remote_closed_count,
                remote_milestones_count,
            ) = self._count_remote_stats(remote_issues_data)

            # 3. Baseline state
            base_state = self._load_baseline_safe()

            # 4. Pre-match links when pulling
            if not push_only:
                _ = self._match_and_link_remote_issues(
                    local_issues_dict, remote_issues_data, dry_run=dry_run
                )

            # 5. Analyze changes via comparator and classify
            (
                changes,
                conflicts,
                local_only_changes,
                remote_only_changes,
                no_changes,
                updates,
                pulls,
                up_to_date,
            ) = self._analyze_and_classify(
                local_issues_dict, remote_issues_data, base_state
            )

            logger.debug(
                "sync_analysis_complete",
                conflicts=len(conflicts),
                updates=len(updates),
                pulls=len(pulls),
                up_to_date=len(up_to_date),
            )

            # 6. Reporting
            self._populate_report_fields(
                report,
                local_issues,
                active_issues_count,
                archived_issues_count,
                all_milestones,
                active_milestones_count,
                archived_milestones_count,
                remote_issues_count,
                remote_open_count,
                remote_closed_count,
                remote_milestones_count,
                conflicts,
                up_to_date,
                local_only_changes,
                remote_only_changes,
                changes,
            )

            # 7. Resolve conflicts
            resolved_issues = self._resolve_conflicts_if_needed(
                conflicts, force_local, force_remote
            )

            # 8. Apply changes (if not dry_run)
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
                report = self._apply_plan(
                    updates,
                    resolved_issues,
                    pulls,
                    dry_run,
                    push_only,
                    pull_only,
                    report,
                )
            elif dry_run:
                logger.info("sync_dry_run_mode", skip_apply=True)

            logger.info("sync_all_issues_completed", error=report.error)
            return report

        except Exception as e:
            report.error = str(e)
            logger.error(
                "sync_all_issues_failed",
                error_type=type(e).__name__,
                error=str(e),
                error_classification="sync_error",
                suggested_action="check_logs_for_details",
            )
            return report

    def _apply_changes(
        self,
        report: SyncReport,
        updates: list,
        resolved_issues: list,
        pulls: list,
        dry_run: bool = False,
        push_only: bool = False,
        pull_only: bool = False,
    ) -> SyncReport:
        """Apply detected changes using the backend.

        Args:
            report: SyncReport to update
            updates: Issues to push (local updates)
            resolved_issues: Issues resolved from conflicts
            pulls: Issues to pull (remote updates)
            push_only: If True, only push changes (skip pulls)
            pull_only: If True, only pull changes (skip pushes)

        Returns:
            Updated SyncReport with applied changes
        """
        from roadmap.common.logging import get_stack_trace

        logger.info(
            "applying_changes_starting",
            updates=len(updates),
            resolved=len(resolved_issues),
            pulls=len(pulls),
            push_only=push_only,
            pull_only=pull_only,
        )
        logger.debug(
            "apply_changes_triggered_from",
            stack=get_stack_trace(depth=3),
        )

        pushed_count = 0
        pulled_count = 0
        push_errors = []
        pull_errors = []

        try:
            # Push local updates and resolved conflicts (skip if pull_only)
            if not pull_only and not dry_run:
                issues_to_push = updates + resolved_issues
                if issues_to_push:
                    pushed_count, push_errors = self._push_updates(
                        issues_to_push, report
                    )

            # Pull remote updates (skip if push_only or dry_run)
            if not push_only and not dry_run and pulls:
                pulled_count, pull_errors = self._pull_updates(pulls)

            report.issues_pushed = pushed_count
            report.issues_pulled = pulled_count

            logger.info(
                "changes_applied_complete",
                pushed=pushed_count,
                pulled=pulled_count,
                push_errors=len(push_errors),
                pull_errors=len(pull_errors),
            )

            # After applying changes, update report to reflect what was applied
            if (pushed_count > 0 or pulled_count > 0) and not dry_run:
                try:
                    if pushed_count > 0:
                        report.issues_needs_push = max(
                            0, report.issues_needs_push - pushed_count
                        )
                        report.issues_up_to_date = (
                            report.issues_up_to_date + pushed_count
                        )

                    if pulled_count > 0:
                        report.issues_needs_pull = max(
                            0, report.issues_needs_pull - pulled_count
                        )
                        report.issues_up_to_date = (
                            report.issues_up_to_date + pulled_count
                        )

                    logger.info(
                        "report_updated_after_apply",
                        up_to_date=report.issues_up_to_date,
                        needs_push=report.issues_needs_push,
                        needs_pull=report.issues_needs_pull,
                    )
                except Exception as e:
                    logger.warning(
                        "report_update_after_apply_failed",
                        error=str(e),
                        error_type=type(e).__name__,
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
