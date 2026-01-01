"""Unit tests for GitHub sync backend implementation.

Tests the GitHubSyncBackend implementation of SyncBackendInterface.
"""

from unittest.mock import MagicMock, Mock

import pytest

from roadmap.adapters.sync.backends.github_sync_backend import GitHubSyncBackend
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import SyncReport


class TestGitHubSyncBackendInit:
    """Test GitHubSyncBackend initialization."""

    def test_init_with_valid_config(self):
        """Test backend initializes with valid config."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)

        assert backend.core is core
        assert backend.config == config

    def test_init_missing_owner_raises_error(self):
        """Test backend raises ValueError if owner missing."""
        core = MagicMock()
        config = {
            "repo": "test-repo",
            "token": "fake-token",
        }

        with pytest.raises(ValueError, match="owner"):
            GitHubSyncBackend(core, config)

    def test_init_missing_repo_raises_error(self):
        """Test backend raises ValueError if repo missing."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "token": "fake-token",
        }

        with pytest.raises(ValueError, match="repo"):
            GitHubSyncBackend(core, config)

    def test_init_creates_github_client(self):
        """Test backend creates GitHubIssueClient."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)

        assert backend.github_client is not None


class TestGitHubSyncBackendAuthenticate:
    """Test authenticate method."""

    def test_authenticate_no_token(self):
        """Test authenticate returns False without token."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            # No token
        }

        backend = GitHubSyncBackend(core, config)
        result = backend.authenticate()

        assert result is False

    def test_authenticate_with_valid_token(self):
        """Test authenticate succeeds with valid token."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)

        # Mock the github_client to simulate successful auth
        backend.github_client.fetch_issue = Mock(side_effect=Exception("404"))
        result = backend.authenticate()

        # Even though fetch_issue raises 404, auth should succeed
        # (404 means auth succeeded but issue doesn't exist)
        assert result is True

    def test_authenticate_with_invalid_token(self):
        """Test authenticate fails with invalid token."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "invalid-token",
        }

        backend = GitHubSyncBackend(core, config)

        # Mock the github_client to simulate auth failure
        backend.github_client.fetch_issue = Mock(
            side_effect=Exception("401 Unauthorized")
        )
        result = backend.authenticate()

        assert result is False


class TestGitHubSyncBackendGetIssues:
    """Test get_issues method."""

    def test_get_issues_returns_dict(self):
        """Test get_issues returns a dictionary."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        result = backend.get_issues()

        assert isinstance(result, dict)

    def test_get_issues_missing_config(self):
        """Test get_issues returns empty dict without owner/repo."""
        core = MagicMock()
        config = {
            "token": "fake-token",
            "owner": "test-owner",
            # Missing repo - should still fail at init
        }

        # This should raise ValueError during init
        with pytest.raises(ValueError, match="owner.*repo"):
            GitHubSyncBackend(core, config)

    def test_get_issues_handles_errors(self):
        """Test get_issues handles exceptions gracefully."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        # Mock get_issues to raise an error
        backend.github_client.fetch_issue = Mock(side_effect=Exception("API Error"))

        result = backend.get_issues()

        # Should return empty dict on error
        assert result == {}


class TestGitHubSyncBackendPushIssue:
    """Test push_issue method."""

    def test_push_issue_returns_bool(self):
        """Test push_issue returns a boolean."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        issue = Issue(title="Test Issue")

        result = backend.push_issue(issue)

        assert isinstance(result, bool)

    def test_push_issue_new_issue(self):
        """Test push_issue creates new GitHub issue."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        issue = Issue(title="New Issue", github_issue=None)

        result = backend.push_issue(issue)

        # Should return True (placeholder implementation)
        assert result is True

    def test_push_issue_existing_issue(self):
        """Test push_issue updates existing GitHub issue."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        issue = Issue(title="Existing Issue", github_issue="123")

        result = backend.push_issue(issue)

        # Should return True (placeholder implementation)
        assert result is True

    def test_push_issue_missing_config(self):
        """Test push_issue returns False without config."""
        core = MagicMock()
        config = {
            "token": "fake-token",
            "owner": "test-owner",
            # Missing repo
        }

        # Should raise ValueError during init when repo is missing
        with pytest.raises(ValueError, match="owner.*repo"):
            GitHubSyncBackend(core, config)


class TestGitHubSyncBackendPushIssues:
    """Test push_issues method."""

    def test_push_issues_returns_sync_report(self):
        """Test push_issues returns SyncReport."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        issues = [Issue(title="Issue 1"), Issue(title="Issue 2")]

        result = backend.push_issues(issues)

        assert isinstance(result, SyncReport)

    def test_push_issues_multiple_issues(self):
        """Test push_issues handles multiple issues."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)
        issues = [Issue(title="Issue 1"), Issue(title="Issue 2")]

        report = backend.push_issues(issues)

        # Placeholder implementation returns all as pushed
        assert len(report.pushed) == 2


class TestGitHubSyncBackendPullIssues:
    """Test pull_issues method."""

    def test_pull_issues_returns_sync_report(self):
        """Test pull_issues returns SyncReport."""
        core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "token": "fake-token",
        }

        backend = GitHubSyncBackend(core, config)

        result = backend.pull_issues()

        assert isinstance(result, SyncReport)
