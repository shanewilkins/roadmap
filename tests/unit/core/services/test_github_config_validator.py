"""Tests for GitHub configuration validator."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from roadmap.core.services.github.github_config_validator import GitHubConfigValidator


@pytest.fixture
def mock_config_path(tmp_path):
    """Create a mock config path."""
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    return roadmap_dir


@pytest.fixture
def mock_service():
    """Create a mock GitHub service."""
    return MagicMock()


@pytest.fixture
def validator(mock_config_path, mock_service):
    """Create a validator with mocked service."""
    with patch(
        "roadmap.core.services.github_config_validator.GitHubIntegrationService",
        return_value=mock_service,
    ):
        validator = GitHubConfigValidator(mock_config_path)
        validator.service = mock_service
        return validator


class TestGitHubConfigValidator:
    """Test GitHubConfigValidator class."""

    def test_init(self, mock_config_path, mock_service):
        """Test validator initialization."""
        with patch(
            "roadmap.core.services.github_config_validator.GitHubIntegrationService",
            return_value=mock_service,
        ):
            validator = GitHubConfigValidator(mock_config_path)
            assert validator.config_path == mock_config_path
            assert validator.config_file == mock_config_path / "config.yaml"

    def test_validate_config_no_token(self, validator, mock_service):
        """Test config validation with missing token."""
        mock_service.get_github_config.return_value = (None, "owner", "repo")
        is_valid, error = validator.validate_config()
        assert not is_valid
        assert "GitHub not configured" in error

    def test_validate_config_no_repo(self, validator, mock_service):
        """Test config validation with missing repo."""
        mock_service.get_github_config.return_value = ("token123", "owner", None)
        is_valid, error = validator.validate_config()
        assert not is_valid

    def test_validate_config_token_too_short(self, validator, mock_service):
        """Test config validation with token too short."""
        mock_service.get_github_config.return_value = ("short", "owner", "repo")
        is_valid, error = validator.validate_config()
        assert not is_valid
        assert "token appears invalid" in error

    def test_validate_config_valid(self, validator, mock_service):
        """Test config validation with valid config."""
        mock_service.get_github_config.return_value = (
            "ghp_validtoken123456",
            "owner",
            "owner/repo",
        )
        is_valid, error = validator.validate_config()
        assert is_valid
        assert error is None

    def test_validate_token_no_token(self, validator, mock_service):
        """Test token validation with no token."""
        mock_service.get_github_config.return_value = (None, "owner", "repo")
        is_valid, error = validator.validate_token()
        assert not is_valid
        assert "GitHub token not set" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_token_valid(self, mock_get, validator, mock_service):
        """Test token validation with valid token."""
        mock_service.get_github_config.return_value = (
            "ghp_validtoken123456",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_token()
        assert is_valid
        assert error is None
        mock_get.assert_called_once()

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_token_invalid(self, mock_get, validator, mock_service):
        """Test token validation with invalid token."""
        mock_service.get_github_config.return_value = (
            "ghp_invalidtoken",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_token()
        assert not is_valid
        assert "invalid or expired" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_token_insufficient_permissions(
        self, mock_get, validator, mock_service
    ):
        """Test token validation with insufficient permissions."""
        mock_service.get_github_config.return_value = (
            "ghp_token",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_token()
        assert not is_valid
        assert "insufficient permissions" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_token_api_error(self, mock_get, validator, mock_service):
        """Test token validation with API error."""
        mock_service.get_github_config.return_value = (
            "ghp_token",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_token()
        assert not is_valid
        assert "GitHub API error" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_token_network_error(self, mock_get, validator, mock_service):
        """Test token validation with network error."""
        mock_service.get_github_config.return_value = (
            "ghp_token",
            "owner",
            "owner/repo",
        )
        mock_get.side_effect = requests.RequestException("Connection failed")

        is_valid, error = validator.validate_token()
        assert not is_valid
        assert "Failed to reach GitHub" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_repo_access_incomplete_config(
        self, mock_get, validator, mock_service
    ):
        """Test repo validation with incomplete config."""
        mock_service.get_github_config.return_value = (None, "owner", None)
        is_valid, error = validator.validate_repo_access()
        assert not is_valid
        assert "incomplete" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_repo_access_valid(self, mock_get, validator, mock_service):
        """Test repo access validation with valid access."""
        mock_service.get_github_config.return_value = (
            "ghp_token",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_repo_access()
        assert is_valid
        assert error is None

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_repo_access_denied(self, mock_get, validator, mock_service):
        """Test repo access validation with access denied."""
        mock_service.get_github_config.return_value = (
            "ghp_token",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_repo_access()
        assert not is_valid
        assert "Access denied" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_repo_access_not_found(self, mock_get, validator, mock_service):
        """Test repo access validation with repo not found."""
        mock_service.get_github_config.return_value = (
            "ghp_token",
            "owner",
            "owner/nonexistent",
        )
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_repo_access()
        assert not is_valid
        assert "not found" in error

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_all_success(self, mock_get, validator, mock_service):
        """Test validate_all with all checks passing."""
        mock_service.get_github_config.return_value = (
            "ghp_validtoken123456",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_all()
        assert is_valid
        assert error is None
        # Should call requests 2 times (token and repo)
        assert mock_get.call_count == 2

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_all_fails_on_config(self, mock_get, validator, mock_service):
        """Test validate_all fails on config validation."""
        mock_service.get_github_config.return_value = (None, "owner", "repo")

        is_valid, error = validator.validate_all()
        assert not is_valid
        assert "GitHub not configured" in error
        # Should not call requests
        mock_get.assert_not_called()

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_all_fails_on_token(self, mock_get, validator, mock_service):
        """Test validate_all fails on token validation."""
        mock_service.get_github_config.return_value = (
            "ghp_validtoken123456",
            "owner",
            "owner/repo",
        )
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        is_valid, error = validator.validate_all()
        assert not is_valid
        assert "invalid or expired" in error
        # Should call requests 1 time (token check)
        assert mock_get.call_count == 1

    @patch("roadmap.core.services.github.github_config_validator.requests.get")
    def test_validate_all_fails_on_repo(self, mock_get, validator, mock_service):
        """Test validate_all fails on repo validation."""
        mock_service.get_github_config.return_value = (
            "ghp_validtoken123456",
            "owner",
            "owner/repo",
        )
        # First call succeeds (token), second fails (repo)
        success_response = Mock()
        success_response.status_code = 200
        fail_response = Mock()
        fail_response.status_code = 404
        mock_get.side_effect = [success_response, fail_response]

        is_valid, error = validator.validate_all()
        assert not is_valid
        assert "not found" in error
        # Should call requests 2 times
        assert mock_get.call_count == 2
