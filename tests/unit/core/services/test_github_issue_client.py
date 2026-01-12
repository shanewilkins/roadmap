"""Tests for GitHub issue client service."""

import os
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.github.handlers.base import GitHubAPIError
from roadmap.core.services.github.github_issue_client import GitHubIssueClient


class TestGitHubIssueClientInitialization:
    """Tests for GitHubIssueClient initialization."""

    def test_init_with_provided_token(self):
        """Test initialization with explicitly provided token."""
        client = GitHubIssueClient(token="test_token_123")
        assert client.token == "test_token_123"

    def test_init_with_env_token(self):
        """Test initialization with token from environment variable."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_456"}):
            client = GitHubIssueClient()
            assert client.token == "env_token_456"

    def test_init_without_token_raises_error(self):
        """Test initialization without token raises GitHubAPIError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(GitHubAPIError, match="GitHub token is required"):
                GitHubIssueClient()

    def test_init_provided_token_takes_precedence(self):
        """Test that provided token takes precedence over environment."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            client = GitHubIssueClient(token="explicit_token")
            assert client.token == "explicit_token"


class TestFetchIssue:
    """Tests for fetch_issue method."""

    @pytest.fixture
    def client(self):
        """Create a GitHubIssueClient instance for testing."""
        return GitHubIssueClient(token="test_token")

    def test_fetch_issue_success(self, client):
        """Test successfully fetching a GitHub issue."""
        expected_data = {
            "number": 123,
            "title": "Test Issue",
            "body": "Issue description",
            "state": "open",
            "labels": ["bug", "urgent"],
            "assignees": ["user1", "user2"],
            "milestone": "v1.0",
            "url": "https://github.com/test/repo/issues/123",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-15T12:00:00Z",
        }

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.fetch_issue.return_value = expected_data
            mock_client.return_value = mock_instance

            result = client.fetch_issue("owner", "repo", 123)

            assert result == expected_data
            mock_client.assert_called_once_with(
                token="test_token", owner="owner", repo="repo"
            )
            mock_instance.fetch_issue.assert_called_once_with(123)

    def test_fetch_issue_not_found(self, client):
        """Test fetching a non-existent GitHub issue."""
        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.fetch_issue.side_effect = GitHubAPIError("Issue not found")
            mock_client.return_value = mock_instance

            with pytest.raises(GitHubAPIError, match="Issue not found"):
                client.fetch_issue("owner", "repo", 999)

    def test_fetch_issue_invalid_number(self, client):
        """Test fetching with invalid issue number."""
        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.fetch_issue.side_effect = ValueError(
                "Issue number must be positive"
            )
            mock_client.return_value = mock_instance

            with pytest.raises(ValueError):
                client.fetch_issue("owner", "repo", -1)

    def test_fetch_issue_api_error(self, client):
        """Test handling of GitHub API errors."""
        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.fetch_issue.side_effect = GitHubAPIError("Rate limited")
            mock_client.return_value = mock_instance

            with pytest.raises(GitHubAPIError):
                client.fetch_issue("owner", "repo", 123)


class TestValidateToken:
    """Tests for validate_token method."""

    @pytest.fixture
    def client(self):
        """Create a GitHubIssueClient instance for testing."""
        return GitHubIssueClient(token="test_token")

    def test_validate_token_success(self, client):
        """Test successful token validation."""
        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.validate_github_token.return_value = (
                True,
                "Token is valid (authenticated as testuser)",
            )
            mock_client.return_value = mock_instance

            is_valid, message = client.validate_token()

            assert is_valid
            assert "Token is valid" in message

    def test_validate_token_invalid(self, client):
        """Test invalid token validation."""
        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.validate_github_token.return_value = (
                False,
                "GitHub token is invalid or expired",
            )
            mock_client.return_value = mock_instance

            is_valid, message = client.validate_token()

            assert not is_valid
            assert "invalid" in message.lower()

    def test_validate_token_api_error(self, client):
        """Test handling of API errors during validation."""
        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.validate_github_token.side_effect = GitHubAPIError(
                "Connection error"
            )
            mock_client.return_value = mock_instance

            is_valid, message = client.validate_token()

            assert not is_valid
            assert "error" in message.lower()


class TestIssueExists:
    """Tests for issue_exists method."""

    @pytest.fixture
    def client(self):
        """Create a GitHubIssueClient instance for testing."""
        return GitHubIssueClient(token="test_token")

    def test_issue_exists_returns_true(self, client):
        """Test issue_exists returns True when issue exists."""
        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = {"number": 123, "title": "Test"}

            result = client.issue_exists("owner", "repo", 123)

            assert result
            mock_fetch.assert_called_once_with("owner", "repo", 123)

    def test_issue_exists_returns_false(self, client):
        """Test issue_exists returns False when issue doesn't exist."""
        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.side_effect = GitHubAPIError("Issue not found")

            result = client.issue_exists("owner", "repo", 999)

            assert not result


