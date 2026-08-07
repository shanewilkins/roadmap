"""Handler for GitHub authentication setup in CLI."""

import click
import structlog
from rich.console import Console

from roadmap.adapters.github.github import GitHubClient
from roadmap.infrastructure.security.credentials import CredentialManager

logger = structlog.get_logger()


class GitAuthenticationHandler:
    """Handles GitHub authentication setup and management."""

    def __init__(self, console: Console):
        """Initialize handler with console for output.

        Args:
            console: Rich Console instance
        """
        self.console = console
        self.cred_manager = CredentialManager()

    def setup_github_auth(self, update_token: bool = False):
        """Set up or update GitHub authentication.

        Args:
            update_token: If True, force update token; otherwise ask if exists

        Raises:
            Exception: If authentication setup fails
        """
        existing_token = None

        if not update_token:
            try:
                existing_token = self.cred_manager.get_token()
                if existing_token:
                    self.console.print("🔍 Found existing GitHub credentials")
                    if click.confirm("Use existing GitHub token?"):
                        logger.info("github_auth_using_existing")
                        self.console.print("✅ GitHub authentication configured")
                        return
                    elif not click.confirm("Update GitHub token?"):
                        self.console.print("Skipped GitHub authentication setup")
                        return
            except Exception as e:
                logger.debug(
                    "existing_token_check_failed",
                    error=str(e),
                    action="check_existing_token",
                )

        # Get new token from user
        self.console.print("🔑 GitHub Authentication Setup", style="bold cyan")
        self.console.print()
        self.console.print(
            "You'll need a Personal Access Token with 'repo' scope to sync with GitHub."
        )
        self.console.print("Create one here: https://github.com/settings/tokens/new")
        self.console.print()
        self.console.print(
            "Required scopes: repo (full control of private repositories)",
            style="dim",
        )
        self.console.print()

        token = click.prompt("Enter your GitHub Personal Access Token", hide_input=True)

        if not token or len(token.strip()) == 0:
            self.console.print("❌ Token cannot be empty", style="bold red")
            logger.warning("github_auth_empty_token", severity="operational")
            return

        # Validate token
        self.console.print("🧪 Validating GitHub token...", style="cyan")
        logger.debug("github_token_validating")

        try:
            client = GitHubClient(token)
            # Test connection and authentication
            user_data = client.test_authentication()
            username = user_data.get("login", "user")
            self.console.print(
                f"✅ Token valid (authenticated as @{username})", style="green"
            )
            logger.info("github_token_valid", username=username)
        except Exception as e:
            self.console.print(f"❌ Token validation failed: {e}", style="bold red")
            logger.error(
                "github_token_validation_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="infrastructure",
            )
            return

        # Store token
        try:
            if self.cred_manager.store_token(token):
                self.console.print("✅ GitHub authentication configured", style="green")
                self.console.print(
                    "Token stored securely in system keychain",
                    style="dim",
                )
                logger.info("github_token_stored")
            else:
                self.console.print(
                    "⚠️  Token validation succeeded but storage failed",
                    style="yellow",
                )
                logger.warning("github_token_storage_failed", severity="operational")
        except Exception as e:
            self.console.print(
                f"⚠️  Token validation succeeded but could not store: {e}",
                style="yellow",
            )
            logger.warning(
                "github_token_storage_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
