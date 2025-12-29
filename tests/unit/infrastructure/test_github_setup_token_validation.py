"""Tests for GitHub integration setup workflow."""

import os
from unittest.mock import MagicMock, patch

import pytest

from roadmap.infrastructure.github.setup import (
    GitHubSetupValidator,
    GitHubTokenResolver,
)


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

    @pytest.mark.parametrize(
        "cli_token,env_dict,existing_token,interactive,yes,expected_token",
        [
            ("ghp_cli_token", {}, None, False, False, "ghp_cli_token"),
            (
                None,
                {"ROADMAP_GITHUB_TOKEN": "ghp_env_token"},
                None,
                False,
                False,
                "ghp_env_token",
            ),
            (None, {}, "ghp_existing_token", False, True, "ghp_existing_token"),
        ],
    )
    def test_resolve_token_sources(
        self, cli_token, env_dict, existing_token, interactive, yes, expected_token
    ):
        """Test resolving token from various sources with priority."""
        resolver = GitHubTokenResolver()
        with patch.dict(os.environ, env_dict, clear=False):
            token, should_continue = resolver.resolve_token(
                cli_token=cli_token,
                interactive=interactive,
                yes=yes,
                existing_token=existing_token,
            )
            assert token == expected_token
            assert should_continue

    def test_resolve_token_interactive_prompt(self):
        """Test resolving token via interactive prompt."""
        resolver = GitHubTokenResolver()
        with patch("click.prompt", return_value="ghp_prompted_token"):
            token, should_continue = resolver.resolve_token(
                cli_token=None,
                interactive=True,
                yes=False,
                existing_token=None,
            )
            assert token == "ghp_prompted_token"
            assert should_continue

    @pytest.mark.parametrize(
        "user_confirms,existing_token,expected_token",
        [
            (True, "ghp_existing_token", "ghp_existing_token"),
            (False, "ghp_existing_token", "ghp_new_token"),
        ],
    )
    def test_resolve_token_existing_with_user_action(
        self, user_confirms, existing_token, expected_token
    ):
        """Test resolving token when user confirms or rejects existing token."""
        resolver = GitHubTokenResolver()
        with patch("click.confirm", return_value=user_confirms):
            with patch("click.prompt", return_value="ghp_new_token"):
                token, should_continue = resolver.resolve_token(
                    cli_token=None,
                    interactive=True,
                    yes=False,
                    existing_token=existing_token,
                )
                assert token == expected_token
                assert should_continue

    def test_resolve_token_non_interactive_no_token(self):
        """Test resolving token in non-interactive mode without token."""
        resolver = GitHubTokenResolver()
        token, should_continue = resolver.resolve_token(
            cli_token=None,
            interactive=False,
            yes=False,
            existing_token=None,
        )
        assert token is None
        assert not should_continue

    @pytest.mark.parametrize(
        "cli_token,env_dict,expected_priority",
        [
            (
                "ghp_cli_token",
                {"ROADMAP_GITHUB_TOKEN": "ghp_env_token"},
                "ghp_cli_token",
            ),
            (None, {"ROADMAP_GITHUB_TOKEN": "ghp_env_token"}, "ghp_env_token"),
        ],
    )
    def test_resolve_token_priority_order(self, cli_token, env_dict, expected_priority):
        """Test token resolution priority: CLI > Environment > Existing."""
        resolver = GitHubTokenResolver()
        with patch.dict(os.environ, env_dict, clear=False):
            token, should_continue = resolver.resolve_token(
                cli_token=cli_token,
                interactive=False,
                yes=False,
                existing_token="ghp_existing_token",
            )
            assert token == expected_priority


class TestGitHubSetupValidator:
    """Test GitHub setup validation functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock GitHub client."""
        return MagicMock()

    @pytest.fixture
    def validator(self, mock_client):
        """Create validator with mock client."""
        return GitHubSetupValidator(mock_client)

    def test_init(self, mock_client):
        """Test validator initialization."""
        validator = GitHubSetupValidator(mock_client)
        assert validator.client == mock_client

    @pytest.mark.parametrize(
        "mock_response_data,should_succeed,expected_result",
        [
            ({"login": "testuser"}, True, "testuser"),
            ({"login": "anotheruser"}, True, "anotheruser"),
        ],
    )
    def test_validate_authentication_success(
        self,
        validator,
        mock_client,
        mock_response_data,
        should_succeed,
        expected_result,
    ):
        """Test successful authentication validation with different usernames."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_client._make_request.return_value = mock_response

        success, result = validator.validate_authentication()

        assert success == should_succeed
        assert result == expected_result
        mock_client._make_request.assert_called_once_with("GET", "/user")

    @pytest.mark.parametrize(
        "error_message",
        [
            "Invalid token",
            "Unauthorized",
            "Token expired",
            "Rate limit exceeded",
        ],
    )
    def test_validate_authentication_failure(
        self, validator, mock_client, error_message
    ):
        """Test failed authentication validation with different error types."""
        mock_client._make_request.side_effect = Exception(error_message)

        success, error = validator.validate_authentication()

        assert not success
        assert error_message in error

    @pytest.mark.parametrize(
        "repo_path,permissions,should_succeed,has_error",
        [
            ("user/repo", {"admin": True}, True, False),
            ("owner/project", {"admin": False, "push": True}, True, False),
            ("org/tool", {"push": True, "pull": True}, True, False),
        ],
    )
    def test_validate_repository_access_success(
        self, validator, mock_client, repo_path, permissions, should_succeed, has_error
    ):
        """Test successful repository access validation with different permission levels."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "full_name": repo_path,
            "permissions": permissions,
        }
        mock_client._make_request.return_value = mock_response
        mock_client.test_repository_access.return_value = {
            "full_name": repo_path,
            "permissions": permissions,
        }

        success, repo_info = validator.validate_repository_access(repo_path)

        assert success == should_succeed
        assert repo_info["full_name"] == repo_path
        mock_client.set_repository.assert_called_once()

    @pytest.mark.parametrize(
        "repo_path,error_type",
        [
            ("invalid/repo", "Invalid repository"),
            ("user/nonexistent", "Repository not found"),
            ("", "Empty repository name"),
        ],
    )
    def test_validate_repository_access_failure(
        self, validator, mock_client, repo_path, error_type
    ):
        """Test failed repository access validation with different error scenarios."""
        mock_client.set_repository.side_effect = Exception(error_type)

        success, error_info = validator.validate_repository_access(repo_path)

        assert not success
        assert "error" in error_info

    @pytest.mark.parametrize(
        "permissions_dict",
        [
            {"pull": True},
            {"pull": True, "push": False},
            {"pull": True, "push": True, "admin": False},
        ],
    )
    def test_validate_repository_access_various_permissions(
        self, validator, mock_client, permissions_dict
    ):
        """Test repository with various permission levels."""
        mock_client.test_repository_access.return_value = {
            "full_name": "user/repo",
            "permissions": permissions_dict,
        }

        success, repo_info = validator.validate_repository_access("user/repo")

        assert success
        assert repo_info["permissions"] == permissions_dict

    def test_test_api_access_success(self, validator, mock_client):
        """Test successful API access test."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "title": "Issue 1"}]
        mock_client._make_request.return_value = mock_response

        result = validator.test_api_access("user/repo")

        assert result
        mock_client._make_request.assert_called_once()

    def test_test_api_access_failure(self, validator, mock_client):
        """Test failed API access test."""
        mock_client._make_request.side_effect = Exception("API error")

        result = validator.test_api_access("user/repo")

        assert not result
