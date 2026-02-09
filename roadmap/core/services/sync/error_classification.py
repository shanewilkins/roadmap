"""Error classification system for sync operations.

This module provides categorization and aggregation of sync errors
to present clear, actionable error summaries to users.
"""

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class ErrorCategory(str, Enum):
    """Categories of sync errors for classification and reporting."""

    # Dependency/relationship errors
    MILESTONE_NOT_FOUND = "milestone_not_found"
    PROJECT_NOT_FOUND = "project_not_found"
    DEPENDENCY_MISSING = "dependency_missing"
    FOREIGN_KEY_CONSTRAINT = "foreign_key_constraint"

    # API/network errors
    API_RATE_LIMIT = "api_rate_limit"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Authentication/authorization errors
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    TOKEN_EXPIRED = "token_expired"

    # Data/validation errors
    INVALID_DATA = "invalid_data"
    SCHEMA_MISMATCH = "schema_mismatch"
    DUPLICATE_ENTITY = "duplicate_entity"

    # Resource errors
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_NOT_FOUND = "resource_not_found"

    # System errors
    DATABASE_ERROR = "database_error"
    FILE_SYSTEM_ERROR = "file_system_error"

    # Unknown/other
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorDetails:
    """Detailed information about a specific error occurrence."""

    category: ErrorCategory
    error_message: str
    error_type: str
    entity_type: str  # "Issue", "Milestone", "Project"
    entity_id: str | None = None
    suggested_fix: str | None = None
    is_recoverable: bool = True
    metadata: dict[str, Any] | None = None


@dataclass
class ErrorSummary:
    """Aggregated summary of errors by category."""

    category: ErrorCategory
    count: int
    sample_messages: list[str]  # Top 3-5 unique error messages
    affected_entities: list[str]  # Sample of affected entity IDs
    suggested_fix: str
    is_recoverable: bool


