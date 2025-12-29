"""Error path tests for git_integration_ops module.

Tests focus on error handling, edge cases, and failure scenarios in the
GitIntegrationOps class which handles all git-related operations including
branch management, commit tracking, and linking issues to branches.

Tier 2 test coverage module addressing:
- Git repository errors and unavailable repositories
- Branch operation failures
- Issue-branch linking errors
- Commit tracking and parsing errors
- Invalid data handling
- Missing dependencies and integration failures
"""

from unittest.mock import Mock

import pytest

from roadmap.common.errors.exceptions import (
    GitError,
)
from roadmap.infrastructure.git_integration_ops import GitIntegrationOps
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestGitIntegrationOpsInitialization:
    """Test GitIntegrationOps initialization and dependency injection."""

    @pytest.mark.parametrize(
        "git,core,expected_git,expected_core",
        [
            (Mock(), TestDataFactory.create_mock_core(is_initialized=True), True, True),
            (None, TestDataFactory.create_mock_core(is_initialized=True), False, True),
            (Mock(), None, True, False),
        ],
    )
    def test_init_various(self, git, core, expected_git, expected_core):
        ops = GitIntegrationOps(git, core)
        assert (ops.git is not None) == expected_git
        assert (ops.core is not None) == expected_core

    def test_init_preserves_references(self):
        mock_git = Mock()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        ops = GitIntegrationOps(mock_git, mock_core)
        assert ops.git is mock_git
        assert ops.core is mock_core


class TestGetGitContext:
    """Test git context retrieval with various error scenarios."""

    def test_get_git_context_not_git_repository(self):
        """Test getting context when not in a git repository."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_git_context()

        assert result == {"is_git_repo": False}
        mock_git.is_git_repository.assert_called_once()

    def test_get_git_context_with_valid_repository(self):
        """Test getting context from valid git repository."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_repository_info.return_value = {"remote": "origin"}

        mock_branch = Mock()
        mock_branch.name = "main"
        mock_branch.extract_issue_id.return_value = None
        mock_git.get_current_branch.return_value = mock_branch

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_git_context()

        assert result["is_git_repo"] is True
        assert result["remote"] == "origin"
        assert result["current_branch"] == "main"

    def test_get_git_context_with_linked_issue(self):
        """Test getting context with linked issue in branch name."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_repository_info.return_value = {}

        mock_branch = Mock()
        mock_branch.name = "feature/issue-123"
        mock_branch.extract_issue_id.return_value = "123"
        mock_git.get_current_branch.return_value = mock_branch

        # Create mock issue and core
        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.id = "123"
        mock_issue.title = "Test Issue"
        mock_status = Mock()
        mock_status.value = "open"
        mock_issue.status = mock_status
        mock_priority = Mock()
        mock_priority.value = "high"
        mock_issue.priority = mock_priority

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.get_git_context()

        assert result["linked_issue"]["id"] == "123"
        assert result["linked_issue"]["title"] == "Test Issue"

    def test_get_git_context_repository_info_error(self):
        """Test get_git_context when get_repository_info fails."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_repository_info.side_effect = Exception("Git error")

        ops = GitIntegrationOps(
            mock_git, TestDataFactory.create_mock_core(is_initialized=True)
        )

        # safe_operation wraps as GitError for READ operations on GitRepository
        with pytest.raises((Exception, GitError)):
            ops.get_git_context()

    def test_get_git_context_with_no_current_branch(self):
        """Test getting context when there's no current branch."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_repository_info.return_value = {}
        mock_git.get_current_branch.return_value = None

        ops = GitIntegrationOps(
            mock_git, TestDataFactory.create_mock_core(is_initialized=True)
        )

        result = ops.get_git_context()

        assert "current_branch" not in result

    def test_get_git_context_with_missing_issue(self):
        """Test getting context when linked issue doesn't exist."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_repository_info.return_value = {}

        mock_branch = Mock()
        mock_branch.name = "feature/issue-999"
        mock_branch.extract_issue_id.return_value = "999"
        mock_git.get_current_branch.return_value = mock_branch

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = None

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.get_git_context()

        assert "linked_issue" not in result


class TestGetCurrentUserFromGit:
    """Test git user retrieval with various error scenarios."""

    def test_get_current_user_success(self):
        """Test successfully getting current git user."""
        mock_git = Mock()
        mock_git.get_current_user.return_value = "John Doe"

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_current_user_from_git()

        assert result == "John Doe"

    def test_get_current_user_not_configured(self):
        """Test when git user is not configured."""
        mock_git = Mock()
        mock_git.get_current_user.return_value = None

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_current_user_from_git()

        assert result is None

    def test_get_current_user_git_error(self):
        """Test when git command fails."""
        mock_git = Mock()
        mock_git.get_current_user.side_effect = Exception("Git config error")

        ops = GitIntegrationOps(mock_git, Mock())

        # safe_operation wraps as GitError for READ operations
        with pytest.raises((Exception, GitError)):
            ops.get_current_user_from_git()

    def test_get_current_user_with_special_characters(self):
        """Test user with special characters in name."""
        mock_git = Mock()
        mock_git.get_current_user.return_value = "José García López"

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_current_user_from_git()

        assert result == "José García López"
