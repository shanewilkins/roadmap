"""Extended coverage tests for GitHub setup module."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from roadmap.infrastructure.github.setup import (
    GitHubConfigManager,
    GitHubInitializationService,
    show_github_setup_instructions,
)
from tests.unit.domain.test_data_factory import TestDataFactory


class TestGitHubConfigManager:
    """Test GitHub configuration management."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.roadmap_dir = Path("/test/roadmap")
        return core

    def test_save_github_config_new_file(self, mock_core):
        """Test saving GitHub config to new file."""
        mock_core.roadmap_dir = Path("/test/roadmap")

        manager = GitHubConfigManager(mock_core)

        # Mock the config file
        with patch("builtins.open", mock_open()) as m_open:
            with patch("pathlib.Path.exists", return_value=False):
                with patch("roadmap.infrastructure.github.setup.console"):
                    manager.save_github_config("owner/repo")

        # Verify file was opened for writing
        m_open.assert_called()

    def test_save_github_config_existing_file(self, mock_core):
        """Test saving GitHub config to existing file."""
        mock_core.roadmap_dir = Path("/test/roadmap")

        existing_config = {"other_setting": "value"}

        manager = GitHubConfigManager(mock_core)
        manager.config_file = MagicMock()
        manager.config_file.exists.return_value = True

        with patch("builtins.open", mock_open(read_data=yaml.dump(existing_config))):
            with patch("roadmap.infrastructure.github.setup.console"):
                with patch(
                    "roadmap.infrastructure.github.setup.yaml.safe_load",
                    return_value=existing_config,
                ):
                    with patch(
                        "roadmap.infrastructure.github.setup.yaml.dump"
                    ) as m_dump:
                        manager.save_github_config("owner/repo")

                        # Verify dump was called
                        m_dump.assert_called_once()
                        args = m_dump.call_args[0]
                        config = args[0]
                        assert "github" in config
                        assert config["github"]["repository"] == "owner/repo"


class TestShowGitHubSetupInstructions:
    """Test setup instructions display."""

    def test_show_instructions_yes_mode(self):
        """Test showing instructions in --yes mode."""
        with patch("roadmap.infrastructure.github.setup.console"):
            result = show_github_setup_instructions("owner/repo", yes=True)
            assert result

    def test_show_instructions_with_confirm_yes(self):
        """Test showing instructions with user confirming."""
        with patch("roadmap.infrastructure.github.setup.console"):
            with patch(
                "roadmap.infrastructure.github.setup.click.confirm", return_value=True
            ):
                result = show_github_setup_instructions("owner/repo", yes=False)
                assert result

    def test_show_instructions_with_confirm_no(self):
        """Test showing instructions with user declining."""
        with patch("roadmap.infrastructure.github.setup.console"):
            with patch(
                "roadmap.infrastructure.github.setup.click.confirm", return_value=False
            ):
                result = show_github_setup_instructions("owner/repo", yes=False)
                assert not result


