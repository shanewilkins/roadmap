"""GitHub initialization service for setup workflow orchestration."""

import click
from structlog import get_logger

from roadmap.common.configuration.github.config_manager import GitHubConfigManager
from roadmap.common.configuration.github.token_resolver import GitHubTokenResolver
from roadmap.common.console import get_console
from roadmap.common.constants import SyncBackend
from roadmap.common.initialization.github.setup_validator import GitHubSetupValidator
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger()
console = get_console()

# Import GitHub modules for type hints (allow test patching)
try:
    from roadmap.adapters.github.github import GitHubClient
    from roadmap.infrastructure.security.credentials import CredentialManager
except ImportError:
    GitHubClient = None  # type: ignore
    CredentialManager = None  # type: ignore


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
