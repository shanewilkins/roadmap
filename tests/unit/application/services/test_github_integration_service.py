"""Tests for GitHubIntegrationService."""

from datetime import UTC
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.github_integration_service import (
    GitHubIntegrationService,
)


class TestGitHubIntegrationService:
    """Test suite for GitHubIntegrationService."""

    @pytest.fixture
    def root_path(self, tmp_path):
        """Create a temporary root path."""
        return tmp_path

    @pytest.fixture
    def config_file(self, root_path):
        """Create a mock config file path."""
        return root_path / "config.yaml"

    @pytest.fixture
    def service(self, root_path, config_file):
        """Create a service instance."""
        return GitHubIntegrationService(root_path=root_path, config_file=config_file)

    def test_init_creates_service(self, service, root_path, config_file):
        """Test that service initializes correctly."""
        assert service.root_path == root_path
        assert service.config_file == config_file
        assert service._team_members_cache is None
        assert service._cache_timestamp is None

    def test_get_github_config_not_configured(self, service):
        """Test get_github_config when GitHub is not configured."""
        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_config_cls:
            mock_config = Mock()
            mock_config.load.return_value = Mock(github=None)
            mock_config_cls.return_value = mock_config
            result = service.get_github_config()
            assert result == (None, None, None)

    def test_get_github_config_configured(self, service):
        """Test get_github_config when GitHub is configured."""
        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_config_cls:
            mock_config = Mock()
            mock_config.load.return_value = Mock(
                github={"owner": "test-owner", "repo": "test-repo"}
            )
            mock_config_cls.return_value = mock_config

            with patch(
                "roadmap.core.services.github_integration_service.get_credential_manager"
            ) as mock_cred:
                mock_cred.return_value.get_token.return_value = "test-token"
                token, owner, repo = service.get_github_config()
                assert token == "test-token"
                assert owner == "test-owner"
                assert repo == "test-repo"

    def test_get_github_config_from_env(self, service):
        """Test get_github_config retrieves token from environment."""
        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_config_cls:
            mock_config = Mock()
            mock_config.load.return_value = Mock(
                github={"owner": "test-owner", "repo": "test-repo"}
            )
            mock_config_cls.return_value = mock_config

            with patch(
                "roadmap.core.services.github_integration_service.get_credential_manager"
            ) as mock_cred:
                mock_cred.return_value.get_token.return_value = None
                with patch(
                    "roadmap.core.services.github_integration_service.os.getenv",
                    return_value="env-token",
                ):
                    token, owner, repo = service.get_github_config()
                    assert token == "env-token"

    def test_get_team_members_github_not_configured(self, service):
        """Test get_team_members when GitHub is not configured."""
        with patch.object(
            service, "get_github_config", return_value=(None, None, None)
        ):
            result = service.get_team_members()
            assert result == []

    @pytest.mark.parametrize(
        "config_return,side_effect,expected_result",
        [
            # Success case
            (("token", "owner", "repo"), None, ["user1", "user2"]),
            # Error case
            (None, Exception("API error"), []),
        ],
    )
    def test_get_team_members(
        self, service, config_return, side_effect, expected_result
    ):
        """Test get_team_members in various scenarios."""
        if side_effect:
            with patch.object(service, "get_github_config", side_effect=side_effect):
                result = service.get_team_members()
                assert result == expected_result
        else:
            with patch.object(service, "get_github_config", return_value=config_return):
                with patch(
                    "roadmap.core.services.github_integration_service.GitHubClient"
                ) as mock_client_cls:
                    mock_client = Mock()
                    mock_client.get_team_members.return_value = expected_result
                    mock_client_cls.return_value = mock_client
                    result = service.get_team_members()
                    assert result == expected_result

    @pytest.mark.parametrize(
        "user_configured,expected_result",
        [
            # User found case
            (True, "test-user"),
            # User not found case
            (False, None),
        ],
    )
    def test_get_current_user(
        self, service, config_file, user_configured, expected_result
    ):
        """Test get_current_user in various scenarios."""
        with patch(
            "roadmap.core.services.github_integration_service.ConfigManager"
        ) as mock_config_cls:
            mock_config = Mock()
            if user_configured:
                mock_user = Mock()
                mock_user.name = "test-user"
                mock_config.load.return_value = Mock(user=mock_user)
            else:
                mock_config.load.return_value = Mock(user=None)
            mock_config_cls.return_value = mock_config

            result = service.get_current_user()
            assert result == expected_result

    def test_get_cached_team_members_first_call(self, service):
        """Test get_cached_team_members caches on first call."""
        with patch.object(service, "get_team_members", return_value=["user1", "user2"]):
            result = service.get_cached_team_members()
            assert result == ["user1", "user2"]
            assert service._team_members_cache == ["user1", "user2"]

    def test_get_cached_team_members_uses_cache(self, service):
        """Test get_cached_team_members uses cache within 5 minutes."""
        from datetime import datetime

        service._team_members_cache = ["cached_user"]
        service._cache_timestamp = datetime.now(UTC)

        with patch.object(service, "get_team_members") as mock_get:
            result = service.get_cached_team_members()
            assert result == ["cached_user"]
            mock_get.assert_not_called()

    def test_validate_assignee_empty(self, service):
        """Test validate_assignee rejects empty assignee."""
        is_valid, error_msg = service.validate_assignee("")
        assert not is_valid
        assert "empty" in error_msg.lower()

    def test_validate_assignee_whitespace(self, service):
        """Test validate_assignee rejects whitespace-only assignee."""
        is_valid, error_msg = service.validate_assignee("   ")
        assert not is_valid

    def test_validate_assignee_github_not_configured(self, service):
        """Test validate_assignee allows any user when GitHub not configured."""
        with patch.object(
            service, "get_github_config", return_value=(None, None, None)
        ):
            is_valid, error_msg = service.validate_assignee("any-user")
            assert is_valid
            assert error_msg == ""

    def test_validate_assignee_in_cached_members(self, service):
        """Test validate_assignee succeeds for cached team member."""
        with patch.object(
            service, "get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch.object(
                service, "get_cached_team_members", return_value=["user1", "user2"]
            ):
                is_valid, error_msg = service.validate_assignee("user1")
                assert is_valid
                assert error_msg == ""

    @pytest.mark.parametrize(
        "validation_result,error_message,expected_valid,expected_in_error",
        [
            # Success case
            ((True, ""), "new-user", True, None),
            # Failure case
            ((False, "User not found"), "invalid-user", False, "not found"),
        ],
    )
    def test_validate_assignee_github_validation(
        self,
        service,
        validation_result,
        error_message,
        expected_valid,
        expected_in_error,
    ):
        """Test validate_assignee with GitHub validation in various scenarios."""
        with patch.object(
            service, "get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch.object(service, "get_cached_team_members", return_value=[]):
                with patch(
                    "roadmap.infrastructure.github_validator.GitHubClient"
                ) as mock_client:
                    mock_client.return_value.validate_assignee.return_value = (
                        validation_result
                    )
                    is_valid, error_msg = service.validate_assignee(error_message)
                    assert is_valid == expected_valid
                    if expected_in_error:
                        assert expected_in_error in error_msg.lower()

    def test_validate_assignee_with_strategy(self, service):
        """Test validate_assignee uses strategy when available."""
        with patch(
            "roadmap.core.services.assignee_validation_service.AssigneeValidationStrategy"
        ) as mock_strategy:
            mock_strategy.return_value.validate.return_value = (
                True,
                "",
                "canonical-id",
            )
            is_valid, error_msg = service.validate_assignee("user")
            assert is_valid
            assert service._last_canonical_assignee == "canonical-id"

    def test_get_last_canonical_assignee(self, service):
        """Test get_last_canonical_assignee returns stored value."""
        service._last_canonical_assignee = "test-canonical"
        result = service.get_last_canonical_assignee()
        assert result == "test-canonical"

    def test_clear_cache(self, service):
        """Test clear_cache resets cache."""
        from datetime import datetime

        service._team_members_cache = ["user1"]
        service._cache_timestamp = datetime.now(UTC)

        service.clear_cache()
        assert service._team_members_cache is None
        assert service._cache_timestamp is None

    def test_service_integration_workflow(self, service):
        """Test basic service workflow."""
        with patch.object(
            service, "get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch.object(
                service, "get_cached_team_members", return_value=["user1"]
            ):
                # Validate user
                is_valid, _ = service.validate_assignee("user1")
                assert is_valid

                # Get canonical form
                canonical = service.get_canonical_assignee("user1")
                assert canonical == "user1"
