"""Comprehensive tests for RoadmapValidator with parameterized scenarios.

Tests cover:
- Validator initialization and schema setup
- Issue, milestone, and project validation
- Field-level validation (strings, IDs, paths, etc.)
- Edge cases and error handling
"""

from datetime import datetime
from pathlib import Path

import pytest

from roadmap.common.constants import (
    MilestoneStatus,
    Priority,
    Status,
)
from roadmap.common.validation import RoadmapValidator, ValidationResult


class TestRoadmapValidatorInitialization:
    """Test RoadmapValidator initialization and setup."""

    def test_validator_initializes(self):
        """Test validator initializes with all schemas."""
        validator = RoadmapValidator()

        assert validator.issue_schema is not None
        assert validator.milestone_schema is not None
        assert validator.project_schema is not None

    def test_validator_schemas_are_configured(self):
        """Test that schemas are properly configured."""
        validator = RoadmapValidator()

        assert validator.issue_schema.schema_name == "issue"
        assert validator.milestone_schema.schema_name == "milestone"
        assert validator.project_schema.schema_name == "project"


class TestIssueValidation:
    """Test issue validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.fixture
    def valid_issue(self):
        return {
            "id": "12345678",
            "title": "Fix login bug",
            "priority": "high",
            "status": "in-progress",
            "issue_type": "bug",
            "assignee": "john_doe",
            "milestone": "v1-0",
            "estimated_hours": 8,
            "progress_percentage": 50,
        }

    def test_valid_issue(self, validator, valid_issue):
        """Test validation of valid issue."""
        result = validator.validate_issue(valid_issue)
        assert result.is_valid

    @pytest.mark.parametrize(
        "field_to_delete,field_to_mutate,mutation_value,expect_valid",
        [
            ("id", None, None, False),
            (None, "id", "invalid", False),
            ("title", None, None, False),
            (None, "title", "", False),
            (None, "title", "x" * 201, False),
            ("priority", None, None, False),
            (None, "priority", "urgent", False),
            ("status", None, None, False),
            (None, "status", "completed", False),
            (None, "issue_type", "task", False),
            (None, "assignee", "invalid@user", False),
            (None, "assignee", "a" * 40, False),
            (None, "assignee", "john_doe-smith", True),
            (None, "milestone", "x" * 101, False),
            (None, "estimated_hours", -5, False),
            (None, "estimated_hours", "abc", False),
            (None, "progress_percentage", -1, False),
            (None, "progress_percentage", 101, False),
            (None, "progress_percentage", 0, True),
            (None, "progress_percentage", 100, True),
        ],
    )
    def test_issue_field_mutations(
        self,
        validator,
        valid_issue,
        field_to_delete,
        field_to_mutate,
        mutation_value,
        expect_valid,
    ):
        """Test issue validation with various field mutations."""
        if field_to_delete:
            del valid_issue[field_to_delete]
        elif field_to_mutate:
            valid_issue[field_to_mutate] = mutation_value

        result = validator.validate_issue(valid_issue)
        assert result.is_valid == expect_valid

    def test_issue_optional_fields(self, validator):
        """Test issue with only required fields."""
        minimal_issue = {
            "id": "12345678",
            "title": "Fix bug",
            "priority": "high",
            "status": "todo",
        }
        result = validator.validate_issue(minimal_issue)
        assert result.is_valid


class TestMilestoneValidation:
    """Test milestone validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.fixture
    def valid_milestone(self):
        return {
            "name": "v1.0 Release",
            "status": "open",
            "description": "First production release",
            "due_date": "2025-12-31",
        }

    def test_valid_milestone(self, validator, valid_milestone):
        """Test validation of valid milestone."""
        result = validator.validate_milestone(valid_milestone)
        assert result.is_valid

    @pytest.mark.parametrize(
        "field_to_delete,field_to_mutate,mutation_value,expect_valid",
        [
            ("name", None, None, False),
            (None, "name", "", False),
            (None, "name", "x" * 101, False),
            ("status", None, None, False),
            (None, "status", "active", False),
            (None, "due_date", 12345, False),
        ],
    )
    def test_milestone_field_mutations(
        self,
        validator,
        valid_milestone,
        field_to_delete,
        field_to_mutate,
        mutation_value,
        expect_valid,
    ):
        """Test milestone validation with various field mutations."""
        if field_to_delete:
            del valid_milestone[field_to_delete]
        elif field_to_mutate:
            valid_milestone[field_to_mutate] = mutation_value

        result = validator.validate_milestone(valid_milestone)
        assert result.is_valid == expect_valid

    @pytest.mark.parametrize(
        "date_value",
        ["2025-12-31", "12/31/2025", "Dec 31, 2025", datetime(2025, 12, 31)],
    )
    def test_milestone_valid_date_formats(self, validator, valid_milestone, date_value):
        """Test milestone accepts various valid date formats."""
        valid_milestone["due_date"] = date_value
        result = validator.validate_milestone(valid_milestone)
        assert result.is_valid

    def test_milestone_minimal(self, validator):
        """Test milestone with only required fields."""
        minimal_milestone = {
            "name": "v1-0",
            "status": "open",
        }
        result = validator.validate_milestone(minimal_milestone)
        assert result.is_valid


