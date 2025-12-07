"""DEPRECATED: Backward compatibility facade for issue filters.

Use roadmap.core.services.issue_helpers instead.
"""

from roadmap.core.services.issue_helpers import (
    IssueFilterValidator,
    IssueQueryService,
)

__all__ = ["IssueFilterValidator", "IssueQueryService"]
