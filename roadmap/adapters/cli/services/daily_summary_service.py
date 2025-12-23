"""Daily summary service for the 'today' command.

Provides business logic for generating daily workflow summaries,
including user identification, milestone selection, issue categorization,
and data aggregation for display.
"""

import os
from datetime import datetime
from typing import Any

from roadmap.common.constants import MilestoneStatus, Status
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class DailySummaryService:
    """Service for generating daily workflow summaries.

    Handles all business logic for the 'today' command, including:
    - User identity resolution from config or environment
    - Upcoming milestone selection
    - Issue categorization and filtering
    - Data aggregation for display
    """

    def __init__(self, core):
        """Initialize daily summary service.

        Args:
            core: RoadmapCore instance for accessing data
        """
        self.core = core

    def get_current_user(self) -> str | None:
        """Get current user from config or environment.

        Returns:
            Current user name or None if not found
        """
        # Get user identity from config (single source of truth)
        current_user = self.core.team.get_current_user()

        if not current_user:
            # Fallback to environment for testing
            current_user = os.getenv("ROADMAP_USER")

        return current_user

    def get_upcoming_milestone(self) -> Any | None:
        """Get the next upcoming milestone.

        Filters open milestones and returns the one with the earliest due date.

        Returns:
            Milestone object or None if no open milestones exist
        """
        milestones = self.core.milestones.list()

        # Filter open milestones and sort by due date
        open_milestones = [m for m in milestones if m.status == MilestoneStatus.OPEN]

        if not open_milestones:
            return None

        # Sort by due date (None dates last), get the first with a due date
        sorted_milestones = sorted(
            open_milestones,
            key=lambda m: (m.due_date is None, m.due_date or datetime.max),
        )

        return sorted_milestones[0] if sorted_milestones else None

    def _get_in_progress_issues(self, issues: list) -> list:
        """Get issues currently in progress.

        Args:
            issues: List of issues to filter

        Returns:
            List of in-progress issues
        """
        return [i for i in issues if i.status == Status.IN_PROGRESS]

    def _get_overdue_issues(self, issues: list) -> list:
        """Get overdue issues that haven't been closed.

        Args:
            issues: List of issues to filter

        Returns:
            List of overdue issues
        """
        return [
            i
            for i in issues
            if i.due_date
            and i.due_date.replace(tzinfo=None) < datetime.now()
            and i.status != Status.CLOSED
        ]

    def _get_blocked_issues(self, issues: list) -> list:
        """Get blocked issues.

        Args:
            issues: List of issues to filter

        Returns:
            List of blocked issues
        """
        return [i for i in issues if i.status == Status.BLOCKED]

    def _get_high_priority_todos(self, issues: list) -> list:
        """Get high-priority TODO issues (top 3).

        Args:
            issues: List of issues to filter

        Returns:
            List of up to 3 high-priority TODO issues
        """
        return [
            i
            for i in issues
            if i.status == Status.TODO and i.priority.value in ["critical", "high"]
        ][:3]

    def _get_completed_today_issues(self, issues: list) -> list:
        """Get issues closed today.

        Args:
            issues: List of issues to filter

        Returns:
            List of issues closed today
        """
        today = datetime.now().date()
        return [
            i
            for i in issues
            if i.status == Status.CLOSED
            and i.actual_end_date
            and i.actual_end_date.date() == today
        ]

    def categorize_issues(self, issues: list, current_user: str) -> dict[str, list]:
        """Categorize issues by status and urgency.

        Args:
            issues: List of issues to categorize
            current_user: Current user name for filtering

        Returns:
            Dictionary with keys: in_progress, overdue, blocked, todo_high_priority, completed_today
        """
        return {
            "in_progress": self._get_in_progress_issues(issues),
            "overdue": self._get_overdue_issues(issues),
            "blocked": self._get_blocked_issues(issues),
            "todo_high_priority": self._get_high_priority_todos(issues),
            "completed_today": self._get_completed_today_issues(issues),
        }

    def get_daily_summary_data(self) -> dict[str, Any]:
        """Get complete daily summary data.

        Validates user and milestone, filters issues, categorizes them,
        and returns all data needed for display.

        Returns:
            Dictionary with keys: current_user, milestone, issues (dict of categories)

        Raises:
            ValueError: If user not found or no upcoming milestones
        """
        # Get user identity
        current_user = self.get_current_user()
        if not current_user:
            raise ValueError(
                "No user configured. Initialize with 'roadmap init' or set ROADMAP_USER."
            )

        logger.debug("Current user", user=current_user)

        # Get upcoming milestone
        upcoming_milestone = self.get_upcoming_milestone()
        if not upcoming_milestone:
            raise ValueError("No upcoming milestones found.")

        logger.debug("Upcoming milestone", milestone=upcoming_milestone.name)

        # Get all issues
        all_issues = self.core.issues.list()

        # Filter: assigned to current user AND in upcoming milestone
        my_milestone_issues = [
            i
            for i in all_issues
            if i.assignee == current_user and i.milestone == upcoming_milestone.name
        ]

        if not my_milestone_issues:
            logger.info(
                "No issues assigned to user in upcoming milestone", user=current_user
            )
            return {
                "current_user": current_user,
                "milestone": upcoming_milestone,
                "issues": {
                    "in_progress": [],
                    "overdue": [],
                    "blocked": [],
                    "todo_high_priority": [],
                    "completed_today": [],
                },
                "has_issues": False,
            }

        # Categorize issues
        categorized = self.categorize_issues(my_milestone_issues, current_user)

        logger.info(
            "Daily summary data prepared",
            user=current_user,
            milestone=upcoming_milestone.name,
            in_progress=len(categorized["in_progress"]),
            overdue=len(categorized["overdue"]),
            blocked=len(categorized["blocked"]),
            todo_high_priority=len(categorized["todo_high_priority"]),
            completed_today=len(categorized["completed_today"]),
        )

        return {
            "current_user": current_user,
            "milestone": upcoming_milestone,
            "issues": categorized,
            "has_issues": True,
        }

    def get_next_action_suggestion(self, data: dict[str, Any]) -> str | None:
        """Get helpful suggestion for next action based on data.

        Args:
            data: Dictionary from get_daily_summary_data()

        Returns:
            Suggestion string or None if no action recommended
        """
        issues = data["issues"]

        if not issues["in_progress"] and issues["todo_high_priority"]:
            issue = issues["todo_high_priority"][0]
            return f"Start work on an issue with: roadmap issue start {issue.id}"

        if issues["overdue"]:
            issue = issues["overdue"][0]
            return f"View overdue issue details with: roadmap issue view {issue.id}"

        return None
