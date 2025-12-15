"""Entity-specific builders for CRUD operations.

This module provides builders for each entity type (Issue, Milestone, Project)
that handle validation and dict building for create/update operations.
"""

from datetime import datetime
from typing import Any

from roadmap.common.errors.exceptions import ValidationError
from roadmap.core.domain import IssueType, Priority


class IssueBuilder:
    """Builder for issue creation and updates."""

    @staticmethod
    def validate_issue_exists(core: Any, issue_id: str) -> bool:
        """Check if an issue exists.

        Args:
            core: The core application context
            issue_id: Issue ID to check

        Returns:
            True if issue exists, False otherwise
        """
        return core.issues.get(issue_id) is not None

    @staticmethod
    def validate_priority(priority: str) -> Priority:
        """Validate and convert priority string.

        Args:
            priority: Priority string (critical, high, medium, low)

        Returns:
            Priority enum value

        Raises:
            ValidationError: If priority is invalid
        """
        try:
            priority_map = {
                "critical": Priority.CRITICAL,
                "high": Priority.HIGH,
                "medium": Priority.MEDIUM,
                "low": Priority.LOW,
            }
            return priority_map[priority.lower()]
        except KeyError as e:
            raise ValidationError(
                domain_message=f"Invalid priority: {priority}",
                user_message=f"Invalid priority: {priority}. Valid values: critical, high, medium, low",
            ) from e

    @staticmethod
    def validate_issue_type(issue_type: str) -> IssueType:
        """Validate and convert issue type string.

        Args:
            issue_type: Issue type string (feature, bug, other)

        Returns:
            IssueType enum value

        Raises:
            ValidationError: If type is invalid
        """
        try:
            type_map = {
                "feature": IssueType.FEATURE,
                "bug": IssueType.BUG,
                "other": IssueType.OTHER,
            }
            return type_map[issue_type.lower()]
        except KeyError as e:
            raise ValidationError(
                domain_message=f"Invalid issue type: {issue_type}",
                user_message=f"Invalid issue type: {issue_type}. Valid values: feature, bug, other",
            ) from e

    @staticmethod
    def build_create_dict(
        title: str,
        priority: str | None = None,
        issue_type: str | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
        estimate: float | None = None,
        depends_on: list[str] | None = None,
        blocks: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build create dictionary for issue.

        Args:
            title: Issue title (required)
            priority: Priority level
            issue_type: Type of issue
            milestone: Milestone ID to assign
            assignee: Assignee name/email
            labels: List of labels
            estimate: Estimated hours
            depends_on: Issue IDs this depends on
            blocks: Issue IDs this blocks

        Returns:
            Dictionary ready for core.issues.create()
        """
        create_dict = {"title": title}

        if priority:
            create_dict["priority"] = IssueBuilder.validate_priority(priority)

        if issue_type:
            create_dict["issue_type"] = IssueBuilder.validate_issue_type(issue_type)

        if milestone:
            create_dict["milestone"] = milestone

        if assignee:
            create_dict["assignee"] = assignee

        if labels:
            create_dict["labels"] = labels

        if estimate is not None:
            create_dict["estimated_hours"] = estimate

        if depends_on:
            create_dict["depends_on"] = depends_on

        if blocks:
            create_dict["blocks"] = blocks

        return create_dict

    @staticmethod
    def build_update_dict(
        title: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        milestone: str | None = None,
        description: str | None = None,
        estimate: float | None = None,
    ) -> dict[str, Any]:
        """Build update dictionary for issue.

        Args:
            title: New title
            priority: New priority
            status: New status
            assignee: New assignee
            milestone: New milestone
            description: New description
            estimate: New estimate

        Returns:
            Dictionary ready for core.issues.update()
        """
        update_dict = {}

        if title is not None:
            update_dict["title"] = title

        if priority is not None:
            update_dict["priority"] = IssueBuilder.validate_priority(priority)

        if status is not None:
            update_dict["status"] = status

        if assignee is not None:
            update_dict["assignee"] = assignee

        if milestone is not None:
            update_dict["milestone"] = milestone

        if description is not None:
            update_dict["description"] = description

        if estimate is not None:
            update_dict["estimated_hours"] = estimate

        return update_dict


class MilestoneBuilder:
    """Builder for milestone creation and updates."""

    @staticmethod
    def validate_milestone_exists(core: Any, milestone_id: str) -> bool:
        """Check if a milestone exists.

        Args:
            core: The core application context
            milestone_id: Milestone ID to check

        Returns:
            True if milestone exists, False otherwise
        """
        return core.milestones.get(milestone_id) is not None

    @staticmethod
    def validate_due_date(due_date: str | None) -> datetime | None:
        """Validate and parse due date.

        Args:
            due_date: Due date string (YYYY-MM-DD format)

        Returns:
            Parsed datetime or None

        Raises:
            ValidationError: If date format is invalid
        """
        if not due_date:
            return None

        try:
            return datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValidationError(
                domain_message="Invalid due date format: expected YYYY-MM-DD",
                user_message=f"Invalid due date format: {due_date}. Expected format: YYYY-MM-DD (example: 2024-12-31)",
            ) from e

    @staticmethod
    def build_create_dict(
        name: str,
        description: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Build create dictionary for milestone.

        Args:
            name: Milestone name (required)
            description: Milestone description
            due_date: Due date (YYYY-MM-DD format)

        Returns:
            Dictionary ready for core.milestones.create()
        """
        create_dict = {"name": name}

        if description:
            create_dict["description"] = description

        if due_date:
            create_dict["due_date"] = MilestoneBuilder.validate_due_date(due_date)

        return create_dict

    @staticmethod
    def build_update_dict(
        name: str | None = None,
        description: str | None = None,
        due_date: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Build update dictionary for milestone.

        Args:
            name: New name
            description: New description
            due_date: New due date (YYYY-MM-DD format)
            status: New status

        Returns:
            Dictionary ready for core.milestones.update()
        """
        update_dict = {}

        if name is not None:
            update_dict["name"] = name

        if description is not None:
            update_dict["description"] = description

        if due_date is not None:
            update_dict["due_date"] = MilestoneBuilder.validate_due_date(due_date)

        if status is not None:
            update_dict["status"] = status

        return update_dict


class ProjectBuilder:
    """Builder for project creation and updates."""

    @staticmethod
    def validate_project_exists(core: Any, project_id: str) -> bool:
        """Check if a project exists.

        Args:
            core: The core application context
            project_id: Project ID to check

        Returns:
            True if project exists, False otherwise
        """
        return core.projects.get(project_id) is not None

    @staticmethod
    def build_create_dict(
        name: str,
        description: str | None = None,
        repository: str | None = None,
    ) -> dict[str, Any]:
        """Build create dictionary for project.

        Args:
            name: Project name (required)
            description: Project description
            repository: Repository URL

        Returns:
            Dictionary ready for core.projects.create()
        """
        create_dict = {"name": name}

        if description:
            create_dict["description"] = description

        if repository:
            create_dict["repository"] = repository

        return create_dict

    @staticmethod
    def build_update_dict(
        name: str | None = None,
        description: str | None = None,
        repository: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Build update dictionary for project.

        Args:
            name: New name
            description: New description
            repository: New repository URL
            status: New status

        Returns:
            Dictionary ready for core.projects.update()
        """
        update_dict = {}

        if name is not None:
            update_dict["name"] = name

        if description is not None:
            update_dict["description"] = description

        if repository is not None:
            update_dict["repository"] = repository

        if status is not None:
            update_dict["status"] = status

        return update_dict
