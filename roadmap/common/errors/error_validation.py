"""Validation related error classes."""

from typing import Any

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError


class ValidationError(RoadmapError):
    """Errors related to data validation."""

    def __init__(
        self, message: str, field: str | None = None, value: Any | None = None, **kwargs
    ):
        """Initialize ValidationError.

        Args:
            message: Error message.
            field: Name of the field that failed validation.
            value: Value that failed validation.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.MEDIUM),
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.field = field
        self.value = value


class StateError(RoadmapError):
    """Raised when operation is invalid for current state."""

    def __init__(self, message: str, current_state: str | None = None, **kwargs):
        """Initialize StateError.

        Args:
            message: Error message.
            current_state: Current state that made the operation invalid.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if current_state:
            context["current_state"] = current_state

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.MEDIUM),
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.current_state = current_state


class IssueNotFoundError(RoadmapError):
    """Raised when an issue cannot be found."""

    def __init__(self, message: str, issue_id: str | None = None, **kwargs):
        """Initialize IssueNotFoundError.

        Args:
            message: Error message.
            issue_id: ID of the issue that was not found.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if issue_id:
            context["issue_id"] = issue_id

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.MEDIUM),
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.issue_id = issue_id


class MilestoneNotFoundError(RoadmapError):
    """Raised when a milestone cannot be found."""

    def __init__(self, message: str, milestone_name: str | None = None, **kwargs):
        """Initialize MilestoneNotFoundError.

        Args:
            message: Error message.
            milestone_name: Name of the milestone that was not found.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if milestone_name:
            context["milestone"] = milestone_name

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.MEDIUM),
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.milestone_name = milestone_name
