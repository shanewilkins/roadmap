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
                "Sprint 1",
                ErrorSeverity.MEDIUM,
                {},
                "Sprint 1",
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


class TestValidationErrorEdgeCases:
    """Test edge cases and boundary conditions for ValidationError."""

    def test_empty_message(self):
        """Test ValidationError with empty message."""
        error = ValidationError("")
        assert str(error) == ""

    def test_very_long_message(self):
        """Test ValidationError with very long message."""
        long_message = "x" * 10000
        error = ValidationError(long_message)
        assert str(error) == long_message

    def test_message_with_special_characters(self):
        """Test ValidationError with special characters in message."""
        special_message = "Error: Invalid value! @#$%^&*()"
        error = ValidationError(special_message)
        assert str(error) == special_message

    def test_unicode_in_message_and_field(self):
        """Test ValidationError with Unicode characters."""
        error = ValidationError("Erreur: valeur invalide", field="électronique")
        assert "électronique" in error.context["field"]

    def test_very_long_field_name(self):
        """Test ValidationError with very long field name."""
        long_field = "field_" + "x" * 1000
        error = ValidationError("Invalid", field=long_field)
        assert error.field == long_field
        assert long_field in error.context["field"]

    def test_very_long_value(self):
        """Test ValidationError with very long value."""
        long_value = "v" * 10000
        error = ValidationError("Invalid", value=long_value)
        assert error.value == long_value

    def test_numeric_field_name(self):
        """Test ValidationError with numeric field name."""
        error = ValidationError("Invalid", field="field_123")
        assert error.field == "field_123"

    def test_context_override_with_field(self):
        """Test that field parameter overrides context field."""
        error = ValidationError(
            "Failed",
            field="new_field",
            context={"field": "old_field"},
        )
        assert error.context["field"] == "new_field"

    def test_zero_value(self):
        """Test ValidationError with zero value."""
        error = ValidationError("Invalid", value=0)
        assert error.value == 0
        assert "0" in error.context["value"]

    def test_false_value(self):
        """Test ValidationError with False value."""
        error = ValidationError("Invalid", value=False)
        assert error.value is False
        assert "False" in error.context["value"]

    def test_empty_string_value(self):
        """Test ValidationError with empty string value."""
        error = ValidationError("Invalid", value="")
        assert error.value == ""
        assert "" in error.context["value"]


class TestStateErrorEdgeCases:
    """Test edge cases for StateError."""

    def test_state_with_special_characters(self):
        """Test StateError with special state values."""
        error = StateError("Failed", current_state="state_with-special.chars")
        assert error.current_state == "state_with-special.chars"

    def test_very_long_state_name(self):
        """Test StateError with very long state name."""
        long_state = "state_" + "x" * 1000
        error = StateError("Failed", current_state=long_state)
        assert error.current_state == long_state


class TestIssueNotFoundErrorEdgeCases:
    """Test edge cases for IssueNotFoundError."""

    def test_numeric_issue_id(self):
        """Test with purely numeric issue ID."""
        error = IssueNotFoundError("Not found", issue_id="12345")
        assert error.issue_id == "12345"

    def test_uuid_issue_id(self):
        """Test with UUID-like issue ID."""
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        error = IssueNotFoundError("Not found", issue_id=uuid_id)
        assert error.issue_id == uuid_id

    def test_issue_id_with_forward_slash(self):
        """Test with issue ID containing forward slash."""
        error = IssueNotFoundError("Not found", issue_id="OWNER/REPO#123")
        assert error.issue_id == "OWNER/REPO#123"


class TestMilestoneNotFoundErrorEdgeCases:
    """Test edge cases for MilestoneNotFoundError."""

    def test_numeric_milestone_name(self):
        """Test with purely numeric milestone name."""
        error = MilestoneNotFoundError("Not found", milestone_name="2024")
        assert error.milestone_name == "2024"

    def test_milestone_with_versions(self):
        """Test with version-like milestone names."""
        error = MilestoneNotFoundError("Not found", milestone_name="v1.2.3-beta.1")
        assert error.milestone_name == "v1.2.3-beta.1"

    def test_milestone_with_dates(self):
        """Test with date-like milestone names."""
        error = MilestoneNotFoundError("Not found", milestone_name="2024-Q1-End")
        assert error.milestone_name == "2024-Q1-End"


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


