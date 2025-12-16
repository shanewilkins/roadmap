"""Issue service - handles all issue-related operations.

The IssueService manages:
- Issue creation with metadata
- Issue listing with filtering (milestone, status, assignee)
- Getting specific issues by ID
- Updating issue fields
- Deleting issues
- Status transitions

Extracted from core.py to separate business logic.
"""

from pathlib import Path

from roadmap.adapters.persistence.parser import IssueParser
from roadmap.adapters.persistence.storage import StateManager
from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.common.logging_utils import log_entry, log_event, log_exit, log_metric
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain.issue import Issue, IssueType, Priority, Status
from roadmap.infrastructure.file_enumeration import FileEnumerationService

logger = get_logger(__name__)


class IssueService:
    """Service for managing issues."""

    def __init__(self, db: StateManager, issues_dir: Path):
        """Initialize issue service.

        Args:
            db: State manager for database operations
            issues_dir: Path to issues directory containing issue markdown files
        """
        self.db = db
        self.issues_dir = issues_dir

    @safe_operation(OperationType.CREATE, "Issue", include_traceback=True)
    def create_issue(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        issue_type: IssueType = IssueType.OTHER,
        milestone: str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
        estimated_hours: float | None = None,
        depends_on: list[str] | None = None,
        blocks: list[str] | None = None,
    ) -> Issue:
        """Create a new issue with provided metadata.

        Args:
            title: Issue title/summary
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
            issue_type: Type of issue (BUG, FEATURE, TASK, etc.)
            milestone: Associated milestone name
            labels: List of labels/tags
            assignee: Assigned user or team member
            estimated_hours: Estimated effort in hours
            depends_on: List of issue IDs this depends on
            blocks: List of issue IDs this blocks

        Returns:
            Newly created Issue object
        """
        log_entry("create_issue", title=title, priority=priority.value)
        logger.info(
            "creating_issue",
            title=title,
            priority=priority.value,
            issue_type=issue_type.value,
        )
        log_event("issue_creation_started", issue_title=title)
        import json

        issue = Issue(
            title=title,
            priority=priority,
            issue_type=issue_type,
            milestone=milestone or "",
            labels=labels or [],
            assignee=assignee,
            estimated_hours=estimated_hours,
            depends_on=depends_on or [],
            blocks=blocks or [],
            content=f"# {title}\n\n## Description\n\nBrief description of the issue or feature request.\n\n## Acceptance Criteria\n\n- [ ] Criterion 1\n- [ ] Criterion 2\n- [ ] Criterion 3",
        )

        issue_path = self.issues_dir / issue.filename
        issue.file_path = str(issue_path)  # Store the path for future updates
        IssueParser.save_issue_file(issue, issue_path)

        # Persist to database (non-blocking - file system is primary source of truth)
        try:
            self.db.create_issue(
                {
                    "id": issue.id,
                    "project_id": None,  # Issues are not project-scoped in current design
                    "milestone_id": None,  # Not directly mapped in current design
                    "title": title,
                    "description": "",
                    "status": "open",
                    "priority": priority.value,
                    "issue_type": issue_type.value,
                    "assignee": assignee,
                    "estimate_hours": estimated_hours,
                    "due_date": None,
                    "metadata": json.dumps(
                        {"filename": issue.filename, "labels": labels or []}
                    ),
                }
            )
        except Exception:
            # Silently continue if DB insert fails - file-based system is primary
            pass

        log_event("issue_created", issue_id=issue.id)
        log_exit("create_issue", issue_id=issue.id)
        return issue

    def _check_milestone_filter(self, issue: Issue, milestone: str | None) -> bool:
        """Check milestone filter.

        Args:
            issue: Issue to check
            milestone: Required milestone or None

        Returns:
            True if milestone matches or no filter
        """
        return not milestone or issue.milestone == milestone

    def _check_status_filter(self, issue: Issue, status: Status | None) -> bool:
        """Check status filter.

        Args:
            issue: Issue to check
            status: Required status or None

        Returns:
            True if status matches or no filter
        """
        return not status or issue.status == status

    def _check_priority_filter(self, issue: Issue, priority: Priority | None) -> bool:
        """Check priority filter.

        Args:
            issue: Issue to check
            priority: Required priority or None

        Returns:
            True if priority matches or no filter
        """
        return not priority or issue.priority == priority

    def _check_type_filter(self, issue: Issue, issue_type: IssueType | None) -> bool:
        """Check issue type filter.

        Args:
            issue: Issue to check
            issue_type: Required issue type or None

        Returns:
            True if type matches or no filter
        """
        return not issue_type or issue.issue_type == issue_type

    def _check_assignee_filter(self, issue: Issue, assignee: str | None) -> bool:
        """Check assignee filter.

        Args:
            issue: Issue to check
            assignee: Required assignee or None

        Returns:
            True if assignee matches or no filter
        """
        return not assignee or issue.assignee == assignee

    def _matches_all_filters(
        self,
        issue: Issue,
        milestone: str | None,
        status: Status | None,
        priority: Priority | None,
        issue_type: IssueType | None,
        assignee: str | None,
    ) -> bool:
        """Check if issue matches all provided filter criteria."""
        return (
            self._check_milestone_filter(issue, milestone)
            and self._check_status_filter(issue, status)
            and self._check_priority_filter(issue, priority)
            and self._check_type_filter(issue, issue_type)
            and self._check_assignee_filter(issue, assignee)
        )

    def _get_priority_order(self) -> dict:
        """Get priority ordering for sorting."""
        return {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }

    def _sort_issues_by_priority_and_date(self, issues: list[Issue]) -> list[Issue]:
        """Sort issues by priority then creation date."""
        priority_order = self._get_priority_order()
        issues.sort(key=lambda x: (priority_order.get(x.priority, 999), x.created))
        return issues

    def list_issues(
        self,
        milestone: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        issue_type: IssueType | None = None,
        assignee: str | None = None,
    ) -> list[Issue]:
        """List issues with optional filtering.

        All filters are combined with AND logic (all must match).

        Args:
            milestone: Filter by milestone name
            status: Filter by status (OPEN, IN_PROGRESS, BLOCKED, REVIEW, DONE)
            priority: Filter by priority level
            issue_type: Filter by issue type
            assignee: Filter by assignee

        Returns:
            List of Issue objects matching all filters, sorted by priority then date
        """
        log_entry("list_issues", milestone=milestone, status=status)
        # Use FileEnumerationService to enumerate and parse all issue files
        issues = FileEnumerationService.enumerate_and_parse(
            self.issues_dir, IssueParser.parse_issue_file
        )
        log_metric("issues_enumerated", len(issues))

        # Apply filters
        filtered_issues = [
            issue
            for issue in issues
            if self._matches_all_filters(
                issue, milestone, status, priority, issue_type, assignee
            )
        ]

        # Sort by priority then by creation date
        sorted_issues = self._sort_issues_by_priority_and_date(filtered_issues)
        log_metric("issues_filtered", len(issues), filtered=len(sorted_issues))
        log_exit("list_issues", issue_count=len(sorted_issues))
        return sorted_issues

    def get_issue(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID.

        Args:
            issue_id: Issue identifier (ID prefix used in filename)

        Returns:
            Issue object if found, None otherwise.

        Note:
            If multiple copies exist (due to migration), prefers milestone-specific
            subdirectories (v.X.X.X) over root directory.
        """
        log_entry("get_issue", issue_id=issue_id)
        # Use FileEnumerationService to find the issue by ID
        issue = FileEnumerationService.find_by_id(
            self.issues_dir, issue_id, IssueParser.parse_issue_file
        )

        if issue and hasattr(issue, "file_path"):
            # Store the original file path so updates preserve the location
            issue.file_path = str(issue.file_path)
            log_event("issue_found", issue_id=issue_id, title=issue.title)
        else:
            log_event("issue_not_found", issue_id=issue_id)

        log_exit("get_issue", found=issue is not None)
        return issue

    @safe_operation(OperationType.UPDATE, "Issue")
    def update_issue(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue with new field values.

        Args:
            issue_id: Issue identifier
            **updates: Fields to update (title, status, priority, etc.)

        Returns:
            Updated Issue object if found, None otherwise
        """
        log_entry("update_issue", issue_id=issue_id, fields=list(updates.keys()))
        logger.info(
            "updating_issue", issue_id=issue_id, update_fields=list(updates.keys())
        )
        from pathlib import Path

        issue = self.get_issue(issue_id)
        if not issue:
            log_event("issue_not_found", issue_id=issue_id)
            log_exit("update_issue", success=False)
            return None

        # Update fields
        for field, value in updates.items():
            if hasattr(issue, field):
                setattr(issue, field, value)
                log_event("issue_field_updated", issue_id=issue_id, field=field)

        # Update timestamp
        issue.updated = now_utc()

        # Save updated issue to its original location
        if issue.file_path:
            issue_path = Path(issue.file_path)
        else:
            # Fallback for issues without stored path (shouldn't happen after fix)
            issue_path = self.issues_dir / issue.filename

        IssueParser.save_issue_file(issue, issue_path)
        log_event("issue_saved", issue_id=issue_id)
        log_exit("update_issue", issue_id=issue_id, success=True)

        return issue

    @safe_operation(OperationType.DELETE, "Issue", include_traceback=True)
    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            True if deleted successfully, False if not found
        """
        log_entry("delete_issue", issue_id=issue_id)
        logger.info("deleting_issue", issue_id=issue_id)
        # Find and delete the issue file by ID pattern
        for issue_file in self.issues_dir.rglob(f"{issue_id}-*.md"):
            try:
                issue_file.unlink()
                log_event("issue_deleted", issue_id=issue_id, file=str(issue_file))
                log_exit("delete_issue", success=True)
                return True
            except Exception:
                continue
        log_event("issue_not_found", issue_id=issue_id)
        log_exit("delete_issue", success=False)
        return False

    def close_issue(self, issue_id: str) -> Issue | None:
        """Close/mark issue as complete.

        Args:
            issue_id: Issue identifier

        Returns:
            Closed Issue object if found, None otherwise
        """
        return self.update_issue(issue_id, status=Status.CLOSED)