class TestGitHubInitializationServiceCoverage:
    """Test GitHub initialization service edge cases."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.roadmap_dir = Path("/test/roadmap")
        return core

    def test_validate_setup_conditions_missing_imports(self, mock_core):
        """Test when GitHub dependencies are not available.

        Covers line 269-270: ImportError handling
        """
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient", None):
            with patch("roadmap.infrastructure.github.setup.CredentialManager", None):
                with pytest.raises(ImportError):
                    service._validate_setup_conditions(
                        "owner/repo", interactive=False, yes=True, token=None
                    )

    def test_configure_integration_import_error(self, mock_core):
        """Test configure integration when imports fail.

        Covers lines 357-361: ImportError in configure
        """
        service = GitHubInitializationService(mock_core)
        service.presenter = None

        with patch("roadmap.infrastructure.github.setup.GitHubClient", None):
            with patch("roadmap.infrastructure.github.setup.CredentialManager", None):
                with patch("roadmap.infrastructure.github.setup.console"):
                    result = service._configure_integration(
                        "owner/repo", interactive=False, yes=True, token=None
                    )
                    # Should return False due to import error
                    assert not result

    def test_configure_integration_general_exception(self, mock_core):
        """Test configure integration with general exception.

        Covers lines 365-371: General exception handling
        """
        service = GitHubInitializationService(mock_core)
        service.presenter = None

        with patch.object(
            service, "_validate_setup_conditions", side_effect=Exception("Test error")
        ):
            with patch("roadmap.infrastructure.github.setup.console"):
                result = service._configure_integration(
                    "owner/repo", interactive=False, yes=True, token=None
                )
                # Should return False due to exception
                assert not result

    def test_resolve_and_test_token_no_token(self, mock_core):
        """Test when token resolution returns no token.

        Covers lines 285: Early return when no token
        """
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.infrastructure.github.setup.GitHubTokenResolver"
        ) as MockResolver:
            mock_resolver = MagicMock()
            MockResolver.return_value = mock_resolver
            mock_resolver.get_existing_token.return_value = None
            mock_resolver.resolve_token.return_value = (None, False)

            with patch("roadmap.infrastructure.github.setup.CredentialManager"):
                result = service._resolve_and_test_token(None, False, True)
                assert result is None

    def test_resolve_and_test_token_with_presenter(self, mock_core):
        """Test token resolution with presenter."""
        presenter = MagicMock()
        service = GitHubInitializationService(mock_core)
        service.presenter = presenter

        with patch(
            "roadmap.infrastructure.github.setup.GitHubTokenResolver"
        ) as MockResolver:
            mock_resolver = MagicMock()
            MockResolver.return_value = mock_resolver
            mock_resolver.get_existing_token.return_value = None
            mock_resolver.resolve_token.return_value = ("test_token", True)

            with patch("roadmap.infrastructure.github.setup.CredentialManager"):
                result = service._resolve_and_test_token("test_token", False, True)
                assert result == "test_token"
                presenter.present_github_testing.assert_called_once()

    def test_validate_github_access_auth_failure_interactive_continue(self, mock_core):
        """Test auth failure with user choosing to continue.

        Covers lines 302-305: Interactive confirm on auth failure
        """
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.infrastructure.github.setup.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (False, {})

                with patch(
                    "roadmap.infrastructure.github.setup.click.confirm",
                    return_value=True,
                ):
                    result = service._validate_github_access(
                        "test_token", "owner/repo", interactive=True, yes=False
                    )
                    assert not result

    def test_validate_github_access_auth_failure_interactive_cancel(self, mock_core):
        """Test auth failure with user choosing to cancel.

        Covers lines 308-314: Interactive cancel on auth failure
        """
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.infrastructure.github.setup.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (False, {})

                with patch(
                    "roadmap.infrastructure.github.setup.click.confirm",
                    return_value=False,
                ):
                    result = service._validate_github_access(
                        "test_token", "owner/repo", interactive=True, yes=False
                    )
                    assert not result

    def test_validate_github_access_repo_failure_interactive_continue(self, mock_core):
        """Test repo access failure with user choosing to continue.

        Covers lines 322: Repo failure confirm
        """
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.infrastructure.github.setup.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (True, {})
                mock_validator.validate_repository_access.return_value = (False, {})

                with patch(
                    "roadmap.infrastructure.github.setup.click.confirm",
                    return_value=True,
                ):
                    result = service._validate_github_access(
                        "test_token", "owner/repo", interactive=True, yes=False
                    )
                    assert result

    def test_validate_github_access_success_path(self, mock_core):
        """Test successful GitHub access validation."""
        service = GitHubInitializationService(mock_core)

        with patch("roadmap.infrastructure.github.setup.GitHubClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.infrastructure.github.setup.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (True, {})
                mock_validator.validate_repository_access.return_value = (True, {})

                result = service._validate_github_access(
                    "test_token", "owner/repo", interactive=False, yes=True
                )
                assert result

    def test_store_credentials_and_config_new_token(self, mock_core):
        """Test storing new credentials.

        Covers lines 343, 348: Store new token path
        """
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.infrastructure.github.setup.CredentialManager"
        ) as MockCredMgr:
            mock_cred_mgr = MagicMock()
            MockCredMgr.return_value = mock_cred_mgr

            with patch(
                "roadmap.infrastructure.github.setup.GitHubConfigManager"
            ) as MockConfigMgr:
                mock_config_mgr = MagicMock()
                MockConfigMgr.return_value = mock_config_mgr

                with patch("roadmap.infrastructure.github.setup.console"):
                    service._store_credentials_and_config(
                        "new_token", "old_token", "owner/repo"
                    )

                    # Should store the new token
                    mock_cred_mgr.store_token.assert_called_once_with("new_token")
                    # Should save config
                    mock_config_mgr.save_github_config.assert_called_once_with(
                        "owner/repo"
                    )

    def test_store_credentials_same_token(self, mock_core):
        """Test when token hasn't changed."""
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.infrastructure.github.setup.CredentialManager"
        ) as MockCredMgr:
            mock_cred_mgr = MagicMock()
            MockCredMgr.return_value = mock_cred_mgr

            with patch(
                "roadmap.infrastructure.github.setup.GitHubConfigManager"
            ) as MockConfigMgr:
                mock_config_mgr = MagicMock()
                MockConfigMgr.return_value = mock_config_mgr

                with patch("roadmap.infrastructure.github.setup.console"):
                    service._store_credentials_and_config(
                        "same_token", "same_token", "owner/repo"
                    )

                    # Should NOT store token again
                    mock_cred_mgr.store_token.assert_not_called()
                    # Should still save config
                    mock_config_mgr.save_github_config.assert_called_once_with(
                        "owner/repo"
                    )

    def test_store_credentials_with_presenter(self, mock_core):
        """Test storing credentials with presenter."""
        presenter = MagicMock()
        service = GitHubInitializationService(mock_core)
        service.presenter = presenter

        with patch(
            "roadmap.infrastructure.github.setup.CredentialManager"
        ) as MockCredMgr:
            mock_cred_mgr = MagicMock()
            MockCredMgr.return_value = mock_cred_mgr

            with patch(
                "roadmap.infrastructure.github.setup.GitHubConfigManager"
            ) as MockConfigMgr:
                mock_config_mgr = MagicMock()
                MockConfigMgr.return_value = mock_config_mgr

                service._store_credentials_and_config(
                    "new_token", "old_token", "owner/repo"
                )

                # Should call presenter method
                presenter.present_github_credentials_stored.assert_called_once()
