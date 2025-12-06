"""Tests for GitHub API client."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from roadmap.adapters.github.github import GitHubAPIError, GitHubClient
from roadmap.core.domain import Priority, Status

pytestmark = pytest.mark.unit


class TestGitHubClient:
    """Test cases for GitHubClient."""

    @pytest.fixture
    def mock_session(self):
        """Mock requests session."""
        with patch(
            "roadmap.adapters.github.github.requests.Session"
        ) as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def client(self, mock_session):
        """Create GitHub client for testing."""
        return GitHubClient(token="test_token", owner="test_owner", repo="test_repo")

    def test_initialization_with_token(self):
        """Test client initialization with token."""
        client = GitHubClient(token="test_token", owner="test_owner", repo="test_repo")
        assert client.token == "test_token"
        assert client.owner == "test_owner"
        assert client.repo == "test_repo"

    @patch.dict("os.environ", {}, clear=True)
    @patch("roadmap.adapters.github.github.get_credential_manager")
    def test_initialization_without_token_raises_error(self, mock_credential_manager):
        """Test that missing token raises error."""
        # Mock credential manager to return None
        mock_credential_manager.return_value.get_token.return_value = None

        with pytest.raises(GitHubAPIError, match="GitHub token is required"):
            GitHubClient()

    @patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"})
    def test_initialization_with_env_token(self):
        """Test initialization with environment token."""
        client = GitHubClient(owner="test_owner", repo="test_repo")
        assert client.token == "env_token"

    def test_set_repository(self, client):
        """Test setting repository."""
        client.set_repository("new_owner", "new_repo")
        assert client.owner == "new_owner"
        assert client.repo == "new_repo"

    def test_check_repository_raises_error_when_not_set(self, client):
        """Test that missing repository raises error."""
        client.owner = None
        client.repo = None

        with pytest.raises(GitHubAPIError, match="Repository not set"):
            client._check_repository()

    def test_make_request_success(self, client, mock_session):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_session.request.return_value = mock_response

        response = client._make_request("GET", "/test")

        assert response == mock_response
        mock_session.request.assert_called_once_with(
            "GET", "https://api.github.com/test"
        )

    def test_make_request_401_error(self, client, mock_session):
        """Test 401 authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Authentication failed"):
            client._make_request("GET", "/test")

    def test_make_request_403_error(self, client, mock_session):
        """Test 403 forbidden error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Access forbidden"):
            client._make_request("GET", "/test")

    def test_make_request_404_error(self, client, mock_session):
        """Test 404 not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Repository or resource not found"):
            client._make_request("GET", "/test")

    def test_make_request_422_error(self, client, mock_session):
        """Test 422 validation error."""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_response.json.return_value = {"message": "Validation failed"}
        mock_response.content = b'{"message": "Validation failed"}'
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Validation error: Validation failed"):
            client._make_request("GET", "/test")

    def test_test_authentication(self, client, mock_session):
        """Test authentication testing."""
        mock_response = Mock()
        mock_response.json.return_value = {"login": "test_user"}
        mock_session.request.return_value = mock_response

        result = client.test_authentication()

        assert result == {"login": "test_user"}
        mock_session.request.assert_called_once_with(
            "GET", "https://api.github.com/user"
        )

    def test_test_repository_access(self, client, mock_session):
        """Test repository access testing."""
        mock_response = Mock()
        mock_response.json.return_value = {"full_name": "test_owner/test_repo"}
        mock_session.request.return_value = mock_response

        result = client.test_repository_access()

        assert result == {"full_name": "test_owner/test_repo"}
        mock_session.request.assert_called_once_with(
            "GET", "https://api.github.com/repos/test_owner/test_repo"
        )

    # Handler tests moved to handler-specific test files:
    # - test_github_issues_handler.py
    # - test_github_comments_handler.py
    # - test_github_labels_handler.py
    # - test_github_collaborators_handler.py
    # - test_github_milestones_handler.py


class TestGitHubClientErrorHandling:
    """Test error handling scenarios for GitHubClient."""

    @pytest.fixture
    def mock_session(self):
        """Mock requests session."""
        with patch(
            "roadmap.adapters.github.github.requests.Session"
        ) as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def client(self, mock_session):
        """Create GitHub client for testing."""
        return GitHubClient(token="test_token", owner="test_owner", repo="test_repo")

    def test_api_error_handling_401_unauthorized(self, client, mock_session):
        """Test handling of 401 unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Authentication failed"):
            client.test_authentication()

    def test_api_error_handling_403_forbidden(self, client, mock_session):
        """Test handling of 403 forbidden error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Access forbidden"):
            client.test_authentication()

    def test_api_error_handling_404_not_found(self, client, mock_session):
        """Test handling of 404 not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Repository or resource not found"):
            client.test_repository_access()

    def test_api_error_handling_500_server_error(self, client, mock_session):
        """Test handling of 500 server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="GitHub API error \\(500\\)"):
            client.test_authentication()

    def test_network_error_handling(self, client, mock_session):
        """Test handling of network errors."""
        mock_session.request.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(GitHubAPIError, match="Request failed"):
            client.test_authentication()

    def test_json_decode_error_handling(self, client, mock_session):
        """Test handling of 422 validation errors."""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_response.content = b'{"message": "Validation Failed"}'
        mock_response.json.return_value = {"message": "Validation Failed"}
        mock_session.request.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Validation error: Validation Failed"):
            client.test_authentication()

    def test_repository_validation_missing_owner(self, mock_session):
        """Test repository validation with missing owner."""
        client = GitHubClient(token="test_token", repo="test_repo")

        with pytest.raises(GitHubAPIError, match="Repository not set"):
            client._check_repository()

    def test_repository_validation_missing_repo(self, mock_session):
        """Test repository validation with missing repo."""
        client = GitHubClient(token="test_token", owner="test_owner")

        with pytest.raises(GitHubAPIError, match="Repository not set"):
            client._check_repository()


    # Handler error tests moved to handler-specific test files
    # (create_issue_with_api_error, update_issue_with_api_error, 
    #  delete_label_not_found, update_label_not_found)
