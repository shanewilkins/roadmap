"""Unified Validation Framework for Roadmap CLI

This module provides centralized validation utilities, field validators, and consistent
validation error handling to eliminate duplicate validation patterns across the codebase.

Key Features:
- Centralized field validation for common data types
- Reusable validation patterns for issues, milestones, and projects
- Consistent validation error reporting
- Extensible validation framework for custom validators
- Integration with error handling framework
"""

from roadmap.common.validation.field_validator import FieldValidator
from roadmap.common.validation.result import ValidationResult
from roadmap.common.validation.roadmap_validator import RoadmapValidator
from roadmap.common.validation.schema_validator import SchemaValidator
from roadmap.common.validation.validators import (
    ValidationType,
    validate_and_raise,
    validate_frontmatter_structure,
)

__all__ = [
    "ValidationResult",
    "FieldValidator",
    "SchemaValidator",
    "RoadmapValidator",
    "ValidationType",
    "validate_and_raise",
    "validate_frontmatter_structure",
    # Global instance for backward compatibility
    "default_validator",
]

# Global validator instance
default_validator = RoadmapValidator()
