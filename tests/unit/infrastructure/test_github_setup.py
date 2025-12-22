"""Tests for GitHub integration setup workflow."""

from unittest.mock import MagicMock, patch

from roadmap.infrastructure.github.setup import GitHubTokenResolver


class TestGitHubTokenResolver:
    """Test GitHub token resolution."""

    def test_init_without_cred_manager(self):
        """Test initialization without credential manager."""
        resolver = GitHubTokenResolver()
        assert resolver.cred_manager is None

    def test_init_with_cred_manager(self):
        """Test initialization with credential manager."""
        cred_manager = MagicMock()
        resolver = GitHubTokenResolver(cred_manager)
        assert resolver.cred_manager == cred_manager

    def test_get_existing_token_no_manager(self):
        """Test getting token when no credential manager."""
        resolver = GitHubTokenResolver()
        token = resolver.get_existing_token()
        assert token is None

    def test_get_existing_token_success(self):
        """Test successfully getting existing token."""
        cred_manager = MagicMock()
        cred_manager.get_token.return_value = "ghp_existing_token"
        resolver = GitHubTokenResolver(cred_manager)
        token = resolver.get_existing_token()
        assert token == "ghp_existing_token"

    def test_get_existing_token_exception(self):
        """Test handling exception when getting token."""
        cred_manager = MagicMock()
        cred_manager.get_token.side_effect = Exception("Token not found")
        resolver = GitHubTokenResolver(cred_manager)
        token = resolver.get_existing_token()
        assert token is None

    def test_resolve_token_cli_provided(self):
        """Test resolving token when CLI token is provided."""
        resolver = GitHubTokenResolver()
        result = resolver.resolve_token(
            cli_token="ghp_cli_token",
            interactive=False,
            yes=False,
            existing_token=None,
        )
        # Should return a tuple or handle appropriately
        assert result is not None

    def test_resolve_token_use_existing(self):
        """Test resolving token when using existing token."""
        resolver = GitHubTokenResolver()
        result = resolver.resolve_token(
            cli_token=None,
            interactive=False,
            yes=True,
            existing_token="ghp_existing_token",
        )
        # Should handle correctly
        assert result is not None

    def test_resolve_token_none(self):
        """Test resolving token when none available."""
        resolver = GitHubTokenResolver()
        result = resolver.resolve_token(
            cli_token=None, interactive=False, yes=False, existing_token=None
        )
        # Should handle correctly
        assert result is not None


class TestGitHubSetupValidation:
    """Test GitHub setup validation functionality."""

    def test_token_resolver_multiple_calls(self):
        """Test using resolver multiple times."""
        resolver = GitHubTokenResolver()
        token1 = resolver.get_existing_token()
        token2 = resolver.get_existing_token()
        assert token1 is None and token2 is None

    def test_token_resolver_with_failing_manager(self):
        """Test resolver with credential manager that keeps failing."""
        cred_manager = MagicMock()
        cred_manager.get_token.side_effect = Exception("Network error")
        resolver = GitHubTokenResolver(cred_manager)

        # Multiple calls should handle errors gracefully
        token1 = resolver.get_existing_token()
        token2 = resolver.get_existing_token()
        assert token1 is None
        assert token2 is None

    def test_resolve_token_various_scenarios(self):
        """Test resolving tokens in various scenarios."""
        resolver = GitHubTokenResolver()

        # Scenario 1: CLI token provided
        result1 = resolver.resolve_token(
            cli_token="token1", interactive=False, yes=False, existing_token=None
        )
        assert result1 is not None

        # Scenario 2: Interactive mode (with mocked prompt)
        with patch("click.prompt", return_value="ghp_prompted_token"):
            result2 = resolver.resolve_token(
                cli_token=None, interactive=True, yes=False, existing_token=None
            )
            assert result2 is not None

        # Scenario 3: Yes flag
        result3 = resolver.resolve_token(
            cli_token=None, interactive=False, yes=True, existing_token="existing"
        )
        assert result3 is not None