class TestProjectValidation:
    """Test project validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.fixture
    def valid_project(self):
        return {
            "id": "abc-123def",
            "name": "Roadmap CLI",
            "description": "Command line tool for roadmap management",
            "owner": "team-dev",
            "estimated_hours": 100,
        }

    def test_valid_project(self, validator, valid_project):
        """Test validation of valid project."""
        result = validator.validate_project(valid_project)
        assert result.is_valid

    @pytest.mark.parametrize(
        "field_to_delete,field_to_mutate,mutation_value,expect_valid",
        [
            ("id", None, None, False),
            (None, "id", "invalid@id!", False),
            ("name", None, None, False),
            (None, "name", "", False),
            (None, "name", "x" * 201, False),
            (None, "owner", "x" * 101, False),
            (None, "estimated_hours", -50, False),
        ],
    )
    def test_project_field_mutations(
        self,
        validator,
        valid_project,
        field_to_delete,
        field_to_mutate,
        mutation_value,
        expect_valid,
    ):
        """Test project validation with various field mutations."""
        if field_to_delete:
            del valid_project[field_to_delete]
        elif field_to_mutate:
            valid_project[field_to_mutate] = mutation_value

        result = validator.validate_project(valid_project)
        assert result.is_valid == expect_valid

    def test_project_minimal(self, validator):
        """Test project with only required fields."""
        minimal_project = {
            "id": "abc-123",
            "name": "My Project",
        }
        result = validator.validate_project(minimal_project)
        assert result.is_valid


class TestRequiredFieldsValidation:
    """Test required fields validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "data,required_fields,expect_valid",
        [
            (
                {"name": "test", "status": "active", "owner": "user"},
                ["name", "status", "owner"],
                True,
            ),
            ({"name": "test", "owner": "user"}, ["name", "status", "owner"], False),
            ({"name": "test"}, ["name", "status", "owner", "description"], False),
            (
                {"name": "test", "status": None, "owner": "user"},
                ["name", "status", "owner"],
                False,
            ),
            (
                {"name": "test", "status": "", "owner": "user"},
                ["name", "status", "owner"],
                False,
            ),
            ({"name": "test"}, [], True),
        ],
    )
    def test_required_fields_validation(
        self, validator, data, required_fields, expect_valid
    ):
        """Test required fields validation with various scenarios."""
        result = validator.validate_required_fields(data, required_fields)
        assert result.is_valid == expect_valid


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


class TestEnumFieldValidation:
    """Test enum field validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    @pytest.mark.parametrize(
        "value,field_name,enum_class,expect_valid",
        [
            ("high", "priority", Priority, True),
            ("urgent", "priority", Priority, False),
            (Priority.HIGH, "priority", Priority, True),
            (None, "priority", Priority, True),
            (999999, "priority", Priority, False),
        ],
    )
    def test_enum_field_validation(
        self, validator, value, field_name, enum_class, expect_valid
    ):
        """Test enum field validation with various values."""
        result = validator.validate_enum_field(value, field_name, enum_class)
        assert result.is_valid == expect_valid

    @pytest.mark.parametrize("priority", Priority)
    def test_all_valid_priority_values(self, validator, priority):
        """Test all valid priority values."""
        result = validator.validate_enum_field(priority.value, "priority", Priority)
        assert result.is_valid

    @pytest.mark.parametrize("status", Status)
    def test_all_valid_status_values(self, validator, status):
        """Test all valid status values."""
        result = validator.validate_enum_field(status.value, "status", Status)
        assert result.is_valid

    @pytest.mark.parametrize("ms_status", MilestoneStatus)
    def test_all_valid_milestone_status_values(self, validator, ms_status):
        """Test all valid milestone status values."""
        result = validator.validate_enum_field(
            ms_status.value, "milestone_status", MilestoneStatus
        )
        assert result.is_valid


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
