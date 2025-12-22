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
        token, should_continue = resolver.resolve_token(
            cli_token="ghp_cli_token",
            interactive=False,
            yes=False,
            existing_token=None,
        )
        assert token == "ghp_cli_token"
        assert should_continue is True

    def test_resolve_token_env_variable(self):
        """Test resolving token from environment variable."""
        resolver = GitHubTokenResolver()
        with patch.dict(os.environ, {"ROADMAP_GITHUB_TOKEN": "ghp_env_token"}):
            token, should_continue = resolver.resolve_token(
                cli_token=None,
                interactive=False,
                yes=False,
                existing_token=None,
            )
            assert token == "ghp_env_token"
            assert should_continue is True

    def test_resolve_token_existing_with_yes(self):
        """Test resolving token when using existing token with yes flag."""
        resolver = GitHubTokenResolver()
        token, should_continue = resolver.resolve_token(
            cli_token=None,
            interactive=False,
            yes=True,
            existing_token="ghp_existing_token",
        )
        assert token == "ghp_existing_token"
        assert should_continue is True

    def test_resolve_token_existing_with_confirm(self):
        """Test resolving token when user confirms existing token."""
        resolver = GitHubTokenResolver()
        with patch("click.confirm", return_value=True):
            token, should_continue = resolver.resolve_token(
                cli_token=None,
                interactive=True,
                yes=False,
                existing_token="ghp_existing_token",
            )
            assert token == "ghp_existing_token"
            assert should_continue is True

    def test_resolve_token_existing_with_reject(self):
        """Test resolving token when user rejects existing token."""
        resolver = GitHubTokenResolver()
        with patch("click.confirm", return_value=False):
            with patch("click.prompt", return_value="ghp_new_token"):
                token, should_continue = resolver.resolve_token(
                    cli_token=None,
                    interactive=True,
                    yes=False,
                    existing_token="ghp_existing_token",
                )
                assert token == "ghp_new_token"
                assert should_continue is True

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
            assert should_continue is True

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
        assert should_continue is False

    def test_resolve_token_priority_cli_over_env(self):
        """Test that CLI token takes priority over environment."""
        resolver = GitHubTokenResolver()
        with patch.dict(os.environ, {"ROADMAP_GITHUB_TOKEN": "ghp_env_token"}):
            token, should_continue = resolver.resolve_token(
                cli_token="ghp_cli_token",
                interactive=False,
                yes=False,
                existing_token=None,
            )
            assert token == "ghp_cli_token"

    def test_resolve_token_priority_env_over_existing(self):
        """Test that environment token takes priority over existing."""
        resolver = GitHubTokenResolver()
        with patch.dict(os.environ, {"ROADMAP_GITHUB_TOKEN": "ghp_env_token"}):
            token, should_continue = resolver.resolve_token(
                cli_token=None,
                interactive=False,
                yes=False,
                existing_token="ghp_existing_token",
            )
            assert token == "ghp_env_token"


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

    def test_validate_authentication_success(self, validator, mock_client):
        """Test successful authentication validation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"login": "testuser"}
        mock_client._make_request.return_value = mock_response

        success, username = validator.validate_authentication()

        assert success is True
        assert username == "testuser"
        mock_client._make_request.assert_called_once_with("GET", "/user")

    def test_validate_authentication_failure(self, validator, mock_client):
        """Test failed authentication validation."""
        mock_client._make_request.side_effect = Exception("Invalid token")

        success, error = validator.validate_authentication()

        assert success is False
        assert "Invalid token" in error

    def test_validate_repository_access_success(self, validator, mock_client):
        """Test successful repository access validation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "full_name": "user/repo",
            "permissions": {"admin": True},
        }
        mock_client._make_request.return_value = mock_response
        mock_client.test_repository_access.return_value = {
            "full_name": "user/repo",
            "permissions": {"admin": True},
        }

        success, repo_info = validator.validate_repository_access("user/repo")

        assert success is True
        assert repo_info["full_name"] == "user/repo"
        mock_client.set_repository.assert_called_once_with("user", "repo")

    def test_validate_repository_access_failure(self, validator, mock_client):
        """Test failed repository access validation."""
        mock_client.set_repository.side_effect = Exception("Invalid repository")

        success, error_info = validator.validate_repository_access("invalid/repo")

        assert success is False
        assert "error" in error_info

    def test_validate_repository_access_read_only(self, validator, mock_client):
        """Test repository with read-only access."""
        mock_client.test_repository_access.return_value = {
            "full_name": "user/repo",
            "permissions": {"pull": True},
        }

        success, repo_info = validator.validate_repository_access("user/repo")

        assert success is True
        assert repo_info["permissions"]["pull"] is True

    def test_test_api_access_success(self, validator, mock_client):
        """Test successful API access test."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "title": "Issue 1"}]
        mock_client._make_request.return_value = mock_response

        result = validator.test_api_access("user/repo")

        assert result is True
        mock_client._make_request.assert_called_once()

    def test_test_api_access_failure(self, validator, mock_client):
        """Test failed API access test."""
        mock_client._make_request.side_effect = Exception("API error")

        result = validator.test_api_access("user/repo")

        assert result is False


class TestGitHubConfigManager:
    """Test GitHub configuration management."""

    @pytest.fixture
    def mock_core(self, tmp_path):
        """Create mock RoadmapCore."""
        core = MagicMock()
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
        assert config["github"]["enabled"] is True
        assert config["github"]["sync_enabled"] is True
        assert config["github"]["sync_settings"]["bidirectional"] is True


class TestShowGitHubSetupInstructions:
    """Test setup instructions display."""

    def test_show_instructions_with_yes(self):
        """Test showing instructions when yes flag is set."""
        result = show_github_setup_instructions("owner/repo", yes=True)
        assert result is True

    def test_show_instructions_with_confirm(self):
        """Test showing instructions when user confirms."""
        with patch("click.confirm", return_value=True):
            result = show_github_setup_instructions("owner/repo", yes=False)
            assert result is True

    def test_show_instructions_with_reject(self):
        """Test showing instructions when user rejects."""
        with patch("click.confirm", return_value=False):
            result = show_github_setup_instructions("owner/repo", yes=False)
            assert result is False


class TestGitHubInitializationService:
    """Test GitHub initialization service orchestration."""

    @pytest.fixture
    def mock_core(self, tmp_path):
        """Create mock RoadmapCore."""
        core = MagicMock()
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
        assert result is False

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
        assert result is False

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
                assert result is False

    def test_configure_integration_exception(self, mock_core):
        """Test configuration handles exceptions."""
        service = GitHubInitializationService(mock_core)

        with patch.object(
            service, "_validate_setup_conditions", side_effect=Exception("Setup error")
        ):
            result = service._configure_integration("owner/repo", False, True, None)
            assert result is False


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
