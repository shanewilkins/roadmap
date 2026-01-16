"""Extended coverage tests for GitHub setup module."""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from roadmap.common.constants import SyncBackend
from roadmap.common.initialization.github.setup_service import (
    GitHubConfigManager,
    GitHubInitializationService,
    show_github_setup_instructions,
)


class TestGitHubConfigManager:
    """Test GitHub configuration management."""

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
            assert "sync_backend: github" in content

    def test_save_github_config_existing_file(self, mock_core):
        """Test saving GitHub config to existing file."""
        manager = GitHubConfigManager(mock_core)

        # Create existing config
        existing_config = {"other_setting": "value"}
        with open(manager.config_file, "w") as f:
            yaml.dump(existing_config, f)

        # Save new config
        manager.save_github_config("owner/repo", sync_backend=SyncBackend.GITHUB)

        # Verify both settings exist
        with open(manager.config_file) as f:
            config = yaml.safe_load(f)
            assert isinstance(config, dict)
            assert config["other_setting"] == "value"
            assert isinstance(config["github"], dict)
            assert config["github"]["repository"] == "owner/repo"

    def test_save_github_config_with_git_backend(self, mock_core):
        """Test saving GitHub config with git backend."""
        manager = GitHubConfigManager(mock_core)

        manager.save_github_config("owner/repo", sync_backend=SyncBackend.GIT)

        with open(manager.config_file) as f:
            config = yaml.safe_load(f)
            assert isinstance(config, dict)
            assert isinstance(config["github"], dict)
            assert config["github"]["sync_backend"] == "git"

    def test_save_github_config_invalid_repo_format(self, mock_core):
        """Test saving config with invalid repository format raises error."""
        manager = GitHubConfigManager(mock_core)

        with pytest.raises(ValueError, match="Invalid GitHub repository format"):
            manager.save_github_config("invalid_repo", sync_backend=SyncBackend.GITHUB)

        # Verify file was not created
        assert not manager.config_file.exists()

    def test_save_github_config_empty_repo(self, mock_core):
        """Test saving config with empty repository raises error."""
        manager = GitHubConfigManager(mock_core)

        with pytest.raises(ValueError, match="Invalid GitHub repository format"):
            manager.save_github_config("", sync_backend=SyncBackend.GITHUB)

        assert not manager.config_file.exists()


class TestShowGitHubSetupInstructions:
    """Test setup instructions display."""

    def test_show_instructions_yes_mode(self):
        """Test showing instructions in --yes mode."""
        with patch("roadmap.common.initialization.github.setup_service.console"):
            result = show_github_setup_instructions("owner/repo", yes=True)
            assert result

    def test_show_instructions_with_confirm_yes(self):
        """Test showing instructions with user confirming."""
        with patch("roadmap.common.initialization.github.setup_service.console"):
            with patch(
                "roadmap.common.initialization.github.setup_service.click.confirm",
                return_value=True,
            ):
                result = show_github_setup_instructions("owner/repo", yes=False)
                assert result

    def test_show_instructions_with_confirm_no(self):
        """Test showing instructions with user declining."""
        with patch("roadmap.common.initialization.github.setup_service.console"):
            with patch(
                "roadmap.common.initialization.github.setup_service.click.confirm",
                return_value=False,
            ):
                result = show_github_setup_instructions("owner/repo", yes=False)
                assert not result


