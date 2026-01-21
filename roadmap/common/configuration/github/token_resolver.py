"""GitHub token resolution and management utilities."""

import os

import click

from roadmap.common.console import get_console

console = get_console()


class GitHubTokenResolver:
    """Resolves GitHub tokens from multiple sources."""

    def __init__(self, cred_manager=None):  # type: ignore
        """Initialize GitHubTokenResolver.

        Args:
            cred_manager: Optional credential manager instance.
        """
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
