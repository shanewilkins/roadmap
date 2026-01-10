"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

from typing import Any

from structlog import get_logger

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.issue_matching_service import IssueMatchingService
from roadmap.core.services.sync_conflict_resolver import (
    Conflict,
    ConflictField,
    ConflictStrategy,
    SyncConflictResolver,
)
from roadmap.core.services.sync_plan import (
    Action,
    PullAction,
    PushAction,
    ResolveConflictAction,
    SyncPlan,
)
from roadmap.core.services.sync_plan_executor import SyncPlanExecutor
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

    def _load_baseline_state(self):
        """Load baseline state from database with fallback to manager.

        Returns:
            SyncState from database, or None if not found
        """
        try:
            from datetime import datetime, timezone

            from roadmap.core.models.sync_state import IssueBaseState, SyncState

            # Load from database (preferred - fast)
            db_baseline = self.core.db.get_sync_baseline()
            if db_baseline:
                logger.debug(
                    "baseline_loaded_from_database",
                    issue_count=len(db_baseline),
                )
                issues = {}
                for issue_id, data in db_baseline.items():
                    issues[issue_id] = IssueBaseState(
                        id=issue_id,
                        status=data.get("status", "todo"),
                        title="",  # Title not stored in baseline
                        assignee=data.get("assignee"),
                        milestone=data.get("milestone"),
                        headline=data.get("headline", ""),
                        content=data.get("content", ""),
                        labels=data.get("labels", []),
                    )

                sync_state = SyncState(
                    last_sync=datetime.now(timezone.utc),
                    backend="github",
                    issues=issues,
                )
                return sync_state

            logger.debug("baseline_not_found_in_database")
            return None

        except Exception as e:
            logger.warning(
                "baseline_load_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

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
            # Authenticate with backend (read-only call to validate access)
            try:
                if not self.backend.authenticate():
                    report.error = "Backend authentication failed"
                    return plan, report
            except Exception as e:
                report.error = f"Backend authentication error: {str(e)}"
                return plan, report

            # Fetch remote snapshot (read-only)
            try:
                remote_issues_data = self.backend.get_issues() or {}
            except Exception as e:
                report.error = f"Failed to fetch remote issues: {str(e)}"
                return plan, report

            # Load local issues (read-only)
            try:
                local_issues = self.core.issues.list_all_including_archived() or []
            except Exception as e:
                report.error = f"Failed to fetch local issues: {str(e)}"
                return plan, report

            local_issues_dict = {issue.id: issue for issue in local_issues}

            # Load baseline (read-only)
            try:
                base_state = self._load_baseline_state()
            except Exception:
                base_state = None

            # Run three-way analysis using the comparator
            changes = self.state_comparator.analyze_three_way(
                local_issues_dict,
                remote_issues_data,
                base_state.issues if base_state else None,
            )

            # Derive high-level actions from changes (declarative only)
            conflicts = [c for c in changes if c.has_conflict]
            local_only_changes = [c for c in changes if c.is_local_only_change()]
            remote_only_changes = [c for c in changes if c.is_remote_only_change()]
            no_changes = [c for c in changes if c.conflict_type == "no_change"]

            # Create push actions for local-only changes (unless pull_only)
            if not pull_only:
                for c in local_only_changes:
                    if c.local_state:
                        plan.add(
                            PushAction(
                                issue_id=c.issue_id,
                                issue_payload=c.local_state.__dict__,
                            )
                        )

            # Create pull actions for remote-only changes (unless push_only)
            if not push_only:
                for c in remote_only_changes:
                    plan.add(
                        PullAction(
                            issue_id=c.issue_id,
                            remote_payload=c.remote_state
                            if hasattr(c, "remote_state")
                            else {},
                        )
                    )

            # Represent conflicts as resolve actions (executor will persist resolution)
            for c in conflicts:
                # Create a placeholder resolution payload (resolver will be run in executor if needed)
                plan.add(
                    ResolveConflictAction(
                        issue_id=c.issue_id,
                        resolution={"conflict_fields": c.local_changes or {}},
                    )
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
                    base_value = base_state.content
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
                    operation="analyze_conflicts",
                    error_type=type(e).__name__,
                    error=str(e),
                    is_recoverable=True,
                    suggested_action="skip_issue",
                )
                continue

        return conflicts

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
        # Extract title and description
        backend_id = remote_issue.backend_id or remote_id
        title = remote_issue.title or f"GitHub #{backend_id}"
        body = remote_issue.headline or ""

        # Add GitHub issue reference as metadata in content
        if body:
            content = f"{body}\n\n---\n*Synced from GitHub: #{backend_id}*"
        else:
            content = f"*Synced from GitHub: #{backend_id}*"

        # Determine status from remote state
        status = Status.CLOSED if remote_issue.status == "closed" else Status.TODO

        # Get labels and add sync marker
        labels = list(remote_issue.labels or [])
        if "synced:from-github" not in labels:
            labels.append("synced:from-github")

        # Get milestone (will be None for backlog)
        milestone = remote_issue.milestone

        # Create the Issue object
        issue = Issue(
            title=title,
            content=content,
            status=status,
            labels=labels,
            milestone=milestone,
            assignee=remote_issue.assignee,
        )

        logger.debug(
            "created_issue_from_remote",
            remote_id=remote_id,
            issue_id=issue.id,
            title=issue.title,
            milestone=issue.milestone,
        )

        return issue

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
        from roadmap.common.logging import get_stack_trace

        logger.debug(
            "match_and_link_remote_issues_start",
            remote_count=len(remote_issues_data),
            local_count=len(local_issues_dict),
            dry_run=dry_run,
            stack=get_stack_trace(depth=3),
        )

        results = {
            "auto_linked": [],
            "potential_duplicates": [],
            "new_remote": [],
        }

        if not remote_issues_data:
            return results

        try:
            # Get all local issues for matching
            local_issues = list(local_issues_dict.values())
            matcher = IssueMatchingService(local_issues)

            # Pre-load all existing remote links for this backend to avoid N+1 queries
            # Get all remote IDs we're processing
            all_remote_ids = list(remote_issues_data.keys())
            existing_links = {}
            try:
                # Fetch all links in batch if possible, otherwise fall back to individual lookups
                for remote_id in all_remote_ids:
                    uuid = self.core.db.remote_links.get_issue_uuid(
                        backend_name="github", remote_id=remote_id
                    )
                    if uuid:
                        existing_links[remote_id] = uuid
            except Exception as e:
                logger.warning(
                    "batch_remote_links_lookup_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

            for remote_id, remote_issue in remote_issues_data.items():
                # Check if already linked via pre-loaded cache
                if remote_id in existing_links:
                    logger.debug(
                        "remote_issue_already_linked",
                        remote_id=remote_id,
                        issue_uuid=existing_links[remote_id],
                    )
                    continue

                # Try to find a match
                matched_issue, score, match_type = matcher.find_best_match(remote_issue)

                if match_type == "auto_link" and matched_issue:
                    # Auto-link with high confidence
                    try:
                        self.core.db.remote_links.link_issue(
                            issue_uuid=matched_issue.id,
                            backend_name="github",
                            remote_id=remote_id,
                        )
                        logger.info(
                            "remote_issue_auto_linked",
                            remote_id=remote_id,
                            issue_uuid=matched_issue.id,
                            score=round(score, 3),
                        )
                        results["auto_linked"].append(remote_id)
                    except Exception as e:
                        logger.warning(
                            "remote_link_creation_failed",
                            remote_id=remote_id,
                            issue_uuid=matched_issue.id,
                            error=str(e),
                        )

                elif match_type == "potential_duplicate" and matched_issue:
                    # Flag for user review - just log at debug, don't update files
                    # (Updating files for 296 potential duplicates was causing massive slowdown)
                    logger.debug(
                        "remote_issue_potential_duplicate",
                        remote_id=remote_id,
                        candidate_id=matched_issue.id,
                        score=round(score, 3),
                    )
                    results["potential_duplicates"].append(remote_id)

                else:
                    # Truly new remote issue - create it locally
                    logger.debug(
                        "remote_issue_no_match",
                        remote_id=remote_id,
                        best_score=round(score, 3) if score > 0 else 0,
                    )

                    try:
                        # Create new Issue from remote data
                        new_issue = self._create_issue_from_remote(
                            remote_id=remote_id, remote_issue=remote_issue
                        )

                        # Create the issue in the repository
                        created_issue = self.core.issues.create(
                            title=new_issue.title,
                            status=new_issue.status,
                            labels=new_issue.labels,
                            milestone=new_issue.milestone,
                            assignee=new_issue.assignee,
                            content=new_issue.content,
                        )

                        if not created_issue:
                            raise Exception("Failed to create issue in repository")

                        # Link it in the database using the created issue's ID
                        self.core.db.remote_links.link_issue(
                            issue_uuid=created_issue.id,
                            backend_name="github",
                            remote_id=remote_id,
                        )

                        logger.info(
                            "remote_issue_created_locally",
                            remote_id=remote_id,
                            issue_uuid=created_issue.id,
                            title=created_issue.title,
                            milestone=created_issue.milestone,
                        )
                        results["new_remote"].append(remote_id)
                    except Exception as e:
                        logger.warning(
                            "remote_issue_creation_failed",
                            remote_id=remote_id,
                            error=str(e),
                        )

            logger.info(
                "remote_matching_complete",
                auto_linked=len(results["auto_linked"]),
                potential_duplicates=len(results["potential_duplicates"]),
                new_remote=len(results["new_remote"]),
            )

        except Exception as e:
            logger.error(
                "remote_matching_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            # If matching fails, treat all unlinked as new
            for remote_id in remote_issues_data.keys():
                existing_issue_uuid = self.core.db.remote_links.get_issue_uuid(
                    backend_name="github", remote_id=remote_id
                )
                if not existing_issue_uuid:
                    results["new_remote"].append(remote_id)

        return results

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

            # 1. Authenticate with backend
            try:
                if not self.backend.authenticate():
                    report.error = "Backend authentication failed"
                    logger.error(
                        "backend_authentication_failed",
                        operation="authenticate",
                        backend_type=type(self.backend).__name__,
                        suggested_action="check_credentials",
                    )
                    return report
                logger.info("backend_authenticated_successfully")
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
                return report
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
                return report

            # 2. Get remote issues (dict format)
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
                    return report
                logger.info(
                    "remote_issues_fetched",
                    remote_count=len(remote_issues_data),
                )
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
                return report
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
                return report

            # 3. Get local issues
            try:
                logger.debug("fetching_local_issues")
                # Get ALL issues including archived for sync
                local_issues = self.core.issues.list_all_including_archived()
                if not local_issues:
                    local_issues = []
                logger.info(
                    "local_issues_fetched",
                    local_count=len(local_issues),
                )
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
                return report
            except Exception as e:
                report.error = f"Failed to fetch local issues: {str(e)}"
                logger.error(
                    "local_issues_fetch_error",
                    operation="fetch_local_issues",
                    error_type=type(e).__name__,
                    error=str(e),
                    error_classification="sync_error",
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
                # Count open vs closed remote issues
                remote_open_count = 0
                remote_closed_count = 0
                for issue_data in (
                    remote_issues_data.values() if remote_issues_data else []
                ):
                    # Check for 'state' field which is set to 'open' or 'closed'
                    state = getattr(issue_data, "state", None) or getattr(
                        issue_data, "status", "open"
                    )
                    if state and state.lower() == "closed":
                        remote_closed_count += 1
                    else:
                        remote_open_count += 1

                # Try to fetch remote milestones
                remote_milestones = self.backend.get_milestones()
                remote_milestones_count = (
                    len(remote_milestones) if remote_milestones else 0
                )
                logger.debug(
                    "remote_items_counted",
                    remote_issues=remote_issues_count,
                    remote_open=remote_open_count,
                    remote_closed=remote_closed_count,
                    remote_milestones=remote_milestones_count,
                )
            except Exception as e:
                logger.debug("remote_items_count_failed", error=str(e))
                remote_issues_count = 0
                remote_open_count = 0
                remote_closed_count = 0
                remote_milestones_count = 0

            # 4. Load previous sync state (base state for three-way merge)
            try:
                logger.debug("loading_sync_state")
                # Load baseline using database (preferred) or git history fallback
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

            # 3b. Match and link unlinked remote issues to local issues (if pulling)
            # This establishes connections before three-way merge analysis
            # Skip matching for push_only mode - duplicate detection happens during push_issue()
            if not push_only:
                _ = self._match_and_link_remote_issues(  # noqa: F841
                    local_issues_dict, remote_issues_data, dry_run=dry_run
                )

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
            report.remote_open_issues = remote_open_count
            report.remote_closed_issues = remote_closed_count
            report.remote_total_milestones = remote_milestones_count
            report.conflicts_detected = len(conflicts)
            report.issues_up_to_date = len(up_to_date)
            report.issues_needs_push = len(local_only_changes)
            report.issues_needs_pull = len(remote_only_changes)
            # Add all changes to report for verbose reporting
            report.changes = changes

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
                # Build a SyncPlan from detected changes and delegate application
                plan = SyncPlan()

                # Push local updates and resolved issues. Batch when multiple.
                issues_to_push = updates + resolved_issues
                if issues_to_push:
                    if len(issues_to_push) == 1:
                        issue = issues_to_push[0]
                        plan.add(PushAction(issue_id=issue.id, issue_payload=issue))
                    else:
                        # Add a single batch push action with list of Issue objects
                        plan.add(
                            Action(
                                action_type="push", payload={"issues": issues_to_push}
                            )
                        )

                # Pull remote changes
                if pulls:
                    # Use a single batch pull action (matching previous behavior of calling pull_issues)
                    plan.add(Action(action_type="pull", payload={"issue_ids": pulls}))

                # Execute the plan via the executor
                executor = SyncPlanExecutor(
                    transport_adapter=self.backend,
                    db_session=self.core.db if hasattr(self.core, "db") else None,
                    core=self.core,
                )
                exec_report = executor.execute(plan, dry_run=dry_run)

                # Merge executor report into our report
                pushed_count = getattr(exec_report, "issues_pushed", 0)
                pulled_count = getattr(exec_report, "issues_pulled", 0)
                report.issues_pushed = pushed_count
                report.issues_pulled = pulled_count
                if getattr(exec_report, "error", None):
                    report.error = exec_report.error

                # Update report counters similar to previous behavior
                if (pushed_count > 0 or pulled_count > 0) and not dry_run:
                    report.issues_needs_push = max(
                        0, report.issues_needs_push - pushed_count
                    )
                    report.issues_up_to_date = report.issues_up_to_date + pushed_count
                    report.issues_needs_pull = max(
                        0, report.issues_needs_pull - pulled_count
                    )
                    report.issues_up_to_date = report.issues_up_to_date + pulled_count
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
                                    pushed_count += 1
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
            # Pull remote updates (skip if push_only or dry_run)
            if not push_only and not dry_run and pulls:
                logger.info(
                    "pulling_remote_updates_start",
                    count=len(pulls),
                )
                try:
                    # Use batch pull with explicit issue list
                    pull_report = self.backend.pull_issues(pulls)
                    if pull_report and pull_report.errors:
                        logger.warning(
                            "pull_batch_had_errors",
                            error_count=len(pull_report.errors),
                            errors=str(pull_report.errors)[:200],
                        )
                        pull_errors = list(pull_report.errors.keys())

                    # Count successful pulls
                    if pull_report and pull_report.pulled:
                        pulled_count = len(pull_report.pulled)
                    else:
                        pulled_count = 0

                    # Update sync baseline state for all successfully pulled issues
                    # TODO: implement proper baseline tracking for pulled issues
                    # Currently: baseline is updated when issues are pushed, but not
                    # when pulled. This means next sync will re-pull the same issues.
                    # Need to:  1) Modify pull_issue to return local issue ID
                    #           2) Track mapping of remote -> local IDs in pull_report
                    #           3) Update baseline sequentially here after pull completes

                    logger.info(
                        "pulling_complete",
                        successful_count=pulled_count,
                        failed_count=len(pull_errors) if pull_errors else 0,
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

            # After applying changes, update report to reflect what was applied
            # Don't re-fetch from remote as state might not be updated yet on remote server
            if (pushed_count > 0 or pulled_count > 0) and not dry_run:
                try:
                    logger.debug(
                        "updating_report_after_apply",
                        pushed=pushed_count,
                        pulled=pulled_count,
                    )

                    # Since baseline was just updated via save_base_state() calls during push/pull,
                    # the pushed issues should now be in baseline matching local state.
                    # Update the report to reflect this without re-fetching (remote might have latency)

                    if pushed_count > 0:
                        # Issues we pushed are now in baseline matching local state
                        # Reduce needs_push count by pushed amount
                        report.issues_needs_push = max(
                            0, report.issues_needs_push - pushed_count
                        )
                        # Add them to up_to_date
                        report.issues_up_to_date = (
                            report.issues_up_to_date + pushed_count
                        )

                    if pulled_count > 0:
                        # Issues we pulled were remote-only, now local matches remote and baseline
                        # Reduce needs_pull count
                        report.issues_needs_pull = max(
                            0, report.issues_needs_pull - pulled_count
                        )
                        # Add them to up_to_date
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
                    # Don't fail - just return the original report

            return report

        except Exception as e:
            report.error = f"Error applying changes: {str(e)}"
            logger.exception(
                "apply_changes_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return report
