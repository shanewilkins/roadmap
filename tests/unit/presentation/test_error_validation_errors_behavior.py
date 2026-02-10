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
                "Milestone not found", milestone_name="sprint-1"
            )

        error = exc_info.value
        assert error.milestone_name == "sprint-1"

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
