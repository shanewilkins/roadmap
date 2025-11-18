"""
Unified Validation Framework for Roadmap CLI

DEPRECATED: This module is maintained for backward compatibility.
New code should import from roadmap.shared.validation instead:

- ValidationType -> roadmap.shared.validation.ValidationType
- ValidationResult -> roadmap.shared.validation.ValidationResult
- FieldValidator -> roadmap.shared.validation.FieldValidator
- SchemaValidator -> roadmap.shared.validation.SchemaValidator
- RoadmapValidator -> roadmap.shared.validation.RoadmapValidator
- validate_and_raise() -> roadmap.shared.validation.validate_and_raise()
- default_validator -> roadmap.shared.validation.default_validator

This module will be removed in v2.0.
See: roadmap/shared/validation.py for the new location.

This module provides centralized validation utilities, field validators, and consistent
validation error handling to eliminate duplicate validation patterns across the codebase.

Key Features:
- Centralized field validation for common data types
- Reusable validation patterns for issues, milestones, and projects
- Consistent validation error reporting
- Extensible validation framework for custom validators
- Integration with error handling framework
"""

import re
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .error_handling import ErrorSeverity, ValidationError
from .models import IssueType, MilestoneStatus, Priority, Status


class ValidationType(Enum):
    """Types of validation checks."""

    REQUIRED = "required"
    FORMAT = "format"
    RANGE = "range"
    ENUM = "enum"
    LENGTH = "length"
    PATTERN = "pattern"
    CUSTOM = "custom"


