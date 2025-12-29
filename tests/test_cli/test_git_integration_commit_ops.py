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
    UpdateError,
)
from roadmap.infrastructure.git_integration_ops import GitIntegrationOps
from tests.unit.domain.test_data_factory import TestDataFactory


class TestLinkIssueToBranch:
    """Test linking issues to git branches with error handling."""

    def test_link_issue_to_current_branch_success(self):
        """Test successfully linking issue to current branch."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_branch = Mock()
        mock_branch.name = "feature/issue-123"
        mock_git.get_current_branch.return_value = mock_branch

        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.git_branches = []
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = mock_issue
        mock_core.issues.update.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.link_issue_to_current_branch("123")

        assert result is True
        mock_core.issues.update.assert_called_once()

    def test_link_issue_not_in_git_repo(self):
        """Test linking issue when not in git repository."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.link_issue_to_current_branch("123")

        assert result is False
        mock_git.get_current_branch.assert_not_called()

    def test_link_issue_no_current_branch(self):
        """Test linking issue when there's no current branch."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_current_branch.return_value = None

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.link_issue_to_current_branch("123")

        assert result is False

    def test_link_nonexistent_issue(self):
        """Test linking nonexistent issue."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_branch = Mock()
        mock_git.get_current_branch.return_value = mock_branch

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = None

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.link_issue_to_current_branch("999")

        assert result is False

    def test_link_issue_already_linked(self):
        """Test linking issue that's already linked to branch."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_branch = Mock()
        mock_branch.name = "feature/issue-123"
        mock_git.get_current_branch.return_value = mock_branch

        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.git_branches = ["feature/issue-123"]
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = mock_issue
        mock_core.issues.update.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.link_issue_to_current_branch("123")

        assert result is True
        # Should still call update (branch list unchanged)
        mock_core.issues.update.assert_called_once()

    def test_link_issue_update_fails(self):
        """Test when issue update fails during linking."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_branch = Mock()
        mock_branch.name = "feature/issue-123"
        mock_git.get_current_branch.return_value = mock_branch

        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.git_branches = []
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = mock_issue
        mock_core.issues.update.return_value = None

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.link_issue_to_current_branch("123")

        assert result is False


class TestGetCommitsForIssue:
    """Test retrieving commits for an issue."""

    def test_get_commits_for_issue_success(self):
        """Test successfully getting commits for issue."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_commits = [{"hash": "abc123", "message": "Fix issue #123"}]
        mock_git.get_commits_for_issue.return_value = mock_commits

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_commits_for_issue("123")

        assert result == mock_commits
        mock_git.get_commits_for_issue.assert_called_once_with("123", None)

    def test_get_commits_for_issue_not_git_repo(self):
        """Test getting commits when not in git repository."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_commits_for_issue("123")

        assert result == []

    def test_get_commits_for_issue_with_date_filter(self):
        """Test getting commits with date filter."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_commits = [{"hash": "abc123"}]
        mock_git.get_commits_for_issue.return_value = mock_commits

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_commits_for_issue("123", since="2024-01-01")

        assert result == mock_commits
        mock_git.get_commits_for_issue.assert_called_once_with("123", "2024-01-01")

    def test_get_commits_git_error(self):
        """Test when git command fails."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_commits_for_issue.side_effect = Exception("Git error")

        ops = GitIntegrationOps(mock_git, Mock())

        # safe_operation wraps as GitError for READ operations
        with pytest.raises((Exception, GitError)):
            ops.get_commits_for_issue("123")

    def test_get_commits_empty_list(self):
        """Test when no commits found for issue."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_commits_for_issue.return_value = []

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_commits_for_issue("999")

        assert result == []


class TestUpdateIssueFromGitActivity:
    """Test updating issue based on git activity."""

    def test_update_issue_from_git_activity_success(self):
        """Test successfully updating issue from git activity."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_commits = [{"hash": "abc123", "message": "WIP: #123"}]
        mock_git.get_commits_for_issue.return_value = mock_commits
        mock_git.parse_commit_message_for_updates.return_value = {
            "status": "in_progress"
        }

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.update.return_value = Mock()

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.update_issue_from_git_activity("123")

        assert result is True
        mock_core.issues.update.assert_called_once()

    def test_update_issue_not_in_git_repo(self):
        """Test updating issue when not in git repository."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.update_issue_from_git_activity("123")

        assert result is False

    def test_update_issue_no_commits(self):
        """Test updating issue with no related commits."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_commits_for_issue.return_value = []

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.update_issue_from_git_activity("123")

        assert result is False

    def test_update_issue_no_updates_in_commits(self):
        """Test updating issue when commits have no roadmap updates."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_commits = [{"hash": "abc123", "message": "Refactor code"}]
        mock_git.get_commits_for_issue.return_value = mock_commits
        mock_git.parse_commit_message_for_updates.return_value = {}

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.update_issue_from_git_activity("123")

        assert result is False

    def test_update_issue_with_multiple_commits(self):
        """Test updating issue with multiple relevant commits."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_commits = [
            {"hash": "abc123", "message": "Start work on #123"},
            {"hash": "def456", "message": "Complete #123"},
        ]
        mock_git.get_commits_for_issue.return_value = mock_commits
        mock_git.parse_commit_message_for_updates.side_effect = [
            {"status": "in_progress"},
            {"status": "done"},
        ]

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.update.return_value = Mock()

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.update_issue_from_git_activity("123")

        assert result is True
        # Verify the latest update was used
        call_kwargs = mock_core.issues.update.call_args[1]
        assert call_kwargs["status"] == "done"

    def test_update_issue_update_fails(self):
        """Test when issue update fails."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_commits = [{"hash": "abc123"}]
        mock_git.get_commits_for_issue.return_value = mock_commits
        mock_git.parse_commit_message_for_updates.return_value = {"status": "done"}

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.update.side_effect = Exception("Update failed")

        ops = GitIntegrationOps(mock_git, mock_core)

        with pytest.raises(UpdateError):
            ops.update_issue_from_git_activity("123")
