"""
GitHub integration setup workflow.
Handles OAuth, token management, and validation.
"""

import os
from typing import TYPE_CHECKING

import click
import yaml

from roadmap.application.core import RoadmapCore
from roadmap.shared.console import get_console

console = get_console()

# Import GitHub modules for type hints (allow test patching)
try:
    from roadmap.infrastructure.github import GitHubClient
    from roadmap.infrastructure.security.credentials import CredentialManager
except ImportError:
    GitHubClient = None  # type: ignore
    CredentialManager = None  # type: ignore

if TYPE_CHECKING:
    pass


class GitHubTokenResolver:
    """Resolves GitHub tokens from multiple sources."""

    def __init__(self, cred_manager=None):  # type: ignore
        self.cred_manager = cred_manager

    def get_existing_token(self) -> str | None:
        """Get existing stored token."""
        if not self.cred_manager:
            return None
        try:
            return self.cred_manager.get_token()
        except Exception:
            return None

    def resolve_token(
        self,
        cli_token: str | None,
        interactive: bool,
        yes: bool,
        existing_token: str | None,
    ) -> tuple[str | None, bool]:
        """
        Resolve which token to use.

        Returns:
            Tuple of (token, should_continue)
        """
        # Priority: CLI arg > environment > stored > prompt
        env_token = os.environ.get("ROADMAP_GITHUB_TOKEN")

        if cli_token:
            return cli_token, True

        if env_token:
            console.print(
                "ℹ️  Using GitHub token from environment variable ROADMAP_GITHUB_TOKEN",
                style="dim",
            )
            return env_token, True

        if existing_token:
            if interactive and not yes:
                console.print("🔍 Found existing GitHub credentials")
                if click.confirm("Use existing GitHub credentials?"):
                    console.print("✅ Using existing GitHub credentials")
                    return existing_token, True
            else:
                return existing_token, True

        # Need to get token from user
        if interactive and not yes:
            console.print(
                "To integrate with GitHub you'll need a personal access token with 'repo' scope."
            )
            console.print("→ Create one: https://github.com/settings/tokens")
            token = click.prompt("Paste your GitHub token", hide_input=True)
            return token, True

        # Non-interactive without token
        console.print(
            "❌ Non-interactive mode requires providing a token via --github-token "
            "or setting ROADMAP_GITHUB_TOKEN, or use --skip-github to skip integration.",
            style="bold red",
        )
        return None, False


class GitHubSetupValidator:
    """Validates GitHub connectivity and permissions during setup."""

    def __init__(self, github_client):  # type: ignore
        self.client = github_client

    def validate_authentication(self) -> tuple[bool, str | None]:
        """
        Validate user authentication.

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
        """
        Validate repository access and permissions.

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


class GitHubConfigManager:
    """Manages GitHub configuration in roadmap config file."""

    def __init__(self, core: RoadmapCore):
        self.core = core
        self.config_file = core.roadmap_dir / "config.yaml"

    def save_github_config(self, github_repo: str) -> None:
        """Save GitHub repository configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        config["github"] = {
            "repository": github_repo,
            "enabled": True,
            "sync_enabled": True,
            "webhook_secret": None,
            "sync_settings": {
                "bidirectional": True,
                "auto_close": True,
                "sync_labels": True,
                "sync_milestones": True,
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        console.print("⚙️  Configuration saved")


def show_github_setup_instructions(github_repo: str, yes: bool) -> bool:
    """
    Show GitHub setup instructions and get user confirmation.

    Returns:
        True if user wants to continue, False to skip
    """
    console.print("🔗 GitHub Integration Setup", style="bold blue")
    console.print(f"\nRepository: {github_repo}")
    console.print("\nTo sync with GitHub, you'll need a personal access token.")
    console.print("→ Open: https://github.com/settings/tokens")
    console.print(
        "→ Create token with 'repo' scope (or 'public_repo' for public repos)"
    )
    console.print("→ Required permissions: Issues, Pull requests, Repository metadata")
    console.print()

    if not yes and not click.confirm("Do you want to set up GitHub integration now?"):
        console.print(
            "⏭️  Skipping GitHub integration (you can set this up later with 'roadmap sync setup')"
        )
        return False

    return True
