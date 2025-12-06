"""GitHub Collaborators handler."""

from roadmap.adapters.github.handlers.base import BaseGitHubHandler


class CollaboratorsHandler(BaseGitHubHandler):
    """Handler for GitHub team and collaborators API operations."""

    def get_current_user(self) -> str:
        """Get the current authenticated user's login."""
        response = self._make_request("GET", "/user")
        return response.json()["login"]

    def get_repository_collaborators(self) -> list[str]:
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

    def get_repository_contributors(self) -> list[str]:
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

    def get_team_members(self) -> list[str]:
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
        except Exception:
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
        except Exception:
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
            return (
                False,
                f"User '{assignee}' does not have access to repository {self.owner}/{self.repo}",
            )

        return True, ""