class ValidationResult:
    """Result of a validation operation."""

    def __init__(
        self,
        is_valid: bool = True,
        errors: list[str] | None = None,
        field: str | None = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.field = field

    def add_error(self, error: str):
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one."""
        if not other.is_valid:
            self.is_valid = False
            self.errors.extend(other.errors)

    def __bool__(self) -> bool:
        return self.is_valid


class FieldValidator:
    """Individual field validator with configurable rules."""

    def __init__(
        self,
        field_name: str,
        required: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        enum_values: list[Any] | None = None,
        custom_validator: Callable[[Any], tuple[bool, str]] | None = None,
        allow_none: bool | None = None,
    ):
        self.field_name = field_name
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.enum_values = enum_values
        self.custom_validator = custom_validator
        # If allow_none is not specified, set it based on required status
        self.allow_none = allow_none if allow_none is not None else not required

    def validate(self, value: Any) -> ValidationResult:
        """Validate a field value."""
        result = ValidationResult(field=self.field_name)

        # Check if value is None
        if value is None:
            if self.required and not self.allow_none:
                result.add_error(f"Field '{self.field_name}' is required")
            return result

        # Check required field
        if self.required and (
            value == "" or (isinstance(value, list | dict) and len(value) == 0)
        ):
            result.add_error(f"Field '{self.field_name}' is required")
            return result

        # Skip other validations if value is None and None is allowed
        if value is None and self.allow_none:
            return result

        # Convert to string for pattern and length checks
        str_value = str(value) if value is not None else ""

        # Check length constraints
        if self.min_length is not None and len(str_value) < self.min_length:
            result.add_error(
                f"Field '{self.field_name}' must be at least {self.min_length} characters"
            )

        if self.max_length is not None and len(str_value) > self.max_length:
            result.add_error(
                f"Field '{self.field_name}' must be no more than {self.max_length} characters"
            )

        # Check pattern
        if self.pattern and not self.pattern.match(str_value):
            result.add_error(
                f"Field '{self.field_name}' does not match required format"
            )

        # Check enum values
        if self.enum_values is not None:
            if hasattr(value, "value"):  # Handle enum objects
                check_value = value.value
            else:
                check_value = value

            if check_value not in self.enum_values:
                result.add_error(
                    f"Field '{self.field_name}' must be one of: {', '.join(map(str, self.enum_values))}"
                )

        # Run custom validator
        if self.custom_validator:
            is_valid, error_msg = self.custom_validator(value)
            if not is_valid:
                result.add_error(f"Field '{self.field_name}': {error_msg}")

        return result


class SchemaValidator:
    """Schema-based validator for complex data structures."""

    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        self.validators: dict[str, FieldValidator] = {}

    def add_field(self, validator: FieldValidator) -> "SchemaValidator":
        """Add a field validator to the schema."""
        self.validators[validator.field_name] = validator
        return self

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate data against the schema."""
        result = ValidationResult()

        # Validate each field
        for field_name, validator in self.validators.items():
            value = data.get(field_name)
            field_result = validator.validate(value)
            result.merge(field_result)

        return result


class RoadmapValidator:
    """Main validation class with predefined validators for roadmap entities."""

    def __init__(self):
        self._setup_predefined_validators()

    def _setup_predefined_validators(self):
        """Set up predefined validators for common roadmap entities."""

        # Issue validation schema
        self.issue_schema = SchemaValidator("issue")
        self.issue_schema.add_field(
            FieldValidator("id", required=True, pattern=r"^[a-f0-9]{8}$")
        ).add_field(
            FieldValidator("title", required=True, min_length=1, max_length=200)
        ).add_field(
            FieldValidator(
                "priority", required=True, enum_values=[p.value for p in Priority]
            )
        ).add_field(
            FieldValidator(
                "status", required=True, enum_values=[s.value for s in Status]
            )
        ).add_field(
            FieldValidator("issue_type", enum_values=[t.value for t in IssueType])
        ).add_field(
            FieldValidator(
                "assignee", max_length=100, custom_validator=self._validate_assignee
            )
        ).add_field(FieldValidator("milestone", max_length=100)).add_field(
            FieldValidator(
                "estimated_hours", custom_validator=self._validate_positive_number
            )
        ).add_field(
            FieldValidator(
                "progress_percentage", custom_validator=self._validate_percentage
            )
        )

        # Milestone validation schema
        self.milestone_schema = SchemaValidator("milestone")
        self.milestone_schema.add_field(
            FieldValidator("name", required=True, min_length=1, max_length=100)
        ).add_field(
            FieldValidator(
                "status", required=True, enum_values=[s.value for s in MilestoneStatus]
            )
        ).add_field(FieldValidator("description", max_length=1000)).add_field(
            FieldValidator("due_date", custom_validator=self._validate_datetime)
        )

        # Project validation schema
        self.project_schema = SchemaValidator("project")
        self.project_schema.add_field(
            FieldValidator("id", required=True, pattern=r"^[a-f0-9-]+$")
        ).add_field(
            FieldValidator("name", required=True, min_length=1, max_length=200)
        ).add_field(FieldValidator("description", max_length=2000)).add_field(
            FieldValidator("owner", max_length=100)
        ).add_field(
            FieldValidator(
                "estimated_hours", custom_validator=self._validate_positive_number
            )
        )

    def _validate_assignee(self, value: Any) -> tuple[bool, str]:
        """Validate assignee format."""
        if value is None:
            return True, ""

        str_value = str(value)
        if not str_value:
            return True, ""

        # Basic username format validation
        if not re.match(r"^[a-zA-Z0-9_-]+$", str_value):
            return (
                False,
                "must contain only alphanumeric characters, hyphens, and underscores",
            )

        if len(str_value) > 39:  # GitHub username limit
            return False, "must be 39 characters or less"

        return True, ""

    def _validate_positive_number(self, value: Any) -> tuple[bool, str]:
        """Validate that a number is positive."""
        if value is None:
            return True, ""

        try:
            num_value = float(value)
            if num_value < 0:
                return False, "must be a positive number"
            return True, ""
        except (ValueError, TypeError):
            return False, "must be a valid number"

    def _validate_percentage(self, value: Any) -> tuple[bool, str]:
        """Validate percentage value (0-100)."""
        if value is None:
            return True, ""

        try:
            num_value = float(value)
            if not 0 <= num_value <= 100:
                return False, "must be between 0 and 100"
            return True, ""
        except (ValueError, TypeError):
            return False, "must be a valid number"

    def _validate_datetime(self, value: Any) -> tuple[bool, str]:
        """Validate datetime format."""
        if value is None:
            return True, ""

        if isinstance(value, datetime):
            return True, ""

        # Try to parse string as datetime
        if isinstance(value, str):
            try:
                from .datetime_parser import parse_datetime

                parse_datetime(value, "flexible")
                return True, ""
            except Exception:
                return False, "must be a valid datetime format"

        return False, "must be a datetime or valid datetime string"

    def validate_issue(self, issue_data: dict[str, Any]) -> ValidationResult:
        """Validate issue data."""
        return self.issue_schema.validate(issue_data)

    def validate_milestone(self, milestone_data: dict[str, Any]) -> ValidationResult:
        """Validate milestone data."""
        return self.milestone_schema.validate(milestone_data)

    def validate_project(self, project_data: dict[str, Any]) -> ValidationResult:
        """Validate project data."""
        return self.project_schema.validate(project_data)

    def validate_required_fields(
        self, data: dict[str, Any], required_fields: list[str]
    ) -> ValidationResult:
        """Validate that required fields are present."""
        result = ValidationResult()
        missing_fields = []

        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)

        if missing_fields:
            result.add_error(f"Missing required fields: {', '.join(missing_fields)}")

        return result

    def validate_enum_field(
        self, value: Any, field_name: str, enum_class: Any
    ) -> ValidationResult:
        """Validate an enum field."""
        result = ValidationResult(field=field_name)

        if value is None:
            return result

        valid_values = [e.value for e in enum_class]
        check_value = value.value if hasattr(value, "value") else value

        if check_value not in valid_values:
            result.add_error(
                f"Invalid {field_name}: {check_value}. Valid values: {', '.join(valid_values)}"
            )

        return result

    def validate_string_length(
        self,
        value: str,
        field_name: str,
        min_length: int = 0,
        max_length: int | None = None,
    ) -> ValidationResult:
        """Validate string length constraints."""
        result = ValidationResult(field=field_name)

        if value is None:
            return result

        if len(value) < min_length:
            result.add_error(f"{field_name} must be at least {min_length} characters")

        if max_length and len(value) > max_length:
            result.add_error(
                f"{field_name} must be no more than {max_length} characters"
            )

        return result

    def validate_id_format(
        self, id_value: str, field_name: str = "id"
    ) -> ValidationResult:
        """Validate ID format (8-character hex for issues, UUID-like for projects)."""
        result = ValidationResult(field=field_name)

        if not id_value:
            result.add_error(f"{field_name} is required")
            return result

        # For issue IDs (8-character hex)
        if len(id_value) == 8 and re.match(r"^[a-f0-9]{8}$", id_value):
            return result

        # For project IDs (UUID-like format)
        if re.match(r"^[a-f0-9-]+$", id_value):
            return result

        result.add_error(f"{field_name} must be a valid ID format")
        return result

    def validate_path(
        self, path_value: str | Path, field_name: str = "path"
    ) -> ValidationResult:
        """Validate file path."""
        result = ValidationResult(field=field_name)

        if path_value is None:
            return result

        try:
            path = Path(path_value)

            # Check for path traversal attempts
            if ".." in str(path):
                result.add_error(f"{field_name} cannot contain '..' (path traversal)")

            # Check for absolute paths when relative expected
            if path.is_absolute() and field_name in ["filename", "relative_path"]:
                result.add_error(f"{field_name} should be a relative path")

        except Exception as e:
            result.add_error(f"Invalid {field_name}: {str(e)}")

        return result

    def validate_github_issue_number(
        self, issue_number: Any, field_name: str = "github_issue"
    ) -> ValidationResult:
        """Validate GitHub issue number."""
        result = ValidationResult(field=field_name)

        if issue_number is None:
            return result

        try:
            num = int(issue_number)
            if num <= 0:
                result.add_error(f"{field_name} must be a positive integer")
        except (ValueError, TypeError):
            result.add_error(f"{field_name} must be a valid integer")

        return result

    def validate_labels(
        self, labels: Any, field_name: str = "labels"
    ) -> ValidationResult:
        """Validate labels list."""
        result = ValidationResult(field=field_name)

        if labels is None:
            return result

        if not isinstance(labels, list):
            result.add_error(f"{field_name} must be a list")
            return result

        for i, label in enumerate(labels):
            if not isinstance(label, str):
                result.add_error(f"{field_name}[{i}] must be a string")
            elif len(label) > 50:
                result.add_error(f"{field_name}[{i}] must be 50 characters or less")
            elif not label.strip():
                result.add_error(f"{field_name}[{i}] cannot be empty")

        return result


# Utility functions for common validation patterns
def validate_and_raise(validation_result: ValidationResult, context: str | None = None):
    """Validate result and raise ValidationError if invalid."""
    if not validation_result.is_valid:
        error_message = "; ".join(validation_result.errors)
        if context:
            error_message = f"{context}: {error_message}"

        raise ValidationError(
            error_message, field=validation_result.field, severity=ErrorSeverity.MEDIUM
        )


def validate_frontmatter_structure(
    frontmatter: dict[str, Any], expected_type: str
) -> tuple[bool, list[str]]:
    """Validate frontmatter structure for backward compatibility."""
    validator = RoadmapValidator()

    if expected_type == "issue":
        result = validator.validate_issue(frontmatter)
    elif expected_type == "milestone":
        result = validator.validate_milestone(frontmatter)
    elif expected_type == "project":
        result = validator.validate_project(frontmatter)
    else:
        return False, [f"Unknown type: {expected_type}"]

    return result.is_valid, result.errors


# Global validator instance
default_validator = RoadmapValidator()
