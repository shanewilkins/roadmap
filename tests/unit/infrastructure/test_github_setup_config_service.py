"""Tests for GitHub integration setup workflow."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.constants import SyncBackend
from roadmap.common.initialization.github.setup_service import (
    GitHubConfigManager,
    GitHubInitializationService,
    GitHubTokenResolver,
    show_github_setup_instructions,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory


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
        manager.save_github_config("owner/repo", sync_backend=SyncBackend.GITHUB)

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

        manager.save_github_config("owner/repo", sync_backend=SyncBackend.GITHUB)

        # Verify both settings exist
        with open(manager.config_file) as f:
            content = f.read()
            assert "github" in content
            assert "other_setting" in content

    def test_save_github_config_structure(self, mock_core):
        """Test that saved config has correct structure."""
        import yaml

        manager = GitHubConfigManager(mock_core)
        manager.save_github_config("owner/repo", sync_backend=SyncBackend.GITHUB)

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

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient", None
        ):
            with patch(
                "roadmap.common.initialization.github.setup_service.CredentialManager",
                None,
            ):
                with pytest.raises(ImportError):
                    service._validate_setup_conditions("owner/repo", False, True, None)

    def test_resolve_and_test_token(self, mock_core):
        """Test token resolution and testing."""
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.common.initialization.github.setup_service.CredentialManager"
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
            "roadmap.common.initialization.github.setup_service.CredentialManager"
        ) as mock_cred_class:
            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubConfigManager"
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

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient", None
        ):
            with patch(
                "roadmap.common.initialization.github.setup_service.CredentialManager",
                None,
            ):
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
