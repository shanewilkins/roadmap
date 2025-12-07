"""Validation utility functions and helpers."""

from enum import Enum
from typing import Any

from roadmap.common.errors import ErrorSeverity, ValidationError

from .result import ValidationResult


class ValidationType(Enum):
    """Types of validation checks."""

    REQUIRED = "required"
    FORMAT = "format"
    RANGE = "range"
    ENUM = "enum"
    LENGTH = "length"
    PATTERN = "pattern"
    CUSTOM = "custom"


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
    from .roadmap_validator import RoadmapValidator

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
