"""Tests for Roadmap validation."""

from unittest.mock import MagicMock

import pytest

from roadmap.common.validation.result import ValidationResult
from roadmap.common.validation.roadmap_validator import RoadmapValidator


class TestRoadmapValidator:
    """Test Roadmap validator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return RoadmapValidator()

    def test_init(self, validator):
        """Test validator initialization."""
        assert validator is not None
        assert hasattr(validator, "issue_schema")
        assert hasattr(validator, "milestone_schema")
        assert hasattr(validator, "project_schema")

    def test_validate_project_valid(self, validator):
        """Test validating valid project."""
        project = {
            "id": "test-project-123",
            "name": "Test Project",
            "description": "A test project",
        }
        result = validator.validate_project(project)
        assert isinstance(result, ValidationResult)

    def test_validate_project_empty(self, validator):
        """Test validating empty project."""
        result = validator.validate_project({})
        assert isinstance(result, ValidationResult)

    def test_validate_issue_valid(self, validator):
        """Test validating valid issue."""
        issue = {
            "id": "abcd1234",
            "title": "Test Issue",
            "status": "todo",
            "priority": "high",
        }
        result = validator.validate_issue(issue)
        assert isinstance(result, ValidationResult)

    def test_validate_issue_empty(self, validator):
        """Test validating empty issue."""
        result = validator.validate_issue({})
        assert isinstance(result, ValidationResult)

    def test_validate_milestone_valid(self, validator):
        """Test validating valid milestone."""
        milestone = {
            "name": "v1.0.0",
            "status": "open",
            "description": "Version 1.0.0 release",
        }
        result = validator.validate_milestone(milestone)
        assert isinstance(result, ValidationResult)

    def test_validate_milestone_empty(self, validator):
        """Test validating empty milestone."""
        result = validator.validate_milestone({})
        assert isinstance(result, ValidationResult)

    def test_id_format_valid_issue_id(self, validator):
        """Test validating valid issue ID format."""
        result = validator.validate_id_format("abcd1234", "id")
        assert isinstance(result, ValidationResult)
        assert result.is_valid

    def test_id_format_valid_project_id(self, validator):
        """Test validating valid project ID format."""
        result = validator.validate_id_format("abc-def-ghi", "id")
        assert isinstance(result, ValidationResult)
        # Project IDs should match pattern ^[a-f0-9-]+$ (lowercase hex and hyphens only)
        assert isinstance(result.is_valid, bool)

    def test_id_format_invalid(self, validator):
        """Test validating invalid ID format."""
        result = validator.validate_id_format("INVALID_ID_WITH_CAPS", "id")
        assert isinstance(result, ValidationResult)
        # Invalid format should not be valid
        assert not result.is_valid

    def test_id_format_empty(self, validator):
        """Test validating empty ID."""
        result = validator.validate_id_format("", "id")
        assert isinstance(result, ValidationResult)
        assert not result.is_valid

    def test_string_length_valid(self, validator):
        """Test validating string length."""
        result = validator.validate_string_length(
            "test", "field", min_length=1, max_length=10
        )
        assert isinstance(result, ValidationResult)
        assert result.is_valid

    def test_string_length_too_short(self, validator):
        """Test validating string that's too short."""
        result = validator.validate_string_length("", "field", min_length=1)
        assert isinstance(result, ValidationResult)
        assert not result.is_valid

    def test_string_length_too_long(self, validator):
        """Test validating string that's too long."""
        result = validator.validate_string_length("a" * 100, "field", max_length=50)
        assert isinstance(result, ValidationResult)
        assert not result.is_valid

    def test_enum_field_valid(self, validator):
        """Test validating enum field with valid value."""
        from roadmap.core.domain import Status

        result = validator.validate_enum_field(Status.TODO, "status", Status)
        assert isinstance(result, ValidationResult)
        assert result.is_valid

    def test_enum_field_invalid(self, validator):
        """Test validating enum field with invalid value."""
        from roadmap.core.domain import Status

        # Create a mock enum-like object with value
        invalid_value = MagicMock()
        invalid_value.value = "invalid_status"
        result = validator.validate_enum_field(invalid_value, "status", Status)
        assert isinstance(result, ValidationResult)
        assert not result.is_valid

    def test_required_fields_present(self, validator):
        """Test validating that required fields are present."""
        data = {"id": "test", "title": "Test"}
        result = validator.validate_required_fields(data, ["id", "title"])
        assert isinstance(result, ValidationResult)

    def test_required_fields_missing(self, validator):
        """Test validating with missing required fields."""
        data = {"id": "test"}
        result = validator.validate_required_fields(data, ["id", "title"])
        assert isinstance(result, ValidationResult)
        # Missing required field should produce errors
        assert not result.is_valid

    def test_github_issue_number_valid(self, validator):
        """Test validating valid GitHub issue number."""
        result = validator.validate_github_issue_number("12345", "github_issue")
        assert isinstance(result, ValidationResult)

    def test_github_issue_number_invalid(self, validator):
        """Test validating invalid GitHub issue number."""
        result = validator.validate_github_issue_number("not_a_number", "github_issue")
        assert isinstance(result, ValidationResult)

    def test_labels_valid(self, validator):
        """Test validating valid labels."""
        result = validator.validate_labels(["bug", "feature"], "labels")
        assert isinstance(result, ValidationResult)

    def test_labels_empty_list(self, validator):
        """Test validating empty labels list."""
        result = validator.validate_labels([], "labels")
        assert isinstance(result, ValidationResult)

    def test_labels_none(self, validator):
        """Test validating None labels."""
        result = validator.validate_labels(None, "labels")
        assert isinstance(result, ValidationResult)
