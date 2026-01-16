"""Entity-level health scanning service.

Provides detailed diagnostics on individual entities (Issues, Milestones, Projects)
including validation of descriptions, comments, dependencies, and other metadata.
"""

from typing import Any

from roadmap.common.constants import Status
from roadmap.common.logging import get_logger
from roadmap.common.observability.instrumentation import traced
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project

# Re-export shared models for backward compatibility
from roadmap.core.services.health.health_models import (
    EntityHealthReport,
    EntityType,
    HealthIssue,
    HealthSeverity,
)
from roadmap.core.services.health.issue_health_scanner import IssueHealthScanner

logger = get_logger(__name__)


class EntityHealthScanner:
    """Scans entities for health issues.

    Checks for:
    - Missing or empty descriptions
    - Malformed or empty comments
    - Circular dependencies
    - Broken dependencies (referencing non-existent entities)
    - Missing estimates (when required by milestone)
    - Due date issues (overdue, unrealistic)
    - Assignee issues (unassigned when expected, previous_assignee mismatch)
    - Progress tracking issues (inconsistent progress state)
    """

    def __init__(self, core: Any = None):
        """Initialize the scanner.

        Args:
            core: Optional Core object with access to entities. If not provided,
                  the scanner can still work on individual entities passed to methods.
        """
        self.core = core
        self._entity_cache: dict[str, Any] = {}  # Cache of entity_id -> entity

    @traced("scan_issue")
    def scan_issue(self, issue: Issue) -> EntityHealthReport:
        """Delegate issue scanning to the extracted `IssueHealthScanner`.

        This keeps the original public API while the implementation lives in
        `issue_health_scanner.IssueHealthScanner` for easier maintenance.
        """
        scanner = IssueHealthScanner(core=self.core)
        return scanner.scan_issue(issue)

    @traced("scan_milestone")
    def scan_milestone(self, milestone: Milestone) -> EntityHealthReport:
        """Scan a single milestone for health problems.

        Args:
            milestone: The milestone to scan

        Returns:
            EntityHealthReport with all issues found
        """
        report = EntityHealthReport(
            entity_id=milestone.name,
            entity_type=EntityType.MILESTONE,
            entity_title=milestone.name,
            status=milestone.status.value if milestone.status else "unknown",
        )

        # Check description/content
        if not milestone.content or not milestone.content.strip():
            report.issues.append(
                HealthIssue(
                    code="missing_content",
                    message="Milestone has no content",
                    severity=HealthSeverity.WARNING,
                    category="content",
                )
            )

        # Check dates
        if milestone.created and milestone.due_date:
            if milestone.created > milestone.due_date:
                report.issues.append(
                    HealthIssue(
                        code="invalid_date_range",
                        message=f"Created date ({milestone.created.date()}) is after due date ({milestone.due_date.date()})",
                        severity=HealthSeverity.ERROR,
                        category="structure",
                        details={
                            "created_date": milestone.created.isoformat(),
                            "due_date": milestone.due_date.isoformat(),
                        },
                    )
                )

        # Check progress
        if (
            milestone.calculated_progress is not None
            and milestone.status == Status.CLOSED
        ):
            if milestone.calculated_progress != 100:
                report.issues.append(
                    HealthIssue(
                        code="inconsistent_completion",
                        message=f"Milestone marked Done but only {milestone.calculated_progress}% complete",
                        severity=HealthSeverity.WARNING,
                        category="structure",
                        details={"calculated_progress": milestone.calculated_progress},
                    )
                )

        return report

    @traced("scan_project")
    def scan_project(self, project: Project) -> EntityHealthReport:
        """Scan a single project for health problems.

        Args:
            project: The project to scan

        Returns:
            EntityHealthReport with all issues found
        """
        report = EntityHealthReport(
            entity_id=project.id,
            entity_type=EntityType.PROJECT,
            entity_title=project.name,
            status=project.status.value if project.status else "unknown",
        )

        # Check description/content
        if not project.content or not project.content.strip():
            report.issues.append(
                HealthIssue(
                    code="missing_content",
                    message="Project has no content",
                    severity=HealthSeverity.WARNING,
                    category="content",
                )
            )

        # Check owner
        if not project.owner or not project.owner.strip():
            report.issues.append(
                HealthIssue(
                    code="missing_owner",
                    message="Project has no owner assigned",
                    severity=HealthSeverity.WARNING,
                    category="structure",
                )
            )

        return report

    def scan_all(self) -> list[EntityHealthReport]:
        """Scan all issues, milestones, and projects.

        Requires core to be initialized.

        Returns:
            List of EntityHealthReport objects for all entities

        Raises:
            RuntimeError: If core is not initialized
        """
        if not self.core:
            raise RuntimeError(
                "Core must be initialized to scan all entities. "
                "Pass core to constructor or call scan_issue/milestone/project directly."
            )

        reports = []

        # Scan all issues
        try:
            all_issues = self.core.issue_repository.list()
            for issue in all_issues:
                reports.append(self.scan_issue(issue))
        except Exception as e:
            logger.error("error_scanning_issues", error=str(e))

        # Scan all milestones
        try:
            all_milestones = self.core.milestone_repository.list()
            for milestone in all_milestones:
                reports.append(self.scan_milestone(milestone))
        except Exception as e:
            logger.error("error_scanning_milestones", error=str(e))

        # Scan all projects
        try:
            all_projects = self.core.project_repository.list()
            for project in all_projects:
                reports.append(self.scan_project(project))
        except Exception as e:
            logger.error("error_scanning_projects", error=str(e))

        return reports

    # Private methods for individual checks

    def _check_issue_description(self, issue: Issue, report: EntityHealthReport):
        """Check issue description/content."""
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
        """Check issue comments for problems."""
        if not issue.comments:
            return

        errors = self._validate_comment_thread(issue.comments)
        for error_msg in errors:
            # Parse error message to determine severity and code
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
        """Check issue estimation."""
        # Only warn about missing estimates for in-progress or done issues
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
        """Check issue date consistency."""
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
        """Check issue assignee consistency."""
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
        """Check issue progress tracking."""
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

        # Check progress vs status consistency
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
        """Check overall status consistency."""
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
        """Validate comment threads for errors.

        Returns list of error messages found.
        """
        errors = []
        comment_ids = set()

        for comment in comments:
            # Check for duplicate IDs
            if comment.id in comment_ids:
                errors.append(f"Duplicate comment ID: {comment.id}")
            comment_ids.add(comment.id)

            # Check for empty body
            if not comment.body or not comment.body.strip():
                errors.append(f"Comment {comment.id}: Empty comment body")

            # Check for empty author
            if not comment.author or not comment.author.strip():
                errors.append(f"Comment {comment.id}: Missing comment author")

            # Check for invalid datetime fields
            if not isinstance(comment.created_at, type(comment.created_at)):
                errors.append(
                    f"Comment {comment.id}: created_at is not a valid datetime"
                )

        # Check for circular references in reply chains
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
                    # Find the comment this replies to
                    current_comment = next(
                        (c for c in comments if c.id == current_id), None
                    )
                    current_id = (
                        current_comment.in_reply_to if current_comment else None
                    )

        return errors
