"""GitHub configuration validation service."""

from pathlib import Path

import requests

from roadmap.core.services.github.github_integration_service import (
    GitHubIntegrationService,
)


class GitHubConfigValidator:
    """Validates GitHub configuration before operations."""

    def __init__(self, config_path: Path):
        """Initialize validator with config path.

        Args:
            config_path: Path to .roadmap directory
        """
        self.config_path = config_path
        self.config_file = config_path / "config.yaml"
        self.service = GitHubIntegrationService(config_path, self.config_file)

    def validate_config(self) -> tuple[bool, str | None]:
        """Validate GitHub configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if config exists
        token, owner, repo = self.service.get_github_config()
        if not token or not repo:
            return (
                False,
                "GitHub not configured. Run: roadmap init --github-repo owner/repo --github-token <token>",
            )

        # Check required fields
        if not repo:
            return False, "GitHub repo not configured in config.yaml"

        if not token:
            return False, "GitHub token not configured in config.yaml"

        # Validate token format (basic check)
        if not isinstance(token, str) or len(token) < 10:
            return False, "GitHub token appears invalid (too short)"

        return True, None

    def validate_token(self) -> tuple[bool, str | None]:
        """Validate GitHub token accessibility.

        Returns:
            Tuple of (is_valid, error_message)
        """
        token, owner, repo = self.service.get_github_config()
        if not token:
            return False, "GitHub token not set"

        try:
            # Test token by making a simple API call
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            response = requests.get(
                "https://api.github.com/user",
                headers=headers,
                timeout=5,
            )

            if response.status_code == 401:
                return False, "GitHub token is invalid or expired"
            elif response.status_code == 403:
                return False, "GitHub token has insufficient permissions"
            elif response.status_code == 200:
                return True, None
            else:
                return (
                    False,
                    f"GitHub API error: {response.status_code}",
                )
        except requests.RequestException as e:
            return False, f"Failed to reach GitHub: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error validating token: {str(e)}"

    def validate_repo_access(self) -> tuple[bool, str | None]:
        """Validate access to configured repository.

        Returns:
            Tuple of (is_valid, error_message)
        """
        token, owner, repo = self.service.get_github_config()
        if not token or not repo:
            return False, "GitHub config incomplete"

        try:
            # Test repo access
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            url = f"https://api.github.com/repos/{repo}"
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 401:
                return False, "GitHub token is invalid or expired"
            elif response.status_code == 403:
                return False, f"Access denied to repository {repo}"
            elif response.status_code == 404:
                return False, f"Repository not found: {repo}"
            elif response.status_code == 200:
                return True, None
            else:
                return (
                    False,
                    f"GitHub API error: {response.status_code}",
                )
        except requests.RequestException as e:
            return False, f"Failed to reach GitHub: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error validating repo: {str(e)}"

    def validate_all(self) -> tuple[bool, str | None]:
        """Run all validations.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Config validation
        is_valid, error = self.validate_config()
        if not is_valid:
            return False, error

        # Token validation
        is_valid, error = self.validate_token()
        if not is_valid:
            return False, error

        # Repo access validation
        is_valid, error = self.validate_repo_access()
        if not is_valid:
            return False, error

        return True, None
