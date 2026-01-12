"""Issue-related helper utilities for filtering, updating, and management.

DEPRECATED: This module is deprecated. Import directly from issue_filter_service instead.
Example: from roadmap.core.services.issue.issue_filter_service import IssueQueryService
"""

# Backward compatibility re-exports
from roadmap.core.services.issue.issue_filter_service import (
    IssueFilterValidator,
    IssueQueryService,
    WorkloadCalculator,
)

__all__ = [
    "IssueFilterValidator",
    "IssueQueryService",
    "WorkloadCalculator",
]
