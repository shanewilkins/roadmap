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

from roadmap.domain.issue import Issue, IssueType, Priority, Status
from roadmap.infrastructure.persistence.parser import IssueParser
from roadmap.infrastructure.storage import StateManager
from roadmap.shared.errors import (
    ErrorHandler,
    ErrorSeverity,
    FileOperationError,
)
from roadmap.shared.timezone_utils import now_utc


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

        return issue

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
        issues = []
        for issue_file in self.issues_dir.rglob("*.md"):
            try:
                issue = IssueParser.parse_issue_file(issue_file)
                # Store the original file path so updates preserve the location
                issue.file_path = str(issue_file)

                # Apply filters
                if milestone and issue.milestone != milestone:
                    continue
                if status and issue.status != status:
                    continue
                if priority and issue.priority != priority:
                    continue
                if issue_type and issue.issue_type != issue_type:
                    continue
                if assignee and issue.assignee != assignee:
                    continue

                issues.append(issue)
            except Exception as e:
                # Log parsing error but continue processing other files
                error_handler = ErrorHandler()
                error_handler.handle_error(
                    FileOperationError(
                        f"Skipping malformed issue file: {issue_file.name}",
                        file_path=issue_file,
                        operation="parse_issue",
                        severity=ErrorSeverity.LOW,
                        cause=e,
                    ),
                    show_traceback=False,
                    exit_on_critical=False,
                )
                continue

        # Sort by priority then by creation date
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        issues.sort(key=lambda x: (priority_order.get(x.priority, 999), x.created))

        return issues

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
        from pathlib import Path

        # Find all copies of the issue
        matching_files = list(self.issues_dir.rglob(f"{issue_id}-*.md"))
        if not matching_files:
            return None

        # Prefer milestone-specific subdirectories over root
        # Sort: milestone subdirs first (v.X.X.X), then root
        def sort_key(path: Path) -> tuple:
            # If file is in a milestone subfolder (v.X.X.X), prioritize it
            if "v." in str(path):
                return (0, str(path))  # Milestone paths first
            else:
                return (1, str(path))  # Root paths second

        matching_files.sort(key=sort_key)
        issue_file = matching_files[0]

        try:
            issue = IssueParser.parse_issue_file(issue_file)
            # Store the original file path so updates preserve the location
            issue.file_path = str(issue_file)
            return issue
        except Exception:
            return None

    def update_issue(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue with new field values.

        Args:
            issue_id: Issue identifier
            **updates: Fields to update (title, status, priority, etc.)

        Returns:
            Updated Issue object if found, None otherwise
        """
        from pathlib import Path

        issue = self.get_issue(issue_id)
        if not issue:
            return None

        # Update fields
        for field, value in updates.items():
            if hasattr(issue, field):
                setattr(issue, field, value)

        # Update timestamp
        issue.updated = now_utc()

        # Save updated issue to its original location
        if issue.file_path:
            issue_path = Path(issue.file_path)
        else:
            # Fallback for issues without stored path (shouldn't happen after fix)
            issue_path = self.issues_dir / issue.filename

        IssueParser.save_issue_file(issue, issue_path)

        return issue

        return issue

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            True if deleted successfully, False if not found
        """
        for issue_file in self.issues_dir.rglob(f"{issue_id}-*.md"):
            try:
                issue_file.unlink()
                return True
            except Exception:
                continue
        return False

    def close_issue(self, issue_id: str) -> Issue | None:
        """Close/mark issue as complete.

        Args:
            issue_id: Issue identifier

        Returns:
            Closed Issue object if found, None otherwise
        """
        return self.update_issue(issue_id, status=Status.CLOSED)
