"""Orchestrates sync merge operations with extracted service components.

This class coordinates the sync process by delegating to specialized services
for baseline management, pull processing, change filtering, and conflict conversion.
"""

from typing import Any

from structlog import get_logger

from roadmap.adapters.sync.services.baseline_state_handler import (
    BaselineStateHandler,
)
from roadmap.adapters.sync.services.conflict_converter import ConflictConverter
from roadmap.adapters.sync.services.local_change_filter import LocalChangeFilter
from roadmap.adapters.sync.services.pull_result_processor import PullResultProcessor
from roadmap.adapters.sync.services.remote_issue_creation_service import (
    RemoteIssueCreationService,
)
from roadmap.adapters.sync.services.sync_state_update_service import (
    SyncStateUpdateService,
)
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.sync_conflict_resolver import (
    ConflictStrategy,
    SyncConflictResolver,
)
from roadmap.core.services.sync.sync_plan import (
    Action,
    PushAction,
    SyncPlan,
)
from roadmap.core.services.sync.sync_plan_executor import SyncPlanExecutor
from roadmap.core.services.sync.sync_report import SyncReport
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync.sync_state_manager import SyncStateManager
from roadmap.core.services.utils.remote_fetcher import RemoteFetcher

logger = get_logger(__name__)


class SyncMergeEngine:
    """Orchestrates sync merge operations using specialized service components."""

    def __init__(
        self,
        core: Any,
        backend: Any,
        state_comparator: SyncStateComparator,
        conflict_resolver: SyncConflictResolver,
        state_manager: SyncStateManager,
    ):
        """Initialize SyncMergeEngine.

        Args:
            core: Core roadmap instance.
            backend: Sync backend.
            state_comparator: State comparator service.
            conflict_resolver: Conflict resolver service.
            state_manager: State manager service.
        """
        self.core = core
        self.backend = backend
        self.state_comparator = state_comparator
        self.conflict_resolver = conflict_resolver
        self.state_manager = state_manager

        # Initialize delegated services for specific concerns
        self._issue_creation_service = RemoteIssueCreationService(core)
        self._state_update_service = SyncStateUpdateService(state_manager)
        self._baseline_handler = BaselineStateHandler(core, self._state_update_service)
        self._conflict_converter = ConflictConverter(state_comparator)

    def _load_baseline_state(self):
        """Load baseline state using the baseline handler."""
        return self._baseline_handler.load_baseline_state()

    def _process_fetched_pull_result(self, fetched):
        """Process pull result using the pull result processor."""
        return PullResultProcessor.process_pull_result(fetched)

    def _update_baseline_for_pulled(self, pulled_remote_ids: list[str]) -> None:
        """Update baseline after pulling using the baseline handler."""
        self._baseline_handler.update_baseline_for_pulled(pulled_remote_ids)

    def _filter_unchanged_issues_from_base(
        self, issues: list, current_local: dict, base_state_issues: dict
    ) -> list:
        """Filter unchanged issues using the local change filter."""
        return LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

    def _convert_issue_changes_to_conflicts(self, issue_changes: list) -> list:
        """Convert issue changes to conflicts using the conflict converter."""
        return self._conflict_converter.convert_changes_to_conflicts(issue_changes)

    def _create_issue_from_remote(
        self, remote_id: str | int, remote_issue: SyncIssue
    ) -> Issue:
        return self._issue_creation_service.create_issue_from_remote(
            remote_id, remote_issue
        )

    def _analyze_changes(self, local_issues_dict, remote_issues_data, base_state):
        return self.state_comparator.analyze_three_way(
            local_issues_dict,
            remote_issues_data,
            base_state.issues if base_state else None,
        )

    def _analyze_and_classify(self, local_issues_dict, remote_issues_data, base_state):
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

    def _resolve_conflicts_if_needed(self, conflicts, force_local, force_remote):
        if not conflicts:
            return []
        strategy = (
            ConflictStrategy.KEEP_LOCAL
            if force_local
            else ConflictStrategy.KEEP_REMOTE
            if force_remote
            else ConflictStrategy.AUTO_MERGE
        )
        try:
            conflict_objects = self._convert_issue_changes_to_conflicts(conflicts)
            resolved_issues = self.conflict_resolver.resolve_batch(
                conflict_objects, strategy
            )
            logger.info(
                "conflicts_resolved",
                count=len(resolved_issues),
                strategy=strategy.value,
            )
            return resolved_issues
        except Exception as e:
            logger.warning(
                "conflicts_resolution_failed",
                error=str(e),
                strategy=getattr(strategy, "value", None),
                exc_info=True,
            )
            return []

    def _apply_plan(
        self,
        updates,
        resolved_issues,
        pulls,
        dry_run,
        push_only,  # noqa: F841
        pull_only,  # noqa: F841
        report: SyncReport,
    ):
        plan = SyncPlan()

        issues_to_push = updates + resolved_issues
        if issues_to_push:
            if len(issues_to_push) == 1:
                issue = issues_to_push[0]
                plan.add(PushAction(issue_id=issue.id, issue_payload=issue))
            else:
                plan.add(Action(action_type="push", payload={"issues": issues_to_push}))

        if pulls:
            plan.add(Action(action_type="pull", payload={"issue_ids": pulls}))

        executor = SyncPlanExecutor(
            transport_adapter=self.backend,
            db_session=self.core.db if hasattr(self.core, "db") else None,
            core=self.core,
        )
        exec_report = executor.execute(plan, dry_run=dry_run)

        pushed_count = getattr(exec_report, "issues_pushed", 0)
        pulled_count = getattr(exec_report, "issues_pulled", 0)
        report.issues_pushed = pushed_count
        report.issues_pulled = pulled_count
        if getattr(exec_report, "error", None):
            report.error = exec_report.error

        if (pushed_count > 0 or pulled_count > 0) and not dry_run:
            report.issues_needs_push = max(0, report.issues_needs_push - pushed_count)
            report.issues_up_to_date = report.issues_up_to_date + pushed_count
            report.issues_needs_pull = max(0, report.issues_needs_pull - pulled_count)
            report.issues_up_to_date = report.issues_up_to_date + pulled_count

        return report

    def _push_updates(self, issues_to_push: list, report: SyncReport):
        pushed_count = 0
        push_errors = []

        issue_ids = [issue.id for issue in issues_to_push]
        logger.info(
            "pushing_issues_start",
            count=len(issue_ids),
            ids=",".join(issue_ids[:5]),
            total_ids=len(issue_ids),
        )

        try:
            if len(issues_to_push) == 1:
                issue = issues_to_push[0]
                logger.debug(
                    "pushing_single_issue",
                    issue_id=issue.id,
                    issue_title=(
                        issue.title[:50] if getattr(issue, "title", None) else None
                    ),
                )
                success = self.backend.push_issue(issue)
                if not success:
                    report.error = "Failed to push issue"
                    logger.error(
                        "push_single_issue_failed",
                        issue_id=issue.id,
                        issue_title=getattr(issue, "title", None),
                    )
                    push_errors.append(issue.id)
                else:
                    try:
                        self.state_manager.save_base_state(issue, remote_version=True)
                        pushed_count += 1
                        logger.debug(
                            "single_issue_sync_state_updated", issue_id=issue.id
                        )
                    except Exception as e:
                        logger.warning(
                            "single_issue_state_update_failed",
                            issue_id=issue.id,
                            error=str(e),
                        )
            else:
                logger.debug("pushing_batch_issues", batch_size=len(issues_to_push))
                push_report = self.backend.push_issues(issues_to_push)
                if push_report and getattr(push_report, "errors", None):
                    report.error = f"Push failed: {getattr(push_report, 'errors', {})}"
                    logger.error(
                        "push_batch_failed",
                        error_count=len(getattr(push_report, "errors", {})),
                        errors=str(getattr(push_report, "errors", {}))[:200],
                    )
                    try:
                        push_errors = (
                            list(push_report.errors.keys())
                            if isinstance(push_report.errors, dict)
                            else []
                        )
                    except Exception:
                        push_errors = []
                else:
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
                "push_operation_exception", error=str(e), error_type=type(e).__name__
            )
            pushed_count = 0

        return pushed_count, push_errors

    def _pull_updates(self, pulls: list):
        pulled_count = 0
        pull_errors = []
        pulled_remote_ids = []

        logger.info("pulling_remote_updates_start", count=len(pulls))
        try:
            fetched = RemoteFetcher.fetch_issues(self.backend, pulls)
            pulled_count, pull_errors, pulled_remote_ids = (
                self._process_fetched_pull_result(fetched)
            )

            try:
                self._update_baseline_for_pulled(pulled_remote_ids)
            except Exception:
                logger.debug(
                    "pull_baseline_update_skipped", reason="baseline_update_error"
                )

            logger.info(
                "pulling_complete",
                successful_count=pulled_count,
                failed_count=len(pull_errors) if pull_errors else 0,
            )
        except Exception as e:
            logger.error(
                "pull_operation_exception", error=str(e), error_type=type(e).__name__
            )
            pulled_count = 0

        return pulled_count, pull_errors

    def _match_and_link_remote_issues(
        self, local_issues_dict: dict, remote_issues_data: dict, dry_run: bool = False
    ) -> dict[str, list[Any]]:
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
            local_issues = list(local_issues_dict.values())
            matcher = __import__(
                "roadmap.core.services.issue_matching_service",
                fromlist=["IssueMatchingService"],
            ).IssueMatchingService(local_issues)

            all_remote_ids = list(remote_issues_data.keys())
            existing_links = {}
            try:
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
                if remote_id in existing_links:
                    logger.debug(
                        "remote_issue_already_linked",
                        remote_id=remote_id,
                        issue_uuid=existing_links[remote_id],
                    )
                    continue

                matched_issue, score, match_type = matcher.find_best_match(remote_issue)

                if match_type == "auto_link" and matched_issue:
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
                    logger.debug(
                        "remote_issue_potential_duplicate",
                        remote_id=remote_id,
                        candidate_id=matched_issue.id,
                        score=round(score, 3),
                    )
                    results["potential_duplicates"].append(remote_id)

                else:
                    logger.debug(
                        "remote_issue_no_match",
                        remote_id=remote_id,
                        best_score=round(score, 3) if score > 0 else 0,
                    )

                    try:
                        new_issue = self._create_issue_from_remote(
                            remote_id=remote_id, remote_issue=remote_issue
                        )

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
            for remote_id in remote_issues_data.keys():
                existing_issue_uuid = self.core.db.remote_links.get_issue_uuid(
                    backend_name="github", remote_id=remote_id
                )
                if not existing_issue_uuid:
                    results["new_remote"].append(remote_id)

        return results

    def _count_remote_stats(self, remote_issues_data):
        try:
            remote_issues_count = len(remote_issues_data) if remote_issues_data else 0
            remote_open_count = 0
            remote_closed_count = 0
            for issue_data in remote_issues_data.values() if remote_issues_data else []:
                state = getattr(issue_data, "state", None) or getattr(
                    issue_data, "status", "open"
                )
                if state and state.lower() == "closed":
                    remote_closed_count += 1
                else:
                    remote_open_count += 1

            remote_milestones = self.backend.get_milestones()
            remote_milestones_count = len(remote_milestones) if remote_milestones else 0
            logger.debug(
                "remote_items_counted",
                remote_issues=remote_issues_count,
                remote_open=remote_open_count,
                remote_closed=remote_closed_count,
                remote_milestones=remote_milestones_count,
            )
        except Exception:
            remote_issues_count = 0
            remote_open_count = 0
            remote_closed_count = 0
            remote_milestones_count = 0

        return (
            remote_issues_count,
            remote_open_count,
            remote_closed_count,
            remote_milestones_count,
        )
