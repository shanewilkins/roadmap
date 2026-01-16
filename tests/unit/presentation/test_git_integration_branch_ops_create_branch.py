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
    CreateError,
)
from roadmap.infrastructure.git.git_integration_ops import GitIntegrationOps
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestCreateIssueWithGitBranch:
    """Test issue creation with optional git branch creation."""

    def test_create_issue_without_branch(self):
        """Test creating issue without creating a branch."""
        mock_git = Mock()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue()
        mock_core.issues.create.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.create_issue_with_git_branch(
            "Test Issue", auto_create_branch=False
        )

        assert result == mock_issue
        mock_core.issues.create.assert_called_once()
        mock_git.create_branch_for_issue.assert_not_called()

    def test_create_issue_with_branch_in_git_repo(self):
        """Test creating issue with branch in git repository."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue()
        mock_core.issues.create.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.create_issue_with_git_branch(
            "Test Issue", auto_create_branch=True, checkout_branch=True
        )

        assert result == mock_issue
        mock_git.create_branch_for_issue.assert_called_once_with(
            mock_issue, checkout=True
        )

    def test_create_issue_with_branch_not_in_git_repo(self):
        """Test creating issue with branch flag but not in git repo."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue()
        mock_core.issues.create.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.create_issue_with_git_branch("Test Issue", auto_create_branch=True)

        assert result == mock_issue
        mock_git.create_branch_for_issue.assert_not_called()

    def test_create_issue_fails(self):
        """Test when issue creation fails."""
        mock_git = Mock()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.create.return_value = None

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.create_issue_with_git_branch("Test Issue")

        assert result is None

    def test_create_issue_with_branch_creation_error(self):
        """Test when branch creation fails during issue creation."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.create_branch_for_issue.side_effect = Exception(
            "Branch creation failed"
        )
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue()
        mock_core.issues.create.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        with pytest.raises(CreateError):
            ops.create_issue_with_git_branch("Test Issue", auto_create_branch=True)

    def test_create_issue_with_extra_kwargs(self):
        """Test creating issue with additional parameters."""
        mock_git = Mock()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = TestDataFactory.create_mock_issue()
        mock_core.issues.create.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.create_issue_with_git_branch(
            "Test Issue",
            priority="high",
            assignee="user@example.com",
            auto_create_branch=False,
        )

        assert result == mock_issue
        # Verify auto_create_branch was not passed to core.issues.create
        call_kwargs = mock_core.issues.create.call_args[1]
        assert "auto_create_branch" not in call_kwargs


class TestSuggestBranchName:
    """Test branch name suggestion."""

    def test_suggest_branch_name_success(self):
        """Test successfully suggesting branch name."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.suggest_branch_name.return_value = "feature/issue-123"

        mock_issue = TestDataFactory.create_mock_issue()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.suggest_branch_name_for_issue("123")

        assert result == "feature/issue-123"

    def test_suggest_branch_name_not_in_repo(self):
        """Test suggesting branch name when not in repo."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False

        mock_issue = TestDataFactory.create_mock_issue()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = mock_issue

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.suggest_branch_name_for_issue("123")

        assert result is None

    def test_suggest_branch_name_issue_not_found(self):
        """Test suggesting branch name for nonexistent issue."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = None

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.suggest_branch_name_for_issue("999")

        assert result is None


class TestGetBranchLinkedIssues:
    """Test getting mapping of branches to linked issues."""

    def test_get_branch_linked_issues_success(self):
        """Test successfully getting branch-issue mapping."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        mock_branch1 = Mock()
        mock_branch1.name = "feature/issue-123"
        mock_branch1.extract_issue_id.return_value = "123"

        mock_branch2 = Mock()
        mock_branch2.name = "feature/issue-456"
        mock_branch2.extract_issue_id.return_value = "456"

        mock_git.get_all_branches.return_value = [mock_branch1, mock_branch2]

        mock_issue1 = Mock()
        mock_issue2 = Mock()
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.side_effect = [mock_issue1, mock_issue2]

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.get_branch_linked_issues()

        assert "feature/issue-123" in result
        assert "feature/issue-456" in result
        assert result["feature/issue-123"] == ["123"]

    def test_get_branch_linked_issues_not_in_repo(self):
        """Test getting branch-issue mapping when not in repo."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = False

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_branch_linked_issues()

        assert result == {}

    def test_get_branch_linked_issues_no_issue_ids(self):
        """Test getting mapping when branches have no issue IDs."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        mock_branch = Mock()
        mock_branch.name = "main"
        mock_branch.extract_issue_id.return_value = None

        mock_git.get_all_branches.return_value = [mock_branch]

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_branch_linked_issues()

        assert result == {}

    def test_get_branch_linked_issues_missing_issue(self):
        """Test getting mapping with branch pointing to nonexistent issue."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        mock_branch = Mock()
        mock_branch.name = "feature/issue-999"
        mock_branch.extract_issue_id.return_value = "999"

        mock_git.get_all_branches.return_value = [mock_branch]

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get.return_value = None

        ops = GitIntegrationOps(mock_git, mock_core)

        result = ops.get_branch_linked_issues()

        assert "feature/issue-999" not in result

    def test_get_branch_linked_issues_empty_branches(self):
        """Test getting mapping when repository has no branches."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_all_branches.return_value = []

        ops = GitIntegrationOps(mock_git, Mock())

        result = ops.get_branch_linked_issues()

        assert result == {}


class TestGitIntegrationOpsIntegration:
    """Test integration scenarios combining multiple operations."""

    def test_full_workflow_create_link_update(self):
        """Test complete workflow: create issue, link to branch, update from commits."""
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True
        mock_git.get_repository_info.return_value = {}

        mock_branch = Mock()
        mock_branch.name = "feature/new-issue"
        mock_branch.extract_issue_id.return_value = "123"
        mock_git.get_current_branch.return_value = mock_branch
        mock_git.create_branch_for_issue.return_value = True

        mock_issue = TestDataFactory.create_mock_issue()
        mock_issue.id = "123"
        mock_issue.git_branches = []

        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.create.return_value = mock_issue
        mock_core.issues.get.return_value = mock_issue
        mock_core.issues.update.return_value = mock_issue

        mock_git.get_commits_for_issue.return_value = [{"hash": "abc123"}]
        mock_git.parse_commit_message_for_updates.return_value = {
            "status": "in_progress"
        }

        ops = GitIntegrationOps(mock_git, mock_core)

        # Create issue
        issue = ops.create_issue_with_git_branch("New Feature", auto_create_branch=True)
        assert issue is not None

        # Link to branch
        linked = ops.link_issue_to_current_branch("123")
        assert linked is True

        # Update from commits
        updated = ops.update_issue_from_git_activity("123")
        assert updated is True
