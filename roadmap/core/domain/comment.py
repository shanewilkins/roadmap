"""Comment model for issue discussions."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Comment:
    """Comment data model for issues."""

    id: int
    issue_id: str
    author: str
    body: str  # Comment content (markdown)
    created_at: datetime
    updated_at: datetime
    external_url: str | None = None
    in_reply_to: int | None = None  # Comment ID this is a reply to (for threading)

    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"Comment by {self.author} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
