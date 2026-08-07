"""GitHub setup validation utilities."""

from roadmap.common.console import get_console

console = get_console()


class GitHubSetupValidator:
    """Validates GitHub connectivity and permissions during setup."""

    def __init__(self, github_client):  # type: ignore
        """Initialize GitHubSetupValidator.

        Args:
            github_client: GitHub client instance.
        """
        self.client = github_client

    def validate_authentication(self) -> tuple[bool, str | None]:
        """Validate user authentication.

        Returns:
            Tuple of (success, username or error)
        """
        try:
            user_response = self.client._make_request("GET", "/user")
            user_info = user_response.json()
            username = user_info.get("login", "unknown")
            console.print(f"✅ Authenticated as: {username}")
            return True, username
        except Exception as e:
            console.print(f"❌ Authentication failed: {e}", style="red")
            return False, str(e)

    def validate_repository_access(self, github_repo: str) -> tuple[bool, dict | None]:
        """Validate repository access and permissions.

        Returns:
            Tuple of (success, repo_info or error_message)
        """
        try:
            owner, repo = github_repo.split("/")
            self.client.set_repository(owner, repo)
            repo_info = self.client.test_repository_access()

            repo_name = repo_info.get("full_name", github_repo)
            console.print(f"✅ Repository access: {repo_name}")

            # Check permissions
            permissions = repo_info.get("permissions", {})
            if permissions.get("admin") or permissions.get("push"):
                console.print("✅ Write access: Available")
            elif permissions.get("pull"):
                console.print(
                    "⚠️  Read-only access: Limited sync capabilities", style="yellow"
                )
            else:
                console.print("❌ No repository access detected", style="red")

            return True, repo_info
        except Exception as e:
            console.print(f"⚠️  Repository validation warning: {e}", style="yellow")
            return False, {"error": str(e)}

    def test_api_access(self, github_repo: str) -> bool:
        """Test basic API calls."""
        try:
            issues_response = self.client._make_request(
                "GET",
                f"/repos/{github_repo}/issues",
                params={"state": "open", "per_page": 1},
            )
            issues = issues_response.json()
            console.print(f"✅ API test successful ({len(issues)} issue(s) found)")
            return True
        except Exception as e:
            console.print(f"⚠️  API test warning: {e}", style="yellow")
            return False
