"""Comment model for issue discussions."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Comment:
    """Comment data model for issues."""

    id: int  # GitHub comment ID
    issue_id: str  # Local issue ID or GitHub issue number
    author: str  # GitHub username
    body: str  # Comment content (markdown)
    created_at: datetime
    updated_at: datetime
    github_url: str | None = None  # GitHub comment URL

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Comment by {self.author} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
