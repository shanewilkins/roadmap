"""Comprehensive tests for RoadmapValidator."""

from pathlib import Path

import pytest

from roadmap.common.constants import (
    Priority,
)
from roadmap.common.validation import RoadmapValidator, ValidationResult


class TestStringLengthValidation:
    """Test string length validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "value,field_name,min_length,max_length,expect_valid",
        [
            ("hello", "test_field", 1, 10, True),
            ("hi", "test_field", 5, 10, False),
            ("hello world", "test_field", 1, 5, False),
            ("hello", "test_field", 5, 10, True),
            ("hello", "test_field", 1, 5, True),
            ("", "test_field", 1, 10, False),
            (None, "test_field", None, None, True),
            ("very long string here", "test_field", 1, None, True),
        ],
    )
    def test_string_length_validation(
        self, validator, value, field_name, min_length, max_length, expect_valid
    ):
        """Test string length validation with various inputs."""
        result = validator.validate_string_length(
            value, field_name, min_length=min_length, max_length=max_length
        )
        assert result.is_valid == expect_valid


class TestIdFormatValidation:
    """Test ID format validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "id_value,field_name,expect_valid",
        [
            ("12345678", "issue_id", True),
            ("abc-123def", "project_id", True),
            ("invalid@id!", "id", False),
            ("ABCDEF12", "id", False),
            ("", "id", False),
            (None, "id", False),
        ],
    )
    def test_id_format_validation(self, validator, id_value, field_name, expect_valid):
        """Test ID format validation with various inputs."""
        result = validator.validate_id_format(id_value, field_name)
        assert result.is_valid == expect_valid


class TestPathValidation:
    """Test path validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "path_value,field_name,expect_valid",
        [
            ("docs/readme.md", "filepath", True),
            ("src/components/Button.tsx", "filepath", True),
            (Path("docs/readme.md"), "filepath", True),
            ("../../../etc/passwd", "filepath", False),
            ("/etc/passwd", "relative_path", False),
            ("/path/to/file.txt", "filename", False),
            (None, "filepath", True),
        ],
    )
    def test_path_validation(self, validator, path_value, field_name, expect_valid):
        """Test path validation with various inputs."""
        result = validator.validate_path(path_value, field_name)
        assert result.is_valid == expect_valid


class TestGithubIssueNumberValidation:
    """Test GitHub issue number validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "issue_number,field_name,expect_valid",
        [
            (123, "github_issue", True),
            ("456", "github_issue", True),
            (-1, "github_issue", False),
            (0, "github_issue", False),
            ("abc", "github_issue", False),
            (None, "github_issue", True),
            (999999999, "github_issue", True),
            (123.45, "github_issue", True),
        ],
    )
    def test_github_issue_number_validation(
        self, validator, issue_number, field_name, expect_valid
    ):
        """Test GitHub issue number validation with various inputs."""
        result = validator.validate_github_issue_number(issue_number, field_name)
        assert result.is_valid == expect_valid


class TestLabelsValidation:
    """Test labels validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "labels_value,field_name,expect_valid",
        [
            (["bug", "feature", "documentation"], "labels", True),
            ([], "labels", True),
            ("bug,feature", "labels", False),
            (["bug", 123, "feature"], "labels", False),
            (["x" * 51], "labels", False),
            (["x" * 50], "labels", True),
            (["bug", "", "feature"], "labels", False),
            (["bug", "   ", "feature"], "labels", False),
            (None, "labels", True),
            (["bug-fix", "type: feature", "p/high-priority"], "labels", True),
        ],
    )
    def test_labels_validation(self, validator, labels_value, field_name, expect_valid):
        """Test labels validation with various inputs."""
        result = validator.validate_labels(labels_value, field_name)
        assert result.is_valid == expect_valid


class TestValidationResultIntegration:
    """Test ValidationResult field tracking."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_result_field_assignment(self, validator):
        """Test ValidationResult tracks field name."""
        result = validator.validate_string_length("", "email", min_length=1)
        assert result.field == "email"

    def test_multiple_validation_errors(
        self,
        validator,
    ):
        """Test issue with multiple validation errors."""
        invalid_issue = {
            "id": "invalid",  # wrong format
            "title": "",  # empty
            "priority": "critical",  # invalid
            "status": "done",  # invalid
        }
        result = validator.validate_issue(invalid_issue)
        assert not result.is_valid
        assert len(result.errors) > 1


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_assignee_with_numbers(self, validator):
        """Test assignee with numbers is valid."""
        result = validator.validate_string_length("user123", "assignee")
        assert result.is_valid

    def test_very_large_numbers(self, validator):
        """Test handling of very large numbers."""
        result = validator.validate_enum_field(999999, "priority", Priority)
        assert not result.is_valid

    def test_unicode_in_string_fields(self, validator):
        """Test unicode characters in string fields."""
        result = validator.validate_string_length("Project 🚀", "name")
        assert result.is_valid

    def test_whitespace_only_assignee(self, validator):
        """Test assignee with only whitespace."""
        result = validator.validate_string_length("   ", "assignee")
        assert result.is_valid  # length check doesn't care about content

    def test_float_issue_number(self, validator):
        """Test float as issue number."""
        result = validator.validate_github_issue_number(123.45, "github_issue")
        # Should convert and check if it's > 0
        assert result.is_valid

    def test_empty_validation_result(self):
        """Test empty ValidationResult."""
        result = ValidationResult()
        assert result.is_valid
        assert result.errors == []
