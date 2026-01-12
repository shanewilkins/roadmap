"""Extracted merge engine helpers used by SyncMergeOrchestrator.

This class holds helper implementations moved out of the large
`sync_merge_orchestrator.py` to make that file smaller and easier to
navigate. The orchestrator delegates to this engine for pure logic and
operations that depend on core/backend/state_manager.
"""

from datetime import UTC, datetime
from typing import Any

from structlog import get_logger

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.remote_fetcher import RemoteFetcher
from roadmap.core.services.sync_conflict_resolver import (
    Conflict,
    ConflictStrategy,
    SyncConflictResolver,
)
from roadmap.core.services.sync_plan import (
    Action,
    PushAction,
    SyncPlan,
)
from roadmap.core.services.sync_plan_executor import SyncPlanExecutor
from roadmap.core.services.sync_report import SyncReport
from roadmap.core.services.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync_state_manager import SyncStateManager

logger = get_logger(__name__)


class SyncMergeEngine:
    def __init__(
        self,
        core: Any,
        backend: Any,
        state_comparator: SyncStateComparator,
        conflict_resolver: SyncConflictResolver,
        state_manager: SyncStateManager,
    ):
        self.core = core
        self.backend = backend
        self.state_comparator = state_comparator
        self.conflict_resolver = conflict_resolver
        self.state_manager = state_manager

    def _load_baseline_state(self):
        try:
            from roadmap.core.models.sync_state import IssueBaseState, SyncState

            db_baseline = self.core.db.get_sync_baseline()
            if db_baseline:
                logger.debug(
                    "baseline_loaded_from_database", issue_count=len(db_baseline)
                )
                issues = {}
                for issue_id, data in db_baseline.items():
                    issues[issue_id] = IssueBaseState(
                        id=issue_id,
                        status=data.get("status", "todo"),
                        title="",
                        assignee=data.get("assignee"),
                        milestone=data.get("milestone"),
                        headline=data.get("headline", ""),
                        content=data.get("content", ""),
                        labels=data.get("labels", []),
                    )

                sync_state = SyncState(
                    last_sync=datetime.now(UTC),
                    backend="github",
                    issues=issues,
                )
                return sync_state

            logger.debug("baseline_not_found_in_database")
            return None

        except Exception as e:
            logger.warning(
                "baseline_load_failed", error=str(e), error_type=type(e).__name__
            )
            return None

    def _process_fetched_pull_result(self, fetched):
        pulled_count = 0
        pull_errors = []
        pulled_remote_ids = []

        if isinstance(fetched, list):
            pulled_items = [r for r in fetched if r]
            pulled_count = len(pulled_items)
            for item in pulled_items:
                try:
                    rid = getattr(item, "backend_id", None) or getattr(item, "id", None)
                    if rid is not None:
                        pulled_remote_ids.append(str(rid))
                except Exception:
                    continue
        else:
            pull_report = fetched
            if getattr(pull_report, "errors", None):
                try:
                    err_keys = (
                        list(pull_report.errors.keys())
                        if isinstance(pull_report.errors, dict)
                        else []
                    )
                except Exception:
                    err_keys = []
                pull_errors = err_keys
                logger.warning(
                    "pull_batch_had_errors",
                    error_count=len(pull_errors),
                    errors=str(pull_report.errors)[:200],
                )

            pulled_raw = getattr(pull_report, "pulled", None)
            if pulled_raw is None:
                pulled_count = 0
                pulled_remote_ids = []
            else:
                try:
                    pulled_iter = list(pulled_raw)
                except Exception:
                    pulled_iter = [pulled_raw]
                pulled_remote_ids = [str(i) for i in pulled_iter]
                pulled_count = len(pulled_remote_ids)

        return pulled_count, pull_errors, pulled_remote_ids

    def _update_baseline_for_pulled(self, pulled_remote_ids: list[str]) -> None:
        backend_name = (
            self.backend.get_backend_name()
            if hasattr(self.backend, "get_backend_name")
            else "github"
        )
        for remote_id in pulled_remote_ids:
            try:
                local_uuid = self.core.db.remote_links.get_issue_uuid(
                    backend_name=backend_name, remote_id=remote_id
                )
                if not local_uuid:
                    continue
                local_issue = self.core.issues.get(local_uuid)
                if not local_issue:
                    continue
                try:
                    self.state_manager.save_base_state(local_issue, remote_version=True)
                except Exception:
                    logger.debug(
                        "save_base_state_for_pulled_failed",
                        remote_id=remote_id,
                        local_uuid=local_uuid,
                    )
            except Exception:
                continue

    def _filter_unchanged_issues_from_base(
        self, issues: list, current_local: dict, base_state_issues: dict
    ) -> list:
        if not base_state_issues:
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
            if issue_id not in current_local:
                logger.debug(
                    "filter_issue_not_in_local",
                    issue_id=issue_id,
                    reason="might_be_stale",
                )
                continue
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

    def _convert_issue_changes_to_conflicts(self, issue_changes: list) -> list:
        from roadmap.core.services.sync_conflict_resolver import ConflictField

        conflicts: list[Conflict] = []

        for change in issue_changes:
            if (
                not change.has_conflict
                or not change.local_state
                or not change.remote_state
            ):
                continue
            try:
                conflicting_fields = []
                if change.local_changes:
                    for field_name, _change_info in change.local_changes.items():
                        if field_name in change.remote_changes:
                            conflict_field = ConflictField(
                                field_name=field_name,
                                local_value=change.local_state.__dict__.get(
                                    field_name, None
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
        backend_id = remote_issue.backend_id or remote_id
        title = remote_issue.title or f"GitHub #{backend_id}"
        body = remote_issue.headline or ""

        if body:
            content = f"{body}\n\n---\n*Synced from GitHub: #{backend_id}*"
        else:
            content = f"*Synced from GitHub: #{backend_id}*"

        status = Status.CLOSED if remote_issue.status == "closed" else Status.TODO

        labels = list(remote_issue.labels or [])
        if "synced:from-github" not in labels:
            labels.append("synced:from-github")

        milestone = remote_issue.milestone

        issue = Issue(
            title=title,
            headline=remote_issue.headline or None,
            content=content,
            labels=labels,
            assignee=remote_issue.assignee,
            milestone=milestone,
            status=status,
        )

        return issue

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
        push_only,
        pull_only,
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
