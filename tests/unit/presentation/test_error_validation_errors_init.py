"""Error path tests for error_validation module.

Tests cover initialization, context handling, field/value tracking,
state tracking, and error message generation for validation errors.
"""

import pytest

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity
from roadmap.common.errors.error_validation import (
    IssueNotFoundError,
    MilestoneNotFoundError,
    StateError,
    ValidationError,
)


class TestValidationErrorInitialization:
    """Test ValidationError initialization and parameter handling."""

    import pytest

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            (
                {"message": "Invalid email format"},
                {
                    "str": "Invalid email format",
                    "field": None,
                    "value": None,
                    "category": ErrorCategory.VALIDATION,
                    "severity": ErrorSeverity.MEDIUM,
                },
            ),
            (
                {"message": "Invalid value", "field": "email"},
                {"field": "email", "context_field": "email"},
            ),
            (
                {"message": "Invalid value", "value": "not-an-email"},
                {"value": "not-an-email", "context_value": "not-an-email"},
            ),
            (
                {
                    "message": "Invalid email",
                    "field": "email_address",
                    "value": "invalid@",
                },
                {
                    "field": "email_address",
                    "value": "invalid@",
                    "context_field": "email_address",
                    "context_value": "invalid@",
                },
            ),
            (
                {
                    "message": "Critical validation failure",
                    "severity": ErrorSeverity.HIGH,
                    "field": "critical_field",
                },
                {"severity": ErrorSeverity.HIGH},
            ),
            (
                {
                    "message": "Validation failed",
                    "field": "username",
                    "context": {"source": "user_input", "attempt": 3},
                },
                {
                    "context_source": "user_input",
                    "context_attempt": 3,
                    "context_field": "username",
                },
            ),
            (
                {"message": "Validation failed", "cause": ValueError("Original error")},
                {"cause_type": ValueError},
            ),
            ({"message": "Invalid number", "value": 12345}, {"context_value": "12345"}),
            ({"message": "Validation failed", "value": None}, {"context_value": None}),
            ({"message": "Validation failed", "field": None}, {"context_field": None}),
        ],
    )
    def test_validation_error_init_parametrized(self, kwargs, expected):
        error = (
            ValidationError(**{k: v for k, v in kwargs.items() if k != "message"})
            if "message" not in kwargs
            else ValidationError(
                kwargs["message"], **{k: v for k, v in kwargs.items() if k != "message"}
            )
        )
        if "str" in expected:
            assert str(error) == expected["str"]
        if "field" in expected:
            assert error.field == expected["field"]
        if "value" in expected:
            assert error.value == expected["value"]
        if "category" in expected:
            assert error.category == expected["category"]
        if "severity" in expected:
            assert error.severity == expected["severity"]
        if "context_field" in expected:
            if expected["context_field"] is None:
                assert "field" not in error.context
            else:
                assert error.context["field"] == expected["context_field"]
        if "context_value" in expected:
            if expected["context_value"] is None:
                assert "value" not in error.context
            else:
                assert expected["context_value"] in error.context["value"]
        if "context_source" in expected:
            assert error.context["source"] == expected["context_source"]
        if "context_attempt" in expected:
            assert error.context["attempt"] == expected["context_attempt"]
        if "cause_type" in expected:
            assert isinstance(error.cause, expected["cause_type"])


class TestStateErrorInitialization:
    """Test StateError initialization and state tracking."""

    @pytest.mark.parametrize(
        "message,current_state,severity,extra_context,expected_state,expected_severity,context_has_state",
        [
            (
                "Invalid operation for current state",
                None,
                ErrorSeverity.MEDIUM,
                {},
                None,
                ErrorSeverity.MEDIUM,
                False,
            ),
            (
                "Cannot transition",
                "closed",
                ErrorSeverity.MEDIUM,
                {},
                "closed",
                ErrorSeverity.MEDIUM,
                True,
            ),
            (
                "Critical state violation",
                "invalid",
                ErrorSeverity.HIGH,
                {},
                "invalid",
                ErrorSeverity.HIGH,
                True,
            ),
            (
                "Cannot close",
                "archived",
                ErrorSeverity.MEDIUM,
                {"expected_state": "open", "transition": "close"},
                "archived",
                ErrorSeverity.MEDIUM,
                True,
            ),
        ],
    )
    def test_state_error_initialization(
        self,
        message,
        current_state,
        severity,
        extra_context,
        expected_state,
        expected_severity,
        context_has_state,
    ):
        """Test StateError initialization with various parameters."""
        kwargs = {"current_state": current_state, "severity": severity}
        if extra_context:
            kwargs["context"] = extra_context
        error = StateError(message, **kwargs)
        assert str(error) == message
        assert error.current_state == expected_state
        assert error.severity == expected_severity
        assert error.category == ErrorCategory.VALIDATION
        if context_has_state:
            assert error.context["current_state"] == expected_state
        else:
            assert "current_state" not in error.context
        if extra_context:
            for key, value in extra_context.items():
                assert error.context[key] == value

    def test_state_error_with_cause(self):
        """Test StateError with cause exception."""
        original_error = RuntimeError("State violation")
        error = StateError("Operation failed", cause=original_error)
        assert error.cause == original_error

    def test_state_none_not_stored_in_context(self):
        """Test that None state is not added to context."""
        error = StateError("Failed", current_state=None)
        assert "current_state" not in error.context


