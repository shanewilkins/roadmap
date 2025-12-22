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

from roadmap.common.cache import SessionCache
from roadmap.common.constants import IssueType, Priority, Status
from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.common.logging_utils import log_entry, log_event, log_exit, log_metric
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain.issue import Issue
from roadmap.core.models import IssueCreateServiceParams, IssueUpdateServiceParams
from roadmap.core.repositories import IssueRepository

logger = get_logger(__name__)


class IssueService:
    """Service for managing issues."""

    # Cache for list_issues results (TTL: 60 seconds)
    _list_issues_cache = SessionCache()
    _cache_ttl = 60  # TTL in seconds

    def __init__(self, repository: IssueRepository):
        """Initialize issue service.

        Args:
            repository: IssueRepository implementation for data persistence
        """
        self.repository = repository

    @safe_operation(OperationType.CREATE, "Issue", include_traceback=True)
    def create_issue(self, params: IssueCreateServiceParams) -> Issue:
        """Create a new issue with provided metadata.

        Args:
            params: IssueCreateServiceParams containing all creation parameters
                - title: Issue title/summary
                - priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
                - issue_type: Type of issue (BUG, FEATURE, TASK, etc.)
                - milestone: Associated milestone name
                - labels: List of labels/tags
                - assignee: Assigned user or team member
                - estimate: Estimated effort in hours
                - depends_on: List of issue IDs this depends on
                - blocks: List of issue IDs this blocks

        Returns:
            Newly created Issue object
        """
        log_entry("create_issue", title=params.title, priority=params.priority)
        logger.info(
            "creating_issue",
            title=params.title,
            priority=params.priority,
            issue_type=params.issue_type,
        )
        log_event("issue_creation_started", issue_title=params.title)

        # Convert string values to enums (if they're not already)
        try:
            priority = (
                Priority[params.priority.upper()]
                if isinstance(params.priority, str)
                else params.priority or Priority.MEDIUM
            )
        except (AttributeError, KeyError):
            priority = Priority.MEDIUM

        try:
            issue_type = (
                IssueType[params.issue_type.upper()]
                if isinstance(params.issue_type, str)
                else params.issue_type or IssueType.OTHER
            )
        except (AttributeError, KeyError):
            issue_type = IssueType.OTHER

        issue = Issue(
            title=params.title,
            priority=priority,
            issue_type=issue_type,
            milestone=params.milestone or "",
            labels=params.labels or [],
            assignee=params.assignee,
            estimated_hours=params.estimate,
            depends_on=params.depends_on or [],
            blocks=params.blocks or [],
            content=f"# {params.title}\n\n## Description\n\nBrief description of the issue or feature request.\n\n## Acceptance Criteria\n\n- [ ] Criterion 1\n- [ ] Criterion 2\n- [ ] Criterion 3",
        )

        # Persist using repository abstraction
        self.repository.save(issue)

        # Invalidate cache after successful creation
        self._list_issues_cache.clear()

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

        # Create cache key from filter parameters
        cache_key = (milestone, status, priority, issue_type, assignee)
        # Convert to string for cache key
        cache_key_str = str(cache_key)

        # Check cache first
        cached = self._list_issues_cache.get(cache_key_str)
        if cached is not None:
            log_metric("cache_hit", 1, operation="list_issues")
            log_exit("list_issues", issue_count=len(cached), from_cache=True)
            return cached

        # Get issues from repository
        issues = self.repository.list()
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

        # Cache the result with TTL
        self._list_issues_cache.set(cache_key_str, sorted_issues, ttl=self._cache_ttl)

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
        # Get issue from repository
        issue = self.repository.get(issue_id)

        if issue and hasattr(issue, "file_path"):
            # Store the original file path so updates preserve the location
            issue.file_path = str(issue.file_path)
            log_event("issue_found", issue_id=issue_id, title=issue.title)
        else:
            log_event("issue_not_found", issue_id=issue_id)

        log_exit("get_issue", found=issue is not None)
        return issue

    @safe_operation(OperationType.UPDATE, "Issue")
    def update_issue(self, params: IssueUpdateServiceParams) -> Issue | None:
        """Update an existing issue with new field values.

        Args:
            params: IssueUpdateServiceParams with fields to update

        Returns:
            Updated Issue object if found, None otherwise
        """
        log_entry(
            "update_issue",
            issue_id=params.issue_id,
            fields=[
                "title",
                "status",
                "priority",
                "assignee",
                "milestone",
                "description",
                "estimate",
                "reason",
            ],
        )
        logger.info(
            "updating_issue",
            issue_id=params.issue_id,
            update_fields=[
                "title",
                "status",
                "priority",
                "assignee",
                "milestone",
                "description",
                "estimate",
            ],
        )

        issue = self.get_issue(params.issue_id)
        if not issue:
            log_event("issue_not_found", issue_id=params.issue_id)
            log_exit("update_issue", success=False)
            return None

        # Update fields if provided
        if params.title is not None:
            issue.title = params.title
            log_event("issue_field_updated", issue_id=params.issue_id, field="title")
        if params.status is not None:
            issue.status = Status(params.status)
            log_event("issue_field_updated", issue_id=params.issue_id, field="status")
        if params.priority is not None:
            try:
                priority = (
                    Priority[params.priority.upper()]
                    if isinstance(params.priority, str)
                    else params.priority
                )
            except (AttributeError, KeyError):
                # Invalid priority - keep current priority
                logger.warning(
                    "invalid_priority_in_update",
                    issue_id=params.issue_id,
                    priority=params.priority,
                )
                priority = issue.priority
            issue.priority = priority
            log_event("issue_field_updated", issue_id=params.issue_id, field="priority")
        if params.assignee is not None:
            issue.assignee = params.assignee
            log_event("issue_field_updated", issue_id=params.issue_id, field="assignee")
        if params.milestone is not None:
            issue.milestone = params.milestone
            log_event(
                "issue_field_updated", issue_id=params.issue_id, field="milestone"
            )
        if params.description is not None:
            issue.content = params.description
            log_event(
                "issue_field_updated", issue_id=params.issue_id, field="description"
            )
        if params.estimate is not None:
            issue.estimated_hours = params.estimate
            log_event("issue_field_updated", issue_id=params.issue_id, field="estimate")

        # Update timestamp
        issue.updated = now_utc()

        # Save updated issue through repository
        self.repository.save(issue)
        log_event("issue_saved", issue_id=params.issue_id)

        # Invalidate cache after successful update
        self._list_issues_cache.clear()

        log_exit("update_issue", issue_id=params.issue_id, success=True)

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
        # Delete issue through repository
        deleted = self.repository.delete(issue_id)

        if deleted:
            log_event("issue_deleted", issue_id=issue_id)
            # Invalidate cache after successful deletion
            self._list_issues_cache.clear()
            log_exit("delete_issue", success=True)
        else:
            log_event("issue_not_found_delete", issue_id=issue_id)
            log_exit("delete_issue", success=False)
        return deleted

    def close_issue(self, issue_id: str) -> Issue | None:
        """Close/mark issue as complete.

        Args:
            issue_id: Issue identifier

        Returns:
            Closed Issue object if found, None otherwise
        """
        params = IssueUpdateServiceParams(issue_id=issue_id, status="closed")
        return self.update_issue(params)
