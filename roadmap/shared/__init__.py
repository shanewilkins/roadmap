"""
Shared Layer - Common Utilities & Patterns

This layer contains utilities and patterns used across all layers.
Common code that would otherwise be duplicated.

Modules:
- datetime_parser.py: Universal datetime parsing
- timezone_utils.py: Timezone-aware datetime handling
- validation.py: Data validation rules and validators
- logging.py: Structured logging configuration
- progress.py: Progress calculation engine
- formatters.py: Output formatting utilities
- errors.py: Exception definitions
- constants.py: Application constants and enums
- utils.py: Miscellaneous utilities

Guidelines:
- No layer-specific logic
- Shared by all other layers
- Pure functions or simple utilities
- No external dependencies
- Focused on one concern per module
"""

from .datetime_parser import (
    UnifiedDateTimeParser,
    parse_datetime,
    parse_file_datetime,
    parse_github_datetime,
    parse_user_datetime,
)
from .logging import (
    configure_for_testing,
    get_logger,
    get_security_logger,
    setup_logging,
)
from .progress import ProgressCalculationEngine, ProgressEventSystem
from .timezone_utils import (
    TimezoneManager,
    ensure_timezone_aware,
    format_datetime,
    format_relative_time,
    get_timezone_manager,
    migrate_naive_datetime,
    now_local,
    now_utc,
)
from .validation import (
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
    # DateTime parsing
    "UnifiedDateTimeParser",
    "parse_datetime",
    "parse_file_datetime",
    "parse_github_datetime",
    "parse_user_datetime",
    # Timezone utilities
    "TimezoneManager",
    "get_timezone_manager",
    "now_utc",
    "now_local",
    "ensure_timezone_aware",
    "migrate_naive_datetime",
    "format_datetime",
    "format_relative_time",
    # Validation
    "ValidationType",
    "ValidationResult",
    "FieldValidator",
    "SchemaValidator",
    "RoadmapValidator",
    "default_validator",
    "validate_and_raise",
    "validate_frontmatter_structure",
    # Logging
    "setup_logging",
    "get_logger",
    "get_security_logger",
    "configure_for_testing",
    # Progress
    "ProgressCalculationEngine",
    "ProgressEventSystem",
]
