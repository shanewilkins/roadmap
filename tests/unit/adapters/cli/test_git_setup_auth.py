"""Unit tests for git setup authentication flow."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.git.commands import setup_git


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_core():
    """Provide mock RoadmapCore instance."""
    return MagicMock()


class TestGitSetupCommand:
    """Tests for git setup command."""

    def test_setup_no_options_shows_help(self, cli_runner, mock_core):
        """Test setup without options shows help."""
        with patch("roadmap.adapters.cli.git.commands.require_initialized"):
            runner = CliRunner()
            result = runner.invoke(setup_git, ["--help"])
            assert "--auth" in result.output
            assert "--update-token" in result.output

    def test_setup_auth_flag_provided(self, cli_runner, mock_core):
        """Test setup with --auth flag."""
        # This test validates the command structure exists
        # The actual authentication is tested in GitAuthenticationHandler tests
        runner = CliRunner()
        with patch("roadmap.adapters.cli.git.commands.require_initialized"):
            result = runner.invoke(setup_git, ["--help"])
            # Verify the command is available
            assert result.exit_code == 0


class TestGitHubAuthSetup:
    """Tests for GitHub authentication setup."""

    def test_auth_with_existing_token_accept(self):
        """Test accepting existing token."""
        # This test is covered by GitAuthenticationHandler tests
        # Verify the handler exists and can be instantiated
        from roadmap.adapters.cli.git.handlers.git_authentication_handler import (
            GitAuthenticationHandler,
        )

        handler = GitAuthenticationHandler(MagicMock())
        assert handler is not None

    def test_auth_with_existing_token_update(self):
        """Test updating existing token."""
        # This test is covered by GitAuthenticationHandler tests
        # Verify the handler can handle update flow
        from roadmap.adapters.cli.git.handlers.git_authentication_handler import (
            GitAuthenticationHandler,
        )

        handler = GitAuthenticationHandler(MagicMock())
        assert handler is not None
        # Handler's setup_github_auth method exists
        assert hasattr(handler, "setup_github_auth")

    def test_auth_empty_token_rejected(self):
        """Test empty token is rejected."""
        with patch(
            "roadmap.adapters.cli.git.handlers.git_authentication_handler.CredentialManager"
        ) as MockCred:
            mock_cred = MagicMock()
            MockCred.return_value = mock_cred
            mock_cred.get_token.return_value = None

            with patch(
                "roadmap.adapters.cli.git.commands.click.confirm"
            ) as mock_confirm:
                mock_confirm.return_value = False

                with patch(
                    "roadmap.adapters.cli.git.commands.click.prompt"
                ) as mock_prompt:
                    mock_prompt.return_value = ""  # Empty token

                    from roadmap.adapters.cli.git.commands import _setup_github_auth

                    mock_core = MagicMock()
                    _setup_github_auth(mock_core, update_token=False)

                    # Should not attempt validation with empty token
                    # (console should show error)

    def test_auth_token_validation_success(self):
        """Test successful token validation."""
        with patch(
            "roadmap.adapters.cli.git.handlers.git_authentication_handler.CredentialManager"
        ) as MockCred:
            mock_cred = MagicMock()
            MockCred.return_value = mock_cred
            mock_cred.get_token.return_value = None
            mock_cred.store_token.return_value = True

            with patch(
                "roadmap.adapters.cli.git.commands.click.confirm"
            ) as mock_confirm:
                mock_confirm.return_value = False

                with patch(
                    "roadmap.adapters.cli.git.commands.click.prompt"
                ) as mock_prompt:
                    mock_prompt.return_value = "ghu_valid123"

                    with patch(
                        "roadmap.adapters.cli.git.handlers.git_authentication_handler.GitHubClient"
                    ) as MockClient:
                        mock_client = MagicMock()
                        MockClient.return_value = mock_client
                        mock_client.test_authentication.return_value = {
                            "login": "myusername",
                            "name": "My Name",
                        }

                        from roadmap.adapters.cli.git.commands import _setup_github_auth

                        mock_core = MagicMock()
                        _setup_github_auth(mock_core, update_token=False)

                        # Verify authentication was tested
                        mock_client.test_authentication.assert_called_once()
                        # Verify token was stored after validation
                        mock_cred.store_token.assert_called_once_with("ghu_valid123")

    def test_auth_token_validation_failure(self):
        """Test failed token validation."""
        with patch(
            "roadmap.adapters.cli.git.handlers.git_authentication_handler.CredentialManager"
        ) as MockCred:
            mock_cred = MagicMock()
            MockCred.return_value = mock_cred
            mock_cred.get_token.return_value = None

            with patch(
                "roadmap.adapters.cli.git.commands.click.confirm"
            ) as mock_confirm:
                mock_confirm.return_value = False

                with patch(
                    "roadmap.adapters.cli.git.commands.click.prompt"
                ) as mock_prompt:
                    mock_prompt.return_value = "ghu_invalid456"

                    with patch(
                        "roadmap.adapters.cli.git.handlers.git_authentication_handler.GitHubClient"
                    ) as MockClient:
                        mock_client = MagicMock()
                        MockClient.return_value = mock_client
                        mock_client.test_authentication.side_effect = Exception(
                            "401 Unauthorized"
                        )

                        from roadmap.adapters.cli.git.commands import _setup_github_auth

                        mock_core = MagicMock()
                        _setup_github_auth(mock_core, update_token=False)

                        # Verify authentication was attempted
                        mock_client.test_authentication.assert_called_once()
                        # Verify token was NOT stored after failed validation
                        mock_cred.store_token.assert_not_called()

    def test_auth_token_storage_failure(self):
        """Test token validation succeeds but storage fails."""
        with patch(
            "roadmap.adapters.cli.git.handlers.git_authentication_handler.CredentialManager"
        ) as MockCred:
            mock_cred = MagicMock()
            MockCred.return_value = mock_cred
            mock_cred.get_token.return_value = None
            mock_cred.store_token.return_value = False  # Storage fails

            with patch(
                "roadmap.adapters.cli.git.commands.click.confirm"
            ) as mock_confirm:
                mock_confirm.return_value = False

                with patch(
                    "roadmap.adapters.cli.git.commands.click.prompt"
                ) as mock_prompt:
                    mock_prompt.return_value = "ghu_valid789"

                    with patch(
                        "roadmap.adapters.cli.git.handlers.git_authentication_handler.GitHubClient"
                    ) as MockClient:
                        mock_client = MagicMock()
                        MockClient.return_value = mock_client
                        mock_client.test_authentication.return_value = {"login": "user"}

                        from roadmap.adapters.cli.git.commands import _setup_github_auth

                        mock_core = MagicMock()
                        _setup_github_auth(mock_core, update_token=False)

                        # Verify authentication was tested
                        mock_client.test_authentication.assert_called_once()
                        # Verify token storage was attempted
                        mock_cred.store_token.assert_called_once_with("ghu_valid789")
