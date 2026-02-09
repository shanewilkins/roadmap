"""SyncPlan executor scaffold for Phase 3 of the sync refactor.

The executor consumes a `SyncPlan` (an ordered collection of `Action`s)
and applies them, producing a `SyncReport` summarizing results. This
module provides a minimal, testable API surface to be implemented in
subsequent steps.

This file is intentionally small and self-contained: it defines the
runtime contract for the executor so other refactors can target it.
"""

from __future__ import annotations

from typing import Any

import structlog

from roadmap.core.services.sync.sync_plan import SyncPlan
from roadmap.core.services.sync.sync_report import SyncReport

logger = structlog.get_logger()


class SyncPlanExecutor:
    """Executor responsible for applying a `SyncPlan`.

    Responsibilities:
    - Apply actions from a `SyncPlan` in deterministic order.
    - Respect `dry_run` (simulate only when True).
    - Record per-action results into a `SyncReport` (report type is
      produced by the analyzer module).
    - Provide hooks for batching, tracing, and pluggable transport
      adapters.

    This scaffold intentionally does not implement applying actions —
    it defines the constructor and main `execute` API to be filled in
    during Phase 3 implementation.
    """

    def __init__(
        self,
        transport_adapter: Any = None,
        db_session: Any = None,
        core: Any = None,
        tracer: Any | None = None,
        *,
        stop_on_error: bool = True,
    ):
        """Create an executor.

        Args:
            transport_adapter: Adapter for remote API calls (pluggable).
            db_session: Database session / unit-of-work used for persisting state.
            core: Optional RoadmapCore instance exposing higher-level services.
            tracer: Optional tracing/tracing client for observability.
            stop_on_error: If True, abort execution on first unrecoverable error.
        """
        self.transport_adapter = transport_adapter
        self.db_session = db_session
        self.core = core
        self.tracer = tracer
        self.stop_on_error = stop_on_error

        # A minimal local cache for created IDs during a single execute run
        self._created_local_ids: dict[str, str] = {}

    def execute(
        self,
        plan: SyncPlan,
        dry_run: bool = True,
        initial_report: SyncReport | None = None,
    ) -> SyncReport:
        """Execute the provided `plan`.

        Iterate the plan's actions, apply them (or simulate when
        `dry_run=True`), and return a `SyncReport` summarizing outcomes.
        """
        report = initial_report or SyncReport()
        self._accumulated_errors = {}

        for action in getattr(plan, "actions", []):
            try:
                result = self._apply_action(action, dry_run=dry_run)
                # Triage basic results into the SyncReport when possible
                if not dry_run and result:
                    if action.action_type == "push":
                        # result is either bool (single item) or int (batch count)
                        push_count = (
                            result if isinstance(result, int) else (1 if result else 0)
                        )
                        report.issues_pushed += push_count
                    elif action.action_type == "pull":
                        # result is either bool (single item) or int (batch count)
                        pull_count = (
                            result if isinstance(result, int) else (1 if result else 0)
                        )
                        report.issues_pulled += pull_count
            except Exception as e:
                logger.error(
                    "sync_action_execution_failed",
                    operation="execute_action",
                    action_type=getattr(action, "action_type", None),
                    error=str(e),
                    action="Recording error and checking stop_on_error",
                    severity="system_error",
                )
                # Record top-level error and optionally stop
                report.error = str(e)
                if self.stop_on_error:
                    return report

        # Transfer accumulated errors to the report
        if self._accumulated_errors:
            report.errors.update(self._accumulated_errors)

        return report

    def _apply_action(self, action: Any, dry_run: bool = True) -> Any:
        """Apply a single action.

        Concrete implementations map action types to handler methods
        (e.g., _handle_push, _handle_pull, _handle_link) and return a
        handler-specific result.
        """
        t = getattr(action, "action_type", None)

        if t == "push":
            return self._handle_push(action, dry_run=dry_run)
        if t == "pull":
            return self._handle_pull(action, dry_run=dry_run)
        if t == "create_local":
            return self._handle_create_local(action, dry_run=dry_run)
        if t == "link":
            return self._handle_link(action, dry_run=dry_run)
        if t == "update_baseline":
            return self._handle_update_baseline(action, dry_run=dry_run)
        if t == "resolve_conflict":
            return self._handle_resolve_conflict(action, dry_run=dry_run)

        # Unknown action: no-op
        return None

    def _handle_push(self, action: Any, dry_run: bool = True) -> bool | int:
        # Support both single-issue ('issue') and batch ('issues') push actions
        issue = action.payload.get("issue")
        issues = action.payload.get("issues")

        if dry_run:
            return False

        adapter = self.transport_adapter
        if adapter is None:
            return False

        # Batch push when provided
        if issues and hasattr(adapter, "push_issues"):
            try:
                r = adapter.push_issues(issues)
                r = self._unwrap_result(r, operation="push_issues")
                if r is None:
                    return False
                # Store errors from the push operation if available
                if hasattr(r, "errors") and r.errors:
                    if not hasattr(self, "_accumulated_errors"):
                        self._accumulated_errors = {}
                    self._accumulated_errors.update(r.errors)
                # Return count of successfully pushed items
                pushed_list = getattr(r, "pushed", [])
                return len(pushed_list) if pushed_list else False
            except Exception as e:
                logger.debug(
                    "batch_push_failed",
                    operation="push_issues_batch",
                    issue_count=len(issues),
                    error=str(e),
                    action="Falling back to single-issue push",
                )
                return False

        # Fallback to single-issue push
        if issue and hasattr(adapter, "push_issue"):
            try:
                result = adapter.push_issue(issue)
                result = self._unwrap_result(
                    result,
                    operation="push_issue",
                    issue_id=getattr(issue, "id", None),
                )
                return bool(result) if result is not None else False
            except Exception as e:
                logger.debug(
                    "single_push_failed",
                    operation="push_issue",
                    issue_id=getattr(issue, "id", None),
                    error=str(e),
                    action="Returning False",
                )
                return False

        return False

    def _handle_pull(self, action: Any, dry_run: bool = True) -> bool | int:
        # Support both single-id ('issue_id') and batch ('issue_ids') pull actions
        issue_id = action.payload.get("issue_id")
        issue_ids = action.payload.get("issue_ids")
        if dry_run:
            return False

        adapter = self.transport_adapter
        if adapter is None:
            return False

        # If a batch of issue IDs were provided, prefer batch API
        if issue_ids and hasattr(adapter, "pull_issues"):
            try:
                r = adapter.pull_issues(issue_ids)
                r = self._unwrap_result(r, operation="pull_issues")
                if r is None:
                    return False
                # Store errors from the pull operation if available
                if hasattr(r, "errors") and r.errors:
                    if not hasattr(self, "_accumulated_errors"):
                        self._accumulated_errors = {}
                    self._accumulated_errors.update(r.errors)
                # Return count of successfully pulled items
                pulled_list = getattr(r, "pulled", [])
                return len(pulled_list) if pulled_list else False
            except Exception as e:
                logger.debug(
                    "batch_pull_failed",
                    operation="pull_issues_batch",
                    issue_count=len(issue_ids),
                    error=str(e),
                    action="Falling back to single-issue pull",
                )
                return False

        # Fallback to single-issue pull if available
        if issue_id and hasattr(adapter, "pull_issue"):
            try:
                result = adapter.pull_issue(issue_id)
                result = self._unwrap_result(
                    result,
                    operation="pull_issue",
                    issue_id=issue_id,
                )
                return bool(result) if result is not None else False
            except Exception as e:
                logger.debug(
                    "single_pull_failed",
                    operation="pull_issue",
                    issue_id=issue_id,
                    error=str(e),
                    action="Continuing to return False",
                )

        return False

    def _unwrap_result(
        self,
        result: Any,
        operation: str,
        issue_id: str | None = None,
    ) -> Any | None:
        """Unwrap Result objects and record errors consistently.

        Returns the unwrapped value for Ok results. For Err results, records
        the error and returns None (or raises if stop_on_error is True).
        """
        if hasattr(result, "is_err") and callable(result.is_err):
            if result.is_err():
                error = result.unwrap_err()
                self._record_result_error(operation, error, issue_id)
                if self.stop_on_error:
                    raise RuntimeError(str(error))
                return None
            return result.unwrap()

        return result

    def _record_result_error(
        self,
        operation: str,
        error: Any,
        issue_id: str | None = None,
    ) -> None:
        """Store a Result error in the accumulated error map."""
        if not hasattr(self, "_accumulated_errors"):
            self._accumulated_errors = {}

        key = issue_id
        if not key and hasattr(error, "entity_id"):
            key = getattr(error, "entity_id")
        if not key:
            key = operation

        message = str(error)
        if key in self._accumulated_errors:
            suffix = len(self._accumulated_errors) + 1
            key = f"{key}:{suffix}"
        self._accumulated_errors[key] = message

    def _handle_create_local(self, action: Any, dry_run: bool = True) -> str | None:
        remote_id = action.payload.get("remote_id")
        remote_payload = action.payload.get("remote") or {}

        if dry_run:
            fake_id = f"dry-{remote_id}"
            self._created_local_ids[str(remote_id)] = fake_id
            return fake_id

        if self.core and getattr(self.core, "issue_service", None):
            try:
                issue = self.core.issue_service.create_issue(remote_payload)
                created_id = (
                    getattr(issue, "id", None)
                    or getattr(issue, "uuid", None)
                    or str(issue)
                )
                self._created_local_ids[str(remote_id)] = created_id
                return created_id
            except Exception as e:
                logger.debug(
                    "create_local_issue_failed",
                    operation="create_issue",
                    remote_id=str(remote_id),
                    error=str(e),
                    action="Trying fallback database method",
                )
                return None

        if self.db_session and hasattr(self.db_session, "create_issue"):
            try:
                created_id = self.db_session.create_issue(remote_payload)
                self._created_local_ids[str(remote_id)] = created_id
                return created_id
            except Exception as e:
                logger.debug(
                    "create_issue_db_failed",
                    operation="create_issue_db_session",
                    remote_id=str(remote_id),
                    error=str(e),
                    action="Returning None",
                )
                return None

        return None

    def _handle_link(self, action: Any, dry_run: bool = True) -> bool:
        local_id = action.payload.get("issue_id")
        backend = action.payload.get("backend")
        remote_id = action.payload.get("remote_id")

        if dry_run:
            return True

        repo = None
        if self.core and getattr(self.core, "remote_link_repo", None):
            repo = self.core.remote_link_repo

        if (
            repo is None
            and self.db_session
            and getattr(self.db_session, "remote_link_repo", None)
        ):
            repo = self.db_session.remote_link_repo

        from roadmap.infrastructure.sync_gateway import SyncGateway

        return SyncGateway.link_issue_in_database(repo, local_id, backend, remote_id)

    def _handle_update_baseline(self, action: Any, dry_run: bool = True) -> bool:
        baseline = action.payload.get("baseline")
        if dry_run:
            return True

        if (
            self.core
            and getattr(self.core, "db", None)
            and hasattr(self.core.db, "set_sync_baseline")
        ):
            try:
                self.core.db.set_sync_baseline(baseline)
                return True
            except Exception as e:
                logger.debug(
                    "set_sync_baseline_failed",
                    operation="set_sync_baseline_core",
                    error=str(e),
                    action="Trying fallback database method",
                )
                return False

        if self.db_session and hasattr(self.db_session, "set_sync_baseline"):
            try:
                self.db_session.set_sync_baseline(baseline)
                return True
            except Exception as e:
                logger.debug(
                    "set_sync_baseline_db_failed",
                    operation="set_sync_baseline_db_session",
                    error=str(e),
                    action="Returning False",
                )
                return False

        return False

    def _handle_resolve_conflict(self, action: Any, dry_run: bool = True) -> bool:
        issue_id = action.payload.get("issue_id")
        resolution = action.payload.get("resolution")

        if dry_run:
            return True

        adapter = self.transport_adapter
        if adapter and hasattr(adapter, "resolve_conflict"):
            try:
                return adapter.resolve_conflict(issue_id, resolution)
            except Exception as e:
                logger.debug(
                    "resolve_conflict_adapter_failed",
                    operation="resolve_conflict",
                    issue_id=issue_id,
                    error=str(e),
                    action="Trying fallback database method",
                )
                return False

        if (
            self.core
            and getattr(self.core, "db", None)
            and hasattr(self.core.db, "apply_conflict_resolution")
        ):
            try:
                return self.core.db.apply_conflict_resolution(issue_id, resolution)
            except Exception as e:
                logger.debug(
                    "apply_conflict_resolution_failed",
                    operation="apply_conflict_resolution",
                    issue_id=issue_id,
                    error=str(e),
                    action="Returning False",
                )
                return False

        return False