class ErrorClassifier:
    """Classifies and aggregates sync errors for user presentation."""

    def __init__(self):
        """Initialize error classifier with empty state."""
        self._errors: list[ErrorDetails] = []
        self._category_counts: dict[ErrorCategory, int] = defaultdict(int)

    def classify_error(
        self,
        error_message: str,
        error_type: str,
        entity_type: str,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ErrorDetails:
        """Classify an error and determine its category.

        Args:
            error_message: The error message text
            error_type: The exception type (e.g., "IntegrityError", "ValueError")
            entity_type: Type of entity affected (Issue, Milestone, Project)
            entity_id: Identifier of affected entity
            metadata: Additional context about the error

        Returns:
            ErrorDetails with classified category and suggested fix
        """
        category = self._determine_category(error_message, error_type, metadata)
        suggested_fix = self._get_suggested_fix(category, error_message)
        is_recoverable = self._is_recoverable(category)

        error_details = ErrorDetails(
            category=category,
            error_message=error_message,
            error_type=error_type,
            entity_type=entity_type,
            entity_id=entity_id,
            suggested_fix=suggested_fix,
            is_recoverable=is_recoverable,
            metadata=metadata,
        )

        self._errors.append(error_details)
        self._category_counts[category] += 1

        return error_details

    def _determine_category(
        self, error_message: str, error_type: str, metadata: dict[str, Any] | None
    ) -> ErrorCategory:
        """Determine error category from message and type.

        Args:
            error_message: Error message text
            error_type: Exception type name
            metadata: Additional context

        Returns:
            Appropriate ErrorCategory
        """
        msg_lower = error_message.lower()
        type_lower = error_type.lower()

        # Check categories in order of specificity
        category = (
            self._check_dependency_errors(msg_lower)
            or self._check_api_errors(msg_lower)
            or self._check_auth_errors(msg_lower)
            or self._check_data_errors(msg_lower, type_lower)
            or self._check_resource_errors(msg_lower)
            or self._check_file_system_errors(type_lower)
        )
        return category or ErrorCategory.UNKNOWN_ERROR

    def _check_dependency_errors(self, msg_lower: str) -> ErrorCategory | None:
        """Check for dependency-related errors."""
        if "foreign key constraint" in msg_lower:
            return ErrorCategory.FOREIGN_KEY_CONSTRAINT
        if "milestone not found" in msg_lower or "no such milestone" in msg_lower:
            return ErrorCategory.MILESTONE_NOT_FOUND
        if "project not found" in msg_lower or "no such project" in msg_lower:
            return ErrorCategory.PROJECT_NOT_FOUND
        if "dependency" in msg_lower and (
            "missing" in msg_lower or "not found" in msg_lower
        ):
            return ErrorCategory.DEPENDENCY_MISSING
        return None

    def _check_api_errors(self, msg_lower: str) -> ErrorCategory | None:
        """Check for API and network errors."""
        if "rate limit" in msg_lower or "429" in msg_lower:
            return ErrorCategory.API_RATE_LIMIT
        if any(x in msg_lower for x in ["connection", "network", "unreachable"]):
            return ErrorCategory.NETWORK_ERROR
        if "timeout" in msg_lower or "timed out" in msg_lower:
            return ErrorCategory.TIMEOUT
        if "503" in msg_lower or "service unavailable" in msg_lower:
            return ErrorCategory.SERVICE_UNAVAILABLE
        return None

    def _check_auth_errors(self, msg_lower: str) -> ErrorCategory | None:
        """Check for authentication and authorization errors."""
        if any(x in msg_lower for x in ["authentication", "unauthorized", "401"]):
            return ErrorCategory.AUTHENTICATION_FAILED
        if (
            "permission denied" in msg_lower
            or "forbidden" in msg_lower
            or "403" in msg_lower
        ):
            return ErrorCategory.PERMISSION_DENIED
        if "token expired" in msg_lower or "invalid token" in msg_lower:
            return ErrorCategory.TOKEN_EXPIRED
        return None

    def _check_data_errors(
        self, msg_lower: str, type_lower: str
    ) -> ErrorCategory | None:
        """Check for data integrity errors."""
        if "integrityerror" in type_lower or "constraint" in msg_lower:
            return ErrorCategory.DATABASE_ERROR
        if "validation" in msg_lower or "invalid" in msg_lower:
            return ErrorCategory.INVALID_DATA
        if "duplicate" in msg_lower:
            return ErrorCategory.DUPLICATE_ENTITY
        return None

    def _check_resource_errors(self, msg_lower: str) -> ErrorCategory | None:
        """Check for resource-related errors."""
        if "deleted" in msg_lower or "removed" in msg_lower:
            return ErrorCategory.RESOURCE_DELETED
        if "not found" in msg_lower or "404" in msg_lower:
            return ErrorCategory.RESOURCE_NOT_FOUND
        return None

    def _check_file_system_errors(self, type_lower: str) -> ErrorCategory | None:
        """Check for file system errors."""
        if any(x in type_lower for x in ["oserror", "ioerror", "filenotfound"]):
            return ErrorCategory.FILE_SYSTEM_ERROR
        return None

    def _get_suggested_fix(self, category: ErrorCategory, error_message: str) -> str:
        """Get actionable suggestion for fixing error category.

        Args:
            category: Error category
            error_message: Original error message

        Returns:
            Human-readable suggestion
        """
        suggestions = {
            ErrorCategory.MILESTONE_NOT_FOUND: "Run 'roadmap sync' again to pull missing milestones, or manually create the milestone locally",
            ErrorCategory.PROJECT_NOT_FOUND: "Ensure projects are synced before issues. Check GitHub project configuration",
            ErrorCategory.DEPENDENCY_MISSING: "Sync dependent entities first (projects → milestones → issues)",
            ErrorCategory.FOREIGN_KEY_CONSTRAINT: "Run 'roadmap health' to check database integrity. May need to reinitialize database",
            ErrorCategory.API_RATE_LIMIT: "Wait for rate limit to reset (usually 1 hour), or use authenticated requests",
            ErrorCategory.NETWORK_ERROR: "Check internet connection and GitHub service status at https://githubstatus.com",
            ErrorCategory.TIMEOUT: "Retry the operation. Consider syncing in smaller batches",
            ErrorCategory.SERVICE_UNAVAILABLE: "GitHub is experiencing issues. Check https://githubstatus.com and retry later",
            ErrorCategory.AUTHENTICATION_FAILED: "Run 'roadmap git setup --auth' to reconfigure GitHub token",
            ErrorCategory.PERMISSION_DENIED: "Verify GitHub token has required permissions (repo, read:org, read:user)",
            ErrorCategory.TOKEN_EXPIRED: "Generate new GitHub token and update with 'roadmap git setup --auth'",
            ErrorCategory.INVALID_DATA: "Check data format. May need to update roadmap CLI to latest version",
            ErrorCategory.SCHEMA_MISMATCH: "Run 'roadmap health fix --fix-type data_integrity' to repair schema issues",
            ErrorCategory.DUPLICATE_ENTITY: "Run 'roadmap health fix --fix-type duplicate_issues' to resolve duplicates",
            ErrorCategory.RESOURCE_DELETED: "Entity was deleted on remote. This is expected and safe to ignore",
            ErrorCategory.RESOURCE_NOT_FOUND: "Entity may have been renamed or deleted. Check GitHub repository",
            ErrorCategory.DATABASE_ERROR: "Run 'roadmap health' and 'roadmap health fix' to repair database",
            ErrorCategory.FILE_SYSTEM_ERROR: "Check file permissions and available disk space",
            ErrorCategory.UNKNOWN_ERROR: "Run with --verbose for more details. Consider reporting as a bug",
        }
        return suggestions.get(category, "Check logs for more details")

    def _is_recoverable(self, category: ErrorCategory) -> bool:
        """Determine if error category is typically recoverable.

        Args:
            category: Error category

        Returns:
            True if error can typically be recovered from
        """
        non_recoverable = {
            ErrorCategory.AUTHENTICATION_FAILED,
            ErrorCategory.TOKEN_EXPIRED,
            ErrorCategory.PERMISSION_DENIED,
            ErrorCategory.SCHEMA_MISMATCH,
        }
        return category not in non_recoverable

    def get_summary(self, max_samples: int = 5) -> list[ErrorSummary]:
        """Get aggregated error summary by category.

        Args:
            max_samples: Maximum number of sample messages/entities per category

        Returns:
            List of ErrorSummary objects, sorted by count (descending)
        """
        summaries = []

        for category, count in self._category_counts.items():
            # Get errors for this category
            category_errors = [e for e in self._errors if e.category == category]

            # Extract unique sample messages (top N)
            messages = list(dict.fromkeys([e.error_message for e in category_errors]))
            sample_messages = messages[:max_samples]

            # Extract sample affected entities
            entities = [e.entity_id for e in category_errors if e.entity_id]
            affected_entities = list(dict.fromkeys(entities))[:max_samples]

            # Get suggested fix (same for all in category)
            suggested_fix = (
                category_errors[0].suggested_fix
                if category_errors and category_errors[0].suggested_fix
                else "Check logs for more details"
            )

            # Check if recoverable (should be same for all)
            is_recoverable = (
                category_errors[0].is_recoverable if category_errors else True
            )

            summary = ErrorSummary(
                category=category,
                count=count,
                sample_messages=sample_messages,
                affected_entities=affected_entities,
                suggested_fix=suggested_fix,
                is_recoverable=is_recoverable,
            )
            summaries.append(summary)

        # Sort by count (most common errors first)
        summaries.sort(key=lambda s: s.count, reverse=True)
        return summaries

    def get_total_errors(self) -> int:
        """Get total number of errors classified."""
        return len(self._errors)

    def get_category_count(self, category: ErrorCategory) -> int:
        """Get count of errors in specific category."""
        return self._category_counts.get(category, 0)

    def clear(self):
        """Clear all collected errors."""
        self._errors.clear()
        self._category_counts.clear()

    def add_errors(self, errors: dict[str, str]) -> None:
        """Bulk add errors from a dictionary of issue_id -> error_message.

        Args:
            errors: Dictionary mapping issue IDs to error messages
        """
        for issue_id, error_msg in errors.items():
            self.classify_error(
                error_message=error_msg,
                error_type="SyncError",
                entity_type="Issue",
                entity_id=issue_id,
            )

    def get_summary_dict(self) -> dict[str, int]:
        """Get summary as a dictionary of category group -> count.

        Returns:
            Dict with keys like "dependency_errors", "api_errors", etc.
        """
        # Group categories into high-level groups
        category_groups = {
            "dependency_errors": [
                ErrorCategory.MILESTONE_NOT_FOUND,
                ErrorCategory.PROJECT_NOT_FOUND,
                ErrorCategory.DEPENDENCY_MISSING,
                ErrorCategory.FOREIGN_KEY_CONSTRAINT,
            ],
            "api_errors": [
                ErrorCategory.API_RATE_LIMIT,
                ErrorCategory.NETWORK_ERROR,
                ErrorCategory.TIMEOUT,
                ErrorCategory.SERVICE_UNAVAILABLE,
            ],
            "auth_errors": [
                ErrorCategory.AUTHENTICATION_FAILED,
                ErrorCategory.PERMISSION_DENIED,
                ErrorCategory.TOKEN_EXPIRED,
            ],
            "data_errors": [
                ErrorCategory.INVALID_DATA,
                ErrorCategory.SCHEMA_MISMATCH,
                ErrorCategory.DUPLICATE_ENTITY,
                ErrorCategory.DATABASE_ERROR,
            ],
            "resource_errors": [
                ErrorCategory.RESOURCE_DELETED,
                ErrorCategory.RESOURCE_NOT_FOUND,
            ],
            "file_system_errors": [
                ErrorCategory.FILE_SYSTEM_ERROR,
            ],
            "unknown_errors": [
                ErrorCategory.UNKNOWN_ERROR,
            ],
        }

        # Aggregate counts by group
        result = {}
        for group_name, categories in category_groups.items():
            total = sum(self._category_counts.get(cat, 0) for cat in categories)
            result[group_name] = total

        return result

    def get_recommendation(self, category_group: str) -> str:
        """Get recommendation for a category group.

        Args:
            category_group: High-level category group (e.g., "dependency_errors")

        Returns:
            Recommendation string
        """
        recommendations = {
            "dependency_errors": "Ensure all dependencies (milestones, projects) are synced first. Run 'roadmap sync' again.",
            "api_errors": "Check GitHub service status at https://githubstatus.com. Retry after a short wait.",
            "auth_errors": "Verify GitHub token with 'roadmap git setup --auth'. Ensure token has required permissions (repo, read:org).",
            "data_errors": "Run 'roadmap health' to check database integrity. May need to run 'roadmap health fix'.",
            "resource_errors": "These resources may have been deleted on GitHub. This is expected after cleanup.",
            "file_system_errors": "Check file permissions and disk space. Ensure .roadmap/ directory is writable.",
            "unknown_errors": "Run with --verbose for detailed error messages. Consider reporting as a bug if persistent.",
        }
        return recommendations.get(category_group, "Check logs for more details")

    def get_issues_by_category(self, category_group: str) -> list[str]:
        """Get list of issue IDs affected by a category group.

        Args:
            category_group: High-level category group (e.g., "dependency_errors")

        Returns:
            List of issue IDs
        """
        # Map group to categories
        category_groups = {
            "dependency_errors": [
                ErrorCategory.MILESTONE_NOT_FOUND,
                ErrorCategory.PROJECT_NOT_FOUND,
                ErrorCategory.DEPENDENCY_MISSING,
                ErrorCategory.FOREIGN_KEY_CONSTRAINT,
            ],
            "api_errors": [
                ErrorCategory.API_RATE_LIMIT,
                ErrorCategory.NETWORK_ERROR,
                ErrorCategory.TIMEOUT,
                ErrorCategory.SERVICE_UNAVAILABLE,
            ],
            "auth_errors": [
                ErrorCategory.AUTHENTICATION_FAILED,
                ErrorCategory.PERMISSION_DENIED,
                ErrorCategory.TOKEN_EXPIRED,
            ],
            "data_errors": [
                ErrorCategory.INVALID_DATA,
                ErrorCategory.SCHEMA_MISMATCH,
                ErrorCategory.DUPLICATE_ENTITY,
                ErrorCategory.DATABASE_ERROR,
            ],
            "resource_errors": [
                ErrorCategory.RESOURCE_DELETED,
                ErrorCategory.RESOURCE_NOT_FOUND,
            ],
            "file_system_errors": [
                ErrorCategory.FILE_SYSTEM_ERROR,
            ],
            "unknown_errors": [
                ErrorCategory.UNKNOWN_ERROR,
            ],
        }

        categories = category_groups.get(category_group, [])
        issue_ids = [
            e.entity_id
            for e in self._errors
            if e.category in categories and e.entity_id
        ]
        return issue_ids
