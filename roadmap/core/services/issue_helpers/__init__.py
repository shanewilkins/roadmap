"""Legacy issue-query helpers retained for the Phase 8 analysis slice."""

# Backward compatibility re-exports
from roadmap.core.services.issue_helpers.issue_filters import (
    IssueFilterValidator,
    IssueQueryService,
    WorkloadCalculator,
)

__all__ = [
    "IssueFilterValidator",
    "IssueQueryService",
    "WorkloadCalculator",
]
