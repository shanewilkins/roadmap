"""Validation Framework - Backward Compatibility Facade

DEPRECATED: This module is maintained for backward compatibility.
Use roadmap.common.validation package instead.

New structure:
- roadmap.common.validation.result - ValidationResult class
- roadmap.common.validation.field_validator - FieldValidator class
- roadmap.common.validation.schema_validator - SchemaValidator class
- roadmap.common.validation.roadmap_validator - RoadmapValidator class
- roadmap.common.validation.validators - utility functions and enums
"""

from roadmap.common.validation import (
    FieldValidator,
    RoadmapValidator,
    SchemaValidator,
    ValidationResult,
    ValidationType,
    default_validator,
    validate_and_raise,
    validate_frontmatter_structure,
)

__all__ = [
    "ValidationType",
    "ValidationResult",
    "FieldValidator",
    "SchemaValidator",
    "RoadmapValidator",
    "validate_and_raise",
    "validate_frontmatter_structure",
    "default_validator",
]
