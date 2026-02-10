"""Error types for sync operations.

This module defines error types used with the Result pattern for sync operations,
enabling explicit error handling without exceptions.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SyncErrorType(StrEnum):
    """Types of errors that can occur during sync operations."""

    # Authentication errors
    AUTHENTICATION_FAILED = "authentication_failed"
    TOKEN_EXPIRED = "token_expired"
    PERMISSION_DENIED = "permission_denied"

    # Network errors
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"
    API_RATE_LIMIT = "api_rate_limit"

    # Data errors
    INVALID_DATA = "invalid_data"
    SCHEMA_MISMATCH = "schema_mismatch"
    DUPLICATE_ENTITY = "duplicate_entity"
    VALIDATION_ERROR = "validation_error"

    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_DELETED = "resource_deleted"
    MILESTONE_NOT_FOUND = "milestone_not_found"
    PROJECT_NOT_FOUND = "project_not_found"

    # Conflict errors
    CONFLICT = "conflict"
    MERGE_CONFLICT = "merge_conflict"

    # System errors
    DATABASE_ERROR = "database_error"
    FILE_SYSTEM_ERROR = "file_system_error"
    CONFIGURATION_ERROR = "configuration_error"

    # Circuit breaker errors
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    RETRY_EXHAUSTED = "retry_exhausted"

    # Unknown
    UNKNOWN_ERROR = "unknown_error"


@dataclass(frozen=True)
class SyncError:
    """Error information for sync operations.

    Provides structured error information for use with Result pattern,
    including error type, message, and recovery suggestions.

    Attributes:
        error_type: The category of error
        message: Human-readable error message
        entity_type: Type of entity affected (Issue, Milestone, Project, etc.)
        entity_id: Identifier of affected entity (optional)
        is_recoverable: Whether the error can be recovered from
        suggested_fix: User-actionable recovery suggestion (optional)
        metadata: Additional error context (optional)
        cause: Original exception if wrapped (optional)
    """

    error_type: SyncErrorType
    message: str
    entity_type: str = "Unknown"
    entity_id: str | None = None
    is_recoverable: bool = True
    suggested_fix: str | None = None
    metadata: dict[str, Any] | None = None
    cause: Exception | None = None

    def __str__(self) -> str:
        """Get string representation of error.

        Returns:
            Formatted error message
        """
        parts = [f"{self.error_type.value}: {self.message}"]
        if self.entity_id:
            parts.append(f"(entity: {self.entity_type} #{self.entity_id})")
        if self.suggested_fix:
            parts.append(f"Fix: {self.suggested_fix}")
        return " ".join(parts)

    def with_entity(
        self, entity_type: str, entity_id: str | None = None
    ) -> "SyncError":
        """Create a new error with entity information.

        Args:
            entity_type: Type of entity (Issue, Milestone, etc.)
            entity_id: Entity identifier

        Returns:
            New SyncError with entity information
        """
        return SyncError(
            error_type=self.error_type,
            message=self.message,
            entity_type=entity_type,
            entity_id=entity_id,
            is_recoverable=self.is_recoverable,
            suggested_fix=self.suggested_fix,
            metadata=self.metadata,
            cause=self.cause,
        )

    def with_suggestion(self, suggested_fix: str) -> "SyncError":
        """Create a new error with a recovery suggestion.

        Args:
            suggested_fix: User-actionable suggestion

        Returns:
            New SyncError with suggestion
        """
        return SyncError(
            error_type=self.error_type,
            message=self.message,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            is_recoverable=self.is_recoverable,
            suggested_fix=suggested_fix,
            metadata=self.metadata,
            cause=self.cause,
        )

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_type: SyncErrorType = SyncErrorType.UNKNOWN_ERROR,
        entity_type: str = "Unknown",
        entity_id: str | None = None,
    ) -> "SyncError":
        """Create SyncError from an exception.

        Args:
            exception: The exception to wrap
            error_type: Category of error (default: UNKNOWN_ERROR)
            entity_type: Type of affected entity
            entity_id: Identifier of affected entity

        Returns:
            SyncError wrapping the exception
        """
        # Infer error type from exception if possible
        inferred_type = cls._infer_error_type(exception)
        if inferred_type:
            error_type = inferred_type

        return cls(
            error_type=error_type,
            message=str(exception),
            entity_type=entity_type,
            entity_id=entity_id,
            is_recoverable=cls._is_recoverable(error_type),
            suggested_fix=cls._get_suggested_fix(error_type),
            cause=exception,
        )

    @staticmethod
    def _infer_error_type(exception: Exception) -> SyncErrorType | None:
        """Infer error type from exception class and message.

        Args:
            exception: The exception to analyze

        Returns:
            Inferred error type or None
        """
        exc_name = type(exception).__name__
        exc_msg = str(exception).lower()

        # Check exception class names first
        class_mappings = {
            ("TimeoutError", "ConnectTimeout"): SyncErrorType.TIMEOUT,
            ("ConnectionError", "ConnectError"): SyncErrorType.NETWORK_ERROR,
            ("ValidationError",): SyncErrorType.VALIDATION_ERROR,
            (
                "IntegrityError",
                "DatabaseError",
                "OperationalError",
            ): SyncErrorType.DATABASE_ERROR,
        }

        for classes, error_type in class_mappings.items():
            if exc_name in classes:
                return error_type

        # Check message patterns - order matters for specificity
        message_patterns = [
            # More specific patterns first
            (["token", "expired"], SyncErrorType.TOKEN_EXPIRED),
            (["milestone", "not found"], SyncErrorType.MILESTONE_NOT_FOUND),
            (["project", "not found"], SyncErrorType.PROJECT_NOT_FOUND),
            # Less specific patterns
            (["timeout"], SyncErrorType.TIMEOUT),
            (["connection"], SyncErrorType.NETWORK_ERROR),
            (["rate limit", "429"], SyncErrorType.API_RATE_LIMIT),
            (["auth", "401"], SyncErrorType.AUTHENTICATION_FAILED),
            (["permission", "403"], SyncErrorType.PERMISSION_DENIED),
            (["not found", "404"], SyncErrorType.RESOURCE_NOT_FOUND),
            (["validation"], SyncErrorType.VALIDATION_ERROR),
            (["duplicate", "unique"], SyncErrorType.DUPLICATE_ENTITY),
            (["schema"], SyncErrorType.SCHEMA_MISMATCH),
            (["conflict"], SyncErrorType.CONFLICT),
        ]

        for patterns, error_type in message_patterns:
            if all(pattern in exc_msg for pattern in patterns):
                return error_type

        return None

    @staticmethod
    def _is_recoverable(error_type: SyncErrorType) -> bool:
        """Determine if an error type is recoverable.

        Args:
            error_type: The error type

        Returns:
            True if the error can be recovered from
        """
        non_recoverable = {
            SyncErrorType.PERMISSION_DENIED,
            SyncErrorType.SCHEMA_MISMATCH,
            SyncErrorType.CONFIGURATION_ERROR,
        }
        return error_type not in non_recoverable

    @staticmethod
    def _get_suggested_fix(error_type: SyncErrorType) -> str | None:
        """Get suggested fix for an error type.

        Args:
            error_type: The error type

        Returns:
            Suggested fix or None
        """
        fixes = {
            SyncErrorType.AUTHENTICATION_FAILED: "Check your credentials and token",
            SyncErrorType.TOKEN_EXPIRED: "Refresh or regenerate your access token",
            SyncErrorType.PERMISSION_DENIED: "Verify you have required permissions",
            SyncErrorType.API_RATE_LIMIT: "Wait for rate limit to reset or reduce request frequency",
            SyncErrorType.TIMEOUT: "Check network connection and try again",
            SyncErrorType.NETWORK_ERROR: "Check network connection and try again",
            SyncErrorType.RESOURCE_NOT_FOUND: "Verify the resource exists and ID is correct",
            SyncErrorType.DUPLICATE_ENTITY: "Use duplicate detection to resolve conflicts",
            SyncErrorType.CIRCUIT_BREAKER_OPEN: "Wait for circuit breaker to reset, then retry",
            SyncErrorType.RETRY_EXHAUSTED: "Check error logs and resolve underlying issue",
            SyncErrorType.CONFIGURATION_ERROR: "Review and fix configuration settings",
        }
        return fixes.get(error_type)


# Common error constructors for convenience


def authentication_error(message: str = "Authentication failed") -> SyncError:
    """Create an authentication error.

    Args:
        message: Error message

    Returns:
        SyncError with AUTHENTICATION_FAILED type
    """
    return SyncError(
        error_type=SyncErrorType.AUTHENTICATION_FAILED,
        message=message,
        is_recoverable=True,
        suggested_fix="Check your credentials and token",
    )


def network_error(message: str = "Network error occurred") -> SyncError:
    """Create a network error.

    Args:
        message: Error message

    Returns:
        SyncError with NETWORK_ERROR type
    """
    return SyncError(
        error_type=SyncErrorType.NETWORK_ERROR,
        message=message,
        is_recoverable=True,
        suggested_fix="Check network connection and try again",
    )


def rate_limit_error(retry_after: int | None = None) -> SyncError:
    """Create a rate limit error.

    Args:
        retry_after: Seconds until rate limit resets

    Returns:
        SyncError with API_RATE_LIMIT type
    """
    message = "API rate limit exceeded"
    if retry_after:
        message += f" (retry after {retry_after}s)"

    metadata = {"retry_after": retry_after} if retry_after else None

    return SyncError(
        error_type=SyncErrorType.API_RATE_LIMIT,
        message=message,
        is_recoverable=True,
        suggested_fix="Wait for rate limit to reset or reduce request frequency",
        metadata=metadata,
    )


def resource_not_found_error(resource_type: str, resource_id: str) -> SyncError:
    """Create a resource not found error.

    Args:
        resource_type: Type of resource (Issue, Milestone, etc.)
        resource_id: Resource identifier

    Returns:
        SyncError with RESOURCE_NOT_FOUND type
    """
    return SyncError(
        error_type=SyncErrorType.RESOURCE_NOT_FOUND,
        message=f"{resource_type} not found",
        entity_type=resource_type,
        entity_id=resource_id,
        is_recoverable=False,
        suggested_fix="Verify the resource exists and ID is correct",
    )


def conflict_error(
    entity_type: str,
    entity_id: str,
    message: str = "Conflict detected",
) -> SyncError:
    """Create a conflict error.

    Args:
        entity_type: Type of entity
        entity_id: Entity identifier
        message: Conflict description

    Returns:
        SyncError with CONFLICT type
    """
    return SyncError(
        error_type=SyncErrorType.CONFLICT,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        is_recoverable=True,
        suggested_fix="Resolve the conflict manually or use --interactive mode",
    )


__all__ = [
    "SyncError",
    "SyncErrorType",
    "authentication_error",
    "network_error",
    "rate_limit_error",
    "resource_not_found_error",
    "conflict_error",
]
