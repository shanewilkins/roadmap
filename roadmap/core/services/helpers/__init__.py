"""Helper utilities for sync and core services.

DEPRECATED: This module is deprecated. Import directly from status_change_service instead.
Example: from roadmap.core.services.status_change_service import parse_status_change
"""

# Backward compatibility re-exports
from roadmap.core.services.status_change_service import (
    extract_issue_status_update,
    extract_milestone_status_update,
    parse_status_change,
)

__all__ = [
    "parse_status_change",
    "extract_issue_status_update",
    "extract_milestone_status_update",
]
