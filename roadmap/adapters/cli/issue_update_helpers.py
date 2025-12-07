"""DEPRECATED: Backward compatibility facade for issue update helpers.

Use roadmap.core.services.issue_helpers instead.
"""

from roadmap.core.services.issue_helpers import (
    IssueUpdateBuilder,
    IssueUpdateDisplay,
)

__all__ = ["IssueUpdateBuilder", "IssueUpdateDisplay"]
