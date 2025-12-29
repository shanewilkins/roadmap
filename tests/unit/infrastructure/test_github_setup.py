"""Tests for GitHub integration setup workflow."""

import os
from unittest.mock import MagicMock, patch

import pytest

from roadmap.infrastructure.github.setup import (
    GitHubConfigManager,
    GitHubInitializationService,
    GitHubSetupValidator,
    GitHubTokenResolver,
    show_github_setup_instructions,
)
from tests.unit.domain.test_data_factory import TestDataFactory


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


class TestGitHubConfigManager:
    """Test GitHub configuration management."""

    @pytest.fixture
    def mock_core(self, tmp_path):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.roadmap_dir = tmp_path / ".roadmap"
        core.roadmap_dir.mkdir(exist_ok=True)
        return core

    def test_init(self, mock_core):
        """Test config manager initialization."""
        manager = GitHubConfigManager(mock_core)
        assert manager.core == mock_core
        assert manager.config_file == mock_core.roadmap_dir / "config.yaml"

    def test_save_github_config_new_file(self, mock_core):
        """Test saving GitHub config to new file."""
        manager = GitHubConfigManager(mock_core)
        manager.save_github_config("owner/repo")

        assert manager.config_file.exists()
        # Verify file contains github config
        with open(manager.config_file) as f:
            content = f.read()
            assert "github" in content
            assert "owner/repo" in content

    def test_save_github_config_existing_file(self, mock_core):
        """Test saving GitHub config to existing file."""
        manager = GitHubConfigManager(mock_core)

        # Create existing config
        with open(manager.config_file, "w") as f:
            f.write("other_setting: value\n")

        manager.save_github_config("owner/repo")

        # Verify both settings exist
        with open(manager.config_file) as f:
            content = f.read()
            assert "github" in content
            assert "other_setting" in content

    def test_save_github_config_structure(self, mock_core):
        """Test that saved config has correct structure."""
        import yaml

        manager = GitHubConfigManager(mock_core)
        manager.save_github_config("owner/repo")

        with open(manager.config_file) as f:
            config = yaml.safe_load(f)

        assert isinstance(config, dict)
        assert "github" in config
        assert config["github"]["repository"] == "owner/repo"
        assert config["github"]["enabled"]
        assert config["github"]["sync_enabled"]
        assert config["github"]["sync_settings"]["bidirectional"]


class TestShowGitHubSetupInstructions:
    """Test setup instructions display."""

    def test_show_instructions_with_yes(self):
        """Test showing instructions when yes flag is set."""
        result = show_github_setup_instructions("owner/repo", yes=True)
        assert result

    def test_show_instructions_with_confirm(self):
        """Test showing instructions when user confirms."""
        with patch("click.confirm", return_value=True):
            result = show_github_setup_instructions("owner/repo", yes=False)
            assert result

    def test_show_instructions_with_reject(self):
        """Test showing instructions when user rejects."""
        with patch("click.confirm", return_value=False):
            result = show_github_setup_instructions("owner/repo", yes=False)
            assert not result


class TestGitHubInitializationService:
    """Test GitHub initialization service orchestration."""

    @pytest.fixture
    def mock_core(self, tmp_path):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.roadmap_dir = tmp_path / ".roadmap"
        core.roadmap_dir.mkdir(exist_ok=True)
        return core

    def test_init(self, mock_core):
        """Test service initialization."""
        service = GitHubInitializationService(mock_core)
        assert service.core == mock_core
        assert service.presenter is None

    def test_setup_skip_github(self, mock_core):
        """Test setup when GitHub integration is skipped."""
        service = GitHubInitializationService(mock_core)
        result = service.setup(
            skip_github=True,
            github_repo="owner/repo",
            detected_info={},
            interactive=False,
            yes=True,
            github_token=None,
        )
        assert not result

    def test_setup_no_repo_name(self, mock_core):
        """Test setup when no repository name is provided."""
        service = GitHubInitializationService(mock_core)
        result = service.setup(
            skip_github=False,
            github_repo=None,
            detected_info={},
            interactive=False,
            yes=True,
            github_token=None,
        )
        assert not result

    def test_setup_with_presenter(self, mock_core):
        """Test setup with custom presenter."""
        service = GitHubInitializationService(mock_core)
        presenter = MagicMock()

        result = service.setup(
            skip_github=False,
            github_repo="owner/repo",
            detected_info={},
            interactive=False,
            yes=True,
            github_token=None,
            presenter=presenter,
        )
        # Should attempt to configure
        assert result is not None

    def test_validate_setup_conditions_missing_imports(self, mock_core):
        """Test validation fails when imports are missing."""
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient", None):
            with patch("roadmap.infrastructure.github.setup.CredentialManager", None):
                with pytest.raises(ImportError):
                    service._validate_setup_conditions("owner/repo", False, True, None)

    def test_resolve_and_test_token(self, mock_core):
        """Test token resolution and testing."""
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.infrastructure.github.setup.CredentialManager"
        ) as mock_cred_class:
            mock_cred = MagicMock()
            mock_cred.get_token.return_value = None
            mock_cred_class.return_value = mock_cred

            token = service._resolve_and_test_token("test_token", False, True)
            assert token == "test_token"

    def test_store_credentials_and_config(self, mock_core):
        """Test storing credentials and configuration."""
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.infrastructure.github.setup.CredentialManager"
        ) as mock_cred_class:
            with patch(
                "roadmap.infrastructure.github.setup.GitHubConfigManager"
            ) as mock_config_class:
                mock_cred = MagicMock()
                mock_cred_class.return_value = mock_cred
                mock_config = MagicMock()
                mock_config_class.return_value = mock_config

                service._store_credentials_and_config(
                    "new_token", "old_token", "owner/repo"
                )

                # Verify token was stored
                mock_cred.store_token.assert_called_once_with("new_token")
                # Verify config was saved
                mock_config.save_github_config.assert_called_once()

    def test_configure_integration_import_error(self, mock_core):
        """Test configuration handles import errors."""
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient", None):
            with patch("roadmap.infrastructure.github.setup.CredentialManager", None):
                result = service._configure_integration("owner/repo", False, True, None)
                assert not result

    def test_configure_integration_exception(self, mock_core):
        """Test configuration handles exceptions."""
        service = GitHubInitializationService(mock_core)

        with patch.object(
            service, "_validate_setup_conditions", side_effect=Exception("Setup error")
        ):
            result = service._configure_integration("owner/repo", False, True, None)
            assert not result


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