class TestGitHubInitializationServiceCoverage:
    """Test GitHub initialization service edge cases."""

    def test_validate_setup_conditions_missing_imports(self, mock_core):
        """Test when GitHub dependencies are not available.

        Covers line 269-270: ImportError handling
        """
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient", None
        ):
            with patch(
                "roadmap.common.initialization.github.setup_service.CredentialManager",
                None,
            ):
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

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient", None
        ):
            with patch(
                "roadmap.common.initialization.github.setup_service.CredentialManager",
                None,
            ):
                with patch(
                    "roadmap.common.initialization.github.setup_service.console"
                ):
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
            with patch("roadmap.common.initialization.github.setup_service.console"):
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
            "roadmap.common.initialization.github.setup_service.GitHubTokenResolver"
        ) as MockResolver:
            mock_resolver = MagicMock()
            MockResolver.return_value = mock_resolver
            mock_resolver.get_existing_token.return_value = None
            mock_resolver.resolve_token.return_value = (None, False)

            with patch(
                "roadmap.common.initialization.github.setup_service.CredentialManager"
            ):
                result = service._resolve_and_test_token(None, False, True)
                assert result is None

    def test_resolve_and_test_token_with_presenter(self, mock_core):
        """Test token resolution with presenter."""
        presenter = MagicMock()
        service = GitHubInitializationService(mock_core)
        service.presenter = presenter

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubTokenResolver"
        ) as MockResolver:
            mock_resolver = MagicMock()
            MockResolver.return_value = mock_resolver
            mock_resolver.get_existing_token.return_value = None
            mock_resolver.resolve_token.return_value = ("test_token", True)

            with patch(
                "roadmap.common.initialization.github.setup_service.CredentialManager"
            ):
                result = service._resolve_and_test_token("test_token", False, True)
                assert result == "test_token"
                presenter.present_github_testing.assert_called_once()

    def test_validate_github_access_auth_failure_interactive_continue(self, mock_core):
        """Test auth failure with user choosing to continue.

        Covers lines 302-305: Interactive confirm on auth failure
        """
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient"
        ) as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (False, {})

                with patch(
                    "roadmap.common.initialization.github.setup_service.click.confirm",
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

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient"
        ) as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (False, {})

                with patch(
                    "roadmap.common.initialization.github.setup_service.click.confirm",
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

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient"
        ) as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubSetupValidator"
            ) as MockValidator:
                mock_validator = MagicMock()
                MockValidator.return_value = mock_validator
                mock_validator.validate_authentication.return_value = (True, {})
                mock_validator.validate_repository_access.return_value = (False, {})

                with patch(
                    "roadmap.common.initialization.github.setup_service.click.confirm",
                    return_value=True,
                ):
                    result = service._validate_github_access(
                        "test_token", "owner/repo", interactive=True, yes=False
                    )
                    assert result

    def test_validate_github_access_success_path(self, mock_core):
        """Test successful GitHub access validation."""
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.common.initialization.github.setup_service.GitHubClient"
        ) as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubSetupValidator"
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
            "roadmap.common.initialization.github.setup_service.CredentialManager"
        ) as MockCredMgr:
            mock_cred_mgr = MagicMock()
            MockCredMgr.return_value = mock_cred_mgr

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubConfigManager"
            ) as MockConfigMgr:
                mock_config_mgr = MagicMock()
                MockConfigMgr.return_value = mock_config_mgr

                with patch(
                    "roadmap.common.initialization.github.setup_service.console"
                ):
                    service._store_credentials_and_config(
                        "new_token", "old_token", "owner/repo"
                    )

                    # Should store the new token
                    mock_cred_mgr.store_token.assert_called_once_with("new_token")
                    # Always pass sync_backend explicitly (defaults to GITHUB)
                    mock_config_mgr.save_github_config.assert_called_once_with(
                        "owner/repo", sync_backend=SyncBackend.GITHUB
                    )

    def test_store_credentials_same_token(self, mock_core):
        """Test when token hasn't changed."""
        service = GitHubInitializationService(mock_core)

        with patch(
            "roadmap.common.initialization.github.setup_service.CredentialManager"
        ) as MockCredMgr:
            mock_cred_mgr = MagicMock()
            MockCredMgr.return_value = mock_cred_mgr

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubConfigManager"
            ) as MockConfigMgr:
                mock_config_mgr = MagicMock()
                MockConfigMgr.return_value = mock_config_mgr

                with patch(
                    "roadmap.common.initialization.github.setup_service.console"
                ):
                    service._store_credentials_and_config(
                        "same_token", "same_token", "owner/repo"
                    )

                    # Should NOT store token again
                    mock_cred_mgr.store_token.assert_not_called()
                    # Always pass sync_backend explicitly (defaults to GITHUB)
                    mock_config_mgr.save_github_config.assert_called_once_with(
                        "owner/repo", sync_backend=SyncBackend.GITHUB
                    )

    def test_store_credentials_with_presenter(self, mock_core):
        """Test storing credentials with presenter."""
        presenter = MagicMock()
        service = GitHubInitializationService(mock_core)
        service.presenter = presenter

        with patch(
            "roadmap.common.initialization.github.setup_service.CredentialManager"
        ) as MockCredMgr:
            mock_cred_mgr = MagicMock()
            MockCredMgr.return_value = mock_cred_mgr

            with patch(
                "roadmap.common.initialization.github.setup_service.GitHubConfigManager"
            ) as MockConfigMgr:
                mock_config_mgr = MagicMock()
                MockConfigMgr.return_value = mock_config_mgr

                service._store_credentials_and_config(
                    "new_token", "old_token", "owner/repo"
                )

                # Should call presenter method
                presenter.present_github_credentials_stored.assert_called_once()


class TestSyncBackendValidation:
    """Test sync_backend enum validation in InitParams."""

    def test_init_params_valid_github_backend(self):
        """Test InitParams with valid github backend."""
        from roadmap.common.models import InitParams

        params = InitParams(name=".roadmap", sync_backend="github")
        assert params.sync_backend == "github"

    def test_init_params_valid_git_backend(self):
        """Test InitParams with valid git backend."""
        from roadmap.common.models import InitParams

        params = InitParams(name=".roadmap", sync_backend="git")
        assert params.sync_backend == "git"

    def test_init_params_invalid_backend_raises_error(self):
        """Test InitParams with invalid backend raises ValueError."""
        from roadmap.common.models import InitParams

        with pytest.raises(ValueError, match="Invalid sync_backend"):
            InitParams(name=".roadmap", sync_backend="invalid")

    def test_init_params_invalid_backend_lists_valid_options(self):
        """Test error message lists valid backend options."""
        from roadmap.common.models import InitParams

        with pytest.raises(ValueError) as exc_info:
            InitParams(name=".roadmap", sync_backend="invalid")

        error_message = str(exc_info.value)
        assert "git" in error_message or "github" in error_message

    def test_sync_backend_enum_values(self):
        """Test SyncBackend enum has correct values."""
        assert SyncBackend.GITHUB.value == "github"
        assert SyncBackend.GIT.value == "git"

    def test_sync_backend_enum_string_compatible(self):
        """Test SyncBackend enum is string-compatible."""
        backend = SyncBackend.GITHUB
        # Should be usable as string
        assert str(backend) == "SyncBackend.GITHUB"
        # But .value should give the actual string value
        assert backend.value == "github"