class TestIssueNotFoundErrorInitialization:
    """Test IssueNotFoundError initialization and issue tracking."""

    @pytest.mark.parametrize(
        "message,issue_id,severity,extra_context,expected_id,context_has_id",
        [
            ("Issue does not exist", None, ErrorSeverity.MEDIUM, {}, None, False),
            (
                "Issue not found",
                "ISSUE-123",
                ErrorSeverity.MEDIUM,
                {},
                "ISSUE-123",
                True,
            ),
            ("Issue not found", "456", ErrorSeverity.MEDIUM, {}, "456", True),
            (
                "Critical issue missing",
                "CRIT-001",
                ErrorSeverity.HIGH,
                {},
                "CRIT-001",
                True,
            ),
            (
                "Not found",
                "ISSUE-999",
                ErrorSeverity.MEDIUM,
                {"searched_in": "database", "timestamp": "2024-01-01"},
                "ISSUE-999",
                True,
            ),
            (
                "Not found",
                "ISSUE-123-DRAFT",
                ErrorSeverity.MEDIUM,
                {},
                "ISSUE-123-DRAFT",
                True,
            ),
        ],
    )
    def test_issue_not_found_error_initialization(
        self, message, issue_id, severity, extra_context, expected_id, context_has_id
    ):
        """Test IssueNotFoundError initialization with various parameters."""
        kwargs = {"issue_id": issue_id, "severity": severity}
        if extra_context:
            kwargs["context"] = extra_context
        error = IssueNotFoundError(message, **kwargs)
        assert str(error) == message
        assert error.issue_id == expected_id
        assert error.severity == severity
        assert error.category == ErrorCategory.VALIDATION
        if context_has_id:
            assert error.context["issue_id"] == expected_id
        else:
            assert "issue_id" not in error.context
        if extra_context:
            for key, value in extra_context.items():
                assert error.context[key] == value

    def test_issue_not_found_error_with_cause(self):
        """Test IssueNotFoundError with cause exception."""
        original_error = LookupError("Database lookup failed")
        error = IssueNotFoundError("Issue not found", cause=original_error)
        assert error.cause == original_error

    def test_issue_id_none_not_stored_in_context(self):
        """Test that None issue_id is not added to context."""
        error = IssueNotFoundError("Not found", issue_id=None)
        assert "issue_id" not in error.context


class TestMilestoneNotFoundErrorInitialization:
    """Test MilestoneNotFoundError initialization and milestone tracking."""

    @pytest.mark.parametrize(
        "message,milestone_name,severity,extra_context,expected_name,context_has_name",
        [
            ("Milestone does not exist", None, ErrorSeverity.MEDIUM, {}, None, False),
            (
                "Milestone not found",
                "sprint-1",
                ErrorSeverity.MEDIUM,
                {},
                "sprint-1",
                True,
            ),
            (
                "Not found",
                "Q4 2024 - Final Release",
                ErrorSeverity.MEDIUM,
                {},
                "Q4 2024 - Final Release",
                True,
            ),
            (
                "Critical milestone missing",
                "Release 1.0",
                ErrorSeverity.HIGH,
                {},
                "Release 1.0",
                True,
            ),
            (
                "Milestone missing",
                "Q1 Planning",
                ErrorSeverity.MEDIUM,
                {"project": "roadmap", "season": "Q1"},
                "Q1 Planning",
                True,
            ),
            (
                "Not found",
                "Sprint #1 (Alpha) [URGENT]",
                ErrorSeverity.MEDIUM,
                {},
                "Sprint #1 (Alpha) [URGENT]",
                True,
            ),
        ],
    )
    def test_milestone_not_found_error_initialization(
        self,
        message,
        milestone_name,
        severity,
        extra_context,
        expected_name,
        context_has_name,
    ):
        """Test MilestoneNotFoundError initialization with various parameters."""
        kwargs = {"milestone_name": milestone_name, "severity": severity}
        if extra_context:
            kwargs["context"] = extra_context
        error = MilestoneNotFoundError(message, **kwargs)
        assert str(error) == message
        assert error.milestone_name == expected_name
        assert error.severity == severity
        assert error.category == ErrorCategory.VALIDATION
        if context_has_name:
            assert error.context["milestone"] == expected_name
        else:
            assert "milestone" not in error.context
        if extra_context:
            for key, value in extra_context.items():
                assert error.context[key] == value

    def test_milestone_not_found_error_with_cause(self):
        """Test MilestoneNotFoundError with cause exception."""
        original_error = KeyError("Key not found")
        error = MilestoneNotFoundError("Not found", cause=original_error)
        assert error.cause == original_error

    def test_milestone_name_none_not_stored_in_context(self):
        """Test that None milestone_name is not added to context."""
        error = MilestoneNotFoundError("Not found", milestone_name=None)
        assert "milestone" not in error.context


class TestErrorInheritance:
    """Test error class inheritance and parent behavior."""

    def test_validation_error_inherits_from_roadmap_error(self):
        """Test ValidationError inherits from RoadmapError."""
        error = ValidationError("Test")
        assert hasattr(error, "category")
        assert hasattr(error, "severity")
        assert hasattr(error, "context")

    def test_state_error_inherits_from_roadmap_error(self):
        """Test StateError inherits from RoadmapError."""
        error = StateError("Test")
        assert hasattr(error, "category")
        assert hasattr(error, "severity")
        assert hasattr(error, "context")

    def test_issue_not_found_inherits_from_roadmap_error(self):
        """Test IssueNotFoundError inherits from RoadmapError."""
        error = IssueNotFoundError("Test")
        assert hasattr(error, "category")
        assert hasattr(error, "severity")
        assert hasattr(error, "context")

    def test_milestone_not_found_inherits_from_roadmap_error(self):
        """Test MilestoneNotFoundError inherits from RoadmapError."""
        error = MilestoneNotFoundError("Test")
        assert hasattr(error, "category")
        assert hasattr(error, "severity")
        assert hasattr(error, "context")
