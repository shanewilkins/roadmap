"""Application-wide constants and enums."""

from enum import Enum


class Priority(str, Enum):
    """Issue priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(str, Enum):
    """Issue status values."""

    TODO = "todo"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "closed"


class MilestoneStatus(str, Enum):
    """Milestone status values."""

    OPEN = "open"
    CLOSED = "closed"


class ProjectStatus(str, Enum):
    """Project status values."""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on-hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    """Risk level values for projects and milestones."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IssueType(str, Enum):
    """Issue type categories."""

    FEATURE = "feature"
    BUG = "bug"
    OTHER = "other"


# Application Configuration Defaults
# ============================================================================

# File and path defaults
DEFAULT_ROADMAP_FILE = "ROADMAP.md"
DEFAULT_CONFIG_FILE = ".roadmaprc"
DEFAULT_DATA_DIR = ".roadmap"
DEFAULT_CACHE_FILE = ".roadmap_cache.json"

# GitHub API defaults
GITHUB_API_BASE = "https://api.github.com"
GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
GITHUB_API_TIMEOUT = 30  # seconds
GITHUB_RATE_LIMIT_THRESHOLD = 10  # remaining requests before warning

# Display defaults
DEFAULT_TABLE_WIDTH = 80
DEFAULT_MAX_ITEMS_DISPLAY = 20
DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Caching defaults
CACHE_TTL_DEFAULT = 3600  # 1 hour in seconds
CACHE_TTL_LONG = 86400  # 24 hours in seconds
CACHE_TTL_SHORT = 300  # 5 minutes in seconds

# Batch operation defaults
DEFAULT_BATCH_SIZE = 50
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1  # seconds
DEFAULT_BACKOFF_FACTOR = 2

# Progress tracking defaults
PROGRESS_REFRESH_INTERVAL = 0.1  # seconds
PROGRESS_BAR_LENGTH = 30

# Logging defaults
LOG_LEVEL_DEFAULT = "INFO"
LOG_FORMAT_DEFAULT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Error handling defaults
ERROR_MESSAGE_MAX_LENGTH = 500
VALIDATION_ERROR_MAX_FIELDS = 10

# Authentication defaults
AUTH_TOKEN_ENV_VAR = "GITHUB_TOKEN"
AUTH_TIMEOUT = 30  # seconds

# Git defaults
GIT_TIMEOUT = 60  # seconds
GIT_MAX_OUTPUT_LINES = 1000
GIT_COMMIT_MESSAGE_MAX_LENGTH = 72

# Project analysis defaults
ANALYSIS_MIN_SAMPLE_SIZE = 5
ANALYSIS_MAX_HISTORICAL_DAYS = 365
ANALYSIS_TREND_WINDOW = 7  # days

# Performance defaults
PERFORMANCE_ENABLE_CACHE = True
PERFORMANCE_ENABLE_ASYNC = True
PERFORMANCE_THREAD_POOL_SIZE = 4
PERFORMANCE_CONNECTION_POOL_SIZE = 10

# Validation defaults
VALIDATION_TITLE_MIN_LENGTH = 1
VALIDATION_TITLE_MAX_LENGTH = 500
VALIDATION_DESCRIPTION_MAX_LENGTH = 5000
VALIDATION_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"
