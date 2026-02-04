"""GitHub Labels handler."""

from typing import Any

from structlog import get_logger

from roadmap.adapters.github.handlers.base import BaseGitHubHandler
from roadmap.core.domain import Priority, Status

logger = get_logger()


class LabelHandler(BaseGitHubHandler):
    """Handler for GitHub Labels API operations."""

    def get_labels(self) -> list[dict[str, Any]]:
        """Get repository labels.
        
        Handles pagination automatically - returns all labels.
        
        Returns:
            List of all repository labels across all pages
        """
        self._check_repository()
        return self._paginate_request(
            "GET", f"/repos/{self.owner}/{self.repo}/labels"
        )

    def create_label(
        self, name: str, color: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a new label."""
        self._check_repository()

        data = {"name": name, "color": color.lstrip("#")}  # Remove # if present

        if description:
            data["description"] = description

        response = self._make_request(
            "POST", f"/repos/{self.owner}/{self.repo}/labels", json=data
        )
        return response.json()

    def update_label(
        self,
        label_name: str,
        new_name: str | None = None,
        color: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing label."""
        self._check_repository()

        data = {}

        if new_name is not None:
            data["new_name"] = new_name
        if color is not None:
            data["color"] = color.lstrip("#")
        if description is not None:
            data["description"] = description

        response = self._make_request(
            "PATCH", f"/repos/{self.owner}/{self.repo}/labels/{label_name}", json=data
        )
        return response.json()

    def delete_label(self, label_name: str) -> None:
        """Delete a label."""
        self._check_repository()
        self._make_request(
            "DELETE", f"/repos/{self.owner}/{self.repo}/labels/{label_name}"
        )

    def priority_to_labels(self, priority: Priority) -> list[str]:
        """Convert priority to GitHub labels."""
        priority_labels = {
            Priority.CRITICAL: ["priority:critical"],
            Priority.HIGH: ["priority:high"],
            Priority.MEDIUM: ["priority:medium"],
            Priority.LOW: ["priority:low"],
        }
        return priority_labels.get(priority, [])

    def status_to_labels(self, status: Status) -> list[str]:
        """Convert status to GitHub labels."""
        status_labels = {
            Status.TODO: ["status:todo"],
            Status.IN_PROGRESS: ["status:in-progress"],
            Status.BLOCKED: ["status:blocked"],
            Status.REVIEW: ["status:review"],
            Status.CLOSED: ["status:done"],
        }
        return status_labels.get(status, [])

    def labels_to_priority(self, labels: list[str]) -> Priority | None:
        """Extract priority from GitHub labels."""
        label_names = [
            label.get("name", label) if isinstance(label, dict) else label
            for label in labels
        ]

        for label in label_names:
            if label == "priority:critical":
                return Priority.CRITICAL
            elif label == "priority:high":
                return Priority.HIGH
            elif label == "priority:medium":
                return Priority.MEDIUM
            elif label == "priority:low":
                return Priority.LOW

        return None

    def labels_to_status(self, labels: list[str]) -> Status | None:
        """Extract status from GitHub labels."""
        label_names = [
            label.get("name", label) if isinstance(label, dict) else label
            for label in labels
        ]

        for label in label_names:
            if label == "status:todo":
                return Status.TODO
            elif label == "status:in-progress":
                return Status.IN_PROGRESS
            elif label == "status:blocked":
                return Status.BLOCKED
            elif label == "status:review":
                return Status.REVIEW
            elif label == "status:done":
                return Status.CLOSED

        return None

    def setup_default_labels(self) -> None:
        """Set up default labels for priority and status."""
        self._check_repository()

        # Priority labels
        priority_labels = [
            ("priority:critical", "FF0000", "Critical priority"),
            ("priority:high", "FF9900", "High priority"),
            ("priority:medium", "FFFF00", "Medium priority"),
            ("priority:low", "00FF00", "Low priority"),
        ]

        # Status labels
        status_labels = [
            ("status:todo", "CCCCCC", "To do"),
            ("status:in-progress", "0366D6", "In progress"),
            ("status:blocked", "D73A49", "Blocked"),
            ("status:review", "A371F7", "In review"),
            ("status:done", "28A745", "Done"),
        ]

        existing_labels = [label["name"] for label in self.get_labels()]

        for name, color, description in priority_labels + status_labels:
            if name not in existing_labels:
                try:
                    self.create_label(name, color, description)
                except Exception as e:
                    # Label might have been created by another process
                    logger.debug("create_label_failed", label_name=name, error=str(e))
