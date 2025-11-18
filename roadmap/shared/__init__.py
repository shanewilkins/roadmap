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
from .errors import (
    ConfigurationError,
    ErrorCategory,
    ErrorSeverity,
    FileOperationError,
    GitOperationError,
    NetworkError,
    RoadmapError,
    ValidationError,
)
from .constants import (
    IssueType,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    RiskLevel,
    Status,
    # Configuration defaults
    AUTH_TOKEN_ENV_VAR,
    AUTH_TIMEOUT,
    ANALYSIS_MAX_HISTORICAL_DAYS,
    ANALYSIS_MIN_SAMPLE_SIZE,
    ANALYSIS_TREND_WINDOW,
    CACHE_TTL_DEFAULT,
    CACHE_TTL_LONG,
    CACHE_TTL_SHORT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CONFIG_FILE,
    DEFAULT_DATA_DIR,
    DEFAULT_CACHE_FILE,
    DEFAULT_DATE_FORMAT,
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_MAX_ITEMS_DISPLAY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_ROADMAP_FILE,
    DEFAULT_TABLE_WIDTH,
    ERROR_MESSAGE_MAX_LENGTH,
    GIT_COMMIT_MESSAGE_MAX_LENGTH,
    GIT_MAX_OUTPUT_LINES,
    GIT_TIMEOUT,
    GITHUB_API_BASE,
    GITHUB_API_TIMEOUT,
    GITHUB_GRAPHQL_ENDPOINT,
    GITHUB_RATE_LIMIT_THRESHOLD,
    LOG_FORMAT_DEFAULT,
    LOG_LEVEL_DEFAULT,
    PERFORMANCE_CONNECTION_POOL_SIZE,
    PERFORMANCE_ENABLE_ASYNC,
    PERFORMANCE_ENABLE_CACHE,
    PERFORMANCE_THREAD_POOL_SIZE,
    PROGRESS_BAR_LENGTH,
    PROGRESS_REFRESH_INTERVAL,
    VALIDATION_ERROR_MAX_FIELDS,
    VALIDATION_NAME_PATTERN,
    VALIDATION_TITLE_MAX_LENGTH,
    VALIDATION_TITLE_MIN_LENGTH,
    DEFAULT_BACKOFF_FACTOR,
)
from . import formatters

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
    # Errors
    "RoadmapError",
    "FileOperationError",
    "ValidationError",
    "NetworkError",
    "GitOperationError",
    "ConfigurationError",
    "ErrorSeverity",
    "ErrorCategory",
    # Constants and enums
    "Priority",
    "Status",
    "MilestoneStatus",
    "ProjectStatus",
    "RiskLevel",
    "IssueType",
    # Configuration defaults
    "DEFAULT_ROADMAP_FILE",
    "DEFAULT_CONFIG_FILE",
    "DEFAULT_DATA_DIR",
    "DEFAULT_CACHE_FILE",
    "GITHUB_API_BASE",
    "GITHUB_GRAPHQL_ENDPOINT",
    "GITHUB_API_TIMEOUT",
    "GITHUB_RATE_LIMIT_THRESHOLD",
    "DEFAULT_TABLE_WIDTH",
    "DEFAULT_MAX_ITEMS_DISPLAY",
    "DEFAULT_DATE_FORMAT",
    "DEFAULT_DATETIME_FORMAT",
    "CACHE_TTL_DEFAULT",
    "CACHE_TTL_LONG",
    "CACHE_TTL_SHORT",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_BACKOFF_FACTOR",
    "PROGRESS_REFRESH_INTERVAL",
    "PROGRESS_BAR_LENGTH",
    "LOG_LEVEL_DEFAULT",
    "LOG_FORMAT_DEFAULT",
    "ERROR_MESSAGE_MAX_LENGTH",
    "VALIDATION_ERROR_MAX_FIELDS",
    "AUTH_TOKEN_ENV_VAR",
    "AUTH_TIMEOUT",
    "GIT_TIMEOUT",
    "GIT_MAX_OUTPUT_LINES",
    "GIT_COMMIT_MESSAGE_MAX_LENGTH",
    "ANALYSIS_MIN_SAMPLE_SIZE",
    "ANALYSIS_MAX_HISTORICAL_DAYS",
    "ANALYSIS_TREND_WINDOW",
    "PERFORMANCE_ENABLE_CACHE",
    "PERFORMANCE_ENABLE_ASYNC",
    "PERFORMANCE_THREAD_POOL_SIZE",
    "PERFORMANCE_CONNECTION_POOL_SIZE",
    "VALIDATION_TITLE_MIN_LENGTH",
    "VALIDATION_TITLE_MAX_LENGTH",
    "VALIDATION_DESCRIPTION_MAX_LENGTH",
    "VALIDATION_NAME_PATTERN",
    # Formatters module
    "formatters",
]
