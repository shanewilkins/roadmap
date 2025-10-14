"""GitHub API client for roadmap CLI."""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .credentials import get_credential_manager, mask_token
from .models import Comment, Issue, Milestone, MilestoneStatus, Priority, Status


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    pass


class GitHubClient:
    """GitHub API client for managing issues and milestones."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            owner: Repository owner (username or organization)
            repo: Repository name
        """
        # Try to get token from multiple sources with priority:
        # 1. Explicit parameter
        # 2. Environment variable
        # 3. Credential manager
        self.token = token or self._get_token_secure()
        self.owner = owner
        self.repo = repo

        if not self.token:
            raise GitHubAPIError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable, use credential manager, or provide token."
            )

        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
            ],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "roadmap-cli/1.0",
            }
        )

    def _get_token_secure(self) -> Optional[str]:
        """Get token from secure sources (environment variable or credential manager)."""
        # First try environment variable
        env_token = os.getenv("GITHUB_TOKEN")
        if env_token:
            return env_token

        # Then try credential manager
        try:
            credential_manager = get_credential_manager()
            return credential_manager.get_token()
        except Exception:
            # Silently fail - credential manager issues shouldn't block functionality
            return None

    def set_repository(self, owner: str, repo: str) -> None:
        """Set the target repository."""
        self.owner = owner
        self.repo = repo

    def _check_repository(self) -> None:
        """Check if repository is set."""
        if not self.owner or not self.repo:
            raise GitHubAPIError(
                "Repository not set. Use set_repository() or provide owner/repo in constructor."
            )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to the GitHub API."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise GitHubAPIError("Authentication failed. Check your GitHub token.")
            elif response.status_code == 403:
                raise GitHubAPIError(
                    "Access forbidden. Check repository permissions and token scopes."
                )
            elif response.status_code == 404:
                raise GitHubAPIError("Repository or resource not found.")
            elif response.status_code == 422:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("message", "Validation failed")
                raise GitHubAPIError(f"Validation error: {error_msg}")
            else:
                raise GitHubAPIError(f"GitHub API error ({response.status_code}): {e}")
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"Request failed: {e}")

    def test_authentication(self) -> Dict[str, Any]:
        """Test authentication and get user info."""
        response = self._make_request("GET", "/user")
        return response.json()

    def test_repository_access(self) -> Dict[str, Any]:
        """Test repository access."""
        self._check_repository()
        response = self._make_request("GET", f"/repos/{self.owner}/{self.repo}")
        return response.json()

    # Issue Management

    def get_issues(
        self,
        state: str = "all",
        labels: Optional[List[str]] = None,
        milestone: Optional[str] = None,
        assignee: Optional[str] = None,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get issues from the repository."""
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
        return response.json()

    def get_issue(self, issue_number: int) -> Dict[str, Any]:
        """Get a specific issue by number."""
        self._check_repository()
        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        )
        return response.json()

    def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new issue."""
        self._check_repository()

        data = {"title": title}

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
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Dict[str, Any]:
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

    def close_issue(self, issue_number: int) -> Dict[str, Any]:
        """Close an issue."""
        return self.update_issue(issue_number, state="closed")

    def reopen_issue(self, issue_number: int) -> Dict[str, Any]:
        """Reopen an issue."""
        return self.update_issue(issue_number, state="open")

    # Milestone Management

    def get_milestones(self, state: str = "open") -> List[Dict[str, Any]]:
        """Get milestones from the repository."""
        self._check_repository()

        params = {"state": state}
        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/milestones", params=params
        )
        return response.json()

    def get_milestone(self, milestone_number: int) -> Dict[str, Any]:
        """Get a specific milestone by number."""
        self._check_repository()
        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
        )
        return response.json()

    def create_milestone(
        self,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        state: str = "open",
    ) -> Dict[str, Any]:
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
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    # Label Management

    def get_labels(self) -> List[Dict[str, Any]]:
        """Get repository labels."""
        self._check_repository()
        response = self._make_request("GET", f"/repos/{self.owner}/{self.repo}/labels")
        return response.json()

    def create_label(
        self, name: str, color: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
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
        new_name: Optional[str] = None,
        color: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    # Utility Methods

    def priority_to_labels(self, priority: Priority) -> List[str]:
        """Convert priority to GitHub labels."""
        priority_labels = {
            Priority.CRITICAL: ["priority:critical"],
            Priority.HIGH: ["priority:high"],
            Priority.MEDIUM: ["priority:medium"],
            Priority.LOW: ["priority:low"],
        }
        return priority_labels.get(priority, [])

    def status_to_labels(self, status: Status) -> List[str]:
        """Convert status to GitHub labels."""
        status_labels = {
            Status.TODO: ["status:todo"],
            Status.IN_PROGRESS: ["status:in-progress"],
            Status.BLOCKED: ["status:blocked"],
            Status.REVIEW: ["status:review"],
            Status.DONE: ["status:done"],
        }
        return status_labels.get(status, [])

    def labels_to_priority(self, labels: List[str]) -> Optional[Priority]:
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

    def labels_to_status(self, labels: List[str]) -> Optional[Status]:
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
                return Status.DONE

        return None

    def setup_default_labels(self) -> None:
        """Set up default priority and status labels in the repository."""
        default_labels = [
            # Priority labels
            {
                "name": "priority:critical",
                "color": "d73a4a",
                "description": "Critical priority issue",
            },
            {
                "name": "priority:high",
                "color": "ff6b6b",
                "description": "High priority issue",
            },
            {
                "name": "priority:medium",
                "color": "ffa500",
                "description": "Medium priority issue",
            },
            {
                "name": "priority:low",
                "color": "28a745",
                "description": "Low priority issue",
            },
            # Status labels
            {
                "name": "status:todo",
                "color": "e1e4e8",
                "description": "Issue is in todo status",
            },
            {
                "name": "status:in-progress",
                "color": "fbca04",
                "description": "Issue is in progress",
            },
            {
                "name": "status:blocked",
                "color": "d93f0b",
                "description": "Issue is blocked waiting for dependencies",
            },
            {
                "name": "status:review",
                "color": "0366d6",
                "description": "Issue is under review",
            },
            {
                "name": "status:done",
                "color": "28a745",
                "description": "Issue is completed",
            },
        ]

        existing_labels = {label["name"] for label in self.get_labels()}

        for label_data in default_labels:
            if label_data["name"] not in existing_labels:
                try:
                    self.create_label(**label_data)
                except GitHubAPIError:
                    # Label might already exist, continue
                    continue

    def get_issue_comments(self, issue_number: int) -> List[Comment]:
        """Get all comments for a specific issue.

        Args:
            issue_number: GitHub issue number

        Returns:
            List of Comment objects
        """
        self._check_repository()

        response = self._make_request(
            "GET", f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
        )

        comments = []
        for comment_data in response.json():
            comment = Comment(
                id=comment_data["id"],
                issue_id=str(issue_number),
                author=comment_data["user"]["login"],
                body=comment_data["body"],
                created_at=datetime.fromisoformat(
                    comment_data["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    comment_data["updated_at"].replace("Z", "+00:00")
                ),
                github_url=comment_data["html_url"],
            )
            comments.append(comment)

        return comments

    def create_issue_comment(self, issue_number: int, body: str) -> Comment:
        """Create a new comment on an issue.

        Args:
            issue_number: GitHub issue number
            body: Comment content (markdown)

        Returns:
            Created Comment object
        """
        self._check_repository()

        data = {"body": body}

        response = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json=data,
        )

        comment_data = response.json()
        return Comment(
            id=comment_data["id"],
            issue_id=str(issue_number),
            author=comment_data["user"]["login"],
            body=comment_data["body"],
            created_at=datetime.fromisoformat(
                comment_data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                comment_data["updated_at"].replace("Z", "+00:00")
            ),
            github_url=comment_data["html_url"],
        )

    def update_issue_comment(self, comment_id: int, body: str) -> Comment:
        """Update an existing comment.

        Args:
            comment_id: GitHub comment ID
            body: Updated comment content (markdown)

        Returns:
            Updated Comment object
        """
        self._check_repository()

        data = {"body": body}

        response = self._make_request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}",
            json=data,
        )

        comment_data = response.json()
        return Comment(
            id=comment_data["id"],
            issue_id="",  # We don't get issue number from this endpoint
            author=comment_data["user"]["login"],
            body=comment_data["body"],
            created_at=datetime.fromisoformat(
                comment_data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                comment_data["updated_at"].replace("Z", "+00:00")
            ),
            github_url=comment_data["html_url"],
        )

    def delete_issue_comment(self, comment_id: int) -> None:
        """Delete a comment.

        Args:
            comment_id: GitHub comment ID
        """
        self._check_repository()

        self._make_request(
            "DELETE", f"/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}"
        )

    # Team Collaboration

    def get_current_user(self) -> str:
        """Get the current authenticated user's login."""
        response = self._make_request("GET", "/user")
        return response.json()["login"]

    def get_repository_collaborators(self) -> List[str]:
        """Get all collaborators for the repository.

        Returns:
            List of usernames of repository collaborators
        """
        self._check_repository()

        # Get direct collaborators
        collaborators = []
        page = 1
        per_page = 100

        while True:
            response = self._make_request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/collaborators",
                params={"page": page, "per_page": per_page},
            )

            page_collaborators = response.json()
            if not page_collaborators:
                break

            collaborators.extend([collab["login"] for collab in page_collaborators])

            if len(page_collaborators) < per_page:
                break

            page += 1

        return sorted(collaborators)

    def get_repository_contributors(self) -> List[str]:
        """Get all contributors to the repository.

        Returns:
            List of usernames of repository contributors
        """
        self._check_repository()

        contributors = []
        page = 1
        per_page = 100

        while True:
            response = self._make_request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/contributors",
                params={"page": page, "per_page": per_page},
            )

            page_contributors = response.json()
            if not page_contributors:
                break

            contributors.extend([contrib["login"] for contrib in page_contributors])

            if len(page_contributors) < per_page:
                break

            page += 1

        return sorted(contributors)

    def get_team_members(self) -> List[str]:
        """Get all team members (collaborators and contributors combined).

        Returns:
            List of unique usernames from collaborators and contributors
        """
        collaborators = self.get_repository_collaborators()
        contributors = self.get_repository_contributors()

        # Combine and deduplicate
        team_members = list(set(collaborators + contributors))
        return sorted(team_members)

    def validate_user_exists(self, username: str) -> bool:
        """Check if a GitHub user exists.
        
        Args:
            username: GitHub username to validate
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            response = self._make_request("GET", f"/users/{username}")
            return response.status_code == 200
        except GitHubAPIError:
            return False

    def validate_user_has_repository_access(self, username: str) -> bool:
        """Check if a user has access to the repository (is collaborator or contributor).
        
        Args:
            username: GitHub username to validate
            
        Returns:
            True if user has repository access, False otherwise
        """
        try:
            team_members = self.get_team_members()
            return username in team_members
        except GitHubAPIError:
            return False

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee for issue assignment.
        
        Args:
            assignee: Username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty"

        assignee = assignee.strip()

        # First check if user exists on GitHub
        if not self.validate_user_exists(assignee):
            return False, f"GitHub user '{assignee}' does not exist"

        # Then check if they have repository access
        if not self.validate_user_has_repository_access(assignee):
            return False, f"User '{assignee}' does not have access to repository {self.owner}/{self.repo}"

        return True, ""
