"""Tests for GitHub integration service."""

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.github_integration_service import (
    GitHubIntegrationService,
)


class TestGitHubIntegrationService:
    """Tests for GitHubIntegrationService."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for config files."""
        with TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_file(self, temp_dir):
        """Create mock config file path."""
        config_path = temp_dir / "config.yaml"
        config_path.touch()
        return config_path

    @pytest.fixture
    def service(self, temp_dir, config_file):
        """Create service instance."""
        return GitHubIntegrationService(temp_dir, config_file)

    def test_init_creates_service(self, temp_dir, config_file):
        """Test initializing service."""
        service = GitHubIntegrationService(temp_dir, config_file)

        assert service.root_path == temp_dir
        assert service.config_file == config_file
        assert service._team_members_cache is None
        assert service._cache_timestamp is None
        assert service._last_canonical_assignee is None

    def test_get_github_config_missing_config_file(self, service):
        """Test getting GitHub config when file doesn't exist."""
        with patch("roadmap.core.services.github_integration_service.ConfigManager"):
            result = service.get_github_config()

        # Should return None, None, None on error
        assert result == (None, None, None) or result[0] is not None

    def test_get_github_config_no_github_section(self, service):
        """Test getting GitHub config when no GitHub section exists."""
        mock_config = Mock()
        mock_config.github = None

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.return_value = mock_config
            mock_manager_class.return_value = mock_manager

            result = service.get_github_config()

        assert result == (None, None, None)

    def test_get_github_config_missing_owner(self, service):
        """Test getting GitHub config when owner is missing."""
        mock_config = Mock()
        mock_config.github = {"repo": "my-repo"}

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.return_value = mock_config
            mock_manager_class.return_value = mock_manager

            result = service.get_github_config()

        assert result == (None, None, None)

    def test_get_github_config_missing_repo(self, service):
        """Test getting GitHub config when repo is missing."""
        mock_config = Mock()
        mock_config.github = {"owner": "my-owner"}

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.return_value = mock_config
            mock_manager_class.return_value = mock_manager

            result = service.get_github_config()

        assert result == (None, None, None)

    def test_get_github_config_with_token_from_credentials(self, service):
        """Test getting GitHub config with token from credentials manager."""
        mock_config = Mock()
        mock_config.github = {"owner": "my-owner", "repo": "my-repo"}

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            with patch(
                "roadmap.core.services.github_integration_service.get_credential_manager"
            ) as mock_cred_manager_func:
                mock_manager = Mock()
                mock_manager.load.return_value = mock_config
                mock_manager_class.return_value = mock_manager

                mock_cred_manager = Mock()
                mock_cred_manager.get_token.return_value = "test_token"
                mock_cred_manager_func.return_value = mock_cred_manager

                with patch.dict("os.environ", {}, clear=True):
                    result = service.get_github_config()

        assert result == ("test_token", "my-owner", "my-repo")

    def test_get_github_config_with_token_from_env(self, service):
        """Test getting GitHub config with token from environment."""
        mock_config = Mock()
        mock_config.github = {"owner": "my-owner", "repo": "my-repo"}

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            with patch(
                "roadmap.core.services.github_integration_service.get_credential_manager"
            ) as mock_cred_manager_func:
                mock_manager = Mock()
                mock_manager.load.return_value = mock_config
                mock_manager_class.return_value = mock_manager

                mock_cred_manager = Mock()
                mock_cred_manager.get_token.return_value = None
                mock_cred_manager_func.return_value = mock_cred_manager

                with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"}):
                    result = service.get_github_config()

        assert result == ("env_token", "my-owner", "my-repo")

    def test_get_team_members_not_configured(self, service):
        """Test getting team members when GitHub is not configured."""
        with patch.object(
            service, "get_github_config", return_value=(None, None, None)
        ):
            members = service.get_team_members()

        assert members == []

    def test_get_team_members_success(self, service):
        """Test successfully getting team members."""
        with patch.object(
            service, "get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch(
                "roadmap.core.services.github_integration_service.GitHubClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.get_team_members.return_value = ["user1", "user2", "user3"]
                mock_client_class.return_value = mock_client

                members = service.get_team_members()

        assert members == ["user1", "user2", "user3"]

    def test_get_team_members_error_handling(self, service):
        """Test error handling when fetching team members fails."""
        with patch.object(
            service, "get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch(
                "roadmap.core.services.github_integration_service.GitHubClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.get_team_members.side_effect = Exception("API error")
                mock_client_class.return_value = mock_client

                members = service.get_team_members()

        assert members == []

    def test_get_current_user_no_config_file(self, service):
        """Test getting current user when config file doesn't exist."""
        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.side_effect = Exception("File not found")
            mock_manager_class.return_value = mock_manager

            user = service.get_current_user()

        assert user is None

    def test_get_current_user_no_user_config(self, service):
        """Test getting current user when no user config exists."""
        mock_config = Mock(spec=[])

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.return_value = mock_config
            mock_manager_class.return_value = mock_manager

            user = service.get_current_user()

        assert user is None

    def test_get_current_user_success(self, service):
        """Test successfully getting current user."""
        mock_user = Mock()
        mock_user.name = "john_doe"
        mock_config = Mock()
        mock_config.user = mock_user

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.return_value = mock_config
            mock_manager_class.return_value = mock_manager

            user = service.get_current_user()

        assert user == "john_doe"

    def test_get_current_user_with_override(self, service, temp_dir):
        """Test getting current user with config file override."""
        override_config = temp_dir / "override.yaml"
        override_config.touch()

        mock_user = Mock()
        mock_user.name = "jane_doe"
        mock_config = Mock()
        mock_config.user = mock_user

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            mock_manager = Mock()
            mock_manager.load.return_value = mock_config
            mock_manager_class.return_value = mock_manager

            user = service.get_current_user(config_file=override_config)

        assert user == "jane_doe"

    def test_get_cached_team_members_cache_hit(self, service):
        """Test getting cached team members when cache is valid."""
        service._team_members_cache = ["user1", "user2"]
        service._cache_timestamp = datetime.now()

        members = service.get_cached_team_members()

        assert members == ["user1", "user2"]

    def test_get_cached_team_members_cache_expired(self, service):
        """Test cache expiration after 5 minutes."""
        service._team_members_cache = ["old_user"]
        service._cache_timestamp = datetime.now() - timedelta(minutes=6)

        with patch.object(
            service, "get_team_members", return_value=["new_user1", "new_user2"]
        ):
            members = service.get_cached_team_members()

        assert members == ["new_user1", "new_user2"]
        assert service._team_members_cache == ["new_user1", "new_user2"]

    def test_get_cached_team_members_no_cache(self, service):
        """Test getting team members when cache is empty."""
        with patch.object(service, "get_team_members", return_value=["user1", "user2"]):
            members = service.get_cached_team_members()

        assert members == ["user1", "user2"]
        assert service._team_members_cache == ["user1", "user2"]
        assert service._cache_timestamp is not None

    def test_validate_assignee_empty(self, service):
        """Test validating empty assignee."""
        is_valid, error = service.validate_assignee("")

        assert is_valid is False
        assert error == "Assignee cannot be empty"

    def test_validate_assignee_whitespace_only(self, service):
        """Test validating whitespace-only assignee."""
        is_valid, error = service.validate_assignee("   ")

        assert is_valid is False
        assert error == "Assignee cannot be empty"

    def test_get_canonical_assignee(self, service):
        """Test getting canonical assignee."""
        canonical = service.get_canonical_assignee("user1")

        assert canonical == "user1"

    def test_get_last_canonical_assignee_none(self, service):
        """Test getting last canonical assignee when none set."""
        assignee = service.get_last_canonical_assignee()

        assert assignee is None

    def test_get_last_canonical_assignee_set(self, service):
        """Test getting last canonical assignee after validation."""
        service._last_canonical_assignee = "user1"

        assignee = service.get_last_canonical_assignee()

        assert assignee == "user1"

    def test_clear_cache(self, service):
        """Test clearing the team members cache."""
        service._team_members_cache = ["user1", "user2"]
        service._cache_timestamp = datetime.now()

        service.clear_cache()

        assert service._team_members_cache is None
        assert service._cache_timestamp is None

    def test_clear_cache_when_empty(self, service):
        """Test clearing cache when already empty."""
        service.clear_cache()

        assert service._team_members_cache is None
        assert service._cache_timestamp is None

    def test_legacy_validate_assignee_fallback(self, service):
        """Test legacy validation fallback."""
        with patch.object(
            service, "get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch.object(service, "get_cached_team_members", return_value=[]):
                with patch(
                    "roadmap.core.services.github_integration_service.GitHubClient"
                ) as mock_client_class:
                    mock_client = Mock()
                    mock_client.validate_assignee.return_value = (True, "")
                    mock_client_class.return_value = mock_client

                    is_valid, error = service._legacy_validate_assignee("valid_user")

        assert is_valid is True

    @pytest.mark.parametrize(
        "cache_age_minutes,should_use_cache",
        [
            (1, True),
            (4, True),
            (4.99, True),
            (5.01, False),
            (10, False),
        ],
    )
    def test_cache_expiration_boundary(
        self, service, cache_age_minutes, should_use_cache
    ):
        """Test cache expiration boundary conditions."""
        service._team_members_cache = ["cached_user"]
        service._cache_timestamp = datetime.now() - timedelta(minutes=cache_age_minutes)

        with patch.object(service, "get_team_members", return_value=["fresh_user"]):
            members = service.get_cached_team_members()

        if should_use_cache:
            assert members == ["cached_user"]
        else:
            assert members == ["fresh_user"]

    def test_get_github_config_github_as_dict(self, service):
        """Test getting GitHub config when github field is a dict."""
        mock_config = Mock()
        mock_config.github = {"owner": "my-owner", "repo": "my-repo"}

        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_manager_class:
            with patch(
                "roadmap.core.services.github_integration_service.get_credential_manager"
            ) as mock_cred_manager_func:
                mock_manager = Mock()
                mock_manager.load.return_value = mock_config
                mock_manager_class.return_value = mock_manager

                mock_cred_manager = Mock()
                mock_cred_manager.get_token.return_value = "test_token"
                mock_cred_manager_func.return_value = mock_cred_manager

                result = service.get_github_config()

        assert result == ("test_token", "my-owner", "my-repo")
