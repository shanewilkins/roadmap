"""GitHub Milestones handler."""

from datetime import datetime
from typing import Any

from roadmap.adapters.github.handlers.base import BaseGitHubHandler


class MilestoneHandler(BaseGitHubHandler):
    """Handler for GitHub Milestones API operations."""

    def get_milestones(self, state: str = "open") -> list[dict[str, Any]]:
        """Get milestones from the repository."""
        self._check_repository()

        params = {"state": state}
        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/milestones", params=params
        )
        return response.json()

    def get_milestone(self, milestone_number: int) -> dict[str, Any]:
        """Get a specific milestone by number."""
        self._check_repository()
        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
        )
        return response.json()

    def create_milestone(
        self,
        title: str,
        description: str | None = None,
        due_date: datetime | None = None,
        state: str = "open",
    ) -> dict[str, Any]:
        """Create a new milestone."""
        self._check_repository()

        data = {"title": title, "state": state}

        if description:
            data["description"] = description
        if due_date:
            # GitHub expects ISO 8601 format with timezone (Z for UTC)
            if due_date.tzinfo is None:
                # Assume UTC for naive datetime
                data["due_on"] = due_date.isoformat() + "Z"
            else:
                data["due_on"] = due_date.isoformat()

        response = self._make_request(
            "POST", f"/repos/{self.owner}/{self.repo}/milestones", json=data
        )
        return response.json()

    def update_milestone(
        self,
        milestone_number: int,
        title: str | None = None,
        description: str | None = None,
        due_date: datetime | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing milestone."""
        self._check_repository()

        data = {}

        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if due_date is not None:
            # GitHub expects ISO 8601 format with timezone (Z for UTC)
            if due_date.tzinfo is None:
                # Assume UTC for naive datetime
                data["due_on"] = due_date.isoformat() + "Z"
            else:
                data["due_on"] = due_date.isoformat()
        if state is not None:
            data["state"] = state

        response = self._make_request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}",
            json=data,
        )
        return response.json()

    def delete_milestone(self, milestone_number: int) -> None:
        """Delete a milestone."""
        self._check_repository()
        self._make_request(
            "DELETE", f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
        )