class TestGetIssueDiff:
    """Tests for get_issue_diff method."""

    @pytest.fixture
    def client(self):
        """Create a GitHubIssueClient instance for testing."""
        return GitHubIssueClient(token="test_token")

    @pytest.fixture
    def github_issue_data(self):
        """Sample GitHub issue data."""
        return {
            "number": 123,
            "title": "GitHub Title",
            "body": "GitHub description",
            "state": "open",
            "labels": ["bug", "urgent"],
            "assignees": ["user1", "user2"],
            "milestone": "v1.0",
            "url": "https://github.com/test/repo/issues/123",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-15T12:00:00Z",
        }

    def test_get_issue_diff_no_changes(self, client, github_issue_data):
        """Test diff when local and GitHub data are identical."""
        local_data = {
            "title": "GitHub Title",
            "body": "GitHub description",
            "state": "open",
            "labels": ["bug", "urgent"],
            "assignees": ["user1", "user2"],
        }

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_issue_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            assert not result["has_changes"]
            assert result["changes"] == {}
            assert result["github_data"] == github_issue_data

    def test_get_issue_diff_title_changed(self, client, github_issue_data):
        """Test diff when title has changed."""
        local_data = {
            "title": "Local Title",
            "body": "GitHub description",
            "state": "open",
            "labels": ["bug", "urgent"],
            "assignees": ["user1", "user2"],
        }

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_issue_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            assert result["has_changes"]
            assert "title" in result["changes"]
            assert result["changes"]["title"]["local"] == "Local Title"
            assert result["changes"]["title"]["github"] == "GitHub Title"
            assert result["changes"]["title"]["changed"]

    def test_get_issue_diff_labels_changed(self, client, github_issue_data):
        """Test diff when labels have changed."""
        local_data = {
            "title": "GitHub Title",
            "body": "GitHub description",
            "state": "open",
            "labels": ["bug", "enhancement"],  # Different from GitHub
            "assignees": ["user1", "user2"],
        }

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_issue_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            assert result["has_changes"]
            assert "labels" in result["changes"]
            assert set(result["changes"]["labels"]["local"]) == {"bug", "enhancement"}
            assert set(result["changes"]["labels"]["github"]) == {"bug", "urgent"}

    def test_get_issue_diff_multiple_changes(self, client, github_issue_data):
        """Test diff detects multiple field changes."""
        local_data = {
            "title": "Local Title",
            "body": "Local description",
            "state": "closed",
            "labels": ["feature"],
            "assignees": ["user3"],
        }

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_issue_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            assert result["has_changes"]
            assert len(result["changes"]) == 5  # All 5 fields changed

    def test_get_issue_diff_multiple_changes_includes_fields(
        self, client, github_issue_data
    ):
        """Test diff result includes all changed fields."""
        local_data = {
            "title": "Local Title",
            "body": "Local description",
            "state": "closed",
            "labels": ["feature"],
            "assignees": ["user3"],
        }

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_issue_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            assert "title" in result["changes"]
            assert "body" in result["changes"]
            assert "state" in result["changes"]
            assert "labels" in result["changes"]
            assert "assignees" in result["changes"]

    def test_get_issue_diff_empty_local_data(self, client, github_issue_data):
        """Test diff with minimal local data."""
        local_data = {}

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_issue_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            assert result["has_changes"]
            # Should detect changes in all fields
            assert len(result["changes"]) >= 1

    def test_get_issue_diff_api_error(self, client):
        """Test get_issue_diff handles API errors."""
        local_data = {"title": "Test"}

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.side_effect = GitHubAPIError("API error")

            with pytest.raises(GitHubAPIError):
                client.get_issue_diff("owner", "repo", 123, local_data)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def client(self):
        """Create a GitHubIssueClient instance for testing."""
        return GitHubIssueClient(token="test_token")

    def test_fetch_issue_with_empty_body(self, client):
        """Test fetching issue with empty body."""
        issue_data = {
            "number": 123,
            "title": "Title",
            "body": "",
            "state": "open",
            "labels": [],
            "assignees": [],
            "milestone": None,
            "url": "https://github.com/test/repo/issues/123",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.fetch_issue.return_value = issue_data
            mock_client.return_value = mock_instance

            result = client.fetch_issue("owner", "repo", 123)

            assert result["body"] == ""
            assert result["labels"] == []
            assert result["assignees"] == []

    def test_fetch_issue_with_unicode_characters(self, client):
        """Test fetching issue with unicode characters."""
        issue_data = {
            "number": 123,
            "title": "Bug: 日本語対応が必要 🐛",
            "body": "Description with émojis and spëcial çharacters",
            "state": "open",
            "labels": ["bug"],
            "assignees": ["user"],
            "milestone": None,
            "url": "https://github.com/test/repo/issues/123",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubClient"
        ) as mock_client:
            mock_instance = MagicMock()
            mock_instance.fetch_issue.return_value = issue_data
            mock_client.return_value = mock_instance

            result = client.fetch_issue("owner", "repo", 123)

            assert "日本語" in result["title"]
            assert "émojis" in result["body"]

    def test_diff_with_duplicate_labels(self, client):
        """Test diff correctly handles duplicate labels."""
        github_data = {
            "number": 123,
            "title": "Title",
            "body": "Body",
            "state": "open",
            "labels": ["bug", "bug", "urgent"],  # Duplicates
            "assignees": [],
            "milestone": None,
            "url": "https://github.com/test/repo/issues/123",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        local_data = {
            "title": "Title",
            "body": "Body",
            "state": "open",
            "labels": ["bug", "urgent"],  # No duplicates
            "assignees": [],
        }

        with patch.object(client, "fetch_issue") as mock_fetch:
            mock_fetch.return_value = github_data

            result = client.get_issue_diff("owner", "repo", 123, local_data)

            # Should be considered the same after deduplication
            assert not result["has_changes"]
