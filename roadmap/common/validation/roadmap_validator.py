"""Main roadmap entity validators."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.common.constants import IssueType, MilestoneStatus, Priority, Status

from .field_validator import FieldValidator
from .result import ValidationResult
from .schema_validator import SchemaValidator


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
                from roadmap.common.datetime_parser import parse_datetime

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
