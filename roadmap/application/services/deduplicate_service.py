"""DeduplicateService - simple self-deduplication for local and remote issues.

Removes obvious duplicates within each dataset (local and remote).
Cross-linking between local and remote is handled by the normal sync machinery.

Features:
- Two-phase self-deduplication (local and remote datasets independently)
- Structured error handling with recovery
- Observability: metrics, tracing, and detailed logging
- Dry-run support for non-destructive testing
- Batch deletion for local duplicates (efficient database operations)
- Batch closure for remote duplicates (efficient API calls)
"""

import time
from dataclasses import dataclass
from typing import Any

from structlog import get_logger

from roadmap.common.observability.instrumentation import traced
from roadmap.common.services import log_event
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.repositories import IssueRepository as IssueRepositoryProtocol
from roadmap.core.services.sync.duplicate_detector import DuplicateDetector

logger = get_logger(__name__)


@dataclass
class DeduplicateResponse:
    """Output of deduplication phase."""

    local_issues: list[Issue]
    remote_issues: dict[str, SyncIssue]
    duplicates_removed: int


class DeduplicateService:
    """Self-deduplication service: remove duplicates within local and remote datasets.

    This service only deduplicates issues within each dataset (local vs local, remote vs remote).
    Cross-matching between local and remote is handled by IssueMatchingService during sync.

    Deletion strategy:
    - Local duplicates: Delete from local database via issue_repo (batch operation)
    - Remote duplicates: Close on backend (GitHub) via batch API calls
    """

    def __init__(
        self,
        issue_repo: IssueRepositoryProtocol,
        duplicate_detector: DuplicateDetector,
        backend: Any | None = None,
    ):
        """Initialize deduplication service.

        Args:
            issue_repo: Repository for reading/writing issues (used to delete duplicates)
            duplicate_detector: Service for detecting duplicates within datasets
            backend: Optional sync backend for closing remote duplicates (GitHub, etc.)
        """
        self.issue_repo = issue_repo
        self.detector = duplicate_detector
        self.backend = backend

    @traced("deduplicate_service_execute")
    def execute(
        self,
        local_issues: list[Issue],
        remote_issues: dict[str, SyncIssue],
        dry_run: bool = False,
    ) -> DeduplicateResponse:
        """Execute self-deduplication (within each dataset).

        Removes obvious duplicates within local issues and within remote issues.
        Does NOT cross-link local to remote (that's handled by IssueMatchingService).

        Args:
            local_issues: List of local issues
            remote_issues: Dict of remote issues (key=id, value=SyncIssue)
            dry_run: If True, don't actually delete duplicates from database

        Returns:
            DeduplicateResponse with clean data and count of duplicates removed
        """
        start_time = time.time()

        logger.info(
            "deduplication_starting",
            local_count=len(local_issues),
            remote_count=len(remote_issues),
            dry_run=dry_run,
        )

        # Phase 1: Deduplicate local issues within themselves
        phase1_start = time.time()
        try:
            logger.debug("deduplication_phase_1_starting", dataset="local")
            deduplicated_local = self.detector.local_self_dedup(local_issues)
            local_dup_ids = {i.id for i in local_issues} - {
                i.id for i in deduplicated_local
            }
            phase1_elapsed = time.time() - phase1_start
            logger.debug(
                "deduplication_phase_1_complete",
                dataset="local",
                duplicates_found=len(local_dup_ids),
                duration_seconds=round(phase1_elapsed, 3),
            )
        except Exception as e:
            logger.error(
                "deduplication_phase_1_failed",
                dataset="local",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Phase 2: Deduplicate remote issues within themselves
        phase2_start = time.time()
        try:
            logger.debug("deduplication_phase_2_starting", dataset="remote")
            deduplicated_remote = self.detector.remote_self_dedup(remote_issues)
            remote_dup_ids = set(remote_issues.keys()) - set(deduplicated_remote.keys())
            # Also track by SyncIssue.id for filtering
            remote_dup_issue_ids = {remote_issues[k].id for k in remote_dup_ids}
            phase2_elapsed = time.time() - phase2_start
            logger.debug(
                "deduplication_phase_2_complete",
                dataset="remote",
                duplicates_found=len(remote_dup_ids),
                duration_seconds=round(phase2_elapsed, 3),
            )
        except Exception as e:
            logger.error(
                "deduplication_phase_2_failed",
                dataset="remote",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        total_duplicates = len(local_dup_ids) + len(remote_dup_ids)

        logger.info(
            "deduplication_detected",
            local_duplicates=len(local_dup_ids),
            remote_duplicates=len(remote_dup_ids),
            total=total_duplicates,
        )

        # Execute deletions if not dry run
        deletion_start = time.time()
        executed_count = 0
        deletion_errors = []
        deletion_elapsed = 0.0  # Initialize to 0.0 for dry_run case

        if not dry_run and total_duplicates > 0:
            logger.info(
                "batch_deletion_starting",
                total_count=total_duplicates,
                local_count=len(local_dup_ids),
                remote_count=len(remote_dup_issue_ids),
            )

            # Phase A: Delete local duplicates from database (batch)
            local_deleted = self._delete_local_duplicates(
                local_dup_ids, deletion_errors
            )

            # Phase B: Delete remote duplicates via GraphQL (batch)
            remote_deleted = self._close_remote_duplicates(
                remote_dup_issue_ids, remote_issues, deletion_errors
            )

            deletion_elapsed = time.time() - deletion_start
            executed_count = local_deleted + remote_deleted

            if executed_count > 0:
                rate = executed_count / deletion_elapsed if deletion_elapsed > 0 else 0
                logger.info(
                    "batch_deletion_complete",
                    deleted_count=executed_count,
                    local_deleted=local_deleted,
                    remote_deleted=remote_deleted,
                    duration_seconds=round(deletion_elapsed, 3),
                    rate_per_second=round(rate, 1),
                )

            if deletion_errors:
                logger.warning(
                    "batch_deletion_with_errors",
                    successful=executed_count,
                    failed=len(deletion_errors),
                    errors=deletion_errors,
                )
            else:
                logger.info(
                    "duplicates_deleted_successfully",
                    count=executed_count,
                    local_deleted=local_deleted,
                    remote_deleted=remote_deleted,
                )

        # Build return data with duplicates filtered out
        all_dup_ids = local_dup_ids | remote_dup_issue_ids
        clean_local = [i for i in local_issues if i.id not in all_dup_ids]
        clean_remote = {
            k: v for k, v in remote_issues.items() if v.id not in all_dup_ids
        }

        duration_seconds = time.time() - start_time

        log_event(
            "deduplication_phase_complete",
            local_before=len(local_issues),
            local_after=len(clean_local),
            local_reduction_pct=(
                (len(local_dup_ids) / len(local_issues) * 100) if local_issues else 0.0
            ),
            remote_before=len(remote_issues),
            remote_after=len(clean_remote),
            remote_reduction_pct=(
                (len(remote_dup_ids) / len(remote_issues) * 100)
                if remote_issues
                else 0.0
            ),
            duplicates_removed=total_duplicates,
            execution_duration_seconds=round(duration_seconds, 3),
            dry_run=dry_run,
        )

        logger.info(
            "deduplication_complete",
            local_before=len(local_issues),
            local_after=len(clean_local),
            remote_before=len(remote_issues),
            remote_after=len(clean_remote),
            duplicates_removed=total_duplicates,
            duration_seconds=round(duration_seconds, 3),
            timing_breakdown={
                "phase1_local_seconds": round(phase1_elapsed, 3),
                "phase2_remote_seconds": round(phase2_elapsed, 3),
                "deletion_seconds": round(deletion_elapsed, 3),
            },
        )

        return DeduplicateResponse(
            local_issues=clean_local,
            remote_issues=clean_remote,
            duplicates_removed=total_duplicates,
        )

    def _safe_delete_duplicate(
        self,
        issue_id: str,
        source: str,
        error_list: list[dict] | None = None,
    ) -> None:
        """Safely delete a duplicate issue with error handling.

        Args:
            issue_id: ID of the duplicate issue to delete
            source: Source of the duplicate (local or remote)
            error_list: Optional list to accumulate errors instead of raising
        """
        try:
            logger.debug(
                "deleting_duplicate",
                issue_id=issue_id,
                source=source,
            )
            self.issue_repo.delete(issue_id)
            logger.debug(
                "deleted_duplicate",
                issue_id=issue_id,
                source=source,
            )
        except Exception as e:
            logger.error(
                "duplicate_deletion_failed",
                issue_id=issue_id,
                source=source,
                error=str(e),
                error_type=type(e).__name__,
            )
            if error_list is not None:
                error_list.append(
                    {
                        "issue_id": issue_id,
                        "source": source,
                        "error": str(e),
                    }
                )
            else:
                raise

    def _delete_local_duplicates(
        self,
        local_dup_ids: set[str],
        error_list: list[dict],
    ) -> int:
        """Delete local duplicate issues in batch.

        Args:
            local_dup_ids: Set of local issue IDs to delete
            error_list: List to accumulate errors

        Returns:
            Number of successfully deleted issues
        """
        if not local_dup_ids:
            return 0

        delete_start = time.time()
        try:
            deleted_count = self.issue_repo.delete_many(list(local_dup_ids))
            delete_elapsed = time.time() - delete_start
            rate = deleted_count / delete_elapsed if delete_elapsed > 0 else 0

            logger.info(
                "local_duplicates_deleted",
                deleted_count=deleted_count,
                attempted_count=len(local_dup_ids),
                duration_seconds=round(delete_elapsed, 3),
                rate_per_second=round(rate, 1),
            )
            return deleted_count
        except Exception as e:
            delete_elapsed = time.time() - delete_start
            logger.error(
                "local_duplicates_deletion_failed",
                attempted=len(local_dup_ids),
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(delete_elapsed, 3),
            )
            error_list.append(
                {
                    "operation": "delete_local_duplicates",
                    "error": str(e),
                    "count": len(local_dup_ids),
                }
            )
            return 0

    def _close_remote_duplicates(
        self,
        remote_dup_issue_ids: set[str],
        remote_issues: dict[str, SyncIssue],
        error_list: list[dict],
    ) -> int:
        """Delete remote duplicate issues in batch via backend using GraphQL.

        Args:
            remote_dup_issue_ids: Set of remote issue IDs to delete
            remote_issues: Dict of all remote issues (for reference)
            error_list: List to accumulate errors

        Returns:
            Number of successfully deleted issues
        """
        if not remote_dup_issue_ids or not self.backend:
            if not self.backend and remote_dup_issue_ids:
                logger.warning(
                    "remote_duplicates_skipped_no_backend",
                    count=len(remote_dup_issue_ids),
                    reason="Backend not available",
                )
            return 0

        delete_start = time.time()
        deleted_count = 0

        try:
            # Get remote issue numbers from the SyncIssue objects
            issues_to_delete = []
            for dup_id in remote_dup_issue_ids:
                # Find the corresponding SyncIssue to get metadata
                for sync_issue in remote_issues.values():
                    if sync_issue.id == dup_id:
                        # Use backend_id (issue number) for GitHub
                        issue_number = sync_issue.backend_id
                        if issue_number:
                            issues_to_delete.append(
                                {
                                    "id": dup_id,
                                    "number": issue_number,
                                    "title": sync_issue.title,
                                }
                            )
                        break

            if not issues_to_delete:
                logger.info(
                    "remote_duplicates_no_numbers",
                    duplicate_count=len(remote_dup_issue_ids),
                )
                return 0

            logger.info(
                "deleting_remote_duplicates_starting",
                count=len(issues_to_delete),
            )

            # Use backend.delete_issues() for GraphQL batch deletion
            if hasattr(self.backend, "delete_issues"):
                # Backend supports batch deletion via GraphQL
                issue_numbers = [issue["number"] for issue in issues_to_delete]
                deleted_count = self.backend.delete_issues(issue_numbers)
            else:
                logger.warning(
                    "backend_no_delete_method",
                    backend_type=type(self.backend).__name__,
                )
                return 0

            delete_elapsed = time.time() - delete_start
            rate = deleted_count / delete_elapsed if delete_elapsed > 0 else 0

            logger.info(
                "remote_duplicates_deleted",
                deleted_count=deleted_count,
                attempted_count=len(issues_to_delete),
                failed_count=len(issues_to_delete) - deleted_count,
                duration_seconds=round(delete_elapsed, 3),
                rate_per_second=round(rate, 1),
            )

            if deleted_count < len(issues_to_delete):
                error_list.append(
                    {
                        "operation": "delete_remote_duplicates",
                        "error": f"Failed to delete {len(issues_to_delete) - deleted_count} remote issues",
                        "total_attempted": len(issues_to_delete),
                    }
                )

            return deleted_count

        except Exception as e:
            delete_elapsed = time.time() - delete_start
            logger.error(
                "remote_duplicates_deletion_failed",
                attempted=len(remote_dup_issue_ids),
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(delete_elapsed, 3),
            )
            error_list.append(
                {
                    "operation": "delete_remote_duplicates",
                    "error": str(e),
                    "count": len(remote_dup_issue_ids),
                }
            )
            return 0
