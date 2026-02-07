"""Port for reading/writing issues to persistent storage."""

from abc import ABC, abstractmethod

from roadmap.core.domain.issue import Issue


class IIssueRepository(ABC):
    """Port for reading/writing issues to persistent storage."""

    @abstractmethod
    def get_all(self) -> list[Issue]:
        """Get all issues including archived."""
        pass

    @abstractmethod
    def get(self, issue_id: str) -> Issue:
        """Get single issue by ID. Raises IssueNotFound."""
        pass

    @abstractmethod
    def save(self, issue: Issue) -> None:
        """Save or update an issue."""
        pass

    @abstractmethod
    def delete(self, issue_id: str) -> None:
        """Permanently delete an issue."""
        pass

    @abstractmethod
    def archive(self, issue_id: str) -> None:
        """Archive an issue (mark state=archived)."""
        pass
