"""DEPRECATED: Backward compatibility facade for error logging.

Use roadmap.infrastructure.logging instead.
"""

from roadmap.infrastructure.logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_error_with_context,
    suggest_recovery,
)

__all__ = [
    "ErrorClassification",
    "classify_error",
    "is_error_recoverable",
    "suggest_recovery",
    "log_error_with_context",
]
