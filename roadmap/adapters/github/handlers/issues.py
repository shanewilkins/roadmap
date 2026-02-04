"""GitHub Issues handler."""

from typing import Any

from roadmap.adapters.github.handlers.base import BaseGitHubHandler


class IssueHandler(BaseGitHubHandler):
    """Handler for GitHub Issues API operations."""

    def get_issues(
        self,
        state: str = "all",
        labels: list[str] | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Get issues from the repository."""
        from structlog import get_logger

        logger = get_logger()
        logger.info("issue_handler_get_issues_called", state=state, per_page=per_page)

        self._check_repository()

        params = {
            "state": state,
            "per_page": per_page,
            "sort": "created",
            "direction": "desc",
        }

        if labels:
            params["labels"] = ",".join(labels)
        if milestone:
            params["milestone"] = milestone
        if assignee:
            params["assignee"] = assignee

        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/issues", params=params
        )
        result = response.json()

        return result

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        """Get a specific issue by number."""
        self._check_repository()
        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        )
        return response.json()

    def create_issue(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
    ) -> dict[str, Any]:
        """Create a new issue."""
        self._check_repository()

        data: dict[str, Any] = {"title": title}

        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone

        response = self._make_request(
            "POST", f"/repos/{self.owner}/{self.repo}/issues", json=data
        )
        return response.json()

    def update_issue(
        self,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        milestone: int | None = None,
    ) -> dict[str, Any]:
        """Update an existing issue."""
        self._check_repository()

        data = {}

        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        if assignees is not None:
            data["assignees"] = assignees
        if milestone is not None:
            data["milestone"] = milestone

        response = self._make_request(
            "PATCH", f"/repos/{self.owner}/{self.repo}/issues/{issue_number}", json=data
        )
        return response.json()

    def close_issue(self, issue_number: int) -> dict[str, Any]:
        """Close an issue."""
        return self.update_issue(issue_number, state="closed")

    def reopen_issue(self, issue_number: int) -> dict[str, Any]:
        """Reopen a closed issue."""
        return self.update_issue(issue_number, state="open")
