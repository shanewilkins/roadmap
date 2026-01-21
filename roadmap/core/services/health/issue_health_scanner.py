"""Issue-specific health scanner extracted from EntityHealthScanner.

This contains the logic that was previously embedded inside
`entity_health_scanner.EntityHealthScanner` for scanning `Issue` objects.
"""

from typing import Any

from roadmap.common.constants import Status
from roadmap.common.logging import get_logger
from roadmap.common.observability.instrumentation import traced
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.services.health.health_models import (
    EntityHealthReport,
    EntityType,
    HealthIssue,
    HealthSeverity,
)

logger = get_logger(__name__)


class IssueHealthScanner:
    """Scan a single issue for health problems (extracted implementations)."""

    def __init__(self, core: Any = None):
        """Initialize IssueHealthScanner.

        Args:
            core: Core roadmap instance.
        """
        self.core = core

    @traced("scan_issue")
    def scan_issue(self, issue: Issue) -> EntityHealthReport:
        report = EntityHealthReport(
            entity_id=issue.id,
            entity_type=EntityType.ISSUE,
            entity_title=issue.title,
            status=issue.status.value,
        )

        self._check_issue_description(issue, report)
        self._check_issue_comments(issue, report)
        self._check_issue_estimates(issue, report)
        self._check_issue_dates(issue, report)
        self._check_issue_assignee(issue, report)
        self._check_issue_progress(issue, report)
        self._check_issue_status_consistency(issue, report)

        return report

    def _check_issue_description(self, issue: Issue, report: EntityHealthReport):
        if not issue.content or not issue.content.strip():
            report.issues.append(
                HealthIssue(
                    code="missing_description",
                    message="Issue has no description or content",
                    severity=HealthSeverity.INFO,
                    category="content",
                )
            )

    def _check_issue_comments(self, issue: Issue, report: EntityHealthReport):
        if not issue.comments:
            return

        errors = self._validate_comment_thread(issue.comments)
        for error_msg in errors:
            if "Duplicate" in error_msg:
                code = "duplicate_comment_id"
                severity = HealthSeverity.ERROR
            elif "circular" in error_msg.lower():
                code = "circular_comment_reference"
                severity = HealthSeverity.ERROR
            elif "datetime" in error_msg:
                code = "invalid_comment_datetime"
                severity = HealthSeverity.ERROR
            elif "Empty" in error_msg:
                code = "empty_comment_body"
                severity = HealthSeverity.WARNING
            elif "author" in error_msg.lower():
                code = "missing_comment_author"
                severity = HealthSeverity.WARNING
            else:
                code = "invalid_comment"
                severity = HealthSeverity.WARNING

            report.issues.append(
                HealthIssue(
                    code=code,
                    message=error_msg,
                    severity=severity,
                    category="content",
                    details={"comment_count": len(issue.comments)},
                )
            )

    def _check_issue_estimates(self, issue: Issue, report: EntityHealthReport):
        if issue.status not in (Status.IN_PROGRESS, Status.CLOSED):
            return

        if issue.estimated_hours is None:
            report.issues.append(
                HealthIssue(
                    code="missing_estimate",
                    message=f"Issue is {issue.status.value} but has no time estimate",
                    severity=HealthSeverity.INFO,
                    category="structure",
                )
            )
        elif issue.estimated_hours <= 0:
            report.issues.append(
                HealthIssue(
                    code="invalid_estimate",
                    message=f"Estimated hours must be positive, got {issue.estimated_hours}",
                    severity=HealthSeverity.WARNING,
                    category="structure",
                    details={"estimated_hours": issue.estimated_hours},
                )
            )

    def _check_issue_dates(self, issue: Issue, report: EntityHealthReport):
        if issue.actual_start_date and issue.actual_end_date:
            if issue.actual_start_date > issue.actual_end_date:
                report.issues.append(
                    HealthIssue(
                        code="invalid_date_range",
                        message="Start date is after end date",
                        severity=HealthSeverity.ERROR,
                        category="structure",
                        details={
                            "actual_start_date": issue.actual_start_date.isoformat(),
                            "actual_end_date": issue.actual_end_date.isoformat(),
                        },
                    )
                )

        if issue.due_date and issue.actual_end_date:
            if issue.actual_end_date > issue.due_date:
                report.issues.append(
                    HealthIssue(
                        code="missed_due_date",
                        message=f"Issue completed after due date ({issue.due_date.date()})",
                        severity=HealthSeverity.INFO,
                        category="structure",
                        details={
                            "due_date": issue.due_date.isoformat(),
                            "completed_date": issue.actual_end_date.isoformat(),
                        },
                    )
                )

    def _check_issue_assignee(self, issue: Issue, report: EntityHealthReport):
        if issue.previous_assignee and not issue.handoff_date:
            report.issues.append(
                HealthIssue(
                    code="missing_handoff_date",
                    message=f"Issue was handed off from {issue.previous_assignee} but no handoff date recorded",
                    severity=HealthSeverity.WARNING,
                    category="structure",
                    details={"previous_assignee": issue.previous_assignee},
                )
            )

    def _check_issue_progress(self, issue: Issue, report: EntityHealthReport):
        if issue.progress_percentage is not None:
            if not (0 <= issue.progress_percentage <= 100):
                report.issues.append(
                    HealthIssue(
                        code="invalid_progress_percentage",
                        message=f"Progress must be 0-100, got {issue.progress_percentage}",
                        severity=HealthSeverity.ERROR,
                        category="structure",
                        details={"progress_percentage": issue.progress_percentage},
                    )
                )

        if issue.status == Status.CLOSED and issue.progress_percentage != 100:
            report.issues.append(
                HealthIssue(
                    code="inconsistent_completion",
                    message=f"Issue marked Done but only {issue.progress_percentage or 0}% complete",
                    severity=HealthSeverity.WARNING,
                    category="structure",
                    details={"progress_percentage": issue.progress_percentage},
                )
            )

    def _check_issue_status_consistency(self, issue: Issue, report: EntityHealthReport):
        if issue.status == Status.CLOSED and not issue.actual_end_date:
            report.issues.append(
                HealthIssue(
                    code="missing_completion_date",
                    message="Issue marked Done but has no actual end date recorded",
                    severity=HealthSeverity.WARNING,
                    category="structure",
                )
            )

        if issue.actual_start_date and issue.status == Status.TODO:
            report.issues.append(
                HealthIssue(
                    code="inconsistent_status",
                    message="Issue has a start date but status is still TODO",
                    severity=HealthSeverity.WARNING,
                    category="structure",
                    details={"actual_start_date": issue.actual_start_date.isoformat()},
                )
            )

    @staticmethod
    def _validate_comment_thread(comments: list[Comment]) -> list[str]:
        errors = []
        comment_ids = set()

        for comment in comments:
            if comment.id in comment_ids:
                errors.append(f"Duplicate comment ID: {comment.id}")
            comment_ids.add(comment.id)

            if not comment.body or not comment.body.strip():
                errors.append(f"Comment {comment.id}: Empty comment body")

            if not comment.author or not comment.author.strip():
                errors.append(f"Comment {comment.id}: Missing comment author")

            # best-effort datetime sanity check
            try:
                _ = comment.created_at
            except Exception:
                errors.append(
                    f"Comment {comment.id}: created_at is not a valid datetime"
                )

        for comment in comments:
            if comment.in_reply_to:
                visited = set()
                current_id = comment.in_reply_to
                while current_id:
                    if current_id in visited:
                        errors.append(
                            f"Comment {comment.id}: Circular reference in reply chain"
                        )
                        break
                    visited.add(current_id)
                    current_comment = next(
                        (c for c in comments if c.id == current_id), None
                    )
                    current_id = (
                        current_comment.in_reply_to if current_comment else None
                    )

        return errors
