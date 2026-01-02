"""
GitHub integration setup workflow.
Handles OAuth, token management, and validation.
"""

import os
from typing import TYPE_CHECKING

import click
import yaml
from structlog import get_logger

from roadmap.common.console import get_console
from roadmap.common.constants import SyncBackend
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger()

console = get_console()

# Import GitHub modules for type hints (allow test patching)
try:
    from roadmap.adapters.github.github import GitHubClient
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

    def save_github_config(
        self, github_repo: str, sync_backend: SyncBackend = SyncBackend.GITHUB
    ) -> None:
        """Save GitHub repository configuration.

        Args:
            github_repo: GitHub repository (owner/repo)
            sync_backend: Backend to use (SyncBackend.GITHUB or SyncBackend.GIT)

        Raises:
            ValueError: If github_repo is invalid format
        """
        # Validate repository format
        if not github_repo or "/" not in github_repo:
            log = logger.bind(github_repo=github_repo, operation="save_github_config")
            log.error("invalid_github_repo_format")
            raise ValueError(
                f"Invalid GitHub repository format: '{github_repo}'. "
                "Expected format: 'owner/repo'"
            )

        try:
            if self.config_file.exists():
                with open(self.config_file) as f:
                    loaded = yaml.safe_load(f)
                    config = loaded if isinstance(loaded, dict) else {}
            else:
                config: dict = {}

            config["github"] = {
                "repository": github_repo,
                "enabled": True,
                "sync_enabled": True,
                "sync_backend": sync_backend.value,
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

            log = logger.bind(
                github_repo=github_repo,
                sync_backend=sync_backend.value,
                operation="save_github_config",
            )
            log.info("github_config_saved")
            get_console().print("⚙️  Configuration saved")

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            log = logger.bind(
                github_repo=github_repo,
                sync_backend=sync_backend.value,
                error=str(e),
                operation="save_github_config",
            )
            log.error("github_config_save_failed")
            raise


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


class GitHubInitializationService:
    """Orchestrates GitHub integration setup during initialization."""

    def __init__(self, core: RoadmapCore):
        self.core = core
        self.presenter = None  # Set by caller if needed

    def setup(
        self,
        skip_github: bool,
        github_repo: str | None,
        detected_info: dict,
        interactive: bool,
        yes: bool,
        github_token: str | None,
        presenter=None,
        sync_backend: SyncBackend = SyncBackend.GITHUB,
    ) -> bool:
        """
        Set up GitHub integration if requested.

        Args:
            skip_github: If True, skip GitHub setup
            github_repo: GitHub repository (owner/repo)
            detected_info: Auto-detected project information
            interactive: If True, prompt user for input
            yes: If True, answer yes to all prompts
            github_token: GitHub personal access token
            presenter: UI presenter for output
            sync_backend: Backend to use (SyncBackend.GITHUB or SyncBackend.GIT)

        Returns:
            True if configured, False if skipped or failed
        """
        self.presenter = presenter

        if skip_github:
            return False

        repo_name = github_repo or detected_info.get("git_repo")
        if not repo_name:
            return False

        return self._configure_integration(
            repo_name, interactive, yes, token=github_token, sync_backend=sync_backend
        )

    def _validate_setup_conditions(self, github_repo, interactive, yes, token):
        """Validate prerequisites for GitHub integration setup.

        Returns:
            True if setup should proceed, False if user wants to skip
        """
        if GitHubClient is None or CredentialManager is None:
            raise ImportError("GitHub integration dependencies not available")

        if interactive and not yes:
            if not show_github_setup_instructions(github_repo, yes):
                return False

        return True

    def _resolve_and_test_token(self, token, interactive, yes):
        """Resolve token and test GitHub connection."""
        cred_manager = CredentialManager()  # type: ignore[call-arg]
        token_resolver = GitHubTokenResolver(cred_manager)

        existing_token = token_resolver.get_existing_token()
        use_token, should_continue = token_resolver.resolve_token(
            token, interactive, yes, existing_token
        )

        if not should_continue or not use_token:
            return None

        if self.presenter:
            self.presenter.present_github_testing()
        else:
            console.print("🧪 Testing GitHub connection...", style="cyan")

        return use_token

    def _validate_github_access(self, use_token, github_repo, interactive, yes):
        """Validate authentication and repository access."""
        github_client = GitHubClient(use_token)  # type: ignore[call-arg]
        validator = GitHubSetupValidator(github_client)

        auth_success, _ = validator.validate_authentication()
        if not auth_success:
            if interactive and not yes:
                if not click.confirm(
                    "Continue without GitHub integration? (recommended to skip until token is fixed)"
                ):
                    return False
            return False

        repo_success, _ = validator.validate_repository_access(github_repo)
        if not repo_success:
            if interactive and not yes:
                if not click.confirm("Continue with GitHub integration anyway?"):
                    return False

        return True

    def _store_credentials_and_config(
        self,
        use_token: str,
        existing_token: str | None,
        github_repo: str,
        sync_backend: SyncBackend = SyncBackend.GITHUB,
    ) -> None:
        """Store credentials and save configuration.

        Args:
            use_token: Token to store
            existing_token: Previously stored token
            github_repo: GitHub repository (owner/repo)
            sync_backend: Backend to use (SyncBackend.GITHUB or SyncBackend.GIT)
        """
        if use_token != existing_token:
            cred_manager = CredentialManager()  # type: ignore[call-arg]
            cred_manager.store_token(use_token)
            if self.presenter:
                self.presenter.present_github_credentials_stored()
            else:
                console.print("✅ GitHub credentials stored", style="green")

        config_manager = GitHubConfigManager(self.core)
        # Always pass sync_backend explicitly for consistency and clarity
        config_manager.save_github_config(github_repo, sync_backend=sync_backend)

    def _configure_integration(
        self,
        github_repo: str,
        interactive: bool,
        yes: bool = False,
        token: str | None = None,
        sync_backend: SyncBackend = SyncBackend.GITHUB,
    ) -> bool:
        """Set up GitHub integration with credential flow.

        Args:
            github_repo: GitHub repository (owner/repo)
            interactive: If True, prompt user for input
            yes: If True, answer yes to all prompts
            token: GitHub personal access token
            sync_backend: Backend to use (SyncBackend.GITHUB or SyncBackend.GIT)

        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Validate setup conditions - this will prompt user if they want to proceed
            setup_result = self._validate_setup_conditions(
                github_repo, interactive, yes, token
            )
            if not setup_result:
                return False

            # Resolve and test token
            use_token = self._resolve_and_test_token(token, interactive, yes)
            if use_token is None:
                return False

            # Validate GitHub access
            if not self._validate_github_access(
                use_token, github_repo, interactive, yes
            ):
                return False

            # Store credentials and config
            cred_manager = CredentialManager()  # type: ignore[call-arg]
            existing_token = GitHubTokenResolver(cred_manager).get_existing_token()
            self._store_credentials_and_config(
                use_token, existing_token, github_repo, sync_backend=sync_backend
            )

            return True

        except ImportError:
            if self.presenter:
                self.presenter.present_github_unavailable("Dependencies not installed")
            else:
                console.print("⚠️  GitHub dependencies not installed", style="yellow")
            return False
        except Exception as e:
            if self.presenter:
                self.presenter.present_github_setup_failed(str(e))
            else:
                console.print(f"❌ GitHub setup failed: {e}", style="red")
            return False
