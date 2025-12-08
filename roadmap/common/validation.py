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

import warnings

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

# Emit deprecation warning when this module is imported
warnings.warn(
    "The 'roadmap.common.validation' module is deprecated. "
    "Use 'roadmap.common.validation' package directly instead. "
    "This module will be removed in v1.0.0.",
    DeprecationWarning,
    stacklevel=2,
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
