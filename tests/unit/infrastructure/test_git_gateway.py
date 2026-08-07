"""Tests for GitGateway adapter gateway.

Tests the gateway pattern for isolating core service access to git infrastructure.
"""

from pathlib import Path
from unittest.mock import Mock

from roadmap.infrastructure.git_gateway import GitGateway


class TestGitGateway:
    """Tests for GitGateway."""

    def test_get_git_integration_returns_git_integration_instance(self):
        """Test that get_git_integration returns a GitIntegration instance."""
        repo_path = Path("/tmp/test_repo")
        result = GitGateway.get_git_integration(repo_path=repo_path)

        # Should return a GitIntegration instance
        assert result is not None
        assert hasattr(result, "repo_path")
        assert result.repo_path == repo_path

    def test_get_git_integration_without_repo_path(self):
        """Test that get_git_integration works without repo_path."""
        result = GitGateway.get_git_integration()

        assert result is not None
        assert hasattr(result, "repo_path")

    def test_get_git_integration_with_config(self):
        """Test that get_git_integration accepts config parameter."""
        config = Mock()
        repo_path = Path("/tmp/test_repo")

        result = GitGateway.get_git_integration(repo_path=repo_path, config=config)

        assert result is not None
        assert result.repo_path == repo_path

    def test_get_git_integration_with_explicit_repo_path(self):
        """Test that explicit repo_path is used when provided."""
        repo_path = Path("/tmp/repo1")
        result = GitGateway.get_git_integration(repo_path=repo_path)

        assert result is not None
        assert result.repo_path == repo_path

    def test_get_git_integration_initializes_with_temp_path_when_none(self):
        """Test that GitIntegration handles None repo_path (creates temp path)."""
        result = GitGateway.get_git_integration(repo_path=None)

        # GitIntegration defaults to a temp path when None is passed
        assert result is not None
        assert result.repo_path is not None
