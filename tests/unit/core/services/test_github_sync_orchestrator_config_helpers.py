"""Tests for github_sync_orchestrator helper methods.

Tests the _get_owner_repo() helper method that was extracted to reduce
duplication in 6 refactored methods.
"""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.github_sync_orchestrator import GitHubSyncOrchestrator


class TestGetOwnerRepoHelper:
    """Test the _get_owner_repo() helper method."""

    @pytest.fixture
    def orchestrator(self):
        """Create a GitHubSyncOrchestrator with mocked GitHub client."""
        with patch("roadmap.core.services.github_sync_orchestrator.GitHubIssueClient"):
            mock_core = MagicMock()
            orchestrator = GitHubSyncOrchestrator(mock_core)
            return orchestrator

    def test_get_owner_repo_with_valid_config(self, orchestrator):
        """Test _get_owner_repo() returns owner and repo when config is valid."""
        orchestrator._config = {
            "github": {
                "owner": "test-owner",
                "repo": "test-repo",
            }
        }

        result = orchestrator._get_owner_repo()

        assert result is not None
        owner, repo = result
        assert owner == "test-owner"
        assert repo == "test-repo"

    def test_get_owner_repo_with_missing_owner(self, orchestrator):
        """Test _get_owner_repo() returns None when owner is missing."""
        orchestrator._config = {
            "github": {
                "repo": "test-repo",
            }
        }

        result = orchestrator._get_owner_repo()

        assert result is None

    def test_get_owner_repo_with_missing_repo(self, orchestrator):
        """Test _get_owner_repo() returns None when repo is missing."""
        orchestrator._config = {
            "github": {
                "owner": "test-owner",
            }
        }

        result = orchestrator._get_owner_repo()

        assert result is None

    def test_get_owner_repo_with_missing_github_section(self, orchestrator):
        """Test _get_owner_repo() returns None when github section is missing."""
        orchestrator._config = {}

        result = orchestrator._get_owner_repo()

        assert result is None

    def test_get_owner_repo_with_none_config(self, orchestrator):
        """Test _get_owner_repo() returns None when config is None."""
        orchestrator._config = None

        result = orchestrator._get_owner_repo()

        assert result is None

    def test_get_owner_repo_with_empty_owner(self, orchestrator):
        """Test _get_owner_repo() handles empty owner gracefully."""
        orchestrator._config = {
            "github": {
                "owner": "",
                "repo": "test-repo",
            }
        }

        result = orchestrator._get_owner_repo()

        # Empty string is still falsy, should return None
        assert result is None

    def test_get_owner_repo_with_empty_repo(self, orchestrator):
        """Test _get_owner_repo() handles empty repo gracefully."""
        orchestrator._config = {
            "github": {
                "owner": "test-owner",
                "repo": "",
            }
        }

        result = orchestrator._get_owner_repo()

        # Empty string is still falsy, should return None
        assert result is None
