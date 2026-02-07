"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

import time
from typing import Any

from structlog import get_logger

from roadmap.adapters.sync.services.sync_analysis_service import SyncAnalysisService
from roadmap.adapters.sync.services.sync_authentication_service import (
    SyncAuthenticationService,
)
from roadmap.adapters.sync.services.sync_data_fetch_service import SyncDataFetchService
from roadmap.adapters.sync.services.sync_report_service import SyncReportService
from roadmap.adapters.sync.sync_merge_engine import SyncMergeEngine
from roadmap.application.services.deduplicate_service import DeduplicateService
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.observability.sync_metrics import get_observability
from roadmap.core.services.sync.duplicate_detector import DuplicateDetector
from roadmap.core.services.sync.duplicate_resolver import DuplicateResolver
from roadmap.core.services.sync.sync_conflict_resolver import (
    Conflict,
    SyncConflictResolver,
)
from roadmap.core.services.sync.sync_plan import (
    PullAction,
    PushAction,
    ResolveConflictAction,
    SyncPlan,
)
from roadmap.core.services.sync.sync_report import SyncReport
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync.sync_state_manager import SyncStateManager
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class SyncMergeOrchestrator:
    """Orchestrates sync using a pluggable backend implementation."""

    def __init__(
        self,
        core: RoadmapCore,
        backend: SyncBackendInterface,
        state_comparator: SyncStateComparator | None = None,
        conflict_resolver: SyncConflictResolver | None = None,
        enable_duplicate_detection: bool = True,
        duplicate_title_threshold: float = 0.90,
        duplicate_content_threshold: float = 0.85,
        duplicate_auto_resolve_threshold: float = 0.95,
    ):
        """Initialize orchestrator with core services and backend.

        Args:
            core: RoadmapCore instance with access to issues
            backend: SyncBackendInterface implementation (GitHub, vanilla Git, etc.)
            state_comparator: SyncStateComparator for detecting changes (optional, creates default)
            conflict_resolver: SyncConflictResolver for resolving conflicts (optional, creates default)
            enable_duplicate_detection: Whether to enable duplicate detection (default: True)
            duplicate_title_threshold: Minimum similarity for title duplicates (0.0-1.0, default: 0.90)
            duplicate_content_threshold: Minimum similarity for content duplicates (0.0-1.0, default: 0.85)
            duplicate_auto_resolve_threshold: Minimum confidence for auto-resolution (0.0-1.0, default: 0.95)
        """
        self.core = core
        self.backend = backend
        # Pass backend to comparator for key normalization
        self.state_comparator = state_comparator or SyncStateComparator(backend=backend)
        self.conflict_resolver = conflict_resolver or SyncConflictResolver()
        self.state_manager = SyncStateManager(core.roadmap_dir)
        self.enable_duplicate_detection = enable_duplicate_detection

        # Initialize observability tracker
        self._observability = get_observability()
        self._current_operation_id: str | None = None

        # Initialize delegated services
        self._auth_service = SyncAuthenticationService(backend)
        self._fetch_service = SyncDataFetchService(core, backend)
        self._analysis_service = SyncAnalysisService(
            self.state_comparator, self.state_manager
        )

        # Initialize duplicate detection services with configurable thresholds
        self._duplicate_detector = DuplicateDetector(
            title_similarity_threshold=duplicate_title_threshold,
            content_similarity_threshold=duplicate_content_threshold,
            auto_resolve_threshold=duplicate_auto_resolve_threshold,
        )
        self._duplicate_resolver = DuplicateResolver(
            issue_service=core.issue_service,
            auto_resolve_threshold=duplicate_auto_resolve_threshold,
        )

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
        return self._auth_service.ensure_authenticated(report)

    def _fetch_remote_issues(self, report: SyncReport):
        return self._fetch_service.fetch_remote_issues(report)

    def _fetch_local_issues(self, report: SyncReport):
        return self._fetch_service.fetch_local_issues(report)

    def _count_active_archived(self, local_issues):
        return self._fetch_service.count_active_archived(local_issues)

    def _count_milestones(self):
        return self._fetch_service.count_milestones()

    def _count_remote_stats(self, remote_issues_data):
        return self._fetch_service.count_remote_stats(remote_issues_data)

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
        interactive_duplicates: bool = False,
    ) -> tuple[SyncPlan, SyncReport]:
        """Pure analysis pass that returns a SyncPlan and SyncReport without side-effects.

        This method performs authentication and data retrieval (reads only),
        runs duplicate detection, runs the three-way analysis, and converts the result
        into a list of `Action`s bundled into a `SyncPlan`. No database or file writes are
        performed here — actions are merely declared for an Executor to apply.

        Args:
            push_only: Only push local changes, skip pulling remote
            pull_only: Only pull remote changes, skip pushing local
            interactive_duplicates: Use interactive resolution for duplicate matches

        Returns:
            Tuple of (SyncPlan, SyncReport)
        """
        report = SyncReport()
        plan = SyncPlan()

        try:
            # Helper: authenticate and fetch remote issues
            def _auth_and_fetch_remote():
                # Handle Result type from backend.authenticate()
                auth_result = self.backend.authenticate()
                if auth_result.is_err():
                    error = auth_result.unwrap_err()
                    report.error = str(error)
                    return None

                # Handle Result type from backend.get_issues()
                issues_result = self.backend.get_issues()
                if issues_result.is_err():
                    error = issues_result.unwrap_err()
                    report.error = str(error)
                    return None

                return issues_result.unwrap()

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

            logger.info(
                "DEBUG: Fetched issues",
                local_count=len(local_issues),
                remote_count=len(remote_issues_data)
                if isinstance(remote_issues_data, dict)
                else "not_a_dict",
            )

            local_issues_dict = {issue.id: issue for issue in local_issues}
            try:
                base_state = self._load_baseline_state()
            except Exception:
                base_state = None

            # Helper: run comparator and classify changes
            def _run_analysis(local_dict, remote_data, base_state):
                logger.info(
                    "DEBUG: Starting three-way analysis",
                    local_count=len(local_dict),
                    remote_count=len(remote_data),
                    base_count=len(base_state.base_issues) if base_state else 0,
                )
                changes = self.state_comparator.analyze_three_way(
                    local_dict,
                    remote_data,
                    base_state.base_issues if base_state else None,
                )
                logger.info(
                    "DEBUG: Three-way analysis complete", changes_count=len(changes)
                )
                conflicts = [c for c in changes if c.has_conflict]
                local_only_changes = [c for c in changes if c.is_local_only_change()]
                remote_only_changes = [c for c in changes if c.is_remote_only_change()]
                no_changes = [c for c in changes if c.conflict_type == "no_change"]
                logger.info(
                    "DEBUG: Classified changes",
                    conflicts=len(conflicts),
                    local_only=len(local_only_changes),
                    remote_only=len(remote_only_changes),
                    no_changes=len(no_changes),
                )
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

    def _load_baseline_safe(self):
        """Load baseline state but swallow errors and return None on failure."""
        return self._analysis_service.load_baseline_safe()

    def _analyze_and_classify(self, local_issues_dict, remote_issues_data, base_state):
        """Run comparator and classify changes into categories used by sync flow."""
        return self._analysis_service.analyze_and_classify(
            local_issues_dict, remote_issues_data, base_state
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
        SyncReportService.populate_report_fields(
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

    def sync_all_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_remote: bool = False,
        push_only: bool = False,
        pull_only: bool = False,
        interactive_duplicates: bool = False,
    ) -> SyncReport:
        """Sync all issues using the configured backend.

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_remote: Resolve conflicts by keeping remote changes
            push_only: If True, only push local changes (skip pulling remote)
            pull_only: If True, only pull remote changes (skip pushing local)
            interactive_duplicates: If True, use interactive resolution for duplicate matches

        Returns:
            SyncReport with detected changes and conflicts
        """
        from roadmap.common.logging import get_stack_trace

        # Start metrics tracking
        self._current_operation_id = self._observability.start_operation(
            self.backend.__class__.__name__
        )
        sync_start_time = time.time()

        report = SyncReport()

        try:
            logger.info(
                "sync_all_issues_starting",
                dry_run=dry_run,
                force_local=force_local,
                force_remote=force_remote,
                sync_mode="analysis" if dry_run else "apply",
                operation_id=self._current_operation_id,
            )
            logger.debug(
                "sync_triggered_from",
                stack=get_stack_trace(depth=4),
            )

            # Phase 1: Initialize
            remote_issues_data, local_issues_dict = self._sync_initialize(
                dry_run, interactive_duplicates, report
            )
            if remote_issues_data is None or local_issues_dict is None:
                return report

            # Phase 2: Deduplicate (detect and remove duplicates from data structures)
            remote_issues_data, local_issues_dict = self._sync_deduplicate(
                remote_issues_data,
                local_issues_dict,
                interactive_duplicates,
                dry_run,
                report,
            )
            if remote_issues_data is None or local_issues_dict is None:
                return report

            # Phase 3: Analyze changes
            (
                changes,
                conflicts,
                local_only_changes,
                remote_only_changes,
                no_changes,
                updates,
                pulls,
                up_to_date,
            ) = self._sync_analyze(local_issues_dict, remote_issues_data, report)

            # Phase 4: Resolve and apply
            report = self._sync_resolve_and_apply(
                conflicts,
                updates,
                pulls,
                dry_run,
                force_local,
                force_remote,
                push_only,
                pull_only,
                report,
            )

            # Phase 5: Execute duplicate resolution (merge/archive)
            local_issues_after_sync = list(local_issues_dict.values())
            self._execute_duplicate_resolution(
                local_issues_after_sync,
                report=report,
                dry_run=dry_run,
                interactive_duplicates=interactive_duplicates,
            )

            # Phase 6: Record metrics
            self._sync_record_metrics(
                sync_start_time,
                conflicts,
                local_issues_dict,
                report,
            )

            logger.info("sync_all_issues_completed", error=report.error)
            return report

        except Exception as e:
            report.error = str(e)
            if self._current_operation_id:
                self._observability.record_error(
                    self._current_operation_id,
                    type(e).__name__,
                    str(e),
                )
            logger.exception("sync_all_issues_failed")
            return report

    def _sync_initialize(
        self,
        dry_run: bool,
        interactive_duplicates: bool,
        report: SyncReport,
    ) -> tuple[dict[str, SyncIssue] | None, dict[str, Issue] | None]:
        """Initialize sync by fetching issues (deduplication is now a separate phase).

        Returns:
            Tuple of (remote_issues_data, local_issues_dict) or (None, None) on error
        """
        # Authenticate
        if not self._ensure_authenticated(report):
            return None, None

        # Fetch remote + local
        fetch_start = time.time()
        remote_issues_data = self._fetch_remote_issues(report)
        if remote_issues_data is None:
            return None, None

        local_issues = self._fetch_local_issues(report)
        if local_issues is None:
            return None, None
        fetch_duration = time.time() - fetch_start

        if self._current_operation_id:
            self._observability.record_fetch(
                self._current_operation_id,
                count=len(remote_issues_data),
                duration=fetch_duration,
            )

        local_issues_dict = {issue.id: issue for issue in local_issues}

        logger.info(
            "sync_state_fetched",
            local_count=len(local_issues_dict),
            remote_count=len(remote_issues_data),
        )

        return remote_issues_data, local_issues_dict

    def _sync_deduplicate(
        self,
        remote_issues_data: dict[str, SyncIssue],
        local_issues_dict: dict[str, Issue],
        interactive_duplicates: bool,
        dry_run: bool,
        report: SyncReport,
    ) -> tuple[dict[str, SyncIssue] | None, dict[str, Issue] | None]:
        """Deduplicate phase: Detect and remove duplicates from data structures.

        This is a SEPARATE phase that runs BEFORE analysis. It:
        1. Detects duplicates in local and remote issues
        2. Executes resolution (delete/archive) actions immediately
        3. REMOVES duplicates from the data structures
        4. Returns only canonical issues for analysis

        Returns:
            Tuple of (deduplicated_remote_issues_data, deduplicated_local_issues_dict)
            or (None, None) on error
        """
        if not self.enable_duplicate_detection:
            logger.info("duplicate_detection_disabled")
            return remote_issues_data, local_issues_dict

        local_issues = list(local_issues_dict.values())

        logger.info(
            "deduplication_phase_starting",
            local_issues_count=len(local_issues),
            remote_issues_count=len(remote_issues_data),
        )

        # Create and execute deduplicate service
        dedup_service = DeduplicateService(
            issue_repo=self.core.issue_service.repository,
            duplicate_detector=self._duplicate_detector,
            backend=self.backend,  # Pass backend for remote duplicate closure
        )

        response = dedup_service.execute(
            local_issues=local_issues,
            remote_issues=remote_issues_data,
            dry_run=dry_run,
        )

        logger.info(
            "deduplication_phase_complete",
            duplicates_removed=response.duplicates_removed,
        )

        # Update report with deduplication metrics
        # duplicates_removed represents hard-deleted duplicates
        report.issues_deleted = response.duplicates_removed

        # Convert returned lists back to dict format for compatibility
        deduplicated_local_dict = {issue.id: issue for issue in response.local_issues}
        deduplicated_remote_dict = response.remote_issues

        # Critical: Update baseline to remove deleted duplicates
        # This ensures the invariant: after sync, local == remote == baseline
        if response.duplicates_removed > 0 and not dry_run:
            self._update_baseline_after_dedup(
                deduplicated_local_dict,
                deduplicated_remote_dict,
            )

        logger.info(
            "deduplication_results",
            local_before=len(local_issues_dict),
            local_after=len(deduplicated_local_dict),
            remote_before=len(remote_issues_data),
            remote_after=len(deduplicated_remote_dict),
        )

        return deduplicated_remote_dict, deduplicated_local_dict

    def _update_baseline_after_dedup(
        self,
        deduplicated_local_dict: dict[str, Issue],
        deduplicated_remote_dict: dict[str, SyncIssue],
    ) -> None:
        """Update baseline to remove duplicates that were deleted.

        After deduplication deletes issues from the database, we must also
        update the baseline state to maintain the invariant:
        baseline == local == remote

        Args:
            deduplicated_local_dict: Local issues dict after deduplication
            deduplicated_remote_dict: Remote issues dict after deduplication
        """
        initial_count = 0
        final_count = 0
        try:
            # Load current baseline
            baseline_state = self.state_manager.load_sync_state()
            if not baseline_state:
                logger.info("baseline_not_found_after_dedup", skip_update=True)
                return

            initial_count = (
                len(baseline_state.base_issues) if baseline_state.base_issues else 0
            )

            # Get remaining issue IDs from deduplicated dicts (no re-enumeration!)
            remaining_ids = set(deduplicated_local_dict.keys()) | set(
                deduplicated_remote_dict.keys()
            )

            # Filter baseline to only include issues that still exist
            # base_issues is a dict[str, IssueBaseState]
            if baseline_state.base_issues:
                baseline_state.base_issues = {
                    issue_id: base_state
                    for issue_id, base_state in baseline_state.base_issues.items()
                    if issue_id in remaining_ids
                }

            # Save updated baseline
            success = self.state_manager.save_sync_state_to_db(baseline_state)
            final_count = (
                len(baseline_state.base_issues) if baseline_state.base_issues else 0
            )

            logger.info(
                "baseline_updated_after_dedup",
                deleted_count=initial_count - final_count,
                baseline_before=initial_count,
                baseline_after=final_count,
                success=success,
            )

        except Exception as e:
            logger.error(
                "baseline_update_after_dedup_failed",
                error=str(e),
                deleted_count=initial_count - final_count,
            )

    def _sync_analyze(
        self,
        local_issues_dict: dict[str, Issue],
        remote_issues_data: dict[str, SyncIssue],
        report: SyncReport,
    ) -> tuple[list, list, list, list, list, list, list, list]:
        """Analyze changes between local and remote issues.

        Returns:
            Tuple of (changes, conflicts, local_only, remote_only, no_changes, updates, pulls, up_to_date)
        """
        # Update report with counts
        local_issues = list(local_issues_dict.values())
        active_issues_count, archived_issues_count = self._count_active_archived(
            local_issues
        )
        all_milestones, active_milestones_count, archived_milestones_count = (
            self._count_milestones()
        )
        (
            remote_issues_count,
            remote_open_count,
            remote_closed_count,
            remote_milestones_count,
        ) = self._count_remote_stats(remote_issues_data)

        # Load baseline state
        base_state = self._load_baseline_safe()

        # Match and link remote issues
        _ = self._match_and_link_remote_issues(
            local_issues_dict, remote_issues_data, dry_run=True
        )

        # Analyze changes
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

        # Populate report
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

    def _sync_resolve_and_apply(
        self,
        conflicts: list,
        updates: list,
        pulls: list,
        dry_run: bool,
        force_local: bool,
        force_remote: bool,
        push_only: bool,
        pull_only: bool,
        report: SyncReport,
    ) -> SyncReport:
        """Resolve conflicts and apply changes.

        Args:
            conflicts: List of conflicted issues
            updates: List of issues to update
            pulls: List of issues to pull
            dry_run: Whether in dry_run mode
            force_local: Force local resolution
            force_remote: Force remote resolution
            push_only: Only push changes
            pull_only: Only pull changes
            report: SyncReport to update

        Returns:
            Updated SyncReport
        """
        # Resolve conflicts
        resolved_issues = self._resolve_conflicts_if_needed(
            conflicts, force_local, force_remote
        )

        # Apply changes
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

        return report

    def _execute_duplicate_resolution(
        self,
        actions_or_issues: list | None = None,
        report: SyncReport | None = None,
        dry_run: bool = False,
        interactive_duplicates: bool = False,
    ) -> None:
        """Execute duplicate resolution (flexible signature for compatibility).

        Can be called two ways:
        1. Legacy: _execute_duplicate_resolution(actions_list, report)
           - Takes list of pre-made ResolutionAction objects
           - Executes them directly
        2. Full: _execute_duplicate_resolution(local_issues, report=..., dry_run=..., interactive_duplicates=...)
           - Takes list of local issues
           - Detects and resolves duplicates

        Args:
            actions_or_issues: List of actions OR list of issues (determines mode)
            report: SyncReport to update (positional for legacy compatibility)
            dry_run: If True, don't persist changes
            interactive_duplicates: If True, use interactive resolution
        """
        # Ensure we have a report
        if report is None:
            from roadmap.core.services.sync.sync_report import SyncReport

            report = SyncReport()

        # Empty list? Just return
        if not actions_or_issues:
            return

        # Check if we're in legacy mode by looking at the first item
        first_item = actions_or_issues[0]

        # Legacy mode indicators: Has 'action_type' attribute
        # Modern Issue objects don't have action_type
        is_legacy_action = hasattr(first_item, "action_type") and hasattr(
            first_item, "issue_id"
        )

        if is_legacy_action:
            # Legacy mode: execute pre-made actions
            self._execute_resolution_actions(actions_or_issues, report, dry_run)
            return

        # Full mode: detect and resolve
        if not self.enable_duplicate_detection:
            return

        local_issues = actions_or_issues

        try:
            logger.info(
                "duplicate_resolution_phase_starting", issue_count=len(local_issues)
            )

            # Detect duplicates in local issues
            detector_result = self._duplicate_detector.detect_all(local_issues, {})
            if isinstance(detector_result, tuple):
                local_duplicates, remote_duplicates = detector_result
            else:
                local_duplicates = detector_result
                remote_duplicates = []

            all_duplicates = local_duplicates + remote_duplicates
            if not all_duplicates:
                logger.info("duplicate_resolution_phase_complete", duplicates_found=0)
                return

            logger.info(
                "duplicates_detected_for_resolution",
                total_matches=len(all_duplicates),
            )

            # Resolve duplicates
            if interactive_duplicates:
                resolution_actions = self._duplicate_resolver.resolve_interactive(
                    all_duplicates
                )
            else:
                resolution_result = self._duplicate_resolver.resolve_automatic(
                    all_duplicates
                )
                if resolution_result.is_err():
                    logger.warning(
                        "automatic_resolution_failed",
                        error=resolution_result.unwrap_err(),
                    )
                    return

                resolution_actions = resolution_result.unwrap()

            if not resolution_actions:
                logger.info("duplicate_resolution_phase_complete", actions_count=0)
                return

            # Execute the resolved actions
            self._execute_resolution_actions(resolution_actions, report, dry_run)

        except Exception as e:
            logger.error(
                "duplicate_resolution_phase_failed",
                error=str(e),
            )

    def _execute_resolution_actions(
        self,
        actions: list,
        report: SyncReport,
        dry_run: bool = False,
    ) -> None:
        """Execute a list of resolution actions.

        Args:
            actions: List of ResolutionAction objects to execute
            report: SyncReport to update with counts
            dry_run: If True, don't persist changes
        """
        merged_count = 0
        archived_count = 0
        skipped_count = 0
        errors = []

        for action in actions:
            # Handle both ResolutionAction and MockResolutionAction
            action_type = getattr(action, "action_type", None)

            # Skip actions that already have errors
            if hasattr(action, "error") and action.error:
                skipped_count += 1
                logger.debug(
                    "skipping_action_with_error",
                    issue_id=getattr(action, "issue_id", None),
                    error=action.error,
                )
                continue

            if action_type == "delete" or action_type == "merge":
                if dry_run:
                    merged_count += 1
                    continue

                issue_id = getattr(action, "issue_id", None)
                if issue_id:
                    try:
                        self.core.issue_service.delete_issue(issue_id)
                        merged_count += 1
                        logger.info("duplicate_deleted", issue_id=issue_id)
                    except Exception as e:
                        errors.append(str(e))
                        logger.warning("delete_failed", issue_id=issue_id, error=str(e))

            elif action_type == "archive":
                if dry_run:
                    archived_count += 1
                    continue

                issue_id = getattr(action, "issue_id", None)
                if issue_id:
                    try:
                        issue = self.core.issue_service.get_issue(issue_id)
                        if issue:
                            from roadmap.common.constants import Status

                            issue.status = Status.ARCHIVED
                            self.core.issue_service.update_issue(issue)
                            archived_count += 1
                            logger.info("duplicate_archived", issue_id=issue_id)
                        else:
                            logger.warning("archive_issue_not_found", issue_id=issue_id)
                    except Exception as e:
                        errors.append(str(e))
                        logger.warning(
                            "archive_failed", issue_id=issue_id, error=str(e)
                        )

            else:
                # skip or unknown action
                skipped_count += 1

        # Update report
        total_actions = len(actions)
        report.duplicates_detected = total_actions
        report.duplicates_auto_resolved = merged_count + archived_count
        report.issues_deleted = merged_count
        report.issues_archived = archived_count

        logger.info(
            "resolution_actions_executed",
            total=total_actions,
            deleted=merged_count,
            archived=archived_count,
            skipped=skipped_count,
            errors=len(errors),
            dry_run=dry_run,
        )

        if errors:
            logger.warning("resolution_errors", count=len(errors))
            for error in errors:
                logger.warning("resolution_error", detail=error)

    def _sync_record_metrics(
        self,
        sync_start_time: float,
        conflicts: list,
        local_issues_dict: dict[str, Issue],
        report: SyncReport,
    ) -> None:
        """Record sync operation metrics.

        Args:
            sync_start_time: Timestamp when sync started
            conflicts: List of conflicts encountered
            local_issues_dict: Dictionary of local issues
            report: SyncReport to attach metrics to
        """
        if not self._current_operation_id:
            return

        sync_duration = time.time() - sync_start_time
        self._observability.record_conflict(
            self._current_operation_id, count=len(conflicts)
        )
        self._observability.record_phase_timing(
            self._current_operation_id, "analysis", sync_duration
        )
        self._observability.record_sync_links(
            self._current_operation_id, created=len(local_issues_dict)
        )
        if report.error:
            self._observability.record_error(
                self._current_operation_id,
                "sync_error",
                report.error,
            )
        final_metrics = self._observability.finalize(self._current_operation_id)
        report.metrics = final_metrics

        # Store metrics to database for historical tracking
        from roadmap.core.services.sync.sync_metadata_service import (
            SyncMetadataService,
        )

        metadata_service = SyncMetadataService(self.core)
        metadata_service.store_sync_metrics(
            self.core, self._current_operation_id, final_metrics.to_dict()
        )
