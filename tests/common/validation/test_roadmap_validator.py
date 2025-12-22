"""Comprehensive tests for RoadmapValidator."""

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
            "milestone": "v1.0",
            "estimated_hours": 8,
            "progress_percentage": 50,
        }

    def test_valid_issue(self, validator, valid_issue):
        """Test validation of valid issue."""
        result = validator.validate_issue(valid_issue)
        assert result.is_valid

    def test_issue_missing_id(self, validator, valid_issue):
        """Test issue validation fails without id."""
        del valid_issue["id"]
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid
        assert any("id" in err.lower() for err in result.errors)

    def test_issue_invalid_id_format(self, validator, valid_issue):
        """Test issue validation fails with invalid id format."""
        valid_issue["id"] = "invalid"
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_missing_title(self, validator, valid_issue):
        """Test issue validation fails without title."""
        del valid_issue["title"]
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_empty_title(self, validator, valid_issue):
        """Test issue validation fails with empty title."""
        valid_issue["title"] = ""
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_title_too_long(self, validator, valid_issue):
        """Test issue validation fails with title > 200 chars."""
        valid_issue["title"] = "x" * 201
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_missing_priority(self, validator, valid_issue):
        """Test issue validation fails without priority."""
        del valid_issue["priority"]
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_invalid_priority(self, validator, valid_issue):
        """Test issue validation fails with invalid priority."""
        valid_issue["priority"] = "urgent"
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_missing_status(self, validator, valid_issue):
        """Test issue validation fails without status."""
        del valid_issue["status"]
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_invalid_status(self, validator, valid_issue):
        """Test issue validation fails with invalid status."""
        valid_issue["status"] = "completed"
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_invalid_issue_type(self, validator, valid_issue):
        """Test issue validation fails with invalid type."""
        valid_issue["issue_type"] = "task"
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_invalid_assignee_format(self, validator, valid_issue):
        """Test issue validation fails with invalid assignee format."""
        valid_issue["assignee"] = "invalid@user"
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_assignee_too_long(self, validator, valid_issue):
        """Test issue validation fails when assignee > 39 chars."""
        valid_issue["assignee"] = "a" * 40
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_valid_assignee_with_special_chars(self, validator, valid_issue):
        """Test valid assignees with hyphens and underscores."""
        valid_issue["assignee"] = "john_doe-smith"
        result = validator.validate_issue(valid_issue)
        assert result.is_valid

    def test_issue_milestone_too_long(self, validator, valid_issue):
        """Test issue validation fails when milestone > 100 chars."""
        valid_issue["milestone"] = "x" * 101
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_negative_estimated_hours(self, validator, valid_issue):
        """Test issue validation fails with negative estimated hours."""
        valid_issue["estimated_hours"] = -5
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_invalid_estimated_hours(self, validator, valid_issue):
        """Test issue validation fails with non-numeric estimated hours."""
        valid_issue["estimated_hours"] = "abc"
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_progress_percentage_below_zero(self, validator, valid_issue):
        """Test issue validation fails with progress < 0."""
        valid_issue["progress_percentage"] = -1
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_progress_percentage_above_100(self, validator, valid_issue):
        """Test issue validation fails with progress > 100."""
        valid_issue["progress_percentage"] = 101
        result = validator.validate_issue(valid_issue)
        assert not result.is_valid

    def test_issue_valid_progress_percentage_boundaries(self, validator, valid_issue):
        """Test issue validation accepts 0 and 100 for progress."""
        valid_issue["progress_percentage"] = 0
        result = validator.validate_issue(valid_issue)
        assert result.is_valid

        valid_issue["progress_percentage"] = 100
        result = validator.validate_issue(valid_issue)
        assert result.is_valid

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

    def test_milestone_missing_name(self, validator, valid_milestone):
        """Test milestone validation fails without name."""
        del valid_milestone["name"]
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_empty_name(self, validator, valid_milestone):
        """Test milestone validation fails with empty name."""
        valid_milestone["name"] = ""
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_name_too_long(self, validator, valid_milestone):
        """Test milestone validation fails with name > 100 chars."""
        valid_milestone["name"] = "x" * 101
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_missing_status(self, validator, valid_milestone):
        """Test milestone validation fails without status."""
        del valid_milestone["status"]
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_invalid_status(self, validator, valid_milestone):
        """Test milestone validation fails with invalid status."""
        valid_milestone["status"] = "active"
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_description_too_long(self, validator, valid_milestone):
        """Test milestone validation fails with description > 1000 chars."""
        valid_milestone["description"] = "x" * 1001
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_invalid_due_date(self, validator, valid_milestone):
        """Test milestone validation fails with invalid date."""
        valid_milestone["due_date"] = 12345  # Invalid type
        result = validator.validate_milestone(valid_milestone)
        assert not result.is_valid

    def test_milestone_valid_due_date_formats(self, validator, valid_milestone):
        """Test milestone accepts various valid date formats."""
        for date_str in ["2025-12-31", "12/31/2025", "Dec 31, 2025"]:
            valid_milestone["due_date"] = date_str
            result = validator.validate_milestone(valid_milestone)
            assert result.is_valid, f"Failed for date format: {date_str}"

    def test_milestone_with_datetime_object(self, validator, valid_milestone):
        """Test milestone accepts datetime objects."""
        valid_milestone["due_date"] = datetime(2025, 12, 31)
        result = validator.validate_milestone(valid_milestone)
        assert result.is_valid

    def test_milestone_minimal(self, validator):
        """Test milestone with only required fields."""
        minimal_milestone = {
            "name": "v1.0",
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

    def test_project_missing_id(self, validator, valid_project):
        """Test project validation fails without id."""
        del valid_project["id"]
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_invalid_id_format(self, validator, valid_project):
        """Test project validation fails with invalid id format."""
        valid_project["id"] = "invalid@id!"
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_missing_name(self, validator, valid_project):
        """Test project validation fails without name."""
        del valid_project["name"]
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_empty_name(self, validator, valid_project):
        """Test project validation fails with empty name."""
        valid_project["name"] = ""
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_name_too_long(self, validator, valid_project):
        """Test project validation fails with name > 200 chars."""
        valid_project["name"] = "x" * 201
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_description_too_long(self, validator, valid_project):
        """Test project validation fails with description > 2000 chars."""
        valid_project["description"] = "x" * 2001
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_owner_too_long(self, validator, valid_project):
        """Test project validation fails with owner > 100 chars."""
        valid_project["owner"] = "x" * 101
        result = validator.validate_project(valid_project)
        assert not result.is_valid

    def test_project_negative_estimated_hours(self, validator, valid_project):
        """Test project validation fails with negative estimated hours."""
        valid_project["estimated_hours"] = -50
        result = validator.validate_project(valid_project)
        assert not result.is_valid

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

    def test_all_fields_present(self, validator):
        """Test validation passes when all fields present."""
        data = {"name": "test", "status": "active", "owner": "user"}
        result = validator.validate_required_fields(data, ["name", "status", "owner"])
        assert result.is_valid

    def test_missing_single_field(self, validator):
        """Test validation fails when one field missing."""
        data = {"name": "test", "owner": "user"}
        result = validator.validate_required_fields(data, ["name", "status", "owner"])
        assert not result.is_valid
        assert "Missing required fields" in str(result.errors)

    def test_missing_multiple_fields(self, validator):
        """Test validation fails when multiple fields missing."""
        data = {"name": "test"}
        result = validator.validate_required_fields(
            data, ["name", "status", "owner", "description"]
        )
        assert not result.is_valid
        assert any("status" in err for err in result.errors)

    def test_null_field_considered_missing(self, validator):
        """Test validation fails when field is null."""
        data = {"name": "test", "status": None, "owner": "user"}
        result = validator.validate_required_fields(data, ["name", "status", "owner"])
        assert not result.is_valid

    def test_empty_string_field_considered_missing(self, validator):
        """Test validation fails when field is empty string."""
        data = {"name": "test", "status": "", "owner": "user"}
        result = validator.validate_required_fields(data, ["name", "status", "owner"])
        assert not result.is_valid

    def test_empty_required_fields_list(self, validator):
        """Test validation passes with empty required fields list."""
        data = {"name": "test"}
        result = validator.validate_required_fields(data, [])
        assert result.is_valid


class TestEnumFieldValidation:
    """Test enum field validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_valid_enum_value(self, validator):
        """Test validation passes with valid enum value."""
        result = validator.validate_enum_field("high", "priority", Priority)
        assert result.is_valid

    def test_invalid_enum_value(self, validator):
        """Test validation fails with invalid enum value."""
        result = validator.validate_enum_field("urgent", "priority", Priority)
        assert not result.is_valid

    def test_enum_value_object(self, validator):
        """Test validation accepts enum objects."""
        result = validator.validate_enum_field(Priority.HIGH, "priority", Priority)
        assert result.is_valid

    def test_none_enum_value(self, validator):
        """Test validation passes with None value."""
        result = validator.validate_enum_field(None, "priority", Priority)
        assert result.is_valid

    def test_all_valid_priority_values(self, validator):
        """Test all valid priority values."""
        for priority in Priority:
            result = validator.validate_enum_field(priority.value, "priority", Priority)
            assert result.is_valid

    def test_all_valid_status_values(self, validator):
        """Test all valid status values."""
        for status in Status:
            result = validator.validate_enum_field(status.value, "status", Status)
            assert result.is_valid

    def test_all_valid_milestone_status_values(self, validator):
        """Test all valid milestone status values."""
        for ms_status in MilestoneStatus:
            result = validator.validate_enum_field(
                ms_status.value, "milestone_status", MilestoneStatus
            )
            assert result.is_valid


class TestStringLengthValidation:
    """Test string length validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_valid_string_length(self, validator):
        """Test validation passes with valid length."""
        result = validator.validate_string_length(
            "hello", "test_field", min_length=1, max_length=10
        )
        assert result.is_valid

    def test_string_too_short(self, validator):
        """Test validation fails when string too short."""
        result = validator.validate_string_length(
            "hi", "test_field", min_length=5, max_length=10
        )
        assert not result.is_valid

    def test_string_too_long(self, validator):
        """Test validation fails when string too long."""
        result = validator.validate_string_length(
            "hello world", "test_field", min_length=1, max_length=5
        )
        assert not result.is_valid

    def test_string_at_min_boundary(self, validator):
        """Test validation passes at minimum boundary."""
        result = validator.validate_string_length(
            "hello", "test_field", min_length=5, max_length=10
        )
        assert result.is_valid

    def test_string_at_max_boundary(self, validator):
        """Test validation passes at maximum boundary."""
        result = validator.validate_string_length(
            "hello", "test_field", min_length=1, max_length=5
        )
        assert result.is_valid

    def test_empty_string_with_min_length(self, validator):
        """Test empty string fails min_length validation."""
        result = validator.validate_string_length(
            "", "test_field", min_length=1, max_length=10
        )
        assert not result.is_valid

    def test_none_value(self, validator):
        """Test None value passes validation."""
        result = validator.validate_string_length(None, "test_field")
        assert result.is_valid

    def test_no_max_length(self, validator):
        """Test validation without max length."""
        result = validator.validate_string_length(
            "very long string here", "test_field", min_length=1
        )
        assert result.is_valid


class TestIdFormatValidation:
    """Test ID format validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_valid_issue_id(self, validator):
        """Test valid 8-character hex ID."""
        result = validator.validate_id_format("12345678", "issue_id")
        assert result.is_valid

    def test_valid_project_id(self, validator):
        """Test valid UUID-like project ID."""
        result = validator.validate_id_format("abc-123def", "project_id")
        assert result.is_valid

    def test_invalid_id_format(self, validator):
        """Test invalid ID format."""
        result = validator.validate_id_format("invalid@id!", "id")
        assert not result.is_valid

    def test_id_with_uppercase_hex(self, validator):
        """Test ID with uppercase hex characters fails."""
        result = validator.validate_id_format("ABCDEF12", "id")
        assert not result.is_valid

    def test_empty_id(self, validator):
        """Test empty ID fails validation."""
        result = validator.validate_id_format("", "id")
        assert not result.is_valid

    def test_none_id(self, validator):
        """Test None ID fails validation."""
        result = validator.validate_id_format(None, "id")
        assert not result.is_valid


class TestPathValidation:
    """Test path validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_valid_relative_path(self, validator):
        """Test valid relative path."""
        result = validator.validate_path("docs/readme.md", "filepath")
        assert result.is_valid

    def test_valid_path_with_directories(self, validator):
        """Test valid path with multiple directories."""
        result = validator.validate_path("src/components/Button.tsx", "filepath")
        assert result.is_valid

    def test_path_with_path_object(self, validator):
        """Test path validation with Path object."""
        result = validator.validate_path(Path("docs/readme.md"), "filepath")
        assert result.is_valid

    def test_path_with_traversal_fails(self, validator):
        """Test path with '..' traversal fails validation."""
        result = validator.validate_path("../../../etc/passwd", "filepath")
        assert not result.is_valid

    def test_absolute_path_for_relative_field(self, validator):
        """Test absolute path fails when relative expected."""
        result = validator.validate_path("/etc/passwd", "relative_path")
        assert not result.is_valid

    def test_absolute_path_for_filename(self, validator):
        """Test absolute path fails for filename field."""
        result = validator.validate_path("/path/to/file.txt", "filename")
        assert not result.is_valid

    def test_none_path(self, validator):
        """Test None path passes validation."""
        result = validator.validate_path(None, "filepath")
        assert result.is_valid


class TestGithubIssueNumberValidation:
    """Test GitHub issue number validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_valid_issue_number(self, validator):
        """Test valid issue number."""
        result = validator.validate_github_issue_number(123, "github_issue")
        assert result.is_valid

    def test_valid_issue_number_as_string(self, validator):
        """Test valid issue number as string."""
        result = validator.validate_github_issue_number("456", "github_issue")
        assert result.is_valid

    def test_invalid_negative_issue_number(self, validator):
        """Test negative issue number fails validation."""
        result = validator.validate_github_issue_number(-1, "github_issue")
        assert not result.is_valid

    def test_invalid_zero_issue_number(self, validator):
        """Test zero issue number fails validation."""
        result = validator.validate_github_issue_number(0, "github_issue")
        assert not result.is_valid

    def test_invalid_non_numeric_issue_number(self, validator):
        """Test non-numeric issue number fails validation."""
        result = validator.validate_github_issue_number("abc", "github_issue")
        assert not result.is_valid

    def test_none_issue_number(self, validator):
        """Test None issue number passes validation."""
        result = validator.validate_github_issue_number(None, "github_issue")
        assert result.is_valid

    def test_large_issue_number(self, validator):
        """Test large issue number passes validation."""
        result = validator.validate_github_issue_number(999999999, "github_issue")
        assert result.is_valid


class TestLabelsValidation:
    """Test labels validation."""

    @pytest.fixture
    def validator(self):
        return RoadmapValidator()

    def test_valid_labels(self, validator):
        """Test valid labels list."""
        result = validator.validate_labels(
            ["bug", "feature", "documentation"], "labels"
        )
        assert result.is_valid

    def test_empty_labels_list(self, validator):
        """Test empty labels list passes validation."""
        result = validator.validate_labels([], "labels")
        assert result.is_valid

    def test_labels_not_list(self, validator):
        """Test non-list labels fails validation."""
        result = validator.validate_labels("bug,feature", "labels")
        assert not result.is_valid

    def test_labels_with_non_string_element(self, validator):
        """Test labels with non-string element fails validation."""
        result = validator.validate_labels(["bug", 123, "feature"], "labels")
        assert not result.is_valid

    def test_label_too_long(self, validator):
        """Test label > 50 characters fails validation."""
        result = validator.validate_labels(["x" * 51], "labels")
        assert not result.is_valid

    def test_label_at_max_length(self, validator):
        """Test label with exactly 50 characters passes validation."""
        result = validator.validate_labels(["x" * 50], "labels")
        assert result.is_valid

    def test_empty_label_string(self, validator):
        """Test empty label string fails validation."""
        result = validator.validate_labels(["bug", "", "feature"], "labels")
        assert not result.is_valid

    def test_label_with_only_whitespace(self, validator):
        """Test label with only whitespace fails validation."""
        result = validator.validate_labels(["bug", "   ", "feature"], "labels")
        assert not result.is_valid

    def test_none_labels(self, validator):
        """Test None labels passes validation."""
        result = validator.validate_labels(None, "labels")
        assert result.is_valid

    def test_labels_with_special_characters(self, validator):
        """Test labels with special characters pass validation."""
        result = validator.validate_labels(
            ["bug-fix", "type: feature", "p/high-priority"], "labels"
        )
        assert result.is_valid


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
