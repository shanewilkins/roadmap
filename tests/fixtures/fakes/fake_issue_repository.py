"""Fake/test implementation of IIssueRepository."""

from roadmap.core.domain.issue import Issue
from roadmap.core.domain.ports.issue_repository import IIssueRepository


class IssueNotFound(Exception):
    """Raised when issue not found in repository."""

    pass


class FakeIssueRepository(IIssueRepository):
    """In-memory test implementation of IIssueRepository."""

    def __init__(self):
        self._issues: dict[str, Issue] = {}
        self.deleted_ids: set[str] = set()
        self.archived_ids: set[str] = set()

    def get_all(self) -> list[Issue]:
        """Get all issues including archived."""
        return list(self._issues.values())

    def get(self, issue_id: str) -> Issue:
        """Get single issue by ID. Raises IssueNotFound."""
        if issue_id not in self._issues:
            raise IssueNotFound(f"Issue {issue_id} not found")
        return self._issues[issue_id]

    def save(self, issue: Issue) -> None:
        """Save or update an issue."""
        self._issues[issue.id] = issue

    def save_all(self, issues: list[Issue]) -> None:
        """Save multiple issues."""
        for issue in issues:
            self.save(issue)

    def delete(self, issue_id: str) -> None:
        """Permanently delete an issue."""
        if issue_id not in self._issues:
            raise IssueNotFound(f"Issue {issue_id} not found")
        del self._issues[issue_id]
        self.deleted_ids.add(issue_id)

    def delete_many(self, issue_ids: list[str]) -> int:
        """Delete multiple issues, returning count of deleted items."""
        deleted_count = 0
        for issue_id in issue_ids:
            try:
                self.delete(issue_id)
                deleted_count += 1
            except IssueNotFound:
                pass
        return deleted_count

    def archive(self, issue_id: str) -> None:
        """Archive an issue (mark in archived_ids)."""
        if issue_id not in self._issues:
            raise IssueNotFound(f"Issue {issue_id} not found")
        self.archived_ids.add(issue_id)

    def reset(self) -> None:
        """Reset state for next test."""
        self._issues.clear()
        self.deleted_ids.clear()
        self.archived_ids.clear()