class TestErrorCategoryAndSeverity:
    """Test error category and severity levels."""

    def test_all_errors_have_validation_category(self):
        """Test all error classes have VALIDATION category."""
        errors = [
            ValidationError("msg"),
            StateError("msg"),
            IssueNotFoundError("msg"),
            MilestoneNotFoundError("msg"),
        ]
        for error in errors:
            assert error.category == ErrorCategory.VALIDATION

    def test_all_errors_default_to_medium_severity(self):
        """Test all error classes default to MEDIUM severity."""
        errors = [
            ValidationError("msg"),
            StateError("msg"),
            IssueNotFoundError("msg"),
            MilestoneNotFoundError("msg"),
        ]
        for error in errors:
            assert error.severity == ErrorSeverity.MEDIUM

    def test_custom_severity_applied_to_all_errors(self):
        """Test custom severity can be set on all error types."""
        errors = [
            ValidationError("msg", severity=ErrorSeverity.LOW),
            StateError("msg", severity=ErrorSeverity.HIGH),
            IssueNotFoundError("msg", severity=ErrorSeverity.LOW),
            MilestoneNotFoundError("msg", severity=ErrorSeverity.HIGH),
        ]
        assert errors[0].severity == ErrorSeverity.LOW
        assert errors[1].severity == ErrorSeverity.HIGH
        assert errors[2].severity == ErrorSeverity.LOW
        assert errors[3].severity == ErrorSeverity.HIGH


class TestContextHandling:
    """Test context dictionary management and merging."""

    def test_context_preserves_initial_values(self):
        """Test that initial context values are preserved."""
        context = {"key1": "value1", "key2": "value2"}
        error = ValidationError("msg", context=context)
        assert error.context["key1"] == "value1"
        assert error.context["key2"] == "value2"

    def test_field_adds_to_context(self):
        """Test that field parameter is added to context."""
        error = ValidationError(
            "msg", field="test_field", context={"existing": "value"}
        )
        assert error.context["existing"] == "value"
        assert error.context["field"] == "test_field"

    def test_multiple_parameters_merge_in_context(self):
        """Test that multiple parameters merge into context."""
        error = StateError(
            "msg",
            current_state="test_state",
            context={"key": "value"},
        )
        assert error.context["key"] == "value"
        assert error.context["current_state"] == "test_state"

    def test_empty_context_initialization(self):
        """Test error with empty context dict."""
        error = ValidationError("msg", context={})
        assert isinstance(error.context, dict)

    def test_context_with_various_value_types(self):
        """Test context with different value types."""
        context = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        error = ValidationError("msg", context=context)
        assert error.context["string"] == "value"
        assert error.context["number"] == 42
        assert error.context["list"] == [1, 2, 3]
        assert error.context["dict"]["nested"] == "value"


class TestErrorIntegration:
    """Integration tests for error validation module."""

    def test_raising_validation_error(self):
        """Test raising and catching ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid email", field="email")

        error = exc_info.value
        assert error.field == "email"
        assert error.context["field"] == "email"

    def test_raising_state_error(self):
        """Test raising and catching StateError."""
        with pytest.raises(StateError) as exc_info:
            raise StateError("Invalid transition", current_state="closed")

        error = exc_info.value
        assert error.current_state == "closed"

    def test_raising_issue_not_found_error(self):
        """Test raising and catching IssueNotFoundError."""
        with pytest.raises(IssueNotFoundError) as exc_info:
            raise IssueNotFoundError("Issue not found", issue_id="ISSUE-1")

        error = exc_info.value
        assert error.issue_id == "ISSUE-1"

    def test_raising_milestone_not_found_error(self):
        """Test raising and catching MilestoneNotFoundError."""
        with pytest.raises(MilestoneNotFoundError) as exc_info:
            raise MilestoneNotFoundError(
                "Milestone not found", milestone_name="Sprint 1"
            )

        error = exc_info.value
        assert error.milestone_name == "Sprint 1"

    def test_error_message_in_exception_string(self):
        """Test that error message appears in string representation."""
        message = "Custom error message"
        error = ValidationError(message)
        assert message in str(error)

    def test_catching_parent_type(self):
        """Test catching errors by parent class."""
        from roadmap.common.errors.error_base import RoadmapError

        errors_to_raise = [
            ValidationError("msg1"),
            StateError("msg2"),
            IssueNotFoundError("msg3"),
            MilestoneNotFoundError("msg4"),
        ]

        for error_instance in errors_to_raise:
            with pytest.raises(RoadmapError):
                raise error_instance
