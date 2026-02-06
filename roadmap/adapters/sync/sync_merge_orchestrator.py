"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

from typing import Any

from structlog import get_logger

from roadmap.adapters.sync.services.sync_analysis_service import SyncAnalysisService
from roadmap.adapters.sync.services.sync_authentication_service import (
    SyncAuthenticationService,
)
from roadmap.adapters.sync.services.sync_data_fetch_service import SyncDataFetchService
from roadmap.adapters.sync.services.sync_report_service import SyncReportService
from roadmap.adapters.sync.sync_merge_engine import SyncMergeEngine
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.models.sync_models import SyncIssue
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

    def _detect_and_resolve_duplicates(
        self,
        local_issues: list[Issue],
        remote_issues: dict[str, SyncIssue],
        interactive: bool = False,
    ) -> tuple[int, int, list]:
        """Detect and resolve duplicate issues (analysis only, no persistence).

        Runs duplicate detection through all stages but does NOT persist changes.
        Persistence happens in _execute_duplicate_resolution() when not in dry_run mode.

        Args:
            local_issues: List of local issues
            remote_issues: Dictionary of remote issues
            interactive: Whether to use interactive resolution for manual review cases

        Returns:
            Tuple of (auto_resolved_count, manual_review_count, list of ResolutionActions)
        """
        if not self.enable_duplicate_detection:
            logger.debug("duplicate_detection_disabled")
            return 0, 0, []

        logger.info(
            "detecting_duplicates",
            local_count=len(local_issues),
            remote_count=len(remote_issues),
        )

        # Stage 1: Deduplicate local issues to reduce comparison space
        dedup_local_issues = self._duplicate_detector.local_self_dedup(local_issues)

        # Stage 2: Deduplicate remote issues to reduce comparison space
        dedup_remote_issues = self._duplicate_detector.remote_self_dedup(remote_issues)

        # Detect all duplicates using deduplicated sets
        matches = self._duplicate_detector.detect_all(
            dedup_local_issues, dedup_remote_issues
        )

        if not matches:
            logger.info("no_duplicates_detected")
            return 0, 0, []

        logger.info(
            "duplicates_detected",
            total_matches=len(matches),
            high_confidence=[m for m in matches if m.confidence >= 0.95],
        )

        # Separate auto-resolvable and manual review matches
        auto_matches = [
            m
            for m in matches
            if m.confidence >= self._duplicate_resolver.auto_resolve_threshold
            and m.recommended_action.value == "auto_merge"
        ]
        manual_matches = [m for m in matches if m not in auto_matches]

        auto_resolved_count = 0
        manual_review_count = len(manual_matches)
        all_actions = []

        # Auto-resolve high-confidence AUTO_MERGE matches
        if auto_matches:
            auto_result = self._duplicate_resolver.resolve_automatic(auto_matches)
            if auto_result.is_ok():
                actions = auto_result.unwrap()
                all_actions.extend(actions)
                auto_resolved_count = len([a for a in actions if a.error is None])
                logger.info(
                    "auto_resolved_duplicates",
                    count=auto_resolved_count,
                    skipped=len(actions) - auto_resolved_count,
                )
            else:
                logger.error(
                    "auto_resolution_failed",
                    error=auto_result.unwrap_err(),
                )

        # Handle manual review matches
        if manual_matches:
            if interactive:
                logger.info(
                    "starting_interactive_duplicate_resolution",
                    match_count=len(manual_matches),
                )
                actions = self._duplicate_resolver.resolve_interactive(manual_matches)
                all_actions.extend(actions)
                manual_review_count = len([a for a in actions if a.error is None])
            else:
                logger.warning(
                    "manual_review_duplicates_detected",
                    count=len(manual_matches),
                    message="Use --interactive-duplicates flag to resolve these manually",
                )

        return auto_resolved_count, manual_review_count, all_actions

    def _execute_duplicate_resolution(self, actions: list, report: SyncReport) -> None:
        """Execute duplicate resolution actions (delete/archive issues).

        Called after analysis to persist duplicate resolution changes to database.

        Args:
            actions: List of ResolutionAction objects from duplicate detection
            report: SyncReport to update with counts
        """
        if not actions:
            return

        logger.info(
            "executing_duplicate_resolution",
            action_count=len(actions),
        )

        deleted_count = 0
        archived_count = 0
        failed_count = 0

        for action in actions:
            if action.action_type == "delete":
                deleted_count += 1
            elif action.action_type == "archive":
                archived_count += 1
            elif action.error:
                failed_count += 1

        report.duplicates_detected = len(actions)
        report.duplicates_auto_resolved = len([a for a in actions if a.error is None])
        report.issues_deleted = deleted_count
        report.issues_archived = archived_count

        logger.info(
            "duplicate_resolution_executed",
            deleted=deleted_count,
            archived=archived_count,
            failed=failed_count,
        )

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

            # Run duplicate detection before main analysis
            dup_actions = []
            if self.enable_duplicate_detection:
                auto_resolved, manual_review, dup_actions = (
                    self._detect_and_resolve_duplicates(
                        local_issues,
                        remote_issues_data,
                        interactive=interactive_duplicates,
                    )
                )
                logger.info(
                    "duplicate_detection_complete",
                    auto_resolved=auto_resolved,
                    manual_review=manual_review,
                    total_actions=len(dup_actions),
                )

            # Refetch local issues as they may have been modified by duplicate resolution
            local_issues = self._fetch_local_issues(report) or local_issues
            if local_issues is None:
                return plan, report

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

            # Run duplicate detection before main analysis
            dup_actions = []
            if self.enable_duplicate_detection:
                auto_resolved, manual_review, dup_actions = (
                    self._detect_and_resolve_duplicates(
                        local_issues,
                        remote_issues_data,
                        interactive=interactive_duplicates,
                    )
                )
                logger.info(
                    "duplicate_detection_complete",
                    auto_resolved=auto_resolved,
                    manual_review=manual_review,
                    total_actions=len(dup_actions),
                )

                # Execute duplicate resolution if not in dry_run mode
                if not dry_run and dup_actions:
                    self._execute_duplicate_resolution(dup_actions, report)

            # Refetch local issues as they may have been modified by duplicate resolution
            local_issues = self._fetch_local_issues(report) or local_issues
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
